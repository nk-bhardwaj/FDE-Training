"""Evaluate token-based chunking across the three Amazon Markdown documents.

Reads every ``data/raw/*.md`` file, strips YAML frontmatter, and runs
``chunk_text()`` from :mod:`app.services.chunking_service` using the
three experiment configurations. Reports per-document/per-config
chunk statistics in a readable comparison table.

This script performs no Gemini or Neon calls.
"""

import sys
from pathlib import Path

from app.services.chunking_service import EXPERIMENT_CONFIGS, chunk_text

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
FRONTMATTER_DELIMITER = "---"


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from Markdown text.

    Frontmatter is a leading block delimited by ``---`` on its own line
    at the very start of the file. If the block is missing or malformed,
    the original text is returned unchanged.
    """
    if not text.startswith(FRONTMATTER_DELIMITER):
        return text

    lines = text.splitlines()
    # The first line must be the opening delimiter.
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return text

    # Find the closing delimiter, starting from the second line.
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_DELIMITER:
            # Return everything after the closing delimiter.
            return "\n".join(lines[index + 1 :]).lstrip("\n")

    # No closing delimiter found; treat the whole file as content.
    return text


def format_table(rows: list[dict[str, object]]) -> str:
    """Format a list of row dicts as a plain-text table."""
    headers = [
        "Document",
        "Chunk Size",
        "Overlap",
        "Chunks",
        "Avg Tokens",
        "Min Tokens",
        "Max Tokens",
        "Total Tokens",
    ]
    widths = {header: len(header) for header in headers}

    for row in rows:
        for header in headers:
            value = str(row.get(header, ""))
            widths[header] = max(widths[header], len(value))

    def _format_row(row: dict[str, object]) -> str:
        return " | ".join(str(row.get(header, "")).rjust(widths[header]) for header in headers)

    separator = "-+-".join("-" * widths[header] for header in headers)
    header_row = {header: header for header in headers}
    lines = [_format_row(header_row), separator]
    lines.extend(_format_row(row) for row in rows)
    return "\n".join(lines)


def main() -> None:
    """Run chunking experiments and print the comparison table."""
    md_files = sorted(DATA_DIR.glob("*.md"))
    if not md_files:
        print("No Markdown files found in data/raw/")
        return

    rows: list[dict[str, object]] = []
    for md_file in md_files:
        raw_text = md_file.read_text(encoding="utf-8")
        text = strip_frontmatter(raw_text)

        for config in EXPERIMENT_CONFIGS:
            chunks = chunk_text(
                text,
                chunk_size=config["chunk_size"],
                chunk_overlap=config["chunk_overlap"],
            )

            if not chunks:
                continue

            token_counts = [chunk.token_count for chunk in chunks]
            total_tokens = sum(token_counts)
            avg_tokens = total_tokens / len(token_counts)
            min_tokens = min(token_counts)
            max_tokens = max(token_counts)

            rows.append(
                {
                    "Document": md_file.name,
                    "Chunk Size": config["chunk_size"],
                    "Overlap": config["chunk_overlap"],
                    "Chunks": len(chunks),
                    "Avg Tokens": f"{avg_tokens:.1f}",
                    "Min Tokens": min_tokens,
                    "Max Tokens": max_tokens,
                    "Total Tokens": total_tokens,
                }
            )

    print("=" * 80)
    print("TOKEN-BASED CHUNKING EVALUATION")
    print("=" * 80)
    print(f"\nDocuments evaluated: {len(md_files)}")
    print(f"Configurations: {len(EXPERIMENT_CONFIGS)}")
    print("\n" + format_table(rows))
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if sys.platform == "win32":
        # Avoid event-loop warnings on Windows for this synchronous script.
        pass
    main()
