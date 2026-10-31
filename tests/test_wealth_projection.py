"""Regression tests for the net-worth projections.

Expected values are worked by hand in the comments so they can be audited
without trusting the code under test.
"""
from datetime import date

from app.services import wealth

CY = date.today().year


def _params(**overrides):
    base = {
        "annual_salary": 100_000,
        "annual_spending": 60_000,
        "salary_growth_rate": 0.0,
        "inflation_rate": 0.0,
        "investment_return_rate": 0.10,
        "retirement_year": CY + 10,
        "retirement_spending_adj": 1.0,
        "horizon_year": CY + 2,
    }
    base.update(overrides)
    return base


def test_forward_projection_flat_rates():
    # Start 100,000. Each year: growth = nw * 10%, then nw += 100,000 - 60,000 + growth.
    #   year 0: growth 10,000 -> 100,000 + 40,000 + 10,000 = 150,000
    #   year 1: growth 15,000 -> 150,000 + 40,000 + 15,000 = 205,000
    #   year 2: growth 20,500 -> 205,000 + 40,000 + 20,500 = 265,500
    rows = wealth.run_projection(_params(), 100_000)
    assert [r["year"] for r in rows] == [CY, CY + 1, CY + 2]
    assert [r["income"] for r in rows] == [100_000, 100_000, 100_000]
    assert [r["spending"] for r in rows] == [60_000, 60_000, 60_000]
    assert [r["investment_growth"] for r in rows] == [10_000, 15_000, 20_500]
    assert [r["net_worth"] for r in rows] == [150_000, 205_000, 265_500]


def test_forward_projection_retirement_cuts_income_and_adjusts_spending():
    # Start 0, no growth, no inflation, no return. Retire next year, spending x0.8 at retirement.
    #   year 0 (working):  0 + 100,000 - 50,000 = 50,000; spending becomes 40,000 for retirement
    #   year 1 (retired):  50,000 + 0 - 40,000 = 10,000
    #   year 2 (retired):  10,000 + 0 - 40,000 = -30,000
    params = _params(
        annual_spending=50_000, investment_return_rate=0.0,
        retirement_year=CY + 1, retirement_spending_adj=0.8, horizon_year=CY + 2,
    )
    rows = wealth.run_projection(params, 0)
    assert [r["income"] for r in rows] == [100_000, 0, 0]
    assert [r["spending"] for r in rows] == [50_000, 40_000, 40_000]
    assert [r["net_worth"] for r in rows] == [50_000, 10_000, -30_000]


def test_backward_projection_flat_rates():
    # Start (today) 150,000. Each step back: nw = (nw - 100,000 + 60,000) / 1.1
    #   1 back: 110,000 / 1.1 = 100,000
    #   2 back:  60,000 / 1.1 =  54,545.45 -> 54,545
    #   3 back: (54,545.45 - 40,000) / 1.1 = 14,545.45 / 1.1 = 13,223.14 -> 13,223
    #   4 back: (13,223.14 - 40,000) / 1.1 = -26,776.86 / 1.1 = -24,342.60 -> -24,343
    #   5 back: (-24,342.60 - 40,000) / 1.1 = -64,342.60 / 1.1 = -58,493.27 -> -58,493
    rows = wealth.run_backward_projection(_params(), 150_000)
    assert [r["year"] for r in rows] == [CY - 5, CY - 4, CY - 3, CY - 2, CY - 1, CY]
    assert [r["net_worth"] for r in rows] == [-58_493, -24_343, 13_223, 54_545, 100_000, 150_000]


def test_backward_inverts_forward_when_rates_are_flat():
    # With zero salary growth and inflation the backward model is the exact inverse
    # of one forward year, so running forward then backward recovers the start.
    params = _params(investment_return_rate=0.07, horizon_year=CY)
    start = 123_456.0
    forward = wealth.run_projection(params, start)[0]["net_worth"]
    back = wealth.run_backward_projection(params, forward)
    one_year_back = next(r["net_worth"] for r in back if r["year"] == CY - 1)
    assert abs(one_year_back - start) <= 1  # rows are rounded to whole dollars


def test_current_net_worth_sums_balances_including_liabilities():
    accounts = [{"balance": 1000.50}, {"balance": 250.25}, {"balance": -300.00}]
    assert wealth.current_net_worth(accounts) == 950.75


def test_load_history_without_finance_csv(monkeypatch, tmp_path):
    # A fresh deploy or restore has no data/finance.csv; the Wealth page must still render.
    monkeypatch.setattr(wealth, "FINANCE_CSV", tmp_path / "finance.csv")
    assert wealth.load_history() == []
