"""Liquidity, collateral eligibility and XVA scenario-adapter tests."""
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest

from derivatives_xva.integrated_margin_funding import (
    CASH_LIMIT, HAIRCUTS, INVENTORY, PROB, TOTAL_COLLATERAL_LIMIT,
    from_xva_result, solve, synthetic_scenarios,
)


def test_stress_liquidity_and_inventory_feasibility():
    plan = solve()
    assert 0 <= plan.cash <= CASH_LIMIT + 1e-7
    assert (plan.pledged_inventory >= -1e-8).all()
    assert (plan.pledged_inventory <= INVENTORY + 1e-7).all()
    assert plan.pledged_inventory.sum() <= TOTAL_COLLATERAL_LIMIT + 1e-7
    assert np.isclose(plan.effective_collateral,
                      np.dot(1 - HAIRCUTS, plan.pledged_inventory))
    assert (plan.unsecured_funding >= -1e-8).all()
    assert (plan.scenario_liquidity_surplus >= -1e-7).all()
    np.testing.assert_allclose(
        plan.scenario_liquidity_surplus,
        plan.cash + plan.effective_collateral
        + plan.unsecured_funding - synthetic_scenarios().margin_call)
    assert np.isclose(plan.expected_cost, np.dot(PROB, plan.scenario_cost))


def test_expected_cost_cannot_exceed_feasible_unsecured_baseline():
    neutral = solve(risk_aversion=0)
    assert neutral.expected_cost <= neutral.all_unsecured_baseline_cost + 1e-6


def test_upstream_xva_exposure_profile_adapter():
    profile = pd.DataFrame({"pfe": [0, 10_000_000, 9_000_000],
                            "initial_margin_proxy": [0, 5_000_000, 6_000_000]})
    mock_xva = SimpleNamespace(exposure_profile=profile, total_xva=800_000.0)
    scenarios = from_xva_result(mock_xva)
    assert scenarios.margin_call.shape == (3,)
    assert scenarios.xva_stress_cost.shape == (3,)
    assert np.all(np.diff(scenarios.margin_call) > 0)
    assert (solve(scenarios).scenario_liquidity_surplus >= -1e-7).all()


def test_invalid_inputs():
    with pytest.raises(ValueError):
        solve(risk_aversion=-1)
    with pytest.raises(ValueError):
        solve(confidence=1.0)
    broken = SimpleNamespace(exposure_profile=pd.DataFrame({"pfe": [1.0]}),
                             total_xva=2.0)
    with pytest.raises(ValueError):
        from_xva_result(broken)
