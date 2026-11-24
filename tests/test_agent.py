from src.trainer.agent import build_config, SYSTEM_PROMPT, build_system_prompt
from datetime import date

def test_build_config_includes_system_prompt() -> None:
    config = build_config()
    assert config.system_instruction == SYSTEM_PROMPT

def test_system_prompt_includes_today() -> None:
    assert "2026-11-23" in build_system_prompt(date(2026, 11, 23))