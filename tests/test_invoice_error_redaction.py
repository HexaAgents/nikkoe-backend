"""Browser response redaction regressions. (2026-09-30 · Codex)"""

from unittest.mock import patch

import httpx
import pytest
from openai import AuthenticationError


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("failure_stage", ["initialization", "request"])
def test_provider_credentials_never_reach_http_response(authed_client, streaming, failure_stage):
    provider_message = "Incorrect API key provided: sk-proj-synthetic-secret"
    error = AuthenticationError(
        provider_message,
        response=httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com/v1/responses")),
        body={"error": {"message": provider_message, "code": "invalid_api_key"}},
    )
    with (
        patch("app.services.invoice_parser.settings.OPENAI_API_KEY", "synthetic-test-key"),
        patch("app.services.invoice_parser.OpenAI") as provider,
    ):
        if failure_stage == "initialization":
            provider.side_effect = error
        else:
            provider.return_value.responses.create.side_effect = error
        route = "/api/receipts/parse-invoice" + ("/stream" if streaming else "")
        response = authed_client.post(route, files={"file": ("synthetic.pdf", b"%PDF-test", "application/pdf")})

    assert response.status_code == (200 if streaming else 502)
    assert "Invoice parsing service is temporarily unavailable" in response.text
    assert "sk-proj" not in response.text
    assert "Incorrect API key" not in response.text
    assert "invalid_api_key" not in response.text
    if streaming:
        assert "event: error" in response.text
        assert "event: done" not in response.text


def test_streaming_fallback_redacts_unexpected_exception(authed_client):
    with patch(
        "app.services.invoice_parser._call_llm",
        side_effect=RuntimeError("Incorrect API key provided: sk-proj-synthetic-secret"),
    ):
        response = authed_client.post(
            "/api/receipts/parse-invoice/stream",
            files={"file": ("synthetic.pdf", b"%PDF-test", "application/pdf")},
        )
    assert response.status_code == 200
    assert "Invoice parsing failed. Please try again." in response.text
    assert "sk-proj" not in response.text
    assert "Incorrect API key" not in response.text
