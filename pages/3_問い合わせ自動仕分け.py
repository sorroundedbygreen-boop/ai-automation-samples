"""問い合わせ自動仕分け（分類 + 優先度付け + 返信下書き）

問い合わせメールを1件ずつ AI で分類し、担当部署・緊急度・感情を判定。
返信の下書きも作り、担当者は「確認して送るだけ」にする。
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from common.llm import ask, is_demo
from common.ui import hero, section, setup

CSV_PATH = Path(__file__).parent.parent / "data" / "inquiries.csv"
CATEGORIES = ["技術サポート", "請求・経理", "解約", "機能要望", "営業・見積", "その他"]

SYSTEM = f"""あなたはSaaS企業のカスタマーサポート責任者です。問い合わせを分析してください。
- category: {" / ".join(CATEGORIES)} のいずれか
- urgency: 高（業務停止・期限が迫る・強い不満）/ 中 / 低
- sentiment: ポジティブ / 中立 / ネガティブ / 怒り
- escalate: 上長対応が必要か（繰り返しの不具合、強い怒り、解約、大口案件など）
- summary: 30字以内の要約
- reply_draft: 丁寧なビジネス敬語の返信下書き。確約できない事項（日時・金額）は「確認のうえご連絡します」とする"""

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "urgency": {"type": "string", "enum": ["高", "中", "低"]},
        "sentiment": {"type": "string", "enum": ["ポジティブ", "中立", "ネガティブ", "怒り"]},
        "escalate": {"type": "boolean"},
        "summary": {"type": "string"},
        "reply_draft": {"type": "string"},
    },
    "required": ["category", "urgency", "sentiment", "escalate", "summary", "reply_draft"],
    "additionalProperties": False,
}

_SIGN = "\n\n引き続きよろしくお願いいたします。\nカスタマーサポート"
DEMO_RESULTS = {
    1: ("技術サポート", "高", "ネガティブ", False, "ログイン不可、本日15時のデモで使用予定",
        "田中様\n\nお問い合わせいただきありがとうございます。ログインできない件、ご不便をおかけし申し訳ございません。\n本日15時のご利用に間に合うよう、最優先で確認いたします。恐れ入りますが、ご登録のメールアドレスと表示されるエラーメッセージをお知らせいただけますでしょうか。"),
    2: ("請求・経理", "低", "中立", False, "来月から請求書の宛名変更を希望",
        "鈴木様\n\nご連絡ありがとうございます。請求書の宛名を「株式会社スズキ 経理部」へ変更する件、承知いたしました。\n反映時期を確認のうえ、改めてご連絡いたします。"),
    3: ("解約", "中", "中立", True, "利用頻度低下のため月末で解約希望",
        "佐藤様\n\nこれまでご利用いただき誠にありがとうございます。\n解約手続きについてご案内いたします。なお、ご利用状況に合わせた低価格プランもございますので、よろしければ併せてご検討ください。詳細は確認のうえご連絡いたします。"),
    4: ("機能要望", "低", "ポジティブ", False, "CSVエクスポートの日付絞り込み機能の要望",
        "伊藤様\n\n貴重なご意見をありがとうございます。CSVエクスポートの日付絞り込み機能について、開発チームに共有いたしました。\n対応時期が決まりましたら改めてご案内いたします。"),
    5: ("技術サポート", "高", "怒り", True, "データ保存不具合が3回目、強い不満",
        "渡辺様\n\n度重なる不具合でご迷惑をおかけしており、誠に申し訳ございません。\n本件は責任者が直接対応いたします。原因の調査結果と再発防止策を確認のうえ、本日中にご連絡いたします。"),
    6: ("営業・見積", "中", "ポジティブ", True, "50名利用のプラン相談と見積依頼",
        "山本様\n\nお問い合わせありがとうございます。50名様でのご利用でしたら、ビジネスプランがおすすめです。\nお見積もりは担当営業より確認のうえご連絡いたします。"),
    7: ("請求・経理", "低", "中立", False, "9月分領収書のPDF発行依頼",
        "中村様\n\nご連絡ありがとうございます。9月分の領収書をPDFにて発行し、確認のうえ送付いたします。"),
    8: ("技術サポート", "中", "中立", False, "APIでkintoneと顧客データ連携したい",
        "小林様\n\nお問い合わせありがとうございます。弊社APIを利用したkintoneとの連携は可能です。\n具体的な連携方法と必要な設定について、確認のうえご案内いたします。"),
}

setup("問い合わせ自動仕分け")
DEMO = is_demo()
hero("DEMO 03 · カスタマーサポート", "問い合わせ自動仕分け",
     "問い合わせを<b>種類・緊急度・感情</b>で分類し、上長対応が必要な案件を検出。返信の下書きまで自動で作成します。",
     ['分類', '感情分析', 'エスカレーション判定', '返信下書き'])

uploaded = st.file_uploader("問い合わせCSV（列: id, from, subject, body）", type="csv")
df = pd.read_csv(uploaded if uploaded else CSV_PATH)
st.write(f"{len(df)}件の問い合わせ" + ("" if uploaded else "（サンプル）"))
st.dataframe(df[["from", "subject", "body"]], width="stretch", hide_index=True, height=200)

if st.button("AIで仕分ける", type="primary"):
    results = []
    progress = st.progress(0.0)
    for n, row in enumerate(df.to_dict("records"), 1):
        if DEMO:
            if row["id"] not in DEMO_RESULTS:
                st.warning("デモモードではサンプルCSV以外は仕分けできません")
                st.stop()
            keys = ["category", "urgency", "sentiment", "escalate", "summary", "reply_draft"]
            r = dict(zip(keys, DEMO_RESULTS[row["id"]]))
            r["reply_draft"] += _SIGN
        else:
            r = ask(SYSTEM, f"件名: {row['subject']}\n本文: {row['body']}", schema=SCHEMA)
        results.append({"id": row["id"], "from": row["from"], "subject": row["subject"], **r})
        progress.progress(n / len(df))
    st.session_state.triage = pd.DataFrame(results)

if (res := st.session_state.get("triage")) is not None:
    order = {"高": 0, "中": 1, "低": 2}
    res = res.sort_values(by="urgency", key=lambda s: s.map(order))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("処理件数", len(res))
    c2.metric("緊急度：高", int((res.urgency == "高").sum()))
    c3.metric("要エスカレーション", int(res.escalate.sum()))
    c4.metric("怒り・ネガティブ", int(res.sentiment.isin(["怒り", "ネガティブ"]).sum()))

    left, right = st.columns([2, 1])
    left.dataframe(res[["urgency", "category", "sentiment", "escalate", "summary", "from"]]
                   .rename(columns={"urgency": "緊急度", "category": "分類", "sentiment": "感情",
                                    "escalate": "要上長", "summary": "要約", "from": "送信者"}),
                   width="stretch", hide_index=True)
    right.bar_chart(res.category.value_counts())

    section("返信下書き（緊急度順）")
    for r in res.itertuples():
        badge = "🔴" if r.urgency == "高" else "🟡" if r.urgency == "中" else "🟢"
        with st.expander(f"{badge} [{r.category}] {r.subject} — {r.summary}" + ("　⚠️上長対応" if r.escalate else "")):
            st.text_area("下書き（編集できます）", r.reply_draft, height=200, key=f"draft_{r.id}")

    st.download_button("結果をCSVでダウンロード", res.to_csv(index=False).encode("utf-8-sig"), "仕分け結果.csv", "text/csv")
