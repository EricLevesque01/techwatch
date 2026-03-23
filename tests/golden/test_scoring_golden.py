"""Golden tests for scoring regressions using the eval corpus."""

from __future__ import annotations

import pytest

from techwatch.evals.corpus import get_golden_fixtures
from techwatch.evals.runner import run_all_evals, run_eval, run_ranking_eval


class TestGoldenScoring:
    """Tests that all golden fixtures score within expected bounds.

    IMPORTANT: If these tests fail after a scoring change, you must
    either justify the regression or update the golden fixtures.
    """

    @pytest.fixture
    def fixtures(self):
        return get_golden_fixtures()

    @pytest.mark.parametrize(
        "fixture_name",
        [f.name for f in get_golden_fixtures()],
    )
    def test_fixture_score_in_bounds(self, fixture_name):
        fixtures = get_golden_fixtures()
        fixture = next(f for f in fixtures if f.name == fixture_name)

        result = run_eval(fixture)
        assert result.passed, (
            f"Fixture '{fixture_name}': score {result.actual_score:.4f} "
            f"outside [{result.expected_min}, {result.expected_max}]. "
            f"{result.reason}"
        )

    def test_ranking_invariants(self, fixtures):
        """Verify that relative ranking relationships hold."""
        violations = run_ranking_eval(fixtures)
        assert not violations, (
            f"Ranking violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_new_perfect_match_ranks_highest(self, fixtures):
        """The new, perfect-match item should be the top-ranked fixture."""
        results, _ = run_all_evals()
        scores = {r.fixture_name: r.actual_score for r in results}
        assert scores["new_perfect_match"] > scores["used_fair_unknown_seller"]
        assert scores["new_perfect_match"] > scores["for_parts_item"]

    def test_for_parts_ranks_lowest(self, fixtures):
        """For-parts items should always rank lowest."""
        results, _ = run_all_evals()
        scores = {r.fixture_name: r.actual_score for r in results}
        for name, score in scores.items():
            if name != "for_parts_item":
                assert score > scores["for_parts_item"], (
                    f"{name} ({score:.4f}) should rank above "
                    f"for_parts_item ({scores['for_parts_item']:.4f})"
                )

    def test_all_fixtures_pass(self, fixtures):
        """Aggregate: all fixtures must score within bounds."""
        results, violations = run_all_evals()
        failed = [r for r in results if not r.passed]
        assert not failed, (
            f"{len(failed)} fixture(s) failed:\n"
            + "\n".join(
                f"  - {r.fixture_name}: {r.actual_score:.4f} "
                f"(expected [{r.expected_min}, {r.expected_max}]) — {r.reason}"
                for r in failed
            )
        )
        assert not violations, (
            f"Ranking violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )
