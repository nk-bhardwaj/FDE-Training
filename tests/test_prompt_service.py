from pathlib import Path

import pytest

from app.services.prompt_service import PromptNotFoundError, PromptService


def test_load_v1():
    service = PromptService()
    text = service.load_prompt("v1")
    assert "customer support" in text.lower()
    assert len(text) > 0


def test_load_v2():
    service = PromptService()
    text = service.load_prompt("v2")
    assert "professional" in text.lower()
    assert "step-by-step" in text.lower() or "step" in text.lower()


def test_load_v3():
    service = PromptService()
    text = service.load_prompt("v3")
    assert "example" in text.lower()
    assert "positive" in text.lower()
    assert "negative" in text.lower()


def test_unsupported_version():
    service = PromptService()
    with pytest.raises(ValueError):
        service.load_prompt("v99")


def test_missing_file_raises():
    service = PromptService(prompts_dir=Path("/nonexistent"))
    with pytest.raises(PromptNotFoundError):
        service.load_prompt("v1")


def test_resolves_paths_independently_of_cwd(tmp_path, monkeypatch):
    # Default PromptService resolves from __file__, not CWD
    monkeypatch.chdir(tmp_path)
    service = PromptService()
    text = service.load_prompt("v1")
    assert len(text) > 0
