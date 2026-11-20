"""Tests for the chunking experiment script."""

from scripts.evaluate_chunking import (
    DATA_DIR,
    format_table,
    strip_frontmatter,
)


class TestStripFrontmatter:
    def test_strips_yaml_frontmatter(self):
        text = "---\nsource_id: foo\ntitle: Bar\n---\n\nActual content here."
        result = strip_frontmatter(text)
        assert result == "Actual content here."

    def test_returns_text_unchanged_without_frontmatter(self):
        text = "Just some content.\n\nNo frontmatter at all."
        result = strip_frontmatter(text)
        assert result == text

    def test_handles_missing_closing_delimiter(self):
        text = "---\nsource_id: foo\nNo closing delimiter."
        result = strip_frontmatter(text)
        assert result == text

    def test_handles_empty_text(self):
        assert strip_frontmatter("") == ""

    def test_handles_whitespace_only(self):
        assert strip_frontmatter("   \n  ") == "   \n  "

    def test_does_not_strip_content_starting_with_dashes(self):
        text = "--- This is a heading, not frontmatter.\n\nBody text."
        result = strip_frontmatter(text)
        assert result == text


class TestFormatTable:
    def test_returns_string(self):
        rows = [
            {
                "Document": "a.md",
                "Chunk Size": 100,
                "Overlap": 10,
                "Chunks": 2,
                "Avg Tokens": "50.0",
                "Min Tokens": 10,
                "Max Tokens": 90,
                "Total Tokens": 100,
            }
        ]
        result = format_table(rows)
        assert isinstance(result, str)
        assert "a.md" in result
        assert "100" in result

    def test_handles_empty_rows(self):
        result = format_table([])
        assert isinstance(result, str)


class TestMain:
    def test_data_dir_exists(self):
        assert DATA_DIR.exists()
        assert DATA_DIR.is_dir()

    def test_raw_documents_exist(self):
        md_files = list(DATA_DIR.glob("*.md"))
        assert len(md_files) == 3
        names = {f.name for f in md_files}
        assert names == {
            "amazon_fba_return_policy.md",
            "amazon_process_return_requests.md",
            "amazon_seller_fulfilled_returns.md",
        }

    def test_all_documents_have_frontmatter(self):
        for md_file in DATA_DIR.glob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            assert text.startswith("---"), f"{md_file.name} missing frontmatter"

    def test_strip_frontmatter_removes_metadata(self):
        for md_file in DATA_DIR.glob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            stripped = strip_frontmatter(text)
            assert "source_id" not in stripped
            assert "document_type" not in stripped
            assert stripped != text


class TestEndToEnd:
    def test_script_produces_output(self, capsys):
        from scripts.evaluate_chunking import main

        main()
        captured = capsys.readouterr()
        assert "TOKEN-BASED CHUNKING EVALUATION" in captured.out
        assert "amazon_fba_return_policy.md" in captured.out
        assert "amazon_process_return_requests.md" in captured.out
        assert "amazon_seller_fulfilled_returns.md" in captured.out
        assert "Chunks" in captured.out
        assert "Avg Tokens" in captured.out

    def test_script_uses_experiment_configs(self, capsys):
        from scripts.evaluate_chunking import main

        main()
        captured = capsys.readouterr()
        assert "300" in captured.out
        assert "500" in captured.out
        assert "800" in captured.out
        assert "50" in captured.out
        assert "75" in captured.out
        assert "100" in captured.out
