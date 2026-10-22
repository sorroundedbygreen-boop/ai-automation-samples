"""請求書データ化（AI-OCR + 構造化抽出）

形式がバラバラな請求書（PDF / 画像 / テキスト）から決まった項目を JSON で抽出し、
金額の整合性チェック・インボイス要件チェックを行って Excel に出力する。
"""
import base64
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from common.llm import ask, is_demo
from common.ui import hero, section, setup

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "invoices"

SYSTEM = """あなたは経理担当者です。請求書から指定された項目を正確に抽出してください。
- 日付は YYYY-MM-DD 形式（和暦は西暦に変換）
- 金額は円単位の整数。記載が無い項目は文字列なら空文字、数値なら 0
- invoice_issues には、適格請求書（インボイス制度）として不足している点を日本語で列挙する
  （登録番号の有無、税率ごとの対価・消費税額の記載など）。問題なければ空配列"""

SCHEMA = {
    "type": "object",
    "properties": {
        "vendor": {"type": "string", "description": "発行元の会社名"},
        "registration_no": {"type": "string", "description": "適格請求書発行事業者の登録番号(T+13桁)"},
        "invoice_no": {"type": "string"},
        "issue_date": {"type": "string"},
        "due_date": {"type": "string"},
        "subtotal": {"type": "integer", "description": "税抜小計"},
        "tax": {"type": "integer", "description": "消費税額"},
        "total": {"type": "integer", "description": "税込請求額"},
        "bank": {"type": "string", "description": "振込先"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "amount": {"type": "integer"},
                },
                "required": ["name", "amount"],
                "additionalProperties": False,
            },
        },
        "invoice_issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["vendor", "registration_no", "invoice_no", "issue_date", "due_date",
                 "subtotal", "tax", "total", "bank", "items", "invoice_issues"],
    "additionalProperties": False,
}

DEMO_RESULTS = {
    "請求書_A.txt": {"vendor": "株式会社ミドリ印刷", "registration_no": "T1234567890123", "invoice_no": "INV-2026-0931",
                   "issue_date": "2026-09-30", "due_date": "2026-10-31", "subtotal": 110000, "tax": 11000, "total": 121000,
                   "bank": "みずほ銀行 渋谷支店 普通 1234567",
                   "items": [{"name": "パンフレット印刷（A4・4色）", "amount": 90000}, {"name": "デザイン修正費", "amount": 20000}],
                   "invoice_issues": []},
    "請求書_B.txt": {"vendor": "合同会社クラウドワークス", "registration_no": "T9876543210987", "invoice_no": "CW-1088",
                   "issue_date": "2026-10-05", "due_date": "2026-10-31", "subtotal": 50000, "tax": 5000, "total": 55000,
                   "bank": "三井住友銀行 新宿支店 当座 7654321",
                   "items": [{"name": "クラウドサーバー利用料（9月分）", "amount": 38000}, {"name": "保守サポート（9月分）", "amount": 12000}],
                   "invoice_issues": []},
    "請求書_C.txt": {"vendor": "有限会社やまだ弁当", "registration_no": "", "invoice_no": "",
                   "issue_date": "2026-10-10", "due_date": "2026-10-31", "subtotal": 35266, "tax": 2734, "total": 38000,
                   "bank": "",
                   "items": [{"name": "会議用弁当 30個", "amount": 32400}, {"name": "お茶 30本", "amount": 4500}, {"name": "配送料", "amount": 1100}],
                   "invoice_issues": ["登録番号の記載がありません（仕入税額控除の対象外となる可能性）",
                                      "税率ごとの消費税額が記載されていません",
                                      "振込先口座の記載がありません"]},
}


def to_content(name: str, data: bytes):
    """ファイル種別に応じて Claude に渡す content block を作る"""
    suffix = Path(name).suffix.lower()
    instruction = {"type": "text", "text": "この請求書から項目を抽出してください。"}
    if suffix == ".pdf":
        doc = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                              "data": base64.standard_b64encode(data).decode()}}
        return [doc, instruction]
    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        media = "image/jpeg" if suffix in (".jpg", ".jpeg") else f"image/{suffix[1:]}"
        img = {"type": "image", "source": {"type": "base64", "media_type": media,
                                           "data": base64.standard_b64encode(data).decode()}}
        return [img, instruction]
    return f"{data.decode('utf-8')}\n\n上記の請求書から項目を抽出してください。"


def check(r: dict) -> list[str]:
    """AIの抽出結果をプログラムで検算する（AIを過信しない仕組み）"""
    warnings = []
    if r["subtotal"] + r["tax"] != r["total"]:
        warnings.append(f"小計+税({r['subtotal'] + r['tax']:,}) ≠ 合計({r['total']:,})")
    if r["items"] and sum(i["amount"] for i in r["items"]) not in (r["subtotal"], r["total"]):
        warnings.append("明細の合計が小計・合計と一致しません")
    return warnings


setup("請求書データ化")
DEMO = is_demo()
hero("DEMO 02 · 経理", "請求書データ化",
     "PDF・画像・テキストの請求書から項目を読み取り、<b>金額の検算</b>と<b>インボイス要件チェック</b>を行ってExcelに出力します。",
     ['PDF / 画像読み取り', '構造化出力', 'プログラム検算', 'Excel出力'])

files = [(f.name, f.getvalue()) for f in st.file_uploader(
    "請求書をアップロード（複数可）", type=["pdf", "png", "jpg", "jpeg", "webp", "txt"], accept_multiple_files=True) or []]
if st.checkbox("サンプル請求書3件を使う", value=not files):
    files += [(p.name, p.read_bytes()) for p in sorted(SAMPLE_DIR.glob("*.txt"))]

if files and st.button(f"{len(files)}件を読み取る", type="primary"):
    rows = []
    progress = st.progress(0.0)
    for n, (name, data) in enumerate(files, 1):
        if DEMO:
            result = DEMO_RESULTS.get(name)
            if result is None:
                st.warning(f"{name}: デモモードではサンプル以外は読み取れません")
                continue
        else:
            result = ask(SYSTEM, to_content(name, data), schema=SCHEMA)
        rows.append({"ファイル": name, **result, "検算エラー": check(result)})
        progress.progress(n / len(files))
    st.session_state.invoices = rows

if rows := st.session_state.get("invoices"):
    needs_review = [r for r in rows if r["invoice_issues"] or r["検算エラー"]]
    c1, c2, c3 = st.columns(3)
    c1.metric("処理件数", f"{len(rows)}件")
    c2.metric("請求額合計", f"¥{sum(r['total'] for r in rows):,}")
    c3.metric("要確認", f"{len(needs_review)}件")

    table = pd.DataFrame([{
        "ファイル": r["ファイル"], "発行元": r["vendor"], "登録番号": r["registration_no"],
        "請求番号": r["invoice_no"], "請求日": r["issue_date"], "支払期限": r["due_date"],
        "小計": r["subtotal"], "消費税": r["tax"], "合計": r["total"], "振込先": r["bank"],
        "要確認事項": " / ".join(r["invoice_issues"] + r["検算エラー"]),
    } for r in rows])
    st.dataframe(table, width="stretch", hide_index=True)

    for r in needs_review:
        st.warning(f"**{r['vendor']}**（{r['ファイル']}）\n\n" + "\n".join(f"- {x}" for x in r["invoice_issues"] + r["検算エラー"]))

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        table.to_excel(writer, sheet_name="請求書一覧", index=False)
        pd.DataFrame([{"ファイル": r["ファイル"], "発行元": r["vendor"], **i} for r in rows for i in r["items"]]) \
            .rename(columns={"name": "品目", "amount": "金額"}).to_excel(writer, sheet_name="明細", index=False)
    st.download_button("Excelでダウンロード", buf.getvalue(), "請求書一覧.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
