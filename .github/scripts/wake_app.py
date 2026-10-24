"""公開中の Streamlit アプリを開き、休止していたら起動ボタンを押す"""
import sys

from playwright.sync_api import sync_playwright

URL = "https://ai-gyomu-jidouka-demo.streamlit.app/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(5_000)

    button = page.get_by_role("button", name="Yes, get this app back up!")
    if button.count() > 0:
        print("休止中だったので起動します")
        button.click()
        page.wait_for_timeout(90_000)
    else:
        print("アプリは起動中です")

    # アプリ本体は iframe 内に表示される。トップページの見出しが出れば成功
    ok = any("AIで" in frame.content() for frame in page.frames)
    browser.close()
    print("確認OK" if ok else "アプリの表示を確認できませんでした")
    sys.exit(0 if ok else 1)
