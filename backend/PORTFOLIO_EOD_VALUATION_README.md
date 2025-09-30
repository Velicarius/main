# Portfolio EOD Valuation Sync Endpoint

This document describes the new synchronous portfolio EOD valuation endpoint that calculates and saves portfolio values for all users.

## Endpoint

**POST** `/admin/portfolio/revalue-eod-sync-save`

### Description
Synchronously calculates the End-of-Day (EOD) portfolio value for all users based on their positions and the latest available price data, then saves the results to the `portfolio_valuations_eod` table.

### Parameters
- `X-Admin-Token` (header): Admin authentication token

### Response
```json
{
  "status": "ok",
  "saved": 2,
  "results": [
    {
      "user_id": "user-123",
      "as_of": "2024-01-15",
      "total_value": 2500.50
    },
    {
      "user_id": "user-456", 
      "as_of": "2024-01-15",
      "total_value": 1500.25
    }
  ],
  "errors": []
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

#### 500 Internal Server Error
```json
{
  "detail": "Database error or calculation failure"
}
```
When there's a database error or calculation failure.

## Algorithm

1. **Get All Users**: Query distinct `user_id` values from the `positions` table
2. **For Each User**:
   - Get all positions for the user
   - For each position:
     - Look up the latest price using `PriceEODRepository.get_latest_price()`
     - Calculate position value: `quantity × latest_price.close`
     - Track the price date for `as_of` calculation
   - Sum all position values to get total portfolio value
   - Set `as_of` to the maximum date among all used prices
   - Save/update the portfolio valuation using `PortfolioValuationEODRepository.upsert()`

3. **Return Results**: Summary with saved count, results, and any errors

## Data Flow

```
Positions Table → PriceEOD Table → Calculation → PortfolioValuationEOD Table
     ↓                ↓                ↓                    ↓
  user_id         latest_price    quantity × price      upsert record
  symbol          close, date     total_value          (user_id, as_of)
  quantity        source          as_of = max(dates)
```

## Database Schema

### PortfolioValuationEOD Table
```sql
CREATE TABLE portfolio_valuations_eod (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    as_of DATE NOT NULL,
    total_value NUMERIC(20,8) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_portfolio_valuations_eod_user_asof 
        UNIQUE (user_id, as_of)
);
```

## Usage Examples

### PowerShell
```powershell
# Call the endpoint
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8001/admin/portfolio/revalue-eod-sync-save" `
  -Headers @{ "X-Admin-Token" = "secret" } |
ConvertTo-Json -Depth 6

# Check database results
docker exec -it infra-postgres-1 psql -U postgres -d postgres -c `
"SELECT user_id, as_of, total_value, currency FROM portfolio_valuations_eod ORDER BY created_at DESC LIMIT 10;"
```

### cURL
```bash
curl -X POST "http://localhost:8001/admin/portfolio/revalue-eod-sync-save" \
  -H "X-Admin-Token: your-admin-token" \
  -H "Content-Type: application/json"
```

### Python
```python
import requests

headers = {"X-Admin-Token": "your-admin-token"}
response = requests.post(
    "http://localhost:8001/admin/portfolio/revalue-eod-sync-save",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(f"Saved {data['saved']} portfolio valuations")
    for result in data['results']:
        print(f"User {result['user_id']}: ${result['total_value']} as of {result['as_of']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## Implementation Details

### Repository Layer
- **File**: `app/services/portfolio_valuation_eod.py`
- **Class**: `PortfolioValuationEODRepository`
- **Method**: `upsert(user_id, as_of, total_value, currency="USD")`
- **Upsert Logic**: Uses PostgreSQL `ON CONFLICT` with unique constraint `uq_portfolio_valuations_eod_user_asof`

### Route Layer
- **File**: `app/api/routes/admin_eod_sync.py`
- **Function**: `revalue_portfolios_eod_sync_save()`
- **Authentication**: `X-Admin-Token` header verification
- **Dependencies**: Local imports to avoid circular dependencies

### Price Data Source
- Uses existing `PriceEODRepository.get_latest_price()` method
- Leverages the `.us` fallback logic for symbol resolution
- Only processes positions with available price data

## Error Handling

### Missing Price Data
- Positions without price data are skipped
- Users with no available prices are marked as `skipped` with reason `"no_prices"`

### Database Errors
- Individual user calculation errors are captured in the `errors` array
- Process continues for other users even if one fails

### Validation
- Symbol normalization: `symbol.strip().lower()`
- Decimal precision: Uses `Decimal` type for financial calculations
- Date handling: `as_of` is set to the maximum date among used prices

## Testing

Run the tests to verify functionality:
```bash
pytest backend/tests/test_portfolio_valuation_eod.py -v
```

## Monitoring

### Success Indicators
- `status: "ok"` in response
- `saved > 0` indicates successful saves
- Empty `errors` array indicates no failures

### Common Issues
1. **No positions**: Users with no positions won't appear in results
2. **Missing prices**: Positions without EOD prices are skipped
3. **Database constraints**: Unique constraint prevents duplicate entries
4. **Authentication**: Missing or invalid `ADMIN_TOKEN`

## Performance Considerations

- **Batch Processing**: Processes all users in a single request
- **Database Efficiency**: Uses upsert to avoid duplicate entries
- **Memory Usage**: Processes users sequentially to avoid memory issues
- **Error Isolation**: Individual user failures don't affect others

## Security

- **Authentication Required**: Admin token verification
- **No User Input**: No user-provided parameters to validate
- **Read-Only Operations**: Only reads positions and prices
- **Controlled Writes**: Only writes to portfolio valuations table




