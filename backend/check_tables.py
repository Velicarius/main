#!/usr/bin/env python3
"""Check admin tables in database"""
from app.database import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        # Check all tables
        result = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
        tables = [row[0] for row in result.fetchall()]
        print('All tables in DB:')
        for table in tables:
            print(f'  - {table}')
        
        # Check admin tables specifically
        admin_tables = ['api_providers', 'api_credentials', 'rate_limits', 'quotas', 'plans', 
                       'feature_flags', 'schedules', 'cache_policies', 'audit_log', 'system_settings']
        existing_admin = [t for t in admin_tables if t in tables]
        print('Admin tables found:', existing_admin)
        
        # Check roles
        result = db.execute(text('SELECT name FROM roles'))
        roles = [row[0] for row in result.fetchall()]
        print('Roles in DB:', roles)
        
    except Exception as e:
        print(f'Error: {e}')
    finally:
        db.close()

if __name__ == '__main__':
    main()
