"""Claude API 呼び出しの共通ヘルパー。

APIキー(ANTHROPIC_API_KEY)が無い環境や、サイドバーで「デモモード」をオンにした場合は、
各アプリが用意したサンプル結果を表示する（ポートフォリオ閲覧者がすぐ試せるように）。
"""
import json
import os

import anthropic
import streamlit as st

MODEL = "claude-opus-5-5"

_client = None


def is_demo() -> bool:
    """サイドバーにデモモードのスイッチを表示し、その状態を返す。各ページで1回だけ呼ぶ。"""
    label = "デモモード（サンプル結果を表示）"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.sidebar.markdown('<span class="tag" style="background:rgba(20,184,166,.18)">● デモモードで表示中</span>',
                            unsafe_allow_html=True)
        return True
    # ウィジェットの key に保存するとページ移動で消えるため、別の変数に保持する
    if "_demo" not in st.session_state:
        st.session_state._demo = False
    st.session_state._demo = st.sidebar.toggle(label, value=st.session_state._demo)
    return st.session_state._demo


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def ask(system: str, content, schema: dict | None = None, effort: str = "low"):
    """Claude に1回問い合わせる。schema を渡すと JSON(dict) を、渡さなければテキストを返す。

    content は文字列、または content block のリスト（PDF・画像を含む場合）。
    失敗時は画面にエラーを出してページの処理を止める。
    """
    output_config = {"effort": effort}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}

    try:
        response = _get_client().beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config=output_config,
            # 安全分類器に誤って断られた場合、サーバー側で別モデルに自動で引き継ぐ
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        _fail("APIキーが無効です。ANTHROPIC_API_KEY を確認してください。")
    except anthropic.RateLimitError:
        _fail("APIの利用上限に達しました。少し待ってから再実行してください。")
    except anthropic.APIConnectionError:
        _fail("Claude API に接続できません。ネットワークを確認するか、デモモードをオンにしてください。")
    except anthropic.APIStatusError as e:
        _fail(f"APIエラー（{e.status_code}）: {e.message}")

    if response.stop_reason == "refusal":
        _fail("AIが回答を辞退しました。入力内容を見直してください。")
    if response.stop_reason == "max_tokens":
        _fail("出力が長すぎて途中で切れました。入力を分割してください。")

    text = "".join(b.text for b in response.content if b.type == "text")
    return json.loads(text) if schema is not None else text


def _fail(message: str):
    st.error(message)
    st.stop()
