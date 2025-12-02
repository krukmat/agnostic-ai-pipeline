import types

import pytest

from scripts.providers import vertex_cli, vertex_sdk


def test_vertex_cli_chat_uses_openai_compat(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT", "proj")
    monkeypatch.setenv("VERTEX_LOCATION", "loc")
    monkeypatch.setenv("USE_OPENAI_COMPAT", "1")
    monkeypatch.setattr(vertex_cli, "_gcloud_token", lambda: "tok")

    class DummyResponse:
        def __init__(self):
            self._json = {
                "choices": [
                    {"message": {"content": [{"type": "text", "text": "hello"}]}}
                ]
            }

        def json(self):
            return self._json

        def raise_for_status(self):
            return None

    class DummyClient:
        def __init__(self, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            return DummyResponse()

    monkeypatch.setattr(vertex_cli, "httpx", types.SimpleNamespace(Client=DummyClient))
    out = vertex_cli.chat(messages=[{"role": "user", "content": [{"type": "text", "text": "hi"}]}], model="m")
    assert out == "hello"


def test_vertex_sdk_chat_extracts_parts(monkeypatch):
    class DummyPart:
        def __init__(self, text):
            self.text = text

    class DummyContent:
        def __init__(self):
            self.parts = [DummyPart("a"), DummyPart("b")]

    class DummyCandidate:
        def __init__(self):
            self.content = DummyContent()

    class DummyResponse:
        def __init__(self):
            self.candidates = [DummyCandidate()]
            self.text = ""

    class DummyModel:
        def generate_content(self, **kwargs):
            return DummyResponse()

    class DummyClient:
        def __init__(self, **kwargs):
            self.models = DummyModel()

    monkeypatch.setenv("GCP_PROJECT", "proj")
    monkeypatch.setenv("VERTEX_LOCATION", "loc")
    monkeypatch.setattr(vertex_sdk, "genai", types.SimpleNamespace(Client=DummyClient))
    out = vertex_sdk.chat(messages=[{"role": "user", "content": [{"type": "text", "text": "hi"}]}], model="m")
    assert out == "ab"
