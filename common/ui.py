"""全ページ共通のデザイン（CSS・ヘッダー・カード）"""
import html

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&family=Inter:wght@500;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, .stButton button, input, textarea {
  font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }

/* サイドバー */
[data-testid="stSidebar"] { background: #0F1B2D; }
[data-testid="stSidebar"] * { color: #C9D3E3 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(20,184,166,.18); border-radius: 8px; }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: #fff !important; font-weight: 700; }
.sb-brand { font-weight: 800; font-size: 1.05rem; letter-spacing: .02em; color: #fff !important; margin: .2rem 0 .1rem; }
.sb-sub { font-size: .75rem; opacity: .7; margin-bottom: 1rem; }

/* ヒーロー */
.hero {
  position: relative; overflow: hidden;
  background: linear-gradient(120deg, #0F1B2D 0%, #13315C 55%, #0E7C74 100%);
  border-radius: 22px; padding: 2.1rem 2.3rem; margin-bottom: 1.6rem; color: #fff;
  box-shadow: 0 18px 40px -22px rgba(15,27,45,.6);
}
.hero::after {
  content: ""; position: absolute; right: -80px; top: -80px; width: 280px; height: 280px;
  background: radial-gradient(circle, rgba(45,212,191,.35), transparent 70%);
}
.hero .eyebrow { font-size: .74rem; font-weight: 700; letter-spacing: .14em; color: #5EEAD4; text-transform: uppercase; }
.hero h1 { color: #fff !important; font-size: 2.05rem; font-weight: 900; margin: .35rem 0 .5rem; line-height: 1.3; padding: 0; }
.hero p { color: #D5DEEC; margin: 0; font-size: .98rem; line-height: 1.8; max-width: 760px; }
.chips { margin-top: 1rem; display: flex; flex-wrap: wrap; gap: .45rem; }
.chip { font-size: .74rem; padding: .25rem .7rem; border-radius: 999px;
        background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.18); color: #E7EEF8; }

/* カード */
.card {
  background: #fff; border: 1px solid #E6EAF0; border-radius: 18px; padding: 1.35rem 1.4rem;
  height: 100%; margin-bottom: 1rem; transition: transform .15s ease, box-shadow .15s ease;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 14px 30px -18px rgba(15,27,45,.35); }
.card .num { font-family: 'Inter'; font-weight: 800; font-size: .8rem; color: #0E9F8E; letter-spacing: .1em; }
.card h3 { font-size: 1.12rem; font-weight: 800; margin: .3rem 0 .55rem; color: #0F1B2D; padding: 0; }
.card p { font-size: .88rem; color: #4A5568; line-height: 1.75; margin: 0 0 .8rem; }
.card .row { font-size: .8rem; color: #4A5568; padding: .45rem 0; border-top: 1px dashed #E6EAF0; }
.card .row b { color: #0F1B2D; display: inline-block; min-width: 3.2em; }
.card .effect { margin-top: .6rem; font-size: .82rem; font-weight: 700; color: #0E7C74; }
.tag { display: inline-block; font-size: .68rem; font-weight: 700; padding: .12rem .5rem; border-radius: 6px;
       background: #ECFDF8; color: #0E7C74; margin-right: .25rem; }

/* セクション見出し */
.section { font-size: 1.05rem; font-weight: 800; color: #0F1B2D; margin: 1.6rem 0 .7rem;
           padding-left: .7rem; border-left: 4px solid #14B8A6; }

/* メトリクス */
[data-testid="stMetric"] { background: #fff; border: 1px solid #E6EAF0; border-radius: 16px; padding: 1rem 1.2rem; }
[data-testid="stMetricLabel"] p { font-size: .8rem !important; color: #6B7280 !important; }
[data-testid="stMetricValue"] { font-weight: 800; color: #0F1B2D; }

/* ボタン */
.stButton button[kind="primary"], .stDownloadButton button {
  background: linear-gradient(120deg, #13315C, #0E9F8E) !important; border: 0 !important;
  border-radius: 10px !important; font-weight: 700 !important; padding: .55rem 1.3rem !important; color: #fff !important;
}
.stButton button[kind="primary"]:hover { filter: brightness(1.1); }

/* 表・エキスパンダー */
[data-testid="stDataFrame"], [data-testid="stExpander"] { border-radius: 14px; overflow: hidden; }
.note { font-size: .76rem; color: #8A94A6; margin-top: 2rem; }
</style>
"""


def setup(page_title: str):
    """ページ設定とCSSの読み込み。各ページの最初に呼ぶ。"""
    st.set_page_config(page_title=f"{page_title}｜AI業務自動化ラボ", page_icon="◆", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sb-brand">◆ AI業務自動化ラボ</div>'
                        '<div class="sb-sub">Generative AI × Business Process</div>', unsafe_allow_html=True)


def hero(eyebrow: str, title: str, lead: str, chips: list[str] = ()):
    chip_html = "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips)
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1>{html.escape(title)}</h1><p>{lead}</p><div class="chips">{chip_html}</div></div>',
        unsafe_allow_html=True,
    )


def section(text: str):
    st.markdown(f'<div class="section">{html.escape(text)}</div>', unsafe_allow_html=True)


def note(text: str):
    st.markdown(f'<div class="note">{html.escape(text)}</div>', unsafe_allow_html=True)
