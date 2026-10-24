from pathlib import Path
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest


def test_assistant_message_uses_correct_role(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        @property
        def models(self):
            return self

        def generate_content(self, **kwargs):
            return SimpleNamespace(text="Fake response")

    import google.genai

    monkeypatch.setattr(google.genai, "Client", FakeClient)

    app_path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    at = AppTest.from_file(str(app_path))
    at.run()
    at.chat_input[0].set_value("Hello there").run()

    assert at.chat_message[-1].name == "assistant"
