"""
Test Suite for Financial Rounding Logic
════════════════════════════════════════════════════════════════

Run: python test_rounding.py
"""

import sys
from decimal import Decimal, ROUND_HALF_UP
from rounding import (
    round_money, round_percent, round_price, safe_divide,
    format_holding, calculate_portfolio_summary,
    calculate_scenario_value, apply_rounding_to_stock_quote
)


class TestResults:
    """Track test pass/fail status."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures = []
    
    def assert_equal(self, actual, expected, test_name, tolerance=0.0001):
        """Assert with floating point tolerance."""
        if isinstance(actual, float) and isinstance(expected, float):
            if abs(actual - expected) <= tolerance:
                self.passed += 1
                print(f"✅ {test_name}")
            else:
                self.failed += 1
                self.failures.append(f"❌ {test_name}: expected {expected}, got {actual}")
                print(f"❌ {test_name}: expected {expected}, got {actual}")
        else:
            if actual == expected:
                self.passed += 1
                print(f"✅ {test_name}")
            else:
                self.failed += 1
                self.failures.append(f"❌ {test_name}: expected {expected}, got {actual}")
                print(f"❌ {test_name}: expected {expected}, got {actual}")
    
    def summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"RESULTS: {self.passed}/{total} passed")
        print(f"{'='*70}")
        if self.failed > 0:
            print("\nFailures:")
            for failure in self.failures:
                print(f"  {failure}")
            return False
        return True


def test_round_money():
    """Test monetary value rounding."""
    print("\n" + "="*70)
    print("TEST: round_money() - Monetary Values")
    print("="*70)
    
    results = TestResults()
    
    # Standard rounding
    results.assert_equal(round_money(123.456), 123.46, "round_money(123.456)")
    results.assert_equal(round_money(123.454), 123.45, "round_money(123.454)")
    results.assert_equal(round_money(123.445), 123.45, "round_money(123.445) - banker's rounding")
    
    # Edge cases
    results.assert_equal(round_money(100.001), 100.00, "round_money(100.001)")
    results.assert_equal(round_money(0.001), 0.00, "round_money(0.001)")
    results.assert_equal(round_money(0.005), 0.01, "round_money(0.005) - banker's rounding")
    
    # Negative zero
    results.assert_equal(round_money(-0.001), 0.00, "round_money(-0.001) - avoid -0.00")
    results.assert_equal(round_money(-123.456), -123.46, "round_money(-123.456)")
    
    # Large values
    results.assert_equal(round_money(56348.455), 56348.46, "round_money(56348.455)")
    results.assert_equal(round_money(380980.75), 380980.75, "round_money(380980.75)")
    
    return results.summary()


def test_round_percent():
    """Test percentage rounding."""
    print("\n" + "="*70)
    print("TEST: round_percent() - Percentage Values")
    print("="*70)
    
    results = TestResults()
    
    # Standard rounding
    results.assert_equal(round_percent(15.678), 15.68, "round_percent(15.678)")
    results.assert_equal(round_percent(0.4905), 0.49, "round_percent(0.4905)")
    results.assert_equal(round_percent(50.0), 50.00, "round_percent(50.0)")
    
    # Edge cases
    results.assert_equal(round_percent(0.001), 0.00, "round_percent(0.001)")
    results.assert_equal(round_percent(-5.432), -5.43, "round_percent(-5.432)")
    results.assert_equal(round_percent(-0.001), 0.00, "round_percent(-0.001) - avoid -0.00")
    
    # Banker's rounding
    results.assert_equal(round_percent(0.445), 0.45, "round_percent(0.445) - ROUND_HALF_UP")
    results.assert_equal(round_percent(0.455), 0.46, "round_percent(0.455) - ROUND_HALF_UP")
    
    return results.summary()


def test_round_price():
    """Test stock price rounding."""
    print("\n" + "="*70)
    print("TEST: round_price() - Stock Prices")
    print("="*70)
    
    results = TestResults()
    
    # NSE prices (2 decimals)
    results.assert_equal(round_price(750.567), 750.57, "round_price(750.567)")
    results.assert_equal(round_price(1500.001), 1500.00, "round_price(1500.001)")
    results.assert_equal(round_price(50.005), 50.01, "round_price(50.005)")
    
    # Large values (NSE max price)
    results.assert_equal(round_price(100000.567), 100000.57, "round_price(100000.567)")
    
    return results.summary()


def test_safe_divide():
    """Test safe division with zero handling."""
    print("\n" + "="*70)
    print("TEST: safe_divide() - Division with Zero Handling")
    print("="*70)
    
    results = TestResults()
    
    # Normal division
    results.assert_equal(safe_divide(100, 10), 10.0, "safe_divide(100, 10)")
    results.assert_equal(safe_divide(100, 3), 33.3333, "safe_divide(100, 3)", tolerance=0.001)
    
    # Zero division with defaults
    results.assert_equal(safe_divide(100, 0), 0.0, "safe_divide(100, 0) - default 0")
    results.assert_equal(safe_divide(100, 0, -1), -1.0, "safe_divide(100, 0, -1) - custom default")
    results.assert_equal(safe_divide(100, 0, 100), 100.0, "safe_divide(100, 0, 100) - custom default")
    
    # Negative values
    results.assert_equal(safe_divide(-100, 10), -10.0, "safe_divide(-100, 10)")
    results.assert_equal(safe_divide(100, -10), -10.0, "safe_divide(100, -10)")
    
    return results.summary()


def test_format_holding():
    """Test single holding calculation."""
    print("\n" + "="*70)
    print("TEST: format_holding() - Single Holding")
    print("="*70)
    
    results = TestResults()
    
    # Test Case 1: Basic holding with gain
    holding = format_holding(
        qty=75,
        buy_price=746.41,
        current_price=750.0,
        symbol="HDFCBANK.NS",
        dayHigh=755.0,
        dayLow=745.0
    )
    
    print(f"  Holding: {holding}")
    results.assert_equal(holding["invested"], 55980.75, "invested value")
    results.assert_equal(holding["currentValue"], 56250.00, "current value")
    results.assert_equal(holding["pnl"], 269.25, "P&L", tolerance=0.01)
    results.assert_equal(holding["pnlPercent"], 0.48, "P&L % (75 * 746.41 = 55980.75)", tolerance=0.01)
    results.assert_equal(holding["qty"], 75, "qty")
    results.assert_equal(holding["buyPrice"], round_price(746.41), "buyPrice")
    
    # Test Case 2: Holding with loss
    holding_loss = format_holding(
        qty=100,
        buy_price=2000.0,
        current_price=1990.0,
    )
    
    print(f"  Loss Holding: {holding_loss}")
    results.assert_equal(holding_loss["invested"], 200000.00, "invested value (loss)")
    results.assert_equal(holding_loss["currentValue"], 199000.00, "current value (loss)")
    results.assert_equal(holding_loss["pnl"], -1000.00, "P&L (loss)")
    results.assert_equal(holding_loss["pnlPercent"], -0.50, "P&L % (loss)")
    
    return results.summary()


def test_portfolio_summary():
    """Test portfolio summary calculation."""
    print("\n" + "="*70)
    print("TEST: calculate_portfolio_summary() - Portfolio Totals")
    print("="*70)
    
    results = TestResults()
    
    # Test Case: 3 holdings
    holdings = [
        {"qty": 75, "buyPrice": 746.41, "currentPrice": 750.0},
        {"qty": 50, "buyPrice": 2500.0, "currentPrice": 2510.0},
        {"qty": 100, "buyPrice": 2000.0, "currentPrice": 1990.0},
    ]
    
    summary = calculate_portfolio_summary(holdings)
    print(f"  Summary: {summary}")
    
    # Calculate expected values
    # Holding 1: 75 * 746.41 = 55980.75 invested
    # Holding 2: 50 * 2500 = 125000 invested
    # Holding 3: 100 * 2000 = 200000 invested
    # Total invested = 380980.75
    
    # Holding 1: 75 * 750 = 56250 current
    # Holding 2: 50 * 2510 = 125500 current
    # Holding 3: 100 * 1990 = 199000 current
    # Total current = 380750
    
    # Total P&L = 380750 - 380980.75 = -230.75
    
    results.assert_equal(summary["totalInvested"], 380980.75, "totalInvested")
    results.assert_equal(summary["totalValue"], 380750.00, "totalValue")
    results.assert_equal(summary["totalPnl"], -230.75, "totalPnl")
    results.assert_equal(summary["totalPnlPercent"], -0.06, "totalPnlPercent", tolerance=0.001)
    
    # Verify consistency: no rounding error in totals
    total_check = round_money(75*746.41) + round_money(50*2500) + round_money(100*2000)
    print(f"  Consistency check: sum of rounded holdings = {total_check}")
    results.assert_equal(
        total_check,
        summary["totalInvested"],
        "Consistency: sum of formatted holdings ≈ total"
    )
    
    return results.summary()


def test_scenario_calculations():
    """Test scenario value calculations (day high/low, 52w high/low)."""
    print("\n" + "="*70)
    print("TEST: calculate_scenario_value() - Price Scenarios")
    print("="*70)
    
    results = TestResults()
    
    # Test Case 1: Day high scenario
    scenario_high = calculate_scenario_value(
        qty=75,
        scenario_price=755.0,
        invested_per_unit=746.41
    )
    
    print(f"  Scenario High: {scenario_high}")
    # 75 * 755 = 56625
    # 75 * 746.41 = 55980.75
    # P&L = 56625 - 55980.75 = 644.25
    # P&L % = 644.25 / 55980.75 * 100 = 1.15%
    
    results.assert_equal(scenario_high["value"], 56625.00, "value at 755")
    results.assert_equal(scenario_high["pnl"], 644.25, "P&L at 755")
    results.assert_equal(scenario_high["pnlPercent"], 1.15, "P&L % at 755", tolerance=0.01)
    
    # Test Case 2: 52-week low scenario
    scenario_low = calculate_scenario_value(
        qty=75,
        scenario_price=645.0,
        invested_per_unit=746.41
    )
    
    print(f"  Scenario Low: {scenario_low}")
    # 75 * 645 = 48375
    # P&L = 48375 - 55980.75 = -7605.75
    # P&L % = -7605.75 / 55980.75 * 100 = -13.58%
    
    results.assert_equal(scenario_low["value"], 48375.00, "value at 645")
    results.assert_equal(scenario_low["pnl"], -7605.75, "P&L at 645")
    results.assert_equal(scenario_low["pnlPercent"], -13.59, "P&L % at 645", tolerance=0.01)
    
    return results.summary()


def test_stock_quote_rounding():
    """Test quote rounding."""
    print("\n" + "="*70)
    print("TEST: apply_rounding_to_stock_quote() - Quote Rounding")
    print("="*70)
    
    results = TestResults()
    
    quote = {
        "symbol": "HDFCBANK.NS",
        "currentPrice": 750.567,
        "dayHigh": 755.234,
        "dayLow": 745.001,
        "high52w": 1234.567,
        "low52w": 645.123,
        "openPrice": 748.456,
        "previousClose": 745.00,
        "change": 5.567,
        "changePercent": 0.7467,
        "history": []
    }
    
    rounded = apply_rounding_to_stock_quote(quote)
    print(f"  Rounded quote: {rounded}")
    
    results.assert_equal(rounded["currentPrice"], 750.57, "currentPrice")
    results.assert_equal(rounded["dayHigh"], 755.23, "dayHigh")
    results.assert_equal(rounded["dayLow"], 745.00, "dayLow")
    results.assert_equal(rounded["high52w"], 1234.57, "high52w")
    results.assert_equal(rounded["change"], 5.57, "change")
    results.assert_equal(rounded["changePercent"], 0.75, "changePercent")
    
    return results.summary()


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\n" + "="*70)
    print("TEST: Edge Cases & Boundary Conditions")
    print("="*70)
    
    results = TestResults()
    
    # Test: Zero quantity
    holding_zero_qty = format_holding(
        qty=0,
        buy_price=100.0,
        current_price=105.0,
    )
    print(f"  Zero qty: {holding_zero_qty}")
    results.assert_equal(holding_zero_qty["invested"], 0.00, "invested with qty=0")
    results.assert_equal(holding_zero_qty["currentValue"], 0.00, "current value with qty=0")
    results.assert_equal(holding_zero_qty["pnl"], 0.00, "P&L with qty=0")
    
    # Test: Zero buy price
    holding_zero_price = format_holding(
        qty=100,
        buy_price=0.0,
        current_price=100.0,
    )
    print(f"  Zero buy price: {holding_zero_price}")
    results.assert_equal(holding_zero_price["invested"], 0.00, "invested with buy_price=0")
    results.assert_equal(holding_zero_price["pnl"], 10000.00, "P&L with buy_price=0")
    
    # Test: Fractional quantities
    holding_fractional = format_holding(
        qty=75.5,
        buy_price=746.41,
        current_price=750.0,
    )
    print(f"  Fractional qty: {holding_fractional}")
    results.assert_equal(holding_fractional["invested"], 56353.96, "invested with fractional qty (75.5 * 746.41)", tolerance=0.015)
    results.assert_equal(holding_fractional["currentValue"], 56625.00, "current value with fractional qty")
    
    # Test: Very small values
    holding_small = format_holding(
        qty=0.001,
        buy_price=50000.0,
        current_price=50100.0,
    )
    print(f"  Very small: {holding_small}")
    results.assert_equal(holding_small["invested"], 50.00, "invested with tiny qty", tolerance=0.01)
    
    return results.summary()


def main():
    """Run all tests."""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "ROUNDING IMPLEMENTATION TEST SUITE".center(68) + "║")
    print("║" + "Portfolio Financial Accuracy Tests".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    all_passed = True
    
    all_passed &= test_round_money()
    all_passed &= test_round_percent()
    all_passed &= test_round_price()
    all_passed &= test_safe_divide()
    all_passed &= test_format_holding()
    all_passed &= test_portfolio_summary()
    all_passed &= test_scenario_calculations()
    all_passed &= test_stock_quote_rounding()
    all_passed &= test_edge_cases()
    
    # Final summary
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Implementation is correct!")
        print("="*70)
        return 0
    else:
        print("❌ SOME TESTS FAILED - Review implementation")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
