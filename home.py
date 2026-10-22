import streamlit as st

from common.llm import is_demo
from common.ui import hero, note, section, setup

setup("ホーム")
DEMO = is_demo()

hero(
    "Portfolio · Generative AI × Business Process",
    "人手の定型業務を、AIで「確認するだけ」に。",
    "総務・経理・カスタマーサポート・物流プロジェクトでよくある業務を題材に、"
    "生成AI（Claude）を組み込んだ業務自動化のデモを公開しています。左のメニューから実際に操作できます。",
    ["RAG", "構造化抽出", "分類・優先度付け", "要件定義支援", "日英バイリンガル", "Human-in-the-loop"],
)

if DEMO:
    st.info("デモモードで表示しています。用意したサンプルデータの処理結果を表示します（APIキー不要）。")

DEMOS = [
    ("01", "社内規程Q&Aボット", "総務・人事",
     "就業規則や経費規程を読み込み、社員の質問に根拠の条文つきで回答します。",
     "同じ質問への回答に時間を取られる", "規程を検索して根拠つきで自動回答", "問い合わせ対応 約70%削減（試算）"),
    ("02", "請求書データ化", "経理",
     "形式がバラバラな請求書から項目を抽出し、検算とインボイス要件チェックを行ってExcelに出力します。",
     "手入力・転記ミス・インボイス確認", "AI抽出 + プログラム検算 + 要確認の振り分け", "入力作業 1枚5分 → 1分（試算）"),
    ("03", "問い合わせ自動仕分け", "カスタマーサポート",
     "問い合わせを種類・緊急度・感情で分類し、返信の下書きまで作成します。",
     "緊急・炎上案件の見落とし", "分類・優先度付け・エスカレーション判定", "一次対応 1件8分 → 3分（試算）"),
    ("04", "物流 要件定義アシスタント", "物流・PMO",
     "現場ヒアリングのメモから、議事録（日英）・業務要件一覧・課題管理表・To-Be業務フローを自動作成します。",
     "ヒアリング後の整理・資料化が重い", "メモ → 要件・課題・フロー図を一括生成", "資料作成 半日 → 30分（試算）"),
]

section("デモ一覧")
for i, (num, title, dept, desc, before, how, effect) in enumerate(DEMOS):
    if i % 2 == 0:
        cols = st.columns(2)
    cols[i % 2].markdown(
        f'<div class="card"><div class="num">DEMO {num}</div><h3>{title}</h3>'
        f'<span class="tag">{dept}</span><p style="margin-top:.6rem">{desc}</p>'
        f'<div class="row"><b>課題</b>{before}</div><div class="row"><b>解決</b>{how}</div>'
        f'<div class="effect">▲ {effect}</div></div>',
        unsafe_allow_html=True,
    )

section("設計で大事にしていること")
p1, p2, p3 = st.columns(3)
for col, (head, body) in zip((p1, p2, p3), [
    ("AIを過信しない", "AIの出力はプログラムで検算し、根拠（出典）を必ず表示。合わないものは「要確認」に回します。"),
    ("最後は人が判断", "返信・資料は「下書き」まで。担当者が確認して確定する Human-in-the-loop の設計です。"),
    ("既存業務にそのまま載る", "出力はExcel・CSVなど決まった形式に固定し、既存のシステムや運用に連携しやすくしています。"),
]):
    col.markdown(f'<div class="card"><h3>{head}</h3><p>{body}</p></div>', unsafe_allow_html=True)

note("※ 掲載しているデータ・企業名・数値はすべてデモ用に作成した架空のものです。削減効果は一般的な前提にもとづく試算です。")
