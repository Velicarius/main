# RBAC Migration Status

## Migration File
- **File**: `versions/rbac_001_add_rbac_roles_and_user_roles.py`
- **Revision ID**: `rbac_001`
- **Depends On**: `ed119d0ac9ac` (news articles migration)
- **Status**: ✅ Ready to run

## What This Migration Does

### Creates Tables
1. **`roles`** - Stores role definitions
   - `id` (UUID, primary key)
   - `name` (string, unique) - Role name (e.g., 'admin', 'user', 'ops')
   - `description` (string, optional)
   - `permissions` (JSONB) - Granular permissions
   - `created_at`, `updated_at` (timestamps)

2. **`user_roles`** - Many-to-many association between users and roles
   - `id` (UUID, primary key)
   - `user_id` (UUID, foreign key to users.id)
   - `role_id` (UUID, foreign key to roles.id)
   - `assigned_at` (timestamp)
   - `assigned_by` (UUID, foreign key to users.id, optional)

### Seeds Default Roles
Inserts 3 default roles:
- **user** - Default user role with basic portfolio access
- **admin** - Administrator with full system access
- **ops** - Operations role for task management

## How to Run

### When Database is Available

```bash
cd backend

# Run the migration
alembic upgrade head

# Verify tables were created
psql -U postgres -d ai_portfolio -c "\dt roles"
psql -U postgres -d ai_portfolio -c "\dt user_roles"

# Check default roles
psql -U postgres -d ai_portfolio -c "SELECT name, description FROM roles;"
```

### Migration Chain
```
ed119d0ac9ac (news tables)
    ↓
rbac_001 (roles & user_roles) ← HEAD
```

## Rollback

If needed, you can rollback this migration:

```bash
# Rollback to previous version
alembic downgrade ed119d0ac9ac

# This will:
# - Drop user_roles table
# - Drop roles table
# - Remove all role assignments
```

## Verification

After running the migration, verify with:

```bash
# Check migration status
alembic current

# Should show: rbac_001 (head)
```

## Database Schema

### roles table
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_roles_name ON roles(name);
```

### user_roles table
```sql
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX idx_user_role ON user_roles(user_id, role_id);
```

## Default Roles Data

```sql
INSERT INTO roles (id, name, description, permissions) VALUES
(
    gen_random_uuid(),
    'user',
    'Default user role with basic access',
    '{"can_view_own_portfolio": true, "can_edit_own_portfolio": true}'
),
(
    gen_random_uuid(),
    'admin',
    'Administrator role with full access',
    '{"can_manage_users": true, "can_manage_roles": true, "can_access_admin_panel": true, "can_view_all_data": true}'
),
(
    gen_random_uuid(),
    'ops',
    'Operations role for system management',
    '{"can_trigger_tasks": true, "can_view_logs": true, "can_manage_providers": true}'
);
```

## Notes

- ✅ Migration file follows Alembic naming convention
- ✅ Properly chains from previous migration (ed119d0ac9ac)
- ✅ Includes both upgrade() and downgrade() functions
- ✅ Seeds default data
- ✅ Creates proper indices
- ✅ Uses CASCADE and SET NULL for foreign keys
- ⚠️ Database must be running to execute migration

## After Migration

Once migration is complete:

1. Use `scripts/make_admin.py` to assign first admin
2. Update JWT authentication to include roles
3. Protect endpoints with role dependencies
4. Update frontend to use role-based access control

See `docs/admin/auth-setup.md` for complete setup guide.
