"""Tests for the per-run token budget tracker."""

import pytest
from pdd_agent.llm.budget import TokenBudget, BudgetExhaustedError, CallRecord


class TestCallRecord:
    def test_fields(self):
        rec = CallRecord(section_id="1.1", input_tokens=100, output_tokens=50, model="gpt-4o", cost_usd=0.001)
        assert rec.section_id == "1.1"
        assert rec.input_tokens == 100
        assert rec.output_tokens == 50
        assert rec.model == "gpt-4o"
        assert rec.cost_usd == 0.001


class TestTokenBudget:
    def test_defaults(self):
        budget = TokenBudget()
        assert budget.max_tokens == 500_000
        assert budget.warning_threshold == 0.8
        assert budget.total_tokens == 0
        assert budget.remaining == 500_000
        assert budget.utilization == 0.0
        assert not budget.is_exhausted

    def test_record_and_totals(self):
        budget = TokenBudget(max_tokens=10000)
        budget.record("1.1", input_tokens=200, output_tokens=100, model="gpt-4o")
        budget.record("1.2", input_tokens=300, output_tokens=150, model="gpt-4o")

        assert budget.total_input_tokens == 500
        assert budget.total_output_tokens == 250
        assert budget.total_tokens == 750
        assert budget.remaining == 9250
        assert len(budget.calls) == 2

    def test_utilization(self):
        budget = TokenBudget(max_tokens=1000)
        budget.record("1.1", input_tokens=400, output_tokens=100)
        assert budget.utilization == 0.5

    def test_utilization_zero_max(self):
        budget = TokenBudget(max_tokens=0)
        assert budget.utilization == 1.0
        assert budget.is_exhausted

    def test_check_budget_ok(self):
        budget = TokenBudget(max_tokens=10000)
        budget.record("1.1", input_tokens=100, output_tokens=50)
        budget.check_budget()

    def test_check_budget_exhausted(self):
        budget = TokenBudget(max_tokens=100)
        budget.record("1.1", input_tokens=80, output_tokens=30)
        with pytest.raises(BudgetExhaustedError, match="exhausted"):
            budget.check_budget()

    def test_warning_threshold(self):
        budget = TokenBudget(max_tokens=1000, warning_threshold=0.8)
        budget.record("1.1", input_tokens=700, output_tokens=100)
        assert budget._warning_emitted is False
        budget.check_budget()
        assert budget._warning_emitted is True

    def test_warning_emitted_once(self):
        budget = TokenBudget(max_tokens=1000, warning_threshold=0.5)
        budget.record("1.1", input_tokens=400, output_tokens=200)
        budget.check_budget()
        assert budget._warning_emitted is True
        budget.check_budget()

    def test_cost_estimation_gpt4o(self):
        budget = TokenBudget()
        rec = budget.record("1.1", input_tokens=1_000_000, output_tokens=0, model="gpt-4o")
        assert rec.cost_usd == pytest.approx(2.50, abs=0.01)

    def test_cost_estimation_gpt4o_output(self):
        budget = TokenBudget()
        rec = budget.record("1.1", input_tokens=0, output_tokens=1_000_000, model="gpt-4o")
        assert rec.cost_usd == pytest.approx(10.00, abs=0.01)

    def test_cost_estimation_unknown_model(self):
        budget = TokenBudget()
        rec = budget.record("1.1", input_tokens=1000, output_tokens=500, model="gpt-4o")
        assert rec.cost_usd > 0

    def test_estimated_cost_usd(self):
        budget = TokenBudget()
        budget.record("1.1", input_tokens=100000, output_tokens=50000, model="gpt-4o")
        budget.record("1.2", input_tokens=200000, output_tokens=100000, model="gpt-4o")
        assert budget.estimated_cost_usd > 0

    def test_summary(self):
        budget = TokenBudget(max_tokens=10000)
        budget.record("1.1", input_tokens=200, output_tokens=100, model="gpt-4o")
        s = budget.summary()
        assert s["max_tokens"] == 10000
        assert s["total_input_tokens"] == 200
        assert s["total_output_tokens"] == 100
        assert s["total_tokens"] == 300
        assert s["remaining"] == 9700
        assert s["num_calls"] == 1
        assert s["exhausted"] is False
        assert "utilization" in s
        assert "estimated_cost_usd" in s

    def test_remaining_never_negative(self):
        budget = TokenBudget(max_tokens=100)
        budget.record("1.1", input_tokens=200, output_tokens=100)
        assert budget.remaining == 0

    def test_is_exhausted_at_exact_limit(self):
        budget = TokenBudget(max_tokens=300)
        budget.record("1.1", input_tokens=200, output_tokens=100)
        assert budget.is_exhausted is True
