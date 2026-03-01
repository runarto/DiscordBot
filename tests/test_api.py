"""Tests for API utility functions and HTTP wrapper functions.

All HTTP calls are intercepted with unittest.mock.patch so no real network
requests are made during testing.
"""

import pytest
import requests
from unittest.mock import MagicMock, patch

from api.api_utils import generate_headers, validate
from api.rapid_sports import get_fixtures, get_teams, get_fixture_result


# ---------------------------------------------------------------------------
# api_utils
# ---------------------------------------------------------------------------

class TestGenerateHeaders:
    def test_contains_required_keys(self):
        headers = generate_headers("test-token")
        assert "x-rapidapi-host" in headers
        assert "x-rapidapi-key" in headers

    def test_uses_provided_token(self):
        headers = generate_headers("my-secret-token")
        assert headers["x-rapidapi-key"] == "my-secret-token"

    def test_correct_host(self):
        headers = generate_headers("token")
        assert headers["x-rapidapi-host"] == "v3.football.api-sports.io"

    def test_different_tokens_produce_different_headers(self):
        h1 = generate_headers("token-a")
        h2 = generate_headers("token-b")
        assert h1["x-rapidapi-key"] != h2["x-rapidapi-key"]


class TestValidate:
    def test_returns_parsed_json_on_success(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"response": [], "results": 0}
        result = validate(mock_response)
        assert result == {"response": [], "results": 0}

    def test_raises_http_error_on_bad_status(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        with pytest.raises(requests.HTTPError):
            validate(mock_response)

    def test_calls_raise_for_status_before_parsing(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500")
        mock_response.json.return_value = {}
        with pytest.raises(requests.HTTPError):
            validate(mock_response)
        mock_response.json.assert_not_called()


# ---------------------------------------------------------------------------
# Shared mock fixture response
# ---------------------------------------------------------------------------

MOCK_FIXTURE = {
    "fixture": {
        "id": 12345,
        "date": "2026-04-05T15:00:00+02:00",
        "status": {"short": "NS"},
    },
    "teams": {
        "home": {"name": "Brann"},
        "away": {"name": "Rosenborg"},
    },
}

MOCK_FIXTURES_RESPONSE = {"response": [MOCK_FIXTURE], "results": 1}


# ---------------------------------------------------------------------------
# get_fixtures
# ---------------------------------------------------------------------------

class TestGetFixtures:
    def test_returns_response_key(self):
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = MOCK_FIXTURES_RESPONSE
            result = get_fixtures("token", 7, 103, 2026)
        assert "response" in result
        assert result["response"][0]["fixture"]["id"] == 12345

    def test_calls_fixtures_endpoint(self):
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {"response": []}
            get_fixtures("token", 7, 103, 2026)
        called_url = mock_get.call_args[0][0]
        assert "fixtures" in called_url

    def test_sends_correct_league_and_season(self):
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {"response": []}
            get_fixtures("token", 7, 103, 2026)
        params = mock_get.call_args[1]["params"]
        assert params["league"] == 103
        assert params["season"] == 2026

    def test_from_date_is_after_today(self):
        from datetime import datetime
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {"response": []}
            get_fixtures("token", 7, 103, 2026)
        params = mock_get.call_args[1]["params"]
        from_date = datetime.strptime(params["from"], "%Y-%m-%d")
        assert from_date > datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def test_uses_oslo_timezone(self):
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {"response": []}
            get_fixtures("token", 7, 103, 2026)
        params = mock_get.call_args[1]["params"]
        assert params["timezone"] == "Europe/Oslo"

    def test_empty_response_is_valid(self):
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {"response": []}
            result = get_fixtures("token", 7, 103, 2026)
        assert result["response"] == []


# ---------------------------------------------------------------------------
# get_teams
# ---------------------------------------------------------------------------

class TestGetTeams:
    def test_returns_response_key(self):
        mock_teams = {"response": [{"team": {"name": "Brann", "id": 1}}]}
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = mock_teams
            result = get_teams("token", 103, 2026)
        assert result["response"][0]["team"]["name"] == "Brann"

    def test_sends_correct_league_and_season(self):
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {"response": []}
            get_teams("token", 103, 2026)
        params = mock_get.call_args[1]["params"]
        assert params["league"] == 103
        assert params["season"] == 2026


# ---------------------------------------------------------------------------
# get_fixture_result
# ---------------------------------------------------------------------------

class TestGetFixtureResult:
    def test_returns_fixture_data(self):
        mock_result = {"response": [MOCK_FIXTURE]}
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = mock_result
            result = get_fixture_result("token", 12345)
        assert result["response"][0]["fixture"]["id"] == 12345

    def test_calls_correct_url_with_match_id(self):
        with patch("api.rapid_sports.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {"response": []}
            get_fixture_result("token", 12345)
        called_url = mock_get.call_args[0][0]
        assert "12345" in called_url
