"""Unit tests for search evaluation Markdown report generation."""

from scripts.compare_search_methods import _build_markdown_report


class TestMarkdownReport:
    """Tests for _build_markdown_report function."""

    def test_report_basic_structure(self):
        """Report contains all required sections."""
        report = _build_markdown_report(
            per_query=[],
            total=0,
            semantic_top1_accuracy=0.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=0.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=0.0,
            keyword_avg_latency=0.0,
        )

        assert "# Day 3 — Search Method Evaluation Report" in report
        assert "## Evaluation Objective" in report
        assert "## Technology Stack" in report
        assert "## Dataset" in report
        assert "## Methodology" in report
        assert "## Results" in report
        assert "## Summary Metrics" in report
        assert "## Observations and Limitations" in report

    def test_report_technology_stack(self):
        """Report mentions required technology stack items."""
        report = _build_markdown_report(
            per_query=[],
            total=0,
            semantic_top1_accuracy=0.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=0.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=0.0,
            keyword_avg_latency=0.0,
        )

        assert "gemini-embedding-001" in report
        assert "768" in report
        assert "Neon PostgreSQL" in report
        assert "pgvector" in report
        assert "full-text search" in report.lower()

    def test_report_dataset_details(self):
        """Report mentions dataset size and categories."""
        report = _build_markdown_report(
            per_query=[],
            total=0,
            semantic_top1_accuracy=0.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=0.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=0.0,
            keyword_avg_latency=0.0,
        )

        assert "30 sample documents" in report
        assert "10 categories" in report

    def test_report_results_table_headers(self):
        """Results table has correct columns."""
        report = _build_markdown_report(
            per_query=[],
            total=0,
            semantic_top1_accuracy=0.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=0.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=0.0,
            keyword_avg_latency=0.0,
        )

        assert "| # | Expected Category | Semantic Top-1 | Keyword Top-1 |" in report
        assert "Semantic Top-3 Categories" in report
        assert "Keyword Top-3 Categories" in report
        assert "Semantic Latency (ms)" in report
        assert "Keyword Latency (ms)" in report

    def test_report_single_query_results(self):
        """Report includes query results with correct formatting."""
        per_query = [
            {
                "index": 1,
                "expected": "order_tracking",
                "query": "Where is my order?",
                "semantic_top1": "order_tracking",
                "keyword_top1": "cancellations",
                "semantic_categories": ["order_tracking", "delivery_delays"],
                "keyword_categories": ["cancellations"],
                "keyword_has_results": True,
                "semantic_status": "success",
                "keyword_status": "success",
                "semantic_latency_ms": 12.345,
                "keyword_latency_ms": 56.789,
            }
        ]
        report = _build_markdown_report(
            per_query=per_query,
            total=1,
            semantic_top1_accuracy=100.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=100.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=12.35,
            keyword_avg_latency=56.79,
        )

        assert "order_tracking" in report
        assert "cancellations" in report
        assert "order_tracking, delivery_delays" in report
        assert "12.35" in report  # rounded
        assert "56.79" in report  # rounded

    def test_report_failure_status_representation(self):
        """Failed searches show as 'failure' in top-1 and 'N/A' in latency."""
        per_query = [
            {
                "index": 1,
                "expected": "refunds",
                "query": "Refund query",
                "semantic_top1": "none",
                "keyword_top1": "no results",
                "semantic_categories": [],
                "keyword_categories": [],
                "keyword_has_results": False,
                "semantic_status": "failure",
                "keyword_status": "failure",
                "semantic_latency_ms": None,
                "keyword_latency_ms": None,
            }
        ]
        report = _build_markdown_report(
            per_query=per_query,
            total=1,
            semantic_top1_accuracy=0.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=0.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=0.0,
            keyword_avg_latency=0.0,
        )

        assert "failure" in report
        assert "N/A" in report

    def test_report_empty_results_representation(self):
        """Empty results (success but no matches) show as 'none'/'no results'."""
        per_query = [
            {
                "index": 1,
                "expected": "refunds",
                "query": "Refund query",
                "semantic_top1": "none",
                "keyword_top1": "no results",
                "semantic_categories": [],
                "keyword_categories": [],
                "keyword_has_results": False,
                "semantic_status": "success",
                "keyword_status": "success",
                "semantic_latency_ms": 10.0,
                "keyword_latency_ms": 20.0,
            }
        ]
        report = _build_markdown_report(
            per_query=per_query,
            total=1,
            semantic_top1_accuracy=0.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=0.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=10.0,
            keyword_avg_latency=20.0,
        )

        assert "none" in report
        assert "no results" in report
        assert "10.00" in report
        assert "20.00" in report

    def test_report_summary_metrics(self):
        """Summary metrics table shows correct values."""
        per_query = [
            {
                "index": 1,
                "expected": "order_tracking",
                "query": "q",
                "semantic_top1": "order_tracking",
                "keyword_top1": "cancellations",
                "semantic_categories": ["order_tracking"],
                "keyword_categories": ["cancellations"],
                "keyword_has_results": True,
                "semantic_status": "success",
                "keyword_status": "success",
                "semantic_latency_ms": 10.0,
                "keyword_latency_ms": 20.0,
            }
        ]
        report = _build_markdown_report(
            per_query=per_query,
            total=1,
            semantic_top1_accuracy=100.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=100.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=10.0,
            keyword_avg_latency=20.0,
        )

        assert "100.0%" in report  # semantic top-1
        assert "0.0%" in report  # keyword top-1
        assert "10.00 ms" in report
        assert "20.00 ms" in report

    def test_report_latency_rounded_to_two_decimals(self):
        """Latency values rounded to two decimal places in results table."""
        per_query = [
            {
                "index": 1,
                "expected": "order_tracking",
                "query": "q",
                "semantic_top1": "order_tracking",
                "keyword_top1": "cancellations",
                "semantic_categories": ["order_tracking"],
                "keyword_categories": ["cancellations"],
                "keyword_has_results": True,
                "semantic_status": "success",
                "keyword_status": "success",
                "semantic_latency_ms": 12.3456789,
                "keyword_latency_ms": 56.789123,
            }
        ]
        report = _build_markdown_report(
            per_query=per_query,
            total=1,
            semantic_top1_accuracy=100.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=100.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=12.3456789,
            keyword_avg_latency=56.789123,
        )

        assert "12.35" in report  # rounded
        assert "56.79" in report  # rounded

    def test_report_observations_section(self):
        """Observations section includes required notes."""
        report = _build_markdown_report(
            per_query=[],
            total=0,
            semantic_top1_accuracy=0.0,
            keyword_top1_accuracy=0.0,
            semantic_top3_hit_rate=0.0,
            keyword_top3_hit_rate=0.0,
            semantic_avg_latency=0.0,
            keyword_avg_latency=0.0,
        )

        assert "Failed searches are reported as failed" in report
        assert "excluded from latency averages" in report
        assert "no results are treated as incorrect" in report
        assert "not compared numerically" in report
