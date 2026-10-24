"""社内規程Q&Aボット（RAG: 検索拡張生成）

1. 規程文書を「条」単位のチャンクに分割
2. 質問と各チャンクの文字バイグラム一致度で関連条文を検索（日本語でも辞書不要）
3. 上位の条文だけを根拠として Claude に渡し、出典つきで回答させる
"""
from collections import Counter
from pathlib import Path

import streamlit as st

from common.llm import ask, is_demo
from common.ui import guide, hero, section, setup

RULES_DIR = Path(__file__).parent.parent / "data" / "rules"
TOP_K = 3

SYSTEM = """あなたは社内規程に詳しい総務担当のアシスタントです。
与えられた【参考条文】だけを根拠に、社員の質問へ簡潔に回答してください。
- 回答の最後に、根拠とした文書名と条番号を「出典：」として列挙する
- 参考条文に答えが無い場合は推測せず「規程に記載がないため、総務部へお問い合わせください」と答える"""

DEMO_ANSWERS = {
    "在宅": "在宅勤務は**週3日まで**利用できます。前日17時までに勤怠システムで申請し、上長の承認を得てください。在宅勤務手当として月額3,000円が支給されます。\n\n出典：就業規則 第15条",
    "タクシー": "タクシーは **22時以降の帰宅時**、または**重い荷物を運ぶとき**に限り利用できます。それ以外は公共交通機関の最も経済的な経路で精算してください。\n\n出典：経費精算規程 第5条",
    "AI": "顧客の個人情報や未公開の財務情報は、社外の生成AIサービスに入力できません。会社が契約した法人向けAIサービス（入力データが学習に使われないもの）は業務で利用可能です。\n\n出典：情報セキュリティ規程 第6条",
}


def bigrams(text: str) -> Counter:
    text = "".join(text.split())
    return Counter(text[i:i + 2] for i in range(len(text) - 1))


@st.cache_data
def load_chunks() -> list[dict]:
    chunks = []
    for path in sorted(RULES_DIR.glob("*.md")):
        for section in path.read_text(encoding="utf-8").split("\n## ")[1:]:
            title, _, body = section.partition("\n")
            chunks.append({"doc": path.stem, "title": title.strip(), "body": body.strip()})
    return chunks


def search(question: str, chunks: list[dict]) -> list[dict]:
    q = bigrams(question)
    scored = []
    for c in chunks:
        overlap = sum((q & bigrams(c["title"] + c["body"])).values())
        scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for score, c in scored[:TOP_K] if score > 0]


setup("社内規程Q&Aボット")
DEMO = is_demo()
hero("DEMO 01 · 総務・人事", "社内規程Q&Aボット",
     "就業規則・経費精算規程・情報セキュリティ規程を検索し、<b>根拠の条文つき</b>で回答します。規程に書かれていないことは推測せず、担当部署へ案内します。",
     ['RAG（検索拡張生成）', '出典の明示', 'ハルシネーション対策'])

guide(
    "会社のルール（就業規則・経費のルールなど）について、社員がチャットで質問すると、"
    "AIが<b>ルールの文書を調べて答えます</b>。答えには<b>どの規程の何条に書いてあるか</b>が必ず付くので、"
    "本当に書いてあるか確認できます。総務や人事の「同じ質問に何度も答える」手間を減らせます。",
    [("質問を選ぶ", "下の「質問の例」のボタンを押すか、画面下の入力欄に自由に質問を書きます"),
     ("AIが規程を調べる", "質問に関係する条文を探し、その内容だけを使って回答を作ります"),
     ("根拠を確認する", "回答の最後の「出典」や「見つかった条文」で、元のルールを確認できます")],
    "規程に書かれていないことを聞くと、AIは推測で答えず「総務部へお問い合わせください」と案内します。",
)

chunks = load_chunks()
with st.expander(f"📄 AIが読み込んでいる規程（{len(chunks)}条）を見る"):
    for c in chunks:
        st.markdown(f"**{c['doc']} {c['title']}**  \n{c['body']}")

if "history" not in st.session_state:
    st.session_state.history = []

section("質問の例（押すとすぐ質問できます）")
EXAMPLES = ["在宅勤務は週何日まで？", "タクシーは使える？", "ChatGPTに顧客情報を入れていい？"]
picked = None
for col, ex in zip(st.columns(len(EXAMPLES)), EXAMPLES):
    if col.button(ex, width="stretch"):
        picked = ex

for role, text in st.session_state.history:
    st.chat_message(role).markdown(text)

if question := (st.chat_input("規程について質問してください（例：有給休暇は何日？）") or picked):
    st.chat_message("user").markdown(question)
    hits = search(question, chunks)

    if DEMO:
        key = next((k for k in DEMO_ANSWERS if k in question or (k == "AI" and "GPT" in question)), None)
        answer = DEMO_ANSWERS.get(key, "（デモモード）この質問のサンプル回答は未登録です。上の「質問の例」のボタンを試してください。")
    elif not hits:
        answer = "関連する規程が見つかりませんでした。総務部へお問い合わせください。"
    else:
        context = "\n\n".join(f"[{c['doc']} {c['title']}]\n{c['body']}" for c in hits)
        with st.spinner("規程を確認しています..."):
            answer = ask(SYSTEM, f"【参考条文】\n{context}\n\n【質問】\n{question}")

    with st.chat_message("assistant"):
        st.markdown(answer)
        if hits:
            with st.expander("🔍 AIが見つけた関連条文"):
                for c in hits:
                    st.markdown(f"- **{c['doc']} {c['title']}**：{c['body'][:80]}…")

    st.session_state.history += [("user", question), ("assistant", answer)]
