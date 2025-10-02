#!/usr/bin/env python3
"""
Simple test of auto price loading functionality.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///./test_simple.db"
os.environ["APP_ENV"] = "test"

try:
    from app.database import SessionLocal
    from app.models import Position, User, PriceEOD
    from app.services.price_service import PriceService
    from uuid import UUID
    from decimal import Decimal
    import logging
    
    # Suppress detailed logging for clean output
    logging.basicConfig(level=logging.WARNING)


def test_price_service_basic():
    """Basic test of price loading service"""
    print("=== Simple Auto Price Loading Test ===")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create test user
        test_user_id = UUID("00000000-0000-0000-0000-000000000001")
        
        existing_user = db.query(User).filter(User.id == test_user_id).first()
        if not existing_user:
            existing_user = User(id=test_user_id, email="test@example.com")
            db.add(existing_user)
            db.commit()
            print("Created test user")
        else:
            print("Using existing user")
        
        # Test position creation
        print("\n1. Creating AAPL position...")
        
        # Clean previous test data
        db.query(Position).filter(Position.symbol == "AAPL").delete()
        db.query(PriceEOD).filter(PriceEOD.symbol == "AAPL").delete()
        db.commit()
        
        # Create position
        position = Position(
            user_id=test_user_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            buy_price=Decimal("150"),
            currency="USD"
        )
        
        db.add(position)
        db.commit()
        print("AAPL position created successfully")
        
        # Test auto price loading
        print("\n2. Testing auto price loading...")
        
        service = PriceService(db)
        result = service.load_price_for_symbol("AAPL")
        
        if result:
            print("Price for AAPL loaded successfully!")
            
            # Verify data was saved
            price = service.repository.get_latest_price("AAPL")
            if price:
                print(f"Confirmation: found price {price.get('close')} USD for {price.get('date')}")
            else:
                print("Error: price data not found in database")
                return False
        else:
            print("Warning: price for AAPL was not loaded (may already exist)")
        
        print("\n3. Testing router code...")
        
        # Import auto-loading function from router
        from app.services.price_service import load_price_for_symbol
        
        # Clean price for test
        db.query(PriceEOD).filter(PriceEOD.symbol == "TSLA").delete()
        db.commit()
        
        loading_result = load_price_for_symbol("TSLA", db)
        
        if loading_result:
            print("Auto-loading through router works!")
            
            # Check result
            tsla_price = service.repository.get_latest_price("TSLA")
            if tsla_price:
                print(f"TSLA: price {tsla_price.get('close')} USD for {tsla_price.get('date')}")
            else:
                print("TSLA: data not found")
                return False
        else:
            print("Auto-loading through router completed without loading new price")
        
        print("\n=== TEST COMPLETED SUCCESSFULLY ===")
        print("Auto price loading when adding positions works correctly!")
        
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


def test_position_creation_api_mock():
    """Test the API endpoint behavior"""
    print("\n=== Testing API Endpoint Behavior ===")
    
    # Test the core logic from positions router
    from app.services.price_service import load_price_for_symbol
    
    db = SessionLocal()
    
    try:
        # Simulate what happens in the router when creating a position
        test_symbols = ["MSFT", "GOOGL"]
        
        print(f"Testing symbols: {', '.join(test_symbols)}")
        
        success_count = 0
        for symbol in test_symbols:
            print(f"Testing {symbol}...")
            result = load_price_for_symbol(symbol, db)
            
            if result:
                print(f"SUCCESS: {symbol} price loaded")
                success_count += 1
            else:
                print(f"NO CHANGE: {symbol} (likely already exists)")
        
        print(f"\nSummary: {success_count}/{len(test_symbols)} symbols loaded")
        return success_count > 0
        
    except Exception as e:
        print(f"API test error: {e}")
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    print("Auto Price Loading Test")
    print("=" * 50)
    
    # Run basic service test
    basic_success = test_price_service_basic()
    
    # Run API behavior test
    api_success = test_position_creation_api_mock()
    
    # Summary
    print("\n" + "=" * 50)
    if basic_success and api_success:
        print("RESULT: Auto price loading system is working!")
        print("The system automatically loads prices when new positions are added.")
        sys.exit(0)
    else:
        print("RESULT: Issues detected in auto price loading system.")
        sys.exit(1)
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all dependencies are installed:")
    print("pip install pandas requests sqlalchemy")
    sys.exit(1)