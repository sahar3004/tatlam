"""
Unit tests for tatlam/cli/batch_cmd.py

Tests batch command CLI functionality.
Target: 100% coverage for main function
"""
from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestBatchCmdMain:
    """Test suite for batch_cmd main function."""

    @patch("tatlam.configure_logging")
    @patch("sys.argv", ["batch_cmd", "--category", "Test Category"])
    @patch("sys.exit")
    def test_main_sync_mode(
        self,
        mock_exit: MagicMock,
        mock_logging: MagicMock,
    ) -> None:
        """Test main function in sync mode."""
        mock_result = {"bundle_id": "TEST-001", "scenarios": [{"id": 1}]}

        mock_logic_module = MagicMock()
        mock_logic_module.run_batch.return_value = mock_result

        with patch.dict(sys.modules, {"tatlam.core.batch_logic": mock_logic_module}):
            # Reload module to pick up the mocked import
            if "tatlam.cli.batch_cmd" in sys.modules:
                del sys.modules["tatlam.cli.batch_cmd"]
            from tatlam.cli.batch_cmd import main

            main()

            mock_logging.assert_called_once()
            mock_logic_module.run_batch.assert_called_once()
            mock_exit.assert_called_with(0)

    @patch("tatlam.configure_logging")
    @patch("sys.argv", ["batch_cmd", "--category", "Test", "--async"])
    @patch("sys.exit")
    def test_main_async_mode(
        self,
        mock_exit: MagicMock,
        mock_logging: MagicMock,
    ) -> None:
        """Test main function with async mode enabled."""
        mock_result = {"bundle_id": "ASYNC-001", "scenarios": [{"id": 1}]}

        mock_logic_module = MagicMock()
        mock_logic_module.run_batch_async.return_value = mock_result

        with patch.dict(sys.modules, {"tatlam.core.batch_logic": mock_logic_module}):
            if "tatlam.cli.batch_cmd" in sys.modules:
                del sys.modules["tatlam.cli.batch_cmd"]
            from tatlam.cli.batch_cmd import main

            main()

            mock_logic_module.run_batch_async.assert_called_once()
            mock_exit.assert_called_with(0)

            mock_logic_module.run_batch_async.assert_called_once()
            mock_exit.assert_called_with(0)

    @patch("tatlam.configure_logging")
    @patch("sys.argv", ["batch_cmd", "--category", "Test", "--owner", "CustomOwner"])
    @patch("sys.exit")
    def test_main_with_custom_owner(
        self,
        mock_exit: MagicMock,
        mock_logging: MagicMock,
    ) -> None:
        """Test main function with custom owner."""
        mock_result = {"bundle_id": "TEST-001", "scenarios": []}

        mock_logic_module = MagicMock()
        mock_logic_module.run_batch.return_value = mock_result

        with patch.dict(sys.modules, {"tatlam.core.batch_logic": mock_logic_module}):
            if "tatlam.cli.batch_cmd" in sys.modules:
                del sys.modules["tatlam.cli.batch_cmd"]
            from tatlam.cli.batch_cmd import main

            main()

            mock_logic_module.run_batch.assert_called_with("Test", owner="CustomOwner")

    @patch("tatlam.configure_logging")
    @patch("sys.argv", ["batch_cmd", "--category", "Test"])
    @patch("sys.exit")
    @patch("builtins.print")
    def test_main_handles_keyboard_interrupt(
        self,
        mock_print: MagicMock,
        mock_exit: MagicMock,
        mock_logging: MagicMock,
    ) -> None:
        """Test main function handles KeyboardInterrupt gracefully."""
        mock_logic_module = MagicMock()
        mock_logic_module.run_batch.side_effect = KeyboardInterrupt()

        with patch.dict(sys.modules, {"tatlam.core.batch_logic": mock_logic_module}):
            if "tatlam.cli.batch_cmd" in sys.modules:
                del sys.modules["tatlam.cli.batch_cmd"]
            from tatlam.cli.batch_cmd import main

            main()

            mock_exit.assert_called_with(130)

    @patch("tatlam.configure_logging")
    @patch("sys.argv", ["batch_cmd", "--category", "Test"])
    @patch("sys.exit")
    @patch("builtins.print")
    def test_main_handles_generic_exception(
        self,
        mock_print: MagicMock,
        mock_exit: MagicMock,
        mock_logging: MagicMock,
    ) -> None:
        """Test main function handles generic exceptions."""
        mock_logic_module = MagicMock()
        mock_logic_module.run_batch.side_effect = Exception("Test error")

        with patch.dict(sys.modules, {"tatlam.core.batch_logic": mock_logic_module}):
            if "tatlam.cli.batch_cmd" in sys.modules:
                del sys.modules["tatlam.cli.batch_cmd"]
            from tatlam.cli.batch_cmd import main

            main()

            mock_exit.assert_called_with(1)

    @patch("tatlam.configure_logging")
    @patch("sys.argv", ["batch_cmd", "--category", "Test"])
    @patch("sys.exit")
    @patch("builtins.print")
    def test_main_prints_success_message(
        self,
        mock_print: MagicMock,
        mock_exit: MagicMock,
        mock_logging: MagicMock,
    ) -> None:
        """Test main function prints success message with details."""
        mock_result = {
            "bundle_id": "SUCCESS-001",
            "scenarios": [{"id": 1}, {"id": 2}, {"id": 3}]
        }

        mock_logic_module = MagicMock()
        mock_logic_module.run_batch.return_value = mock_result

        with patch.dict(sys.modules, {"tatlam.core.batch_logic": mock_logic_module}):
            if "tatlam.cli.batch_cmd" in sys.modules:
                del sys.modules["tatlam.cli.batch_cmd"]
            from tatlam.cli.batch_cmd import main

            main()

            # Verify success message was printed
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("SUCCESS-001" in call for call in print_calls)

    @patch("tatlam.configure_logging")
    @patch("sys.argv", ["batch_cmd", "--category", "Test"])
    @patch("sys.exit")
    def test_main_handles_missing_bundle_id(
        self,
        mock_exit: MagicMock,
        mock_logging: MagicMock,
    ) -> None:
        """Test main handles result without bundle_id."""
        mock_result: dict[str, Any] = {"scenarios": []}

        mock_logic_module = MagicMock()
        mock_logic_module.run_batch.return_value = mock_result

        with patch.dict(sys.modules, {"tatlam.core.batch_logic": mock_logic_module}):
            if "tatlam.cli.batch_cmd" in sys.modules:
                del sys.modules["tatlam.cli.batch_cmd"]
            from tatlam.cli.batch_cmd import main

            main()

            mock_exit.assert_called_with(0)
