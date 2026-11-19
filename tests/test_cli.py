import sys
from unittest.mock import MagicMock, patch

import app.cli as cli


@patch("app.cli.subprocess.run")
def test_lint_calls_ruff_check(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    assert cli.lint() == 0
    mock_run.assert_called_once_with([sys.executable, "-m", "ruff", "check", "."])


@patch("app.cli.subprocess.run")
def test_format_code_calls_ruff_format(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    assert cli.format_code() == 0
    mock_run.assert_called_once_with([sys.executable, "-m", "ruff", "format", "."])


@patch("app.cli.subprocess.run")
def test_format_check_calls_ruff_format_check(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    assert cli.format_check() == 0
    mock_run.assert_called_once_with([sys.executable, "-m", "ruff", "format", "--check", "."])


@patch("app.cli.subprocess.run")
def test_test_calls_pytest(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    assert cli.test() == 0
    mock_run.assert_called_once_with([sys.executable, "-m", "pytest", "-v"])


@patch("app.cli.subprocess.run")
def test_exit_code_propagates_on_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1)
    assert cli.lint() == 1
    assert cli.format_code() == 1
    assert cli.format_check() == 1
    assert cli.test() == 1
