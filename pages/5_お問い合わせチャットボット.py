"""お問い合わせチャットボット（ECサイトのお客様向け窓口）

1. 注文番号が含まれていれば、注文データを照会して配送状況を答える（プログラムで確実に）
2. それ以外は FAQ をキーワードで探し、その内容だけを根拠に AI が回答する
3. 答えられない・お客様が希望した場合は、担当者への引き継ぎフォームを出す
"""
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from common.llm import ask, is_demo
from common.ui import guide, hero, note, section, setup

DATA = Path(__file__).parent.parent / "data" / "shop"
ORDER_RE = re.compile(r"HR-?\d{5}", re.IGNORECASE)
HANDOFF_WORDS = ["担当者", "人と話", "オペレーター", "電話したい", "クレーム"]
GREETING = ("こんにちは！ハルノ雑貨店のサポートです🌿\n\n"
            "送料・返品・お支払いなどのご質問や、**注文番号**（例：HR-10234）をお送りいただくと配送状況をお調べします。")

SYSTEM = """あなたはオンラインショップ「ハルノ雑貨店」のカスタマーサポート担当です。
【FAQ】と【注文情報】だけを根拠に、お客様の質問へ丁寧で親しみやすい敬語で、3〜4文で簡潔に答えてください。
FAQに答えが無い場合や、個別の判断が必要な場合は推測で答えず、resolved を false にして担当者へ引き継ぐ旨を伝えてください。"""

SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "resolved": {"type": "boolean"}},
    "required": ["answer", "resolved"],
    "additionalProperties": False,
}


@st.cache_data
def load_faq() -> list[dict]:
    sections = (DATA / "faq.md").read_text(encoding="utf-8").split("\n## ")[1:]
    return [{"title": t.strip(), "body": b.strip()} for t, _, b in (s.partition("\n") for s in sections)]


@st.cache_data
def load_orders() -> pd.DataFrame:
    return pd.read_csv(DATA / "orders.csv", dtype=str).fillna("")


# 短い質問でも見つけられるよう、FAQごとの言い換え表現を持っておく
KEYWORDS = {
    "送料": ["送料", "配送料", "配送無料", "送料無料"],
    "配送日数・お届け日": ["いつ届", "届く", "お届け", "日数", "日時指定", "時間指定", "何日"],
    "返品・交換": ["返品", "交換", "返金", "不良", "壊れ"],
    "支払い方法": ["支払", "決済", "カード", "後払い", "PayPay", "代引"],
    "注文のキャンセル・変更": ["キャンセル", "取り消", "注文を変更", "注文変更"],
    "ギフト包装": ["ギフト", "包装", "ラッピング", "プレゼント"],
    "ポイント": ["ポイント"],
    "営業時間・問い合わせ窓口": ["営業時間", "電話", "窓口", "何時まで"],
}


def search_faq(question: str, faq: list[dict]) -> dict | None:
    by_title = {f["title"]: f for f in faq}
    for title, words in KEYWORDS.items():
        if any(w.lower() in question.lower() for w in words) and title in by_title:
            return by_title[title]
    return None


def order_text(o: dict) -> str:
    lines = [f"ご注文 **{o['order_id']}** の状況をお調べしました。", "",
             f"- 状況：**{o['status']}**", f"- 商品：{o['items']}", f"- ご注文日：{o['order_date']}"]
    if o["ship_date"]:
        lines.append(f"- 発送日：{o['ship_date']}（{o['carrier']}　お問い合わせ番号 {o['tracking_no']}）")
    lines.append(f"- お届け{'日' if o['status'] == '配達完了' else '予定'}：{o['eta']}")
    return "\n".join(lines)


def respond(question: str) -> dict:
    """回答と「裏側で何をしたか」を返す"""
    faq, orders = load_faq(), load_orders()

    if any(w in question for w in HANDOFF_WORDS):
        return {"answer": "承知しました。担当者におつなぎします。下のフォームにご連絡先とご用件をご入力ください。",
                "intent": "担当者への引き継ぎ希望", "source": "—", "resolved": False}

    if m := ORDER_RE.search(question):
        order_id = m.group().upper().replace("HR", "HR-").replace("--", "-")
        hit = orders[orders.order_id == order_id]
        if hit.empty:
            return {"answer": f"申し訳ありません、注文番号 **{order_id}** が見つかりませんでした。番号をご確認のうえ、もう一度お送りください。",
                    "intent": "注文状況の確認", "source": f"注文データを照会 → 該当なし（{order_id}）", "resolved": False}
        return {"answer": order_text(hit.iloc[0].to_dict()), "intent": "注文状況の確認",
                "source": f"注文データを照会 → {order_id} が見つかりました", "resolved": True}

    item = search_faq(question, faq)
    if DEMO:
        if item is None:
            return {"answer": "申し訳ありません、そのご質問にはこの場でお答えできません。担当者よりご連絡しますので、下のフォームからお問い合わせください。",
                    "intent": "FAQで回答できない質問", "source": "FAQを検索 → 該当なし", "resolved": False}
        return {"answer": item["body"], "intent": "よくある質問", "source": f"FAQ「{item['title']}」", "resolved": True}

    # FAQは短いので、キーワードで見つからなければ全文を渡して AI に判断させる
    context = (f"## {item['title']}\n{item['body']}" if item
               else "\n\n".join(f"## {f['title']}\n{f['body']}" for f in faq))
    with st.spinner("お調べしています..."):
        r = ask(SYSTEM, f"【FAQ】\n{context}\n\n【お客様の質問】\n{question}", schema=SCHEMA)
    return {"answer": r["answer"], "intent": "よくある質問" if item else "FAQで回答できない質問",
            "source": f"FAQ「{item['title']}」" if item else "FAQを検索 → 該当なし", "resolved": r["resolved"]}


setup("お問い合わせチャットボット")
DEMO = is_demo()
hero("DEMO 05 · カスタマーサポート / EC", "お問い合わせチャットボット",
     "ネットショップのお客様からの質問に<b>24時間自動で回答</b>するチャットボットです。"
     "よくある質問への回答、<b>注文番号からの配送状況の確認</b>、答えられないときの<b>担当者への引き継ぎ</b>までを行います。",
     ["FAQ自動回答", "注文データ照会", "有人対応への引き継ぎ", "24時間対応"])

guide(
    "架空のネットショップ「ハルノ雑貨店」のサイトに置くチャット窓口のイメージです。お客様が質問すると、"
    "AIが<b>よくある質問（FAQ）</b>や<b>注文データ</b>を調べて答えます。AIで答えられない質問は、"
    "無理に答えずに<b>担当者へ引き継ぐ</b>ので、間違った案内でトラブルになるのを防げます。"
    "右側の「裏側の動き」で、AIが何を調べて答えたかも確認できます。",
    [("お客様として質問する", "下のボタンを押すか、入力欄に自由に質問を書きます"),
     ("AIが調べて答える", "FAQや注文データを調べ、その内容だけを使って答えます"),
     ("裏側を確認する", "右側に「何の質問と判断したか」「どこを調べたか」が表示されます"),
     ("引き継ぎを試す", "「担当者と話したい」を押すと、担当者への連絡フォームが出ます")],
    "注文番号は HR-10234（発送済み）・HR-10235（準備中）・HR-10236（配達完了）が試せます。",
)

if "chat" not in st.session_state:
    st.session_state.chat = [{"role": "assistant", "text": GREETING}]
    st.session_state.log = []

section("質問の例（押すとお客様として質問します）")
EXAMPLES = ["送料はいくら？", "返品したい", "HR-10234の配送状況", "支払い方法は？", "担当者と話したい"]
picked = None
for i, ex in enumerate(EXAMPLES):
    if i % 3 == 0:
        cols = st.columns(3)
    if cols[i % 3].button(ex, width="stretch"):
        picked = ex

chat_col, side_col = st.columns([3, 2], gap="large")
with chat_col:
    box = st.container(border=True)  # 会話はここに表示し、入力欄はその下に置く
    question = st.chat_input("メッセージを入力（例：ギフト包装はできますか？）") or picked
    if question:
        result = respond(question)
        st.session_state.chat += [{"role": "user", "text": question}, {"role": "assistant", "text": result["answer"]}]
        st.session_state.log.append(result)
    for m in st.session_state.chat:
        box.chat_message(m["role"], avatar="🌿" if m["role"] == "assistant" else "🙂").markdown(m["text"])

with side_col:
    log = st.session_state.log
    section("裏側の動き（最新の質問）")
    if log:
        last = log[-1]
        st.markdown(
            f'<div class="card"><div class="row"><b>判断</b>{last["intent"]}</div>'
            f'<div class="row"><b>調べた所</b>{last["source"]}</div>'
            f'<div class="row"><b>結果</b>{"✅ 自動で解決" if last["resolved"] else "👤 担当者へ引き継ぎ"}</div></div>',
            unsafe_allow_html=True)
    else:
        st.caption("質問すると、AIが何を調べて答えたかがここに表示されます。")

    section("このセッションの対応状況")
    m1, m2 = st.columns(2)
    m1.metric("自動で解決", f"{sum(r['resolved'] for r in log)}件")
    m2.metric("担当者へ引き継ぎ", f"{sum(not r['resolved'] for r in log)}件")

    if log and not log[-1]["resolved"]:
        section("担当者への引き継ぎフォーム")
        with st.form("handoff", clear_on_submit=True):
            st.text_input("お名前")
            st.text_input("メールアドレス")
            st.text_area("ご用件", value=st.session_state.chat[-2]["text"], height=80)
            if st.form_submit_button("担当者に送る", type="primary"):
                st.success("受け付けました。担当者より平日10時〜18時にご連絡します。（デモのため実際には送信・保存されません）")

    if st.button("会話をリセット"):
        del st.session_state["chat"]
        st.rerun()

note("※ ショップ名・商品・注文データ・電話番号はすべてデモ用に作成した架空のものです。")
