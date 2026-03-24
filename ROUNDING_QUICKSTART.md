# Quick Start: Financial Rounding API

## Test the Implementation

### 1. Run Local Tests

```bash
cd backend
python test_rounding.py
```

**Expected Output:**
```
✅ ALL TESTS PASSED - Implementation is correct!
```

### 2. Start the Backend Server

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:7860
INFO:     Application startup complete
```

### 3. Test the Portfolio Endpoint

#### Using cURL:
```bash
curl -X POST http://localhost:7860/api/stocks/portfolio \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio": [
      {
        "symbol": "HDFCBANK.NS",
        "qty": 75,
        "buyPrice": 746.41
      },
      {
        "symbol": "INFY.NS",
        "qty": 50,
        "buyPrice": 1820.00
      },
      {
        "symbol": "ITC.NS",
        "qty": 100,
        "buyPrice": 465.50
      }
    ]
  }'
```

#### Using Python:
```python
import requests
import json

url = "http://localhost:7860/api/stocks/portfolio"
payload = {
    "portfolio": [
        {"symbol": "HDFCBANK.NS", "qty": 75, "buyPrice": 746.41},
        {"symbol": "INFY.NS", "qty": 50, "buyPrice": 1820.00},
        {"symbol": "ITC.NS", "qty": 100, "buyPrice": 465.50}
    ]
}

response = requests.post(url, json=payload)
data = response.json()

print("Holdings:")
for holding in data["holdings"]:
    print(f"  {holding['symbol']}: ₹{holding['currentValue']} (P&L: {holding['pnlPercent']}%)")

print(f"\nPortfolio Summary:")
print(f"  Total Invested: ₹{data['summary']['totalInvested']}")
print(f"  Total Value: ₹{data['summary']['totalValue']}")
print(f"  Total P&L: ₹{data['summary']['totalPnl']} ({data['summary']['totalPnlPercent']}%)")

# Verify consistency
total_from_items = sum(h['currentValue'] for h in data['holdings'])
print(f"\n✓ Consistency Check:")
print(f"  Sum of item values: ₹{total_from_items:.2f}")
print(f"  Portfolio total: ₹{data['summary']['totalValue']}")
print(f"  Match: {abs(total_from_items - data['summary']['totalValue']) < 0.01}")
```

#### Expected Response:
```json
{
  "holdings": [
    {
      "symbol": "HDFCBANK.NS",
      "qty": 75,
      "buyPrice": 746.41,
      "currentPrice": 752.15,
      "invested": 55980.75,
      "currentValue": 56411.25,
      "pnl": 430.50,
      "pnlPercent": 0.77,
      "dayHigh": 755.67,
      "dayLow": 748.00,
      "high52w": 1234.56,
      "low52w": 645.00,
      ...
    },
    ...
  ],
  "summary": {
    "totalInvested": 193530.75,
    "totalValue": 197445.32,
    "totalPnl": 3914.57,
    "totalPnlPercent": 2.02
  }
}
```

### 4. Test the New Scenarios Endpoint

#### Using cURL:
```bash
curl -X POST http://localhost:7860/api/stocks/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio": [
      {
        "symbol": "HDFCBANK.NS",
        "qty": 75,
        "buyPrice": 746.41
      }
    ]
  }'
```

#### Using Python:
```python
import requests

url = "http://localhost:7860/api/stocks/scenarios"
payload = {
    "portfolio": [
        {"symbol": "HDFCBANK.NS", "qty": 75, "buyPrice": 746.41}
    ]
}

response = requests.post(url, json=payload)
data = response.json()

holding = data["holdings"][0]
print(f"Scenarios for {holding['symbol']}:")
print(f"  Current: ₹{holding['scenarios']['current']['value']} (P&L: ₹{holding['scenarios']['current']['pnl']})")
print(f"  Day High: ₹{holding['scenarios']['dayHigh']['value']} (P&L: ₹{holding['scenarios']['dayHigh']['pnl']})")
print(f"  Day Low: ₹{holding['scenarios']['dayLow']['value']} (P&L: ₹{holding['scenarios']['dayLow']['pnl']})")
print(f"  52W High: ₹{holding['scenarios']['high52w']['value']} (P&L: ₹{holding['scenarios']['high52w']['pnl']})")
print(f"  52W Low: ₹{holding['scenarios']['low52w']['value']} (P&L: ₹{holding['scenarios']['low52w']['pnl']})")

summary = data["scenarioSummary"]
print(f"\nPortfolio Summary:")
print(f"  At Current: ₹{summary['atCurrent']['value']} (+{summary['atCurrent']['pnlPercent']}%)")
print(f"  At Day High: ₹{summary['atDayHigh']['value']} (+{summary['atDayHigh']['pnlPercent']}%)")
print(f"  At Day Low: ₹{summary['atDayLow']['value']} ({summary['atDayLow']['pnlPercent']}%)")
print(f"  At 52W High: ₹{summary['at52wHigh']['value']} (+{summary['at52wHigh']['pnlPercent']}%)")
print(f"  At 52W Low: ₹{summary['at52wLow']['value']} ({summary['at52wLow']['pnlPercent']}%)")
```

#### Expected Response:
```json
{
  "holdings": [
    {
      "symbol": "HDFCBANK.NS",
      "qty": 75,
      "buyPrice": 746.41,
      "invested": 55980.75,
      "scenarios": {
        "current": {
          "value": 56411.25,
          "pnl": 430.50,
          "pnlPercent": 0.77
        },
        "dayHigh": {
          "price": 755.67,
          "value": 56675.25,
          "pnl": 694.50,
          "pnlPercent": 1.24
        },
        "dayLow": {
          "price": 748.00,
          "value": 56100.00,
          "pnl": 119.25,
          "pnlPercent": 0.21
        },
        "high52w": {
          "price": 1234.56,
          "value": 92592.00,
          "pnl": 36611.25,
          "pnlPercent": 65.36
        },
        "low52w": {
          "price": 645.00,
          "value": 48375.00,
          "pnl": -7605.75,
          "pnlPercent": -13.59
        }
      }
    }
  ],
  "scenarioSummary": {
    "totalInvested": 55980.75,
    "atCurrent": {...},
    "atDayHigh": {...},
    "atDayLow": {...},
    "at52wHigh": {...},
    "at52wLow": {...}
  }
}
```

---

## Integration with Frontend

### React/SWR Example:

```typescript
import useSWR from 'swr';

interface Portfolio {
  portfolio: Array<{
    symbol: string;
    qty: number;
    buyPrice: number;
  }>;
}

interface PortfolioResponse {
  holdings: any[];
  summary: {
    totalInvested: number;
    totalValue: number;
    totalPnl: number;
    totalPnlPercent: number;
  };
}

function Dashboard({ portfolio }: { portfolio: Portfolio }) {
  const { data, error, isLoading } = useSWR<PortfolioResponse>(
    ['/api/stocks/portfolio', portfolio],
    ([url, payload]) =>
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).then(r => r.json())
  );

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!data) return null;

  return (
    <div>
      <h2>Portfolio</h2>
      <div className="summary">
        <p>Total Value: ₹{data.summary.totalValue.toFixed(2)}</p>
        <p>Total P&L: ₹{data.summary.totalPnl.toFixed(2)} ({data.summary.totalPnlPercent.toFixed(2)}%)</p>
      </div>
      
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Qty</th>
            <th>Buy Price</th>
            <th>Current Price</th>
            <th>Current Value</th>
            <th>P&L</th>
            <th>P&L %</th>
          </tr>
        </thead>
        <tbody>
          {data.holdings.map(holding => (
            <tr key={holding.symbol}>
              <td>{holding.symbol}</td>
              <td>{holding.qty}</td>
              <td>₹{holding.buyPrice.toFixed(2)}</td>
              <td>₹{holding.currentPrice.toFixed(2)}</td>
              <td>₹{holding.currentValue.toFixed(2)}</td>
              <td className={holding.pnl >= 0 ? 'positive' : 'negative'}>
                ₹{holding.pnl.toFixed(2)}
              </td>
              <td className={holding.pnlPercent >= 0 ? 'positive' : 'negative'}>
                {holding.pnlPercent.toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Dashboard;
```

---

## Verify Rounding Consistency

All endpoints now guarantee:
```
sum(round(each holding)) ≈ round(total portfolio)
```

**Example Verification:**
```python
# After getting portfolio response
holdings = response['holdings']
summary = response['summary']

item_sum = sum(h['currentValue'] for h in holdings)
total = summary['totalValue']

# Should be equal (within ₹0.01 rounding tolerance)
assert abs(item_sum - total) < 0.01, f"Mismatch: {item_sum} vs {total}"
print("✓ Rounding consistency verified!")
```

---

## API Documentation

### POST /api/stocks/portfolio
Calculate portfolio with P&L metrics.

**Request:**
```json
{
  "portfolio": [
    {
      "symbol": "HDFCBANK.NS",
      "qty": 75,
      "buyPrice": 746.41
    }
  ]
}
```

**Response:**
- `holdings[]` - Array of holdings with P&L calculations
  - `symbol` - Stock symbol
  - `qty` - Number of shares
  - `buyPrice` - Purchase price per share (₹)
  - `currentPrice` - Current market price (₹)
  - `invested` - Total investment (₹)
  - `currentValue` - Current portfolio value (₹)
  - `pnl` - Profit/Loss in rupees (₹)
  - `pnlPercent` - Profit/Loss percentage (%)
  - `dayHigh`, `dayLow`, `high52w`, `low52w` - Price levels
  - `history` - Last 30 days closing prices

- `summary` - Portfolio totals
  - `totalInvested` - Total amount invested (₹)
  - `totalValue` - Current total value (₹)
  - `totalPnl` - Total profit/loss (₹)
  - `totalPnlPercent` - Total return percentage (%)

---

### POST /api/stocks/scenarios (NEW)
Calculate portfolio value at different price scenarios.

**Request:** (Same as /api/stocks/portfolio)

**Response:**
- `holdings[]` - Array with scenario analysis
  - `symbol` - Stock symbol
  - `scenarios` - Price scenarios
    - `current` - At current price
    - `dayHigh` - If price reaches day high
    - `dayLow` - If price reaches day low
    - `high52w` - If price reaches 52-week high
    - `low52w` - If price reaches 52-week low
  - Each scenario includes `value`, `pnl`, `pnlPercent`

- `scenarioSummary` - Portfolio totals at each scenario

---

## Troubleshooting

### Issue: Values don't match between frontend and backend
**Solution:** Clear cache and restart backend
```bash
curl http://localhost:7860/api/stocks/cache/clear
```

### Issue: Portfolio total doesn't equal sum of holdings
**Status:** This should NOT happen anymore!
- If it does, take a screenshot and file an issue
- All tests verify this consistency

### Issue: Very small values showing as -₹0.00
**Status:** Fixed! Rounding now avoids negative zero

### Issue: Percentage values seem off
**Solution:** Check that percentages are being rounded to 2 decimals, not 4
- Use `round_percent()` function
- All API responses now return 2 decimals

---

## Files Reference

| File | Purpose | Size |
|------|---------|------|
| `backend/rounding.py` | Rounding utilities | 220 lines |
| `backend/test_rounding.py` | Test suite | 450 lines |
| `backend/ROUNDING_GUIDE.md` | Detailed documentation | 500+ lines |
| `backend/main.py` | Updated endpoints | Modified |
| `ROUNDING_IMPLEMENTATION_SUMMARY.md` | This project summary | 300+ lines |

---

## Next Steps

1. ✅ Run tests locally
2. ✅ Test all endpoints with sample data
3. ✅ Verify consistency checks pass
4. ✅ Deploy to Hugging Face Spaces (auto-deployed on git push)
5. ✅ Update frontend to use API responses
6. ✅ Monitor for any issues

---

**Status:** Production-Ready ✓
