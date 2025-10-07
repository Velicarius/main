import logging
from datetime import date
from decimal import Decimal
from typing import Dict, Any, List

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.services.price_eod import PriceEODRepository
from app.services.portfolio_valuation_eod import PortfolioValuationEODRepository
from app.models.position import Position

logger = logging.getLogger(__name__)

# Import Celery app
from app.celery_app import celery_app


@celery_app.task(name="portfolio.save_daily_valuations", bind=True)
def save_daily_valuations(self) -> Dict[str, Any]:
    """
    Calculate and save daily portfolio valuations for all users.

    This task:
    1. Gets all unique user_ids from positions
    2. For each user, calculates total portfolio value using latest EOD prices
    3. Saves valuation to portfolio_valuations_eod table

    Returns:
        Summary dictionary with saved count, results, and errors
    """
    logger.info("Starting daily portfolio valuation task")

    db = SessionLocal()
    try:
        price_repo = PriceEODRepository(db)
        pv_repo = PortfolioValuationEODRepository(db)

        # Get all unique user_ids from positions
        user_ids = [row[0] for row in db.query(Position.user_id).distinct().all()]

        if not user_ids:
            logger.warning("No users found with positions")
            return {
                "status": "no_users",
                "message": "No users found with positions",
                "saved": 0,
                "results": [],
                "errors": []
            }

        logger.info(f"Processing portfolio valuations for {len(user_ids)} users")

        saved = 0
        results = []
        errors = []

        for uid in user_ids:
            try:
                # Get all positions for this user
                positions = db.query(Position).filter(Position.user_id == uid).all()

                if not positions:
                    logger.debug(f"User {uid} has no positions, skipping")
                    continue

                # Calculate total portfolio value
                total = Decimal("0")
                used_dates = []
                missing_symbols = []

                for pos in positions:
                    sym = (pos.symbol or "").strip().lower()

                    # Skip USD positions (cash)
                    if sym == "usd":
                        continue

                    # Get latest EOD price for this symbol
                    last_price = price_repo.get_latest_price(sym)

                    if not last_price:
                        missing_symbols.append(sym)
                        logger.warning(f"No EOD price found for symbol {sym} (user {uid})")
                        continue

                    # Add to total value
                    total += Decimal(str(pos.quantity)) * Decimal(str(last_price.close))
                    used_dates.append(last_price.date)

                # Skip if no prices were found
                if not used_dates:
                    results.append({
                        "user_id": str(uid),
                        "skipped": True,
                        "reason": "no_prices",
                        "missing_symbols": missing_symbols
                    })
                    continue

                # Use the most recent date from all price data
                as_of = max(used_dates)

                # Save valuation to database
                pv_repo.upsert(uid, as_of, total, currency="USD")

                results.append({
                    "user_id": str(uid),
                    "as_of": str(as_of),
                    "total_value": float(total),
                    "positions_count": len(positions) - len(missing_symbols)
                })
                saved += 1
                logger.info(f"Saved valuation for user {uid}: ${float(total):,.2f} as of {as_of}")

            except Exception as e:
                error_msg = f"Failed to save valuation for user {uid}: {str(e)}"
                logger.error(error_msg)
                errors.append({"user_id": str(uid), "error": str(e)})

        result = {
            "status": "completed",
            "message": f"Processed {len(user_ids)} users, saved {saved} valuations",
            "saved": saved,
            "results": results,
            "errors": errors
        }

        logger.info(f"Portfolio valuation task completed: {result}")
        return result

    finally:
        db.close()
