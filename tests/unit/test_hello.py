"""Unit tests for marvin.brain.hello.ask()."""

from unittest.mock import MagicMock, patch

from marvin.brain.hello import ask


def test_ask_returns_text_from_response_field():
    """ask() should return the value of the 'response' key from Ollama's JSON reply."""
    # Arrange — build a fake Response object that mimics httpx.Response
    fake_response = MagicMock()
    fake_response.json.return_value = {"response": "hello back from marvin"}

    # Act — patch httpx.post in the namespace where hello.py uses it
    with patch("marvin.brain.hello.httpx.post", return_value=fake_response):
        result = ask("hello")

    # Assert
    assert result == "hello back from marvin"
