from sqlalchemy import create_engine, text
from app.core.config import settings

def check_db_connection():
    """Проверка подключения к базе данных"""
    try:
        e = create_engine(settings.database_url)
        with e.connect() as conn:
            r = conn.execute(text("SELECT version()"))
            version = list(r)[0][0]
            print("Connected OK, PostgreSQL version:", version)
            return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    check_db_connection()











