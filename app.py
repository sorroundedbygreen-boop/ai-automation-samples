"""エントリーポイント：ページ一覧（サイドバーのメニュー）を定義する"""
import streamlit as st

st.navigation([
    st.Page("home.py", title="ホーム", icon=":material/home:", default=True),
    st.Page("pages/1_社内規程QAボット.py", title="社内規程Q&Aボット", icon=":material/menu_book:"),
    st.Page("pages/2_請求書データ化.py", title="請求書データ化", icon=":material/receipt_long:"),
    st.Page("pages/3_問い合わせ自動仕分け.py", title="問い合わせ自動仕分け", icon=":material/mark_email_unread:"),
    st.Page("pages/4_物流要件定義アシスタント.py", title="物流 要件定義アシスタント", icon=":material/local_shipping:"),
]).run()
