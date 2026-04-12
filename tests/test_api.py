"""Tests for API utility functions."""

import pytest
import requests
from unittest.mock import MagicMock, patch

from api.api_utils import generate_headers, parse_score, parse_utc, fotmob_status_to_state, normalise_xgscore_name


class TestGenerateHeaders:
    def test_contains_user_agent(self):
        headers = generate_headers()
        assert "User-Agent" in headers

    def test_contains_accept(self):
        headers = generate_headers()
        assert "Accept" in headers

    def test_user_agent_is_string(self):
        headers = generate_headers()
        assert isinstance(headers["User-Agent"], str)


class TestParseScore:
    def test_home_win(self):
        assert parse_score("2-1") == (2, 1)

    def test_away_win(self):
        assert parse_score("0-3") == (0, 3)

    def test_draw(self):
        assert parse_score("1-1") == (1, 1)

    def test_none_input(self):
        assert parse_score(None) is None

    def test_empty_string(self):
        assert parse_score("") is None

    def test_invalid_format(self):
        assert parse_score("abc") is None


class TestParseUtc:
    def test_valid_utc_string(self):
        dt = parse_utc("2026-04-05T13:00:00Z")
        assert dt is not None
        assert dt.year == 2026

    def test_none_input(self):
        assert parse_utc(None) is None

    def test_empty_string(self):
        assert parse_utc("") is None


class TestFotmobStatusToState:
    def test_finished(self):
        assert fotmob_status_to_state({"finished": True}) == "finished"

    def test_live(self):
        assert fotmob_status_to_state({"started": True, "finished": False}) == "live"

    def test_scheduled(self):
        assert fotmob_status_to_state({}) == "scheduled"

    def test_cancelled(self):
        assert fotmob_status_to_state({"cancelled": True}) == "cancelled"

    def test_postponed(self):
        assert fotmob_status_to_state({"reason": {"longKey": "postponed"}}) == "postponed"


class TestNormaliseXgscoreName:
    def test_known_mapping(self):
        assert normalise_xgscore_name("Bodø-Glimt") == "Bodø/Glimt"
        assert normalise_xgscore_name("HamKam") == "Hamarkameratene"

    def test_unknown_name_passthrough(self):
        assert normalise_xgscore_name("Rosenborg") == "Rosenborg"
