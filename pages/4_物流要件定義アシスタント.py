"""物流 要件定義アシスタント

物流センター立ち上げプロジェクトの現場ヒアリングメモ（日英混在）から、
議事録（日・英）、業務要件一覧、課題管理表、ベンダーへの確認事項（英語）、To-Be業務フロー図を作る。
"""
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from common.llm import ask, is_demo
from common.ui import hero, note, section, setup

SAMPLE = Path(__file__).parent.parent / "data" / "logistics" / "ヒアリングメモ_定例3.txt"
PROCESSES = ["入荷", "保管", "ピッキング", "出荷", "在庫管理", "返品", "その他"]
LANES = ["現場作業者", "WMS", "自動倉庫(AS/RS)", "取引先・外部"]

SYSTEM = f"""あなたは物流センター立ち上げプロジェクトのPMO兼要件定義コンサルタントです。
現場ヒアリングのメモ（日本語・英語が混在）を読み、業務部門とシステム設計チームの橋渡しとなる資料を作ってください。
- requirements: 業務要件。process は {" / ".join(PROCESSES)} のいずれか。as_is（現状）と to_be（あるべき姿）を対比し、
  requirement はシステムに求める機能として具体的に書く。priority は Must / Should / Could。ID は REQ-001 から連番
- issues: 未決事項・宿題・リスク。期限や担当がメモに無ければ「要調整」とする。ID は ISS-001 から連番
- vendor_questions_en: マテハンベンダー・設計チームに英語で確認すべき質問
- flow_steps / flow_edges: 入荷から出荷までの To-Be 業務フロー。lane は {" / ".join(LANES)} のいずれか
- メモに無いことは推測で書かない"""

SCHEMA = {
    "type": "object",
    "properties": {
        "summary_ja": {"type": "string"},
        "summary_en": {"type": "string"},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "requirements": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"}, "process": {"type": "string", "enum": PROCESSES},
                "as_is": {"type": "string"}, "to_be": {"type": "string"}, "requirement": {"type": "string"},
                "priority": {"type": "string", "enum": ["Must", "Should", "Could"]},
            },
            "required": ["id", "process", "as_is", "to_be", "requirement", "priority"],
            "additionalProperties": False}},
        "issues": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "issue": {"type": "string"},
                           "owner": {"type": "string"}, "due": {"type": "string"}},
            "required": ["id", "issue", "owner", "due"], "additionalProperties": False}},
        "vendor_questions_en": {"type": "array", "items": {"type": "string"}},
        "flow_steps": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "label": {"type": "string"},
                           "lane": {"type": "string", "enum": LANES}},
            "required": ["id", "label", "lane"], "additionalProperties": False}},
        "flow_edges": {"type": "array", "items": {
            "type": "object",
            "properties": {"src": {"type": "string"}, "dst": {"type": "string"}},
            "required": ["src", "dst"], "additionalProperties": False}},
    },
    "required": ["summary_ja", "summary_en", "decisions", "requirements", "issues",
                 "vendor_questions_en", "flow_steps", "flow_edges"],
    "additionalProperties": False,
}

DEMO_RESULT = {
    "summary_ja": "新DCの入荷・保管・ピッキング・在庫管理について現場の課題を確認した。ASNのEDI受信と、温度管理品を自動倉庫の対象外とする方針が決定。自動倉庫のポート数はピーク出荷量のデータを待って決める。",
    "summary_en": "We reviewed current operational issues in receiving, storage, picking and inventory control for the new DC. It was agreed that ASNs will be received via EDI and that temperature-controlled items will be excluded from the AS/RS. The number of AS/RS ports will be decided once peak shipment data is available.",
    "decisions": ["ASN（事前出荷通知）はEDIで受信する前提で進める",
                  "温度管理品は自動倉庫の対象外とし、別ゾーンで管理する",
                  "次回までに過去1年分の日別出荷データを準備する（高橋）"],
    "requirements": [
        {"id": "REQ-001", "process": "入荷", "as_is": "紙の入荷予定表を見ながら検品", "to_be": "ASNを取り込み、予定と実績を自動照合",
         "requirement": "EDIで受信したASNをWMSに取り込み、入荷予定として表示できること", "priority": "Must"},
        {"id": "REQ-002", "process": "入荷", "as_is": "ケース入荷でもピース数を手入力", "to_be": "ケースのコードを読むと入数を自動計算",
         "requirement": "ITFコードのスキャンで商品マスタの入数からピース数を自動算出できること", "priority": "Must"},
        {"id": "REQ-003", "process": "入荷", "as_is": "賞味期限・ロットをExcelに手入力", "to_be": "入荷時に期限・ロットをシステム登録",
         "requirement": "対象商品（医薬品・サプリ等）の入荷時に賞味期限・ロット番号を必須入力にできること", "priority": "Must"},
        {"id": "REQ-004", "process": "保管", "as_is": "温度管理品も通常品と同じ扱い", "to_be": "温度管理品は専用ゾーンで保管",
         "requirement": "商品マスタに温度区分を持ち、自動倉庫に入れない商品を別ロケーションへ自動で割り当てられること", "priority": "Must"},
        {"id": "REQ-005", "process": "ピッキング", "as_is": "印刷リストで人が歩いて集品、ミス月30件", "to_be": "GTP方式で作業者の前に棚が届く",
         "requirement": "店舗別オーダーを自動倉庫へ連携し、GTPステーションで画面指示に従って集品できること", "priority": "Must"},
        {"id": "REQ-006", "process": "出荷", "as_is": "目視で検品", "to_be": "スキャンで自動照合",
         "requirement": "出荷検品時にスキャンでオーダーと照合し、不一致時は警告を出せること", "priority": "Must"},
        {"id": "REQ-007", "process": "出荷", "as_is": "トラック遅延で積み込みが夜まで続く", "to_be": "車両の到着状況に合わせて出荷順を調整",
         "requirement": "出荷締め（15時）と車両の到着予定から、方面別の出荷優先順位を表示できること", "priority": "Should"},
        {"id": "REQ-008", "process": "在庫管理", "as_is": "年2回、2日間センターを止めて棚卸", "to_be": "稼働しながら循環棚卸",
         "requirement": "ロケーション単位の循環棚卸指示と、差異の承認ワークフローを持つこと", "priority": "Should"},
        {"id": "REQ-009", "process": "在庫管理", "as_is": "WMSと会計の在庫が合わない", "to_be": "日次で差異を検知",
         "requirement": "WMSと基幹（会計）システムの在庫を日次で突き合わせ、差異レポートを出力できること", "priority": "Could"},
    ],
    "issues": [
        {"id": "ISS-001", "issue": "自動倉庫のポート数の決定（ピーク出荷量のデータが必要）", "owner": "Lee / 高橋", "due": "次回定例"},
        {"id": "ISS-002", "issue": "過去1年分の日別出荷データの準備", "owner": "高橋", "due": "次回定例"},
        {"id": "ISS-003", "issue": "返品の受け入れフローが未検討", "owner": "要調整", "due": "要調整"},
        {"id": "ISS-004", "issue": "既存WMSの改修か新WMS導入かの比較資料の作成", "owner": "Lee", "due": "10/29"},
        {"id": "ISS-005", "issue": "温度管理品ゾーンの面積・設備要件の確認", "owner": "要調整", "due": "要調整"},
    ],
    "vendor_questions_en": [
        "Given a peak volume of roughly 3x the normal daily shipments, how many AS/RS ports would you recommend, and what throughput margin should we plan for?",
        "Can the AS/RS controller receive store-level orders from the WMS in real time, and which interface (API, file transfer, etc.) do you support?",
        "Is there any way to accommodate temperature-controlled items near the AS/RS area, or should they be handled in a completely separate zone?",
        "During system maintenance or failure of the AS/RS, what is the recommended fallback operation for picking?",
    ],
    "flow_steps": [
        {"id": "s1", "label": "ASN送信（EDI）", "lane": "取引先・外部"},
        {"id": "s2", "label": "入荷予定の取込", "lane": "WMS"},
        {"id": "s3", "label": "入荷検品\n（ITFスキャン・期限登録）", "lane": "現場作業者"},
        {"id": "s4", "label": "温度区分の判定\nロケーション割当", "lane": "WMS"},
        {"id": "s5", "label": "自動倉庫へ格納", "lane": "自動倉庫(AS/RS)"},
        {"id": "s6", "label": "温度管理ゾーンへ格納", "lane": "現場作業者"},
        {"id": "s7", "label": "店舗別オーダー連携", "lane": "WMS"},
        {"id": "s8", "label": "GTPステーションへ出庫", "lane": "自動倉庫(AS/RS)"},
        {"id": "s9", "label": "画面指示で集品\nスキャン検品", "lane": "現場作業者"},
        {"id": "s10", "label": "方面別に出荷", "lane": "現場作業者"},
    ],
    "flow_edges": [
        {"src": "s1", "dst": "s2"}, {"src": "s2", "dst": "s3"}, {"src": "s3", "dst": "s4"},
        {"src": "s4", "dst": "s5"}, {"src": "s4", "dst": "s6"}, {"src": "s5", "dst": "s7"},
        {"src": "s6", "dst": "s7"}, {"src": "s7", "dst": "s8"}, {"src": "s8", "dst": "s9"}, {"src": "s9", "dst": "s10"},
    ],
}

LANE_COLORS = {"現場作業者": "#FEF3C7", "WMS": "#DBEAFE", "自動倉庫(AS/RS)": "#D1FAE5", "取引先・外部": "#EDE9FE"}


def to_dot(r: dict) -> str:
    """フロー情報から Graphviz の図を作る（担当ごとに色分け）"""
    lines = ['digraph G {', 'rankdir=TB; nodesep=0.5; ranksep=0.28; bgcolor="transparent";',
             'node [shape=box, style="rounded,filled", fontname="Noto Sans JP", fontsize=11, '
             'color="#CBD5E1", penwidth=1, margin="0.18,0.1"];',
             'edge [color="#94A3B8", arrowsize=0.6, penwidth=1.2];']
    for s in r["flow_steps"]:
        label = s["label"].replace('"', "'").replace("\n", "\\n")
        lines.append(f'"{s["id"]}" [label="{label}", fillcolor="{LANE_COLORS.get(s["lane"], "#F1F5F9")}"];')
    for e in r["flow_edges"]:
        lines.append(f'"{e["src"]}" -> "{e["dst"]}";')
    lines.append("}")
    return "\n".join(lines)


setup("物流 要件定義アシスタント")
DEMO = is_demo()
hero("DEMO 04 · 物流・PMO", "物流 要件定義アシスタント",
     "物流センター立ち上げの現場ヒアリングメモ（日英混在）から、<b>議事録（日・英）</b>・<b>業務要件一覧</b>・"
     "<b>課題管理表</b>・<b>ベンダー確認事項（英語）</b>・<b>To-Be業務フロー図</b>をまとめて作成します。",
     ["要件定義", "As-Is / To-Be", "課題管理", "日英バイリンガル", "業務フロー図"])

memo = st.text_area("ヒアリングメモ・議事メモ（そのまま貼り付けてOK）", SAMPLE.read_text(encoding="utf-8"), height=260)

if st.button("資料を作成する", type="primary"):
    if DEMO:
        if memo.strip() != SAMPLE.read_text(encoding="utf-8").strip():
            st.warning("デモモードでは、サンプルのメモに対する結果を表示します。")
        st.session_state.req = DEMO_RESULT
    else:
        with st.spinner("要件と課題を整理しています..."):
            st.session_state.req = ask(SYSTEM, memo, schema=SCHEMA, effort="medium")

if r := st.session_state.get("req"):
    reqs = pd.DataFrame(r["requirements"])
    issues = pd.DataFrame(r["issues"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("業務要件", f"{len(reqs)}件")
    c2.metric("うち Must", f"{(reqs.priority == 'Must').sum()}件")
    c3.metric("課題・宿題", f"{len(issues)}件")
    c4.metric("ベンダー確認", f"{len(r['vendor_questions_en'])}件")

    tab1, tab2, tab3, tab4 = st.tabs(["議事録（日・英）", "業務要件一覧", "課題管理表", "To-Be 業務フロー"])
    with tab1:
        ja, en = st.columns(2)
        with ja:
            section("サマリー")
            st.write(r["summary_ja"])
            section("決定事項")
            for d in r["decisions"]:
                st.markdown(f"- {d}")
        with en:
            section("Summary (EN)")
            st.write(r["summary_en"])
            section("Questions to vendor / design team")
            for q in r["vendor_questions_en"]:
                st.markdown(f"- {q}")
    with tab2:
        process = st.multiselect("工程で絞り込み", PROCESSES, default=[p for p in PROCESSES if p in set(reqs.process)])
        st.dataframe(reqs[reqs.process.isin(process)].rename(columns={
            "id": "ID", "process": "工程", "as_is": "現状（As-Is）", "to_be": "あるべき姿（To-Be）",
            "requirement": "システム要件", "priority": "優先度"}), width="stretch", hide_index=True)
    with tab3:
        st.dataframe(issues.rename(columns={"id": "ID", "issue": "課題・宿題", "owner": "担当", "due": "期限"}),
                     width="stretch", hide_index=True)
    with tab4:
        st.graphviz_chart(to_dot(r))
        st.markdown(" ".join(f'<span class="tag" style="background:{c};color:#334155">{l}</span>' for l, c in LANE_COLORS.items()), unsafe_allow_html=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame({"項目": ["サマリー", "Summary (EN)"] + ["決定事項"] * len(r["decisions"]),
                      "内容": [r["summary_ja"], r["summary_en"]] + r["decisions"]}).to_excel(writer, sheet_name="議事録", index=False)
        reqs.to_excel(writer, sheet_name="業務要件一覧", index=False)
        issues.to_excel(writer, sheet_name="課題管理表", index=False)
        pd.DataFrame({"Questions": r["vendor_questions_en"]}).to_excel(writer, sheet_name="Vendor Q&A", index=False)
    st.download_button("Excelで一括ダウンロード", buf.getvalue(), "要件定義資料.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

note("※ ヒアリングメモ・人物・数値はすべてデモ用に作成した架空のものです。")
