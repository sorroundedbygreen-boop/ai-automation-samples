import streamlit as st

from common.llm import is_demo

st.set_page_config(page_title="AI業務自動化サンプル", page_icon="🤖", layout="wide")
DEMO = is_demo()

st.title("🤖 AI業務自動化 サンプル集")
st.write("企業でよくある「人手の定型業務」を生成AI（Claude）で自動化するデモです。左のメニューから選んでください。")

if DEMO:
    st.info("現在 **デモモード** です。用意済みのサンプル結果を表示します。"
            "実際にAIを動かすには環境変数 `ANTHROPIC_API_KEY` を設定し、左のスイッチをオフにしてください。")
else:
    st.success("AIモード：実際に Claude API を呼び出して処理します。")

c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("① 社内規程Q&Aボット")
    st.write("就業規則・経費規程などを読み込み、社員の質問に**根拠となる条文つき**で回答。")
    st.caption("効果: 総務・人事への問い合わせ対応を削減")
with c2:
    st.subheader("② 請求書データ化")
    st.write("バラバラな形式の請求書（PDF/画像/テキスト）から項目を抽出し、Excelに一覧化。インボイス要件もチェック。")
    st.caption("効果: 経理の手入力・転記ミスを削減")
with c3:
    st.subheader("③ 問い合わせ自動仕分け")
    st.write("問い合わせを**カテゴリ・緊急度・感情**で自動分類し、返信の下書きまで作成。")
    st.caption("効果: CSの一次対応時間を短縮、炎上案件の見逃し防止")
