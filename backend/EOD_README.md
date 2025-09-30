# EOD Stooq Pipeline

This document describes the End-of-Day (EOD) data pipeline that fetches daily price data from Stooq.com.

## Feature Flags

The EOD pipeline is controlled by the following environment variables:

- `EOD_ENABLE` (default: `false`) - Enable/disable the entire EOD pipeline
- `EOD_SOURCE` (default: `stooq`) - Data source (currently only 'stooq' is supported)
- `EOD_SCHEDULE_CRON` (default: `30 23 * * *`) - CRON schedule for automatic refresh (23:30 Europe/Warsaw)
- `STQ_TIMEOUT` (default: `10`) - Timeout in seconds for Stooq API requests
- `ADMIN_TOKEN` - Required for manual EOD refresh endpoints

## Usage

### Automatic Refresh

When `EOD_ENABLE=true`, the system automatically fetches EOD data daily according to the CRON schedule:

```bash
# Enable EOD with default settings
export EOD_ENABLE=true
export ADMIN_TOKEN=your-secret-token

# Start Celery beat scheduler
celery -A app.celery_app beat --loglevel=info

# Start Celery worker
celery -A app.celery_app worker --loglevel=info
```

### Manual Refresh

Trigger EOD refresh manually via API:

```bash
# Trigger EOD refresh
curl -X POST "http://localhost:8001/admin/eod/refresh" \
  -H "X-Admin-Token: your-secret-token" \
  -H "Content-Type: application/json"

# Check task status
curl "http://localhost:8001/admin/eod/status/{task_id}" \
  -H "X-Admin-Token: your-secret-token"

# View current configuration
curl "http://localhost:8001/admin/eod/config" \
  -H "X-Admin-Token: your-secret-token"
```

### Environment Configuration

Add to your `.env` file:

```env
# EOD Configuration
EOD_ENABLE=true
EOD_SOURCE=stooq
EOD_SCHEDULE_CRON=30 23 * * *
STQ_TIMEOUT=10
ADMIN_TOKEN=your-secret-admin-token
```

## Architecture

### Components

1. **Stooq Client** (`app/quotes/stooq.py`)
   - Fetches CSV data from Stooq.com
   - Normalizes data format
   - Handles errors and timeouts

2. **PriceEOD Repository** (`app/services/price_eod.py`)
   - Database operations for price data
   - Upsert functionality to prevent duplicates
   - Query methods for historical data

3. **Celery Tasks** (`app/tasks/fetch_eod.py`)
   - `run_eod_refresh` - Main refresh task with feature flag checks
   - `fetch_eod_for_symbols` - Legacy task for manual symbol fetching
   - Retry logic with exponential backoff

4. **Admin API** (`app/routers/admin_eod.py`)
   - Manual trigger endpoints
   - Task status monitoring
   - Configuration viewing

5. **Celery Beat** (`app/celery_app.py`)
   - Scheduled task execution
   - Feature flag-aware scheduling

### Data Flow

1. Celery Beat triggers `run_eod_refresh` task at scheduled time
2. Task checks feature flags (`EOD_ENABLE`, `EOD_SOURCE`)
3. Discovers symbols from existing positions in database
4. For each symbol:
   - Fetches data from Stooq using `fetch_eod()`
   - Retries on failure with exponential backoff
   - Upserts data to database via `PriceEODRepository`
5. Logs results and continues with next symbol on individual failures

### Error Handling

- **Network errors**: Retry with exponential backoff (1s, 3s, 9s)
- **Invalid symbols**: Log error and continue with other symbols
- **Database errors**: Log error and continue
- **Feature disabled**: Graceful exit with informative message

### Logging

All operations are logged with appropriate levels:

- `INFO`: Task start/completion, successful symbol processing
- `WARNING`: Retry attempts, invalid symbols, configuration issues
- `ERROR`: Failed operations, unexpected errors
- `DEBUG`: Detailed operation steps, retry delays

## Testing

Run smoke tests to verify functionality:

```bash
# Run EOD-specific tests
pytest backend/tests/test_stooq_client_smoke.py -v

# Run all tests
pytest backend/tests/ -v
```

## Troubleshooting

### Common Issues

1. **EOD not running automatically**
   - Check `EOD_ENABLE=true` in environment
   - Verify Celery beat is running
   - Check logs for configuration warnings

2. **Manual refresh fails**
   - Verify `ADMIN_TOKEN` is set and correct
   - Check API endpoint is accessible
   - Review task logs for specific errors

3. **No data for symbols**
   - Verify symbols exist in positions table
   - Check Stooq.com has data for the symbol
   - Review network connectivity and timeout settings

4. **Database errors**
   - Ensure database is accessible
   - Check `prices_eod` table exists
   - Verify database permissions

### Monitoring

- Check Celery task status via admin API
- Monitor application logs for EOD-related messages
- Verify data in `prices_eod` table
- Use Flower (if enabled) to monitor Celery tasks





