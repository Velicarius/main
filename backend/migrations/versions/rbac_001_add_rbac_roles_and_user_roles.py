"""Add RBAC roles and user_roles tables

Revision ID: rbac_001
Revises:
Create Date: 2025-10-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'rbac_001'
down_revision = 'ed119d0ac9ac'  # Latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('permissions', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_roles_name', 'roles', ['name'])

    # Create user_roles association table
    op.create_table(
        'user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_user_role', 'user_roles', ['user_id', 'role_id'], unique=True)

    # Insert default roles
    op.execute("""
        INSERT INTO roles (id, name, description, permissions) VALUES
        (gen_random_uuid(), 'user', 'Default user role with basic access', '{"can_view_own_portfolio": true, "can_edit_own_portfolio": true}'),
        (gen_random_uuid(), 'admin', 'Administrator role with full access', '{"can_manage_users": true, "can_manage_roles": true, "can_access_admin_panel": true, "can_view_all_data": true}'),
        (gen_random_uuid(), 'ops', 'Operations role for system management', '{"can_trigger_tasks": true, "can_view_logs": true, "can_manage_providers": true}')
    """)


def downgrade():
    op.drop_index('idx_user_role', 'user_roles')
    op.drop_table('user_roles')
    op.drop_index('ix_roles_name', 'roles')
    op.drop_table('roles')
