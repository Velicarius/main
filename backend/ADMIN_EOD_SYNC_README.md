# Synchronous EOD Refresh Endpoint

This document describes the new synchronous EOD refresh endpoint that allows fetching the latest daily price data for a specific symbol.

## Endpoint

**POST** `/admin/eod/{symbol}/refresh-sync`

### Description
Synchronously fetches the latest daily price data from Stooq.com for a specific symbol and stores it in the database.

### Parameters
- `symbol` (path parameter): Stock symbol (e.g., `aapl`, `msft`, `googl`)
- `X-Admin-Token` (header): Admin authentication token

### Response
```json
{
  "status": "ok",
  "symbol": "aapl",
  "as_of": "2024-01-15",
  "records_processed": 1,
  "source": "stooq"
}
```

### Error Responses

#### 403 Forbidden
```json
{
  "detail": "Forbidden"
}
```
When `X-Admin-Token` header is missing or invalid.

#### 404 Not Found
```json
{
  "detail": "No EOD data from Stooq for aapl"
}
```
When no data is available for the symbol.

#### 502 Bad Gateway
```json
{
  "detail": "Failed to fetch aapl from Stooq: Network error"
}
```
When there's a network error or malformed data from Stooq.

## Usage Examples

### cURL
```bash
# Fetch latest data for AAPL
curl -X POST "http://localhost:8001/admin/eod/aapl/refresh-sync" \
  -H "X-Admin-Token: your-admin-token" \
  -H "Content-Type: application/json"

# Fetch latest data for Microsoft
curl -X POST "http://localhost:8001/admin/eod/msft/refresh-sync" \
  -H "X-Admin-Token: your-admin-token"
```

### Python
```python
import requests

headers = {"X-Admin-Token": "your-admin-token"}
response = requests.post(
    "http://localhost:8001/admin/eod/aapl/refresh-sync",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(f"Updated {data['symbol']} as of {data['as_of']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## Implementation Details

### Stooq Client
- **File**: `app/marketdata/stooq_client.py`
- **Dependencies**: None (uses only Python standard library)
- **Function**: `fetch_latest_from_stooq(symbol, timeout=10)`
- **Data Source**: `https://stooq.com/q/d/l/?s={symbol}&i=d`

### Admin Route
- **File**: `app/api/routes/admin_eod_sync.py`
- **Authentication**: `X-Admin-Token` header
- **Database**: Uses `PriceEODRepository.upsert_prices()`
- **Symbol Processing**: Converts to lowercase (Stooq preference)

### Data Format
The endpoint fetches CSV data from Stooq and converts it to:
```python
{
    "date": date(2024, 1, 15),
    "open": 150.0,
    "high": 155.0,
    "low": 148.0,
    "close": 152.0,
    "volume": 1000000,
    "source": "stooq"
}
```

## Environment Variables

Required environment variable:
- `ADMIN_TOKEN`: Secret token for admin authentication

## Testing

Run the tests to verify functionality:
```bash
pytest backend/tests/test_admin_eod_sync.py -v
```

## Notes

- Symbols are automatically converted to lowercase (Stooq.com preference)
- The endpoint uses upsert logic to prevent duplicate entries
- Network timeout is set to 10 seconds by default
- Only the latest daily record is fetched and stored
- No external dependencies required (uses Python standard library only)





