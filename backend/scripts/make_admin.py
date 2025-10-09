#!/usr/bin/env python3
"""
CLI Script to make a user an admin
Usage: python scripts/make_admin.py <email>
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.role import Role, UserRole


def make_admin(email: str):
    """
    Assign admin role to a user by email

    Args:
        email: Email of the user to make admin

    Returns:
        None
    """
    db: Session = SessionLocal()

    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()

        if not user:
            print(f"ERROR: User with email '{email}' not found")
            print("\nAvailable users:")
            users = db.query(User).all()
            for u in users:
                print(f"  - {u.email} (id: {u.id})")
            return

        # Find admin role
        admin_role = db.query(Role).filter(Role.name == "admin").first()

        if not admin_role:
            print("ERROR: Admin role not found in database")
            print("💡 Run database migrations first: alembic upgrade head")
            return

        # Check if user already has admin role
        existing = db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role_id == admin_role.id
        ).first()

        if existing:
            print(f"SUCCESS: User '{email}' already has admin role")
            print(f"\nCurrent roles: {', '.join(user.roles)}")
            return

        # Assign admin role
        user_role = UserRole(
            user_id=user.id,
            role_id=admin_role.id,
            assigned_by=None  # System assignment
        )

        db.add(user_role)
        db.commit()

        print(f"SUCCESS: Successfully assigned admin role to '{email}'")
        print(f"\nUser roles: {', '.join(user.roles)}")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        db.rollback()
    finally:
        db.close()


def list_users():
    """List all users and their roles"""
    db: Session = SessionLocal()

    try:
        users = db.query(User).all()

        if not users:
            print("No users found in database")
            return

        print("\nUsers in database:\n")
        print(f"{'Email':<40} {'Name':<20} {'Roles'}")
        print("-" * 80)

        for user in users:
            roles_str = ", ".join(user.roles) if user.roles else "(no roles)"
            name = user.name or "(no name)"
            print(f"{user.email:<40} {name:<20} {roles_str}")

    except Exception as e:
        print(f"ERROR: {str(e)}")
    finally:
        db.close()


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/make_admin.py <email>")
        print("       python scripts/make_admin.py --list")
        print("\nExamples:")
        print("  python scripts/make_admin.py user@example.com")
        print("  python scripts/make_admin.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_users()
    else:
        email = sys.argv[1]
        make_admin(email)


if __name__ == "__main__":
    main()
