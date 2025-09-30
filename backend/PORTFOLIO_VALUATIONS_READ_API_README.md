# Portfolio Valuations EOD Read API

This document describes the REST endpoints for reading End-of-Day (EOD) portfolio valuations.

## Endpoints

### 1. List Portfolio Valuations

**GET** `/portfolio-valuations/{user_id}`

#### Description
Retrieves a list of portfolio valuations for a specific user, optionally filtered by date range.

#### Parameters
- `user_id` (path parameter): User UUID
- `start_date` (query parameter, optional): Start date filter (YYYY-MM-DD)
- `end_date` (query parameter, optional): End date filter (YYYY-MM-DD)

#### Response
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "b3ae7081-fc71-499b-b46b-4f51156b537e",
    "as_of": "2024-01-15",
    "total_value": "2500.50",
    "currency": "USD",
    "created_at": "2024-01-15T23:30:00"
  },
  {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "user_id": "b3ae7081-fc71-499b-b46b-4f51156b537e",
    "as_of": "2024-01-16",
    "total_value": "2550.75",
    "currency": "USD",
    "created_at": "2024-01-16T23:30:00"
  }
]
```

### 2. Latest Portfolio Valuation

**GET** `/portfolio-valuations/{user_id}/latest`

#### Description
Retrieves the most recent portfolio valuation for a specific user.

#### Parameters
- `user_id` (path parameter): User UUID

#### Response
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "user_id": "b3ae7081-fc71-499b-b46b-4f51156b537e",
  "as_of": "2024-01-16",
  "total_value": "2550.75",
  "currency": "USD",
  "created_at": "2024-01-16T23:30:00"
}
```

#### Error Response
```json
{
  "detail": "No valuation found"
}
```
When no portfolio valuations exist for the user (404 status).

## Usage Examples

### PowerShell
```powershell
# List all valuations for a user
Invoke-RestMethod -Uri "http://localhost:8001/portfolio-valuations/b3ae7081-fc71-499b-b46b-4f51156b537e" | ConvertTo-Json -Depth 6

# List valuations for a date range
Invoke-RestMethod -Uri "http://localhost:8001/portfolio-valuations/b3ae7081-fc71-499b-b46b-4f51156b537e?start_date=2024-01-01&end_date=2024-01-31" | ConvertTo-Json -Depth 6

# Get latest valuation
Invoke-RestMethod -Uri "http://localhost:8001/portfolio-valuations/b3ae7081-fc71-499b-b46b-4f51156b537e/latest" | ConvertTo-Json -Depth 6
```

### cURL
```bash
# List all valuations
curl "http://localhost:8001/portfolio-valuations/b3ae7081-fc71-499b-b46b-4f51156b537e"

# List valuations with date filter
curl "http://localhost:8001/portfolio-valuations/b3ae7081-fc71-499b-b46b-4f51156b537e?start_date=2024-01-01&end_date=2024-01-31"

# Get latest valuation
curl "http://localhost:8001/portfolio-valuations/b3ae7081-fc71-499b-b46b-4f51156b537e/latest"
```

### Python
```python
import requests
from uuid import UUID

user_id = "b3ae7081-fc71-499b-b46b-4f51156b537e"
base_url = "http://localhost:8001"

# List all valuations
response = requests.get(f"{base_url}/portfolio-valuations/{user_id}")
if response.status_code == 200:
    valuations = response.json()
    print(f"Found {len(valuations)} valuations")
    for val in valuations:
        print(f"  {val['as_of']}: ${val['total_value']}")

# List valuations with date filter
params = {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
}
response = requests.get(f"{base_url}/portfolio-valuations/{user_id}", params=params)
if response.status_code == 200:
    valuations = response.json()
    print(f"Found {len(valuations)} valuations in date range")

# Get latest valuation
response = requests.get(f"{base_url}/portfolio-valuations/{user_id}/latest")
if response.status_code == 200:
    latest = response.json()
    print(f"Latest valuation: ${latest['total_value']} as of {latest['as_of']}")
elif response.status_code == 404:
    print("No valuations found for user")
```

## Implementation Details

### Repository Layer
- **File**: `app/services/portfolio_valuation_eod.py`
- **Class**: `PortfolioValuationEODRepository`
- **Methods**:
  - `list_by_user(user_id, start_date=None, end_date=None)` - Returns list of valuations
  - `latest_by_user(user_id)` - Returns most recent valuation or None

### Schema Layer
- **File**: `app/schemas.py`
- **Class**: `PortfolioValuationEODOut`
- **Fields**: `id`, `user_id`, `as_of`, `total_value`, `currency`, `created_at`

### Route Layer
- **File**: `app/routers/portfolio_valuations.py`
- **Endpoints**:
  - `GET /portfolio-valuations/{user_id}` - List valuations
  - `GET /portfolio-valuations/{user_id}/latest` - Latest valuation

### Database Queries
- **List Query**: Filters by `user_id`, optional date range, orders by `as_of` ASC
- **Latest Query**: Filters by `user_id`, orders by `as_of` DESC, takes first result

## Data Flow

```
Client Request → FastAPI Router → Repository → Database → Response
     ↓                ↓              ↓           ↓         ↓
  user_id         validation      SQL query   results   JSON schema
  date filters    UUID parsing    filtering   mapping   serialization
```

## Error Handling

### 404 Not Found
- **Latest Endpoint**: When no valuations exist for the user
- **List Endpoint**: Returns empty array (not 404)

### 422 Validation Error
- **Invalid UUID**: When `user_id` is not a valid UUID format
- **Invalid Date**: When date parameters are not in YYYY-MM-DD format

### 500 Internal Server Error
- **Database Errors**: Connection issues, query failures
- **Serialization Errors**: Data type conversion issues

## Performance Considerations

### Query Optimization
- **Indexes**: Uses `ix_pv_user_asof` and `ix_pv_asof` indexes
- **Filtering**: Date filters reduce result set size
- **Ordering**: Efficient sorting by indexed `as_of` column

### Caching Opportunities
- **Latest Valuation**: Could be cached per user
- **Date Range Queries**: Could be cached with TTL
- **User Lists**: Could be cached for frequently accessed users

## Security Considerations

### Authentication
- **No Authentication**: Currently no auth required (public read endpoints)
- **Future Enhancement**: Could add user-based authentication

### Authorization
- **No Authorization**: Users can query any user's valuations
- **Future Enhancement**: Could restrict to own user_id only

### Data Exposure
- **Financial Data**: Portfolio values are sensitive information
- **Recommendation**: Add authentication and authorization

## Testing

### Unit Tests
```bash
pytest backend/tests/test_portfolio_valuations_read_api.py -v
```

### Integration Tests
```bash
# Test with real database
pytest backend/tests/ -k "portfolio_valuations" -v
```

### Manual Testing
```bash
# Check API endpoints are available
curl "http://localhost:8001/openapi.json" | jq '.paths | keys | map(select(contains("portfolio-valuations")))'
```

## Monitoring

### Success Indicators
- **200 Status**: Successful data retrieval
- **Empty Arrays**: Valid response for users with no data
- **404 Status**: Expected for users with no valuations

### Error Monitoring
- **500 Errors**: Database connection issues
- **422 Errors**: Invalid input parameters
- **Slow Queries**: Performance issues with large datasets

## Future Enhancements

### Features
1. **Pagination**: For users with many valuations
2. **Sorting Options**: Sort by date, value, etc.
3. **Aggregation**: Summary statistics, trends
4. **Export**: CSV/Excel export functionality

### Performance
1. **Caching**: Redis-based caching for frequent queries
2. **Database Optimization**: Additional indexes, query optimization
3. **API Rate Limiting**: Prevent abuse of read endpoints

### Security
1. **Authentication**: JWT-based user authentication
2. **Authorization**: User-based access control
3. **Audit Logging**: Track who accesses what data




