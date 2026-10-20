@echo off
cd /d %~dp0
pip install -q -r requirements.txt
python -m streamlit run app.py
