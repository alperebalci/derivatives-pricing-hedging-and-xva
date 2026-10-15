# Integrated Collateral, Margin Funding and XVA Stress Optimization

A small two-stage LP that connects the **existing synthetic XVA exposure engine** to funding and collateral decisions via a validated scenario adapter.

## Decision problem

Preposition cash and a portfolio of two eligible collateral inventories *before* stress is known, accounting for different haircut and opportunity-cost assumptions. Once one of three stress scenarios is realized, borrow unsecured cash only to cover any residual margin call.

- **Here-and-now:** `cash`, `collateral_0`, `collateral_1`; their limits and inventory are enforced once for **all** scenarios.
- **Recourse:** `unsecured_funding_s`, a scenario-specific payment of the outstanding call.
- **Constraint:** `cash + sum_i (1 - haircut_i) * collateral_i + unsecured_funding_s >= margin_call_s`.
- **Scenario cost:** cash carry + pledged-collateral carry + stressed unsecured funding spread + upstream *exogenous* XVA cost adjustment.
- **Objective:** minimize expected cost + `lambda * CVaR_alpha(cost)` via a linear-programming epigraph.

The solver reports expected cost, CVaR, per-scenario liquidity surpluses and a comparable all-unsecured benchmark. All amounts use one consistent synthetic currency scale.

## Adapter to existing XVA model

`from_xva_result(result)` accepts the existing `derivatives_xva.xva.XVAResult`, reads `result.exposure_profile` (`pfe`, `initial_margin_proxy`) and `result.total_xva`, validates them, and constructs a deliberately transparent *illustrative* three-scenario margin demand and XVA-cost scale.

**Important:** A positive exposure quantile is not itself a CSA initial-margin call. The adapter is a research scenario mapping, not a regulatory IM methodology, netting-eligible exposure calculator, or XVA accounting reconciliation. The baseline XVA engine is unchanged; the optimization charges **incremental scenario costs** without asserting a valuation-consistent decomposition of FVA/MVA.

## Run and test

```bash
pip install -e ".[dev]"
python -m derivatives_xva.integrated_margin_funding
python -m derivatives_xva.integrated_margin_funding --from-xva
pytest -q tests/test_integrated_margin_funding.py
```

The default CLI uses fixed synthetic margin scenarios. The `--from-xva` flag runs a *small* upstream Vasicek exposure simulation and passes its `XVAResult` through the adapter. The test suite verifies haircuts, inventory conservation, liquidity coverage, all-unsecured baseline feasibility, and the adapter contract.

## Future research

Integrate actual collateral eligibility matrices and ownership, rehypothecation controls, CSA threshold/MTA mechanics, VM versus IM liquidity waterfalls, netting-set margin requirements, secured credit capacity, default waterfall and explicit multi-period margin paths. Recompute FVA/MVA *endogenously* rather than using exogenous stress add-ons, and test sensitivity to stressed liquidity spreads and margin period of risk.

**Limitations:** no claims of clearinghouse, OTC collateral, regulatory margin, close-out netting, capital adequacy, or production implementation. This synthetic model is strictly for research and education.
