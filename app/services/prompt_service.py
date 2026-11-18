from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class PromptNotFoundError(Exception):
    """Raised when a prompt file is not found."""

    pass


class PromptService:
    def __init__(self, prompts_dir: Path | None = None) -> None:
        if prompts_dir is None:
            # Resolve to project root / app / prompts regardless of CWD
            self.prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

    def load_prompt(self, version: str) -> str:
        valid_versions = {"v1", "v2", "v3"}
        if version not in valid_versions:
            raise ValueError(
                f"Unsupported prompt version: {version}. Valid versions: {sorted(valid_versions)}"
            )

        file_name = f"customer_support_{version}.txt"
        file_path = self.prompts_dir / file_name

        if not file_path.is_file():
            logger.warning("Prompt file not found: %s", file_path)
            raise PromptNotFoundError(f"Prompt file not found: {file_name}")

        content = file_path.read_text(encoding="utf-8")
        logger.debug("Loaded prompt version=%s length=%d", version, len(content))
        return content
