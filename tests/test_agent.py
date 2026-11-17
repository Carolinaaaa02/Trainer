from src.trainer.agent import SYSTEM_PROMPT, build_config


def test_build_config_includes_system_prompt() -> None:
    config = build_config()
    assert config.system_instruction == SYSTEM_PROMPT