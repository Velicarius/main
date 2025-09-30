import logging
from sqlalchemy.orm import Session
from app.models.position import Position
from app.models.user import User

log = logging.getLogger(__name__)

DEMO_POSITIONS = [
    {"symbol": "AAPL.US", "quantity": 10, "buy_price": 150.0, "currency": "USD", "account": "demo"},
    {"symbol": "MSFT.US", "quantity": 5, "buy_price": 300.0, "currency": "USD", "account": "demo"},
    {"symbol": "TSLA.US", "quantity": 3, "buy_price": 700.0, "currency": "USD", "account": "demo"},
]

DEMO_USER_EMAIL = "demo@example.com"


def seed_demo_user(db: Session):
    """Create a demo user if it doesn't exist"""
    existing_user = db.query(User).filter_by(email=DEMO_USER_EMAIL).first()
    if not existing_user:
        demo_user = User(email=DEMO_USER_EMAIL)
        db.add(demo_user)
        db.commit()
        log.info("Created demo user")
        return demo_user
    return existing_user


def seed_positions(db: Session):
    """Seed demo positions if they don't exist"""
    # Ensure demo user exists
    demo_user = seed_demo_user(db)
    
    seeded_count = 0
    for row in DEMO_POSITIONS:
        exists = db.query(Position).filter_by(
            symbol=row["symbol"], 
            account=row["account"],
            user_id=demo_user.id
        ).first()
        
        if not exists:
            position = Position(
                user_id=demo_user.id,
                symbol=row["symbol"],
                quantity=row["quantity"],
                buy_price=row["buy_price"],
                currency=row["currency"],
                account=row["account"]
            )
            db.add(position)
            seeded_count += 1
    
    if seeded_count > 0:
        db.commit()
        log.info(f"Seeded {seeded_count} demo positions")
    else:
        log.info("Demo positions already exist, skipping seed")


def seed_demo_data(db: Session):
    """Main seeding function"""
    try:
        seed_positions(db)
        log.info("Demo data seeding completed successfully")
    except Exception as e:
        log.error(f"Error seeding demo data: {e}")
        db.rollback()
        raise









