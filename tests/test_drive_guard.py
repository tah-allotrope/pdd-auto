"""Tests for the gws availability guard."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pdd_agent.ingest.drive import GWS_ERROR_MESSAGE, _check_gws_available


class TestGwsGuard:
    def test_raises_when_gws_not_found(self):
        with patch("pdd_agent.ingest.drive.shutil.which", return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                _check_gws_available()
            assert "gws CLI not found" in str(exc_info.value)
            assert "demo workflows" in str(exc_info.value)
            assert "scripts/run_demo.py" in str(exc_info.value)

    def test_no_raise_when_gws_found(self):
        with patch("pdd_agent.ingest.drive.shutil.which", return_value="/usr/bin/gws"):
            _check_gws_available()

    def test_error_message_mentions_alternatives(self):
        with patch("pdd_agent.ingest.drive.shutil.which", return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                _check_gws_available()
            msg = str(exc_info.value)
            assert "npm install -g @googleworkspace/cli" in msg
            assert "gws auth setup" in msg
            assert "scripts/run_inegol_demo.py" in msg
