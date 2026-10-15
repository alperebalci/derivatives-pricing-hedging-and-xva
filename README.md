# Derivatives Pricing, Hedging and XVA
<!-- portfolio-umbrella:start -->
## Portfolio role

This repository is a primary umbrella repository in the consolidated Jors Academy portfolio. It groups related native research projects under `projects/` and serves as the main entry point for this domain.
<!-- portfolio-umbrella:end -->

Quantitative derivatives research focused on the decision layer around valuation, risk, counterparty exposure and hedge design.

The repository is deliberately not a collection of isolated pricing formulas. The common architecture is:

```text
market / curve state
        ↓
volatility surface / stochastic-vol calibration
        ↓
vanilla + exotic valuation and Greeks
        ↓
netting / collateral / Monte Carlo exposure
        ↓
XVA and tail-risk measurement
        ↓
XVA + portfolio hedge optimization
        ↓
benchmark + reconciliation tests
```

## Project map

| Project | Core question | Methods | Status |
|---|---|---|---|
| [Curve Construction](projects/curve-construction/) | Build an internally consistent discount curve and reprice par instruments | Bootstrapping, discount factors, forward rates | Implemented |
| [Options, Volatility & Greeks](projects/options-volatility-and-greeks/) | Price vanilla options and recover implied volatility / risk sensitivities | Black-Scholes, Greeks, root finding | Implemented |
| [Volatility Surface Calibration](projects/volatility-surface-calibration/) | Fit smile/skew representations across strike and maturity slices | Raw SVI, Hagan SABR, nonlinear least squares | Implemented |
| [Heston Calibration](projects/heston-calibration/) | Calibrate stochastic-volatility dynamics to an option surface | Heston characteristic function, Carr-Madan FFT-style integration, nonlinear calibration | Flagship |
| [Exotic Monte Carlo](projects/exotic-monte-carlo/) | Price path-dependent options with reproducible sampling error | GBM Monte Carlo, antithetic variates, Asian/barrier payoffs | Implemented |
| [Collateral & Netting](projects/collateral-and-netting/) | How do netting, CSA thresholds, MTA and margin lag reshape counterparty exposure? | Netting-set simulation, variation margin, EPE/ENE/PFE | Flagship |
| [Integrated Collateral, Margin Funding & XVA Stress](projects/integrated-collateral-funding-xva/) | Preposition haircut-adjusted collateral and cash to cover scenario margin calls with funding recourse | Two-stage LP, expected cost + CVaR, existing XVA exposure adapter | Research prototype |
| [XVA Exposure Engine](projects/xva-exposure-engine/) | How much counterparty/funding valuation adjustment arises from simulated swap exposure? | Vasicek, Monte Carlo, EPE/ENE/PFE, CVA/DVA/FVA/MVA, wrong-way proxy | Flagship |
| [XVA Hedge Optimization](projects/xva-hedge-optimization/) | Which credit/funding/rates hedge mix reduces residual XVA sensitivities under budget limits? | Finite-difference XVA Greeks, normalized minimax LP | Flagship |
| [Robust Hedge Optimization](projects/robust-hedge-optimization/) | Which hedge overlay minimizes worst stress loss under cost and notional constraints? | LP, minimax optimization, scenario stress P&L | Flagship |

## Design principles

Every project is designed to contain:

1. an explicit quantitative finance problem;
2. a transparent mathematical model;
3. deterministic or seeded synthetic inputs;
4. executable Python code;
5. benchmark or reconciliation checks;
6. automated tests;
7. explicit limitations.

The emphasis is on models that are inspectable and falsifiable. Synthetic performance is not presented as evidence of trading profitability or production fitness.

## Installation

Python 3.10+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Run examples

```bash
python projects/curve-construction/run.py
python projects/options-volatility-and-greeks/run.py
python projects/volatility-surface-calibration/run.py
python projects/heston-calibration/run.py
python projects/exotic-monte-carlo/run.py
python projects/collateral-and-netting/run.py
python -m derivatives_xva.xva
python projects/xva-exposure-engine/run.py
python projects/xva-hedge-optimization/run.py
python -m derivatives_xva.hedge
python projects/robust-hedge-optimization/run.py
```

## Repository structure

```text
projects/
├── curve-construction/
├── options-volatility-and-greeks/
├── volatility-surface-calibration/
├── heston-calibration/
├── exotic-monte-carlo/
├── collateral-and-netting/
├── xva-exposure-engine/
├── xva-hedge-optimization/
└── robust-hedge-optimization/

src/
└── derivatives_xva/
    ├── curves.py
    ├── options.py
    ├── vol_surface.py
    ├── heston.py
    ├── exotics.py
    ├── collateral.py
    ├── rates.py
    ├── xva.py
    ├── xva_hedge.py
    └── hedge.py

tests/
```

## Scope

This is a research and educational codebase. It is not a production pricing library, front-office risk engine, regulatory capital calculator, counterparty-credit platform, margin engine, hedge-accounting system, or trading system.

Production implementation would require market-data governance, multi-curve construction, collateral agreements, netting sets, calibration infrastructure, legal terms, model validation, numerical controls, trade lifecycle handling and institution-specific valuation policy.

## Disclaimer

Educational and research use only. Nothing in this repository is investment, trading, accounting, legal, credit or regulatory advice.
