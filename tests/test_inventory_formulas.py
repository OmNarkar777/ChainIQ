"""
Unit tests for all inventory optimisation formulas.
Run: pytest tests/test_inventory_formulas.py -v
"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest
from backend.agents.inventory_agent import (
    calc_safety_stock, calc_reorder_point, calc_eoq,
    calc_days_until_stockout, calc_stockout_risk_pct,
    classify_urgency, calc_recommended_order_qty, Z_95,
)

class TestSafetyStock:
    def test_standard(self):
        # SS = 1.65 x 10 x sqrt(9) = 49.5
        assert abs(calc_safety_stock(10.0, 9) - 49.5) < 0.01
    def test_zero_sigma(self):
        assert calc_safety_stock(0.0, 7) == 0.0
    def test_zero_lead_time(self):
        assert calc_safety_stock(10.0, 0) == 0.0
    def test_longer_lt_needs_more_ss(self):
        assert calc_safety_stock(10.0, 14) > calc_safety_stock(10.0, 7)
    def test_sqrt_scaling(self):
        ss7  = calc_safety_stock(10.0, 7)
        ss14 = calc_safety_stock(10.0, 14)
        assert abs(ss14 / ss7 - math.sqrt(14/7)) < 0.01

class TestReorderPoint:
    def test_basic(self):
        assert calc_reorder_point(10.0, 7, 20.0) == 90.0
    def test_zero_ss(self):
        assert calc_reorder_point(10.0, 7, 0.0) == 70.0
    def test_higher_demand_higher_rop(self):
        assert calc_reorder_point(50.0, 7, 10.0) > calc_reorder_point(5.0, 7, 10.0)

class TestEOQ:
    def test_textbook(self):
        eoq = calc_eoq(1000/365, unit_cost=25.0, ordering_cost=50.0, holding_cost_pct=0.20)
        assert abs(eoq - 141.4) < 2.0
    def test_higher_order_cost_increases_eoq(self):
        assert calc_eoq(20.0, 100, ordering_cost=500) > calc_eoq(20.0, 100, ordering_cost=100)
    def test_zero_demand(self):
        assert calc_eoq(0.0, 100) == 0.0
    def test_minimises_total_cost(self):
        avg, uc, S, h = 30.0, 200.0, 500.0, 0.20
        eoq = calc_eoq(avg, uc, S, h)
        D = avg * 365
        H = h * uc
        tc  = lambda q: (D/q)*S + (q/2)*H
        assert tc(eoq) <= tc(eoq*0.8)
        assert tc(eoq) <= tc(eoq*1.2)

class TestDaysUntilStockout:
    def test_basic(self):
        assert calc_days_until_stockout(70.0, 10.0) == 7.0
    def test_zero_demand(self):
        assert calc_days_until_stockout(100.0, 0.0) == 365.0
    def test_zero_stock(self):
        assert calc_days_until_stockout(0.0, 10.0) == 0.0
    def test_capped_365(self):
        assert calc_days_until_stockout(10000.0, 1.0) == 365.0

class TestStockoutRisk:
    def test_high_when_days_lt_lead_time(self):
        assert calc_stockout_risk_pct(3.0, 7) > 50.0
    def test_low_when_plenty_of_stock(self):
        assert calc_stockout_risk_pct(30.0, 7) < 20.0
    def test_bounded(self):
        for d in [0,1,3,7,14,30,90]:
            r = calc_stockout_risk_pct(d, 7)
            assert 0.0 <= r <= 100.0

class TestUrgency:
    def test_critical(self):
        assert classify_urgency(3, 7, 30, 100) == "CRITICAL"
    def test_high(self):
        assert classify_urgency(9, 7, 90, 200) == "HIGH"
    def test_medium(self):
        assert classify_urgency(20, 7, 50, 100) == "MEDIUM"
    def test_low(self):
        assert classify_urgency(60, 7, 600, 100) == "LOW"

class TestOrderQty:
    def test_at_least_eoq(self):
        assert calc_recommended_order_qty(200, 150, 100, "LOW") >= 200.0
    def test_critical_buffer(self):
        assert calc_recommended_order_qty(100, 150, 50, "CRITICAL") > calc_recommended_order_qty(100, 150, 50, "MEDIUM")
    def test_non_negative(self):
        assert calc_recommended_order_qty(5, 50, 500, "LOW") >= 0.0