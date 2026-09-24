import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from market_intel import extract
from market_intel.api import app
from market_intel.schema import ModelComparison
from market_intel.store import save_model_comparison


class _FakeClient:
    """Imita client.chat.completions.create devolvendo um tool call com JSON."""

    def __init__(self, arguments: dict):
        self._arguments = arguments
        self.last_kwargs = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.last_kwargs = kwargs
        tool_call = SimpleNamespace(function=SimpleNamespace(arguments=json.dumps(self._arguments)))
        message = SimpleNamespace(tool_calls=[tool_call])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_extract_model_comparison_parses_tool_call(monkeypatch):
    fake = _FakeClient({"model_name": "Kling 3.0", "provider": "Kling AI", "price_per_second_usd": 0.11})
    monkeypatch.setattr(extract, "client", fake)

    result = extract.extract_model_comparison("texto qualquer")

    assert (result.model_name, result.provider, result.price_per_second_usd) == ("Kling 3.0", "Kling AI", 0.11)
    assert result.evidence == []
    # A tool é forçada (não "auto"), senão o modelo poderia responder em texto solto.
    assert fake.last_kwargs["tool_choice"]["function"]["name"] == "extract_model_comparison"


def test_extract_quality_score_returns_none_when_absent(monkeypatch):
    monkeypatch.setattr(extract, "client", _FakeClient({}))

    assert extract.extract_quality_score("review sem nota numérica") is None


def test_api_lists_models_with_model_key():
    save_model_comparison(ModelComparison(model_name="Kling 3.0", provider="Kling AI"), "kling-3.0")

    response = TestClient(app).get("/api/models")

    assert response.status_code == 200
    [item] = response.json()
    assert item["model_key"] == "kling-3.0"
    assert item["model_name"] == "Kling 3.0"


def test_api_lists_providers_empty():
    response = TestClient(app).get("/api/providers")

    assert response.status_code == 200
    assert response.json() == []


def test_api_lists_history_after_a_save():
    save_model_comparison(ModelComparison(model_name="Kling 3.0", provider="Kling AI", price_per_second_usd=0.11), "kling-3.0")

    response = TestClient(app).get("/api/history")

    assert response.status_code == 200
    [entry] = [e for e in response.json() if e["field"] == "price_per_second_usd"]
    assert entry["entity_key"] == "kling-3.0"
    assert entry["old_value"] is None
    assert entry["new_value"] == "0.11"
