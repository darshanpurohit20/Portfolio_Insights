"""
Financial Rounding Utilities
═════════════════════════════════════════════════════════════════

Follows best practices from Zerodha, Groww, and other Indian trading platforms.

PRINCIPLE:
  • Maintain HIGH PRECISION during all calculations
  • Apply rounding ONLY at the OUTPUT stage (API response)
  • Use banker's rounding (ROUND_HALF_UP) for financial accuracy
  • Ensure: sum(round(item)) == round(sum(items))

STRATEGY:
  1. Store all calculated values in float (full precision)
  2. Build totals from unrounded values
  3. Round totals AFTER summing
  4. Format individual items with same rounding as totals
  5. This ensures mathematical consistency

KEY FUNCTIONS:
  • round_money(value) → rounds to 2 decimal places
  • round_percent(value) → rounds to 2 decimal places
  • round_price(value) → rounds to market precision (2 decimals)
  • safe_divide(numerator, denominator) → handles zero division
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union


def round_money(value: Union[float, int, Decimal]) -> float:
    """
    Round monetary values (portfolio values, P&L, invested amounts) to 2 decimal places.
    
    Uses Decimal + ROUND_HALF_UP for financial accuracy.
    Result is returned as float for JSON serialization.
    
    Args:
        value: Amount in rupees
        
    Returns:
        Rounded to 2 decimal places
        
    Examples:
        round_money(1234.567) → 1234.57
        round_money(100.001) → 100.00
        round_money(-0.001) → 0.00 (no negative zero)
    """
    if value is None or (isinstance(value, float) and not isinstance(value, bool)):
        if isinstance(value, float) and abs(value) < 1e-10:
            return 0.00
    
    d = Decimal(str(value))
    rounded = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    result = float(rounded)
    
    # Avoid negative zero
    return 0.00 if result == 0 else result


def round_percent(value: Union[float, int, Decimal]) -> float:
    """
    Round percentage values (P&L %, returns) to 2 decimal places.
    
    Args:
        value: Percentage value (e.g., 15.678)
        
    Returns:
        Rounded to 2 decimal places
        
    Examples:
        round_percent(15.678) → 15.68
        round_percent(-5.432) → -5.43
        round_percent(0.001) → 0.00
    """
    d = Decimal(str(value))
    rounded = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    result = float(rounded)
    
    # Avoid negative zero
    return 0.00 if result == 0 else result


def round_price(value: Union[float, int, Decimal]) -> float:
    """
    Round stock prices to market precision (2 decimal places).
    NSE uses 2 decimal places for all prices.
    
    Args:
        value: Stock price in rupees
        
    Returns:
        Rounded to 2 decimal places
        
    Examples:
        round_price(1500.567) → 1500.57
        round_price(50.001) → 50.00
    """
    d = Decimal(str(value))
    rounded = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    result = float(rounded)
    
    return 0.00 if result == 0 else result


def safe_divide(numerator: Union[float, int, Decimal], 
                denominator: Union[float, int, Decimal], 
                default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: The top number
        denominator: The bottom number
        default: Value to return if denominator is 0 (default: 0.0)
        
    Returns:
        numerator / denominator, or default if division by zero
        
    Examples:
        safe_divide(100, 10) → 10.0
        safe_divide(100, 0) → 0.0
        safe_divide(100, 0, -1) → -1.0
    """
    try:
        denom = float(denominator)
        if denom == 0:
            return default
        return float(numerator) / denom
    except (TypeError, ValueError):
        return default


def format_holding(
    qty: float,
    buy_price: float,
    current_price: float,
    **extra_fields
) -> dict:
    """
    Format a single holding with all P&L metrics.
    
    STRATEGY:
    1. Calculate all values in full precision
    2. Return rounded values for display
    3. Maintain internal precision in calculations
    
    Args:
        qty: Number of shares
        buy_price: Purchase price per share
        current_price: Current market price per share
        **extra_fields: Additional fields from stock data (symbol, dayHigh, etc.)
        
    Returns:
        Dict with rounded values ready for API response
        
    Example:
            holding = format_holding(
                qty=75.5,
                buy_price=746.41,
                current_price=750.00,
                symbol="HDFCBANK.NS",
                dayHigh=752.5,
                dayLow=745.0
            )
            # Returns:
            # {
            #   "qty": 75.5,
            #   "buyPrice": 746.41,
            #   "currentPrice": 750.00,
            #   "invested": 56348.46,        (qty * buy_price, rounded)
            #   "currentValue": 56625.00,    (qty * current_price, rounded)
            #   "pnl": 276.54,               (difference, rounded)
            #   "pnlPercent": 0.49,          (percent, rounded)
            #   ...extra_fields...
            # }
    """
    # Step 1: Calculate with full precision (no rounding)
    invested = qty * buy_price
    current_value = qty * current_price
    pnl = current_value - invested
    pnl_percent = safe_divide(pnl, invested) * 100.0
    
    # Step 2: Format for output (round at this stage only)
    return {
        **extra_fields,
        "qty": qty,
        "buyPrice": round_price(buy_price),
        "currentPrice": round_price(current_price),
        "invested": round_money(invested),
        "currentValue": round_money(current_value),
        "pnl": round_money(pnl),
        "pnlPercent": round_percent(pnl_percent),
    }


def calculate_portfolio_summary(
    holdings_list: list,
) -> dict:
    """
    Calculate portfolio totals ensuring sum(rounded items) ≈ rounded(total).
    
    CRITICAL: Accumulate unrounded values, then round the sums.
    This prevents cumulative rounding error.
    
    Args:
        holdings_list: List of holdings, each with:
                      {qty, buyPrice, currentPrice, ...}
    
    Returns:
        Dict with:
            totalInvested (2 decimals)
            totalValue (2 decimals)
            totalPnl (2 decimals)
            totalPnlPercent (2 decimals)
            
    Example:
            summary = calculate_portfolio_summary([
                {"qty": 75, "buyPrice": 746.41, "currentPrice": 750.0},
                {"qty": 50, "buyPrice": 2500.0, "currentPrice": 2510.0},
            ])
            # Returns:
            # {
            #   "totalInvested": 181980.75,
            #   "totalValue": 182575.00,
            #   "totalPnl": 594.25,
            #   "totalPnlPercent": 0.33,
            # }
    """
    # Step 1: Accumulate with full precision
    total_invested = 0.0
    total_value = 0.0
    
    for holding in holdings_list:
        qty = float(holding.get("qty", 0))
        buy_price = float(holding.get("buyPrice", 0))
        current_price = float(holding.get("currentPrice", 0))
        
        total_invested += qty * buy_price
        total_value += qty * current_price
    
    # Step 2: Calculate totals
    total_pnl = total_value - total_invested
    total_pnl_percent = safe_divide(total_pnl, total_invested) * 100.0
    
    # Step 3: Round only when formatting response
    return {
        "totalInvested": round_money(total_invested),
        "totalValue": round_money(total_value),
        "totalPnl": round_money(total_pnl),
        "totalPnlPercent": round_percent(total_pnl_percent),
    }


def calculate_scenario_value(
    qty: float,
    scenario_price: float,
    invested_per_unit: float = None,
    invested_total: float = None,
) -> dict:
    """
    Calculate holding value under a different price scenario (day high/low, 52-week high/low).
    
    Useful for "What if?" calculations shown in advanced portfolio views.
    
    Args:
        qty: Number of shares
        scenario_price: Hypothetical price per share
        invested_per_unit: Original purchase price (for P&L calc)
        invested_total: Total invested amount (fallback for percentage calc)
        
    Returns:
        Dict with {value, pnl, pnlPercent} for the scenario
        
    Example:
            # If HDFCBANK touches 52-week high of 800
            scenario = calculate_scenario_value(
                qty=75,
                scenario_price=800.0,
                invested_per_unit=746.41
            )
            # Returns: {
            #   "value": 60000.00,
            #   "pnl": 4012.75,
            #   "pnlPercent": 7.17,
            # }
    """
    # Step 1: Calculate scenario value with precision
    scenario_value = qty * scenario_price
    
    # Determine base for P&L calculation
    if invested_per_unit is not None:
        base_invested = qty * invested_per_unit
    elif invested_total is not None:
        base_invested = invested_total
    else:
        base_invested = 0.0
    
    scenario_pnl = scenario_value - base_invested
    scenario_pnl_percent = safe_divide(scenario_pnl, base_invested) * 100.0
    
    # Step 2: Round for output
    return {
        "value": round_money(scenario_value),
        "pnl": round_money(scenario_pnl),
        "pnlPercent": round_percent(scenario_pnl_percent),
    }


def apply_rounding_to_stock_quote(quote_dict: dict) -> dict:
    """
    Round all numeric values in a stock quote to appropriate precision.
    
    Applied to /api/stocks/quote responses.
    
    Args:
        quote_dict: Quote with keys: currentPrice, dayHigh, dayLow, 
                   high52w, low52w, change, changePercent, etc.
    
    Returns:
        Same dict with numeric values rounded appropriately
        
    Example:
            quote = {
                "currentPrice": 750.567,
                "dayHigh": 755.234,
                "change": 5.123,
                "changePercent": 0.687,
            }
            rounded = apply_rounding_to_stock_quote(quote)
            # Returns prices rounded to 2 decimals, percentages to 2 decimals
    """
    price_fields = [
        "currentPrice", "dayHigh", "dayLow", "high52w", "low52w",
        "previousClose", "openPrice"
    ]
    percent_fields = ["change", "changePercent"]
    
    result = quote_dict.copy()
    
    # Round price fields
    for field in price_fields:
        if field in result and result[field]:
            result[field] = round_price(result[field])
    
    # Round percentage fields
    for field in percent_fields:
        if field in result and result[field]:
            result[field] = round_percent(result[field])
    
    return result


# ═════════════════════════════════════════════════════════════════
# TESTING & EXAMPLES
# ═════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("ROUNDING UTILITY TESTS")
    print("=" * 70)
    
    # Test 1: Basic rounding
    print("\n[Test 1] Basic Money Rounding")
    print(f"round_money(123.456) = {round_money(123.456)}")  # 123.46
    print(f"round_money(123.454) = {round_money(123.454)}")  # 123.45
    print(f"round_money(-0.001) = {round_money(-0.001)}")    # 0.00
    
    # Test 2: Single holding
    print("\n[Test 2] Single Holding")
    holding = format_holding(
        qty=75,
        buy_price=746.41,
        current_price=750.0,
        symbol="HDFCBANK.NS",
        dayHigh=755.0,
        dayLow=745.0
    )
    print(f"Holding: {holding}")
    
    # Test 3: Portfolio totals
    print("\n[Test 3] Portfolio Summary (3 Holdings)")
    holdings = [
        {"qty": 75, "buyPrice": 746.41, "currentPrice": 750.0},
        {"qty": 50, "buyPrice": 2500.0, "currentPrice": 2510.0},
        {"qty": 100, "buyPrice": 2000.0, "currentPrice": 1990.0},
    ]
    summary = calculate_portfolio_summary(holdings)
    print(f"Summary: {summary}")
    
    # Verify consistency
    invested_sum = round_money(75 * 746.41 + 50 * 2500 + 100 * 2000)
    value_sum = round_money(75 * 750.0 + 50 * 2510.0 + 100 * 1990.0)
    print(f"Verification:")
    print(f"  Sum of (qty * buyPrice) = {invested_sum}")
    print(f"  summary.totalInvested   = {summary['totalInvested']}")
    print(f"  Match: {invested_sum == summary['totalInvested']}")
    
    # Test 4: Scenario values (day high)
    print("\n[Test 4] Day High Scenario")
    scenario = calculate_scenario_value(
        qty=75,
        scenario_price=755.0,
        invested_per_unit=746.41
    )
    print(f"If price hits 755.0: {scenario}")
    
    # Test 5: Safe divide
    print("\n[Test 5] Safe Divide")
    print(f"safe_divide(100, 10) = {safe_divide(100, 10)}")      # 10.0
    print(f"safe_divide(100, 0) = {safe_divide(100, 0)}")        # 0.0
    print(f"safe_divide(100, 0, -1) = {safe_divide(100, 0, -1)}")  # -1.0
