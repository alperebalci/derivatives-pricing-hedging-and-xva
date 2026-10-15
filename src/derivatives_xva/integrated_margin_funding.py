"""Joint collateral prepositioning and XVA-aware stress funding.

An educational two-stage LP. Cash and eligible collateral are committed before
stress is known; unsecured funding is recourse. Scenario XVA adjustments are
exogenous costs from an upstream valuation engine (not independently optimized).
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.optimize import linprog

PROB = np.array([0.65, 0.25, 0.10])
HAIRCUTS = np.array([0.05, 0.18])
INVENTORY = np.array([30.0, 25.0])
TOTAL_COLLATERAL_LIMIT = 40.0
CASH_LIMIT = 30.0
CASH_CARRY = 0.028
COLLATERAL_COST = np.array([0.012, 0.045])
FUNDING_SPREAD = np.array([0.035, 0.075, 0.16])


@dataclass(frozen=True)
class MarginScenarios:
    margin_call: np.ndarray
    xva_stress_cost: np.ndarray


@dataclass(frozen=True)
class MarginFundingResult:
    cash: float
    pledged_inventory: np.ndarray
    effective_collateral: float
    unsecured_funding: np.ndarray
    scenario_cost: np.ndarray
    scenario_liquidity_surplus: np.ndarray
    expected_cost: float
    cvar_cost: float
    objective: float
    all_unsecured_baseline_cost: float


def synthetic_scenarios() -> MarginScenarios:
    """Amounts and losses are in arbitrary consistent millions."""
    return MarginScenarios(np.array([25.0, 43.0, 66.0]),
                           np.array([0.8, 2.2, 5.8]))


def from_xva_result(result) -> MarginScenarios:
    """Map existing XVAResult exposure profile into illustrative stress inputs.

    Scales currency units to millions. This is a research *scenario adapter*,
    not a CSA margin formula or replacement for the XVA valuation engine.
    """
    df = result.exposure_profile
    if not {"pfe", "initial_margin_proxy"}.issubset(df.columns):
        raise ValueError("XVA exposure profile lacks required columns")
    pfe = float(np.max(df["pfe"].to_numpy(float))) / 1e6
    im = float(np.max(df["initial_margin_proxy"].to_numpy(float))) / 1e6
    xva = abs(float(result.total_xva)) / 1e6
    if not np.all(np.isfinite([pfe, im, xva])) or min(pfe, im, xva) < 0:
        raise ValueError("Invalid XVA scenario data")
    reference = max(15.0, im + 0.20 * pfe)
    return MarginScenarios(
        reference * np.array([0.85, 1.10, 1.65]),
        xva * np.array([0.7, 1.25, 2.0]),
    )


def tail_cvar(cost: np.ndarray, confidence: float) -> float:
    return float(min(t + np.dot(PROB, np.maximum(cost - t, 0)) /
                     (1 - confidence) for t in cost))


def solve(
    scenarios: MarginScenarios | None = None,
    risk_aversion: float = 0.6,
    confidence: float = 0.85,
) -> MarginFundingResult:
    p = scenarios if scenarios is not None else synthetic_scenarios()
    demand = np.asarray(p.margin_call, dtype=float)
    xva = np.asarray(p.xva_stress_cost, dtype=float)
    if (demand.shape != (3,) or xva.shape != (3,)
        or not np.all(np.isfinite(demand)) or not np.all(np.isfinite(xva))
        or (demand < 0).any() or (xva < 0).any()
        or risk_aversion < 0 or not 0 < confidence < 1):
        raise ValueError("Invalid demand, XVA, aversion or confidence")

    names = ["cash", "collateral_0", "collateral_1"]
    names += [f"unsecured_{s}" for s in range(3)]
    names += ["eta"] + [f"z_{s}" for s in range(3)]
    idx = {name: i for i, name in enumerate(names)}
    ub, upper = [], []
    def le(coefficients, limit):
        row = np.zeros(len(names))
        for key, value in coefficients.items():
            row[idx[key]] = float(value)
        ub.append(row)
        upper.append(float(limit))

    # Collateral carries a haircut; its nominal inventory cannot be double used.
    le({"collateral_0": 1, "collateral_1": 1}, TOTAL_COLLATERAL_LIMIT)
    cost_first = {"cash": CASH_CARRY,
                  "collateral_0": float(COLLATERAL_COST[0]),
                  "collateral_1": float(COLLATERAL_COST[1])}
    obj = np.zeros(len(names))
    for name, amount in cost_first.items():
        obj[idx[name]] = amount
    for s in range(3):
        # Fixed pre-stress decisions + scenario-specific funding must meet call.
        le({"cash": -1, "collateral_0": -(1 - float(HAIRCUTS[0])),
            "collateral_1": -(1 - float(HAIRCUTS[1])),
            f"unsecured_{s}": -1}, -demand[s])
        # Total cost_s = cash/collateral carry + funding spread * borrowing
        #                + scenario XVA stress add-on (exogenous).
        cost_s = {**cost_first, f"unsecured_{s}": float(FUNDING_SPREAD[s])}
        # z_s >= total_cost_s - eta.
        le({**cost_s, "eta": -1, f"z_{s}": -1}, -xva[s])
        obj[idx[f"unsecured_{s}"]] += PROB[s] * FUNDING_SPREAD[s]
        obj[idx[f"z_{s}"]] = risk_aversion * PROB[s] / (1 - confidence)
    obj[idx["eta"]] = risk_aversion
    bounds = [(0, None)] * len(names)
    bounds[idx["cash"]] = (0, CASH_LIMIT)
    bounds[idx["collateral_0"]] = (0, float(INVENTORY[0]))
    bounds[idx["collateral_1"]] = (0, float(INVENTORY[1]))
    bounds[idx["eta"]] = (None, None)
    ans = linprog(obj, A_ub=np.array(ub), b_ub=np.array(upper),
                  bounds=bounds, method="highs")
    if not ans.success:
        raise RuntimeError(f"Margin-funding LP failed: {ans.message}")
    v = dict(zip(names, ans.x))
    cash = float(v["cash"])
    pledge = np.array([v["collateral_0"], v["collateral_1"]])
    unsecured = np.array([v[f"unsecured_{s}"] for s in range(3)])
    effective = float(np.dot(1 - HAIRCUTS, pledge))
    first_cost = cash * CASH_CARRY + np.dot(COLLATERAL_COST, pledge)
    scenario_cost = first_cost + FUNDING_SPREAD * unsecured + xva
    expected = float(np.dot(PROB, scenario_cost))
    cvar = tail_cvar(scenario_cost, confidence)
    baseline = float(np.dot(PROB, FUNDING_SPREAD * demand + xva))
    return MarginFundingResult(
        cash, pledge, effective, unsecured,
        scenario_cost, cash + effective + unsecured - demand,
        expected, cvar, expected + risk_aversion * cvar, baseline,
    )


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-xva", action="store_true",
                    help="use small upstream synthetic XVA exposure simulation")
    args = ap.parse_args()
    scenarios = None
    if args.from_xva:
        from .xva import XVAProblem, solve as solve_xva
        from .rates import VasicekParams
        scenarios = from_xva_result(solve_xva(
            XVAProblem(params=VasicekParams(), n_paths=300)))
    r = solve(scenarios)
    print(f"Reserved cash: {r.cash:.4f}")
    print("Pledged collateral inventory:", r.pledged_inventory.round(4))
    print("Unsecured recourse by scenario:", r.unsecured_funding.round(4))
    print(f"Expected all-in modeled cost: {r.expected_cost:.4f}")
    print(f"Cost CVaR: {r.cvar_cost:.4f}")
    print(f"All-unsecured expected baseline: {r.all_unsecured_baseline_cost:.4f}")
    print("Scenario scaling illustrative; no capital or legal CSA validation.")


if __name__ == "__main__":
    main()
