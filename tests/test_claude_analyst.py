"""Tests for claude_analyst.get_insights — all API calls are mocked."""

from __future__ import annotations

import importlib
import json
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

import claude_analyst


WEEK_DATA = {
    "totals": {"cost": 32900, "installs": 9136, "CPI": 3.60, "ROAS_d7": 0.628, "CTR": 0.0256},
    "deltas": {"cost": 0.073, "installs": 0.033, "CPI": 0.039, "ROAS_d7": -0.051, "CTR": -0.030},
}
TOP_ROAS = [
    {"campaign": "RetargetPro_US", "ROAS_d7": 0.872, "CPI": 3.94},
    {"campaign": "SummerBoost_US", "ROAS_d7": 0.797, "CPI": 1.92},
]
BURNING = [
    {"campaign": "CreativeTest_UK", "CTR_change": -0.392, "CPI_change": 0.334, "CPI_prev": 2.10, "CPI_curr": 2.80},
]


def _make_response(text: str) -> MagicMock:
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


def _stub_anthropic(response_text: str):
    """Return a patched sys.modules entry for anthropic with a stubbed client."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_response(response_text)
    mod = types.ModuleType("anthropic")
    mod.Anthropic = MagicMock(return_value=mock_client)
    return mod


class TestGetInsights(unittest.TestCase):

    # ── Test 1: successful call returns parsed dict ──────────────────────────
    def test_success_returns_parsed_dict(self):
        payload = json.dumps({
            "summary": "Неделя прошла стабильно, ROAS D7 снизился на фоне роста CPI.",
            "bullets": ["RetargetPro_US показывает лучший ROAS D7 — 87.2%."],
            "recommendations": ["Перераспределить бюджет в пользу RetargetPro_US."],
        })
        with patch.dict(sys.modules, {"anthropic": _stub_anthropic(payload)}):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}):
                importlib.reload(claude_analyst)
                result = claude_analyst.get_insights(WEEK_DATA, {}, BURNING, TOP_ROAS)

        self.assertIsInstance(result, dict)
        self.assertIn("summary", result)
        self.assertIsInstance(result["bullets"], list)
        self.assertIsInstance(result["recommendations"], list)

    # ── Test 2: invalid JSON in response returns None ────────────────────────
    def test_invalid_json_returns_none(self):
        with patch.dict(sys.modules, {"anthropic": _stub_anthropic("not valid json")}):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}):
                importlib.reload(claude_analyst)
                result = claude_analyst.get_insights(WEEK_DATA, {}, BURNING, TOP_ROAS)

        self.assertIsNone(result)

    # ── Test 3: missing API key returns None without raising ─────────────────
    def test_missing_api_key_returns_none(self):
        env = {k: v for k, v in __import__("os").environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            importlib.reload(claude_analyst)
            result = claude_analyst.get_insights(WEEK_DATA, {}, BURNING, TOP_ROAS)

        self.assertIsNone(result)

    # ── Test 4: network error returns None ───────────────────────────────────
    def test_network_error_returns_none(self):
        bad_client = MagicMock()
        bad_client.messages.create.side_effect = ConnectionError("network down")
        mod = types.ModuleType("anthropic")
        mod.Anthropic = MagicMock(return_value=bad_client)

        with patch.dict(sys.modules, {"anthropic": mod}):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}):
                importlib.reload(claude_analyst)
                result = claude_analyst.get_insights(WEEK_DATA, {}, BURNING, TOP_ROAS)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
