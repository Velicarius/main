# RBAC (Role-Based Access Control) Setup Guide

## Overview

This guide explains how to set up and use the Role-Based Access Control (RBAC) system in the AI Portfolio application.

## 🎯 Features

- **JWT tokens with roles** - Authentication tokens include user roles
- **Three default roles** - `user`, `admin`, `ops`
- **Protected endpoints** - Admin-only API endpoints
- **Frontend role checking** - React components for role-based UI
- **CLI tools** - Script to make users admin
- **Comprehensive tests** - Full test coverage for RBAC

## 📋 Table of Contents

1. [Database Setup](#database-setup)
2. [Creating the First Admin](#creating-the-first-admin)
3. [Backend Usage](#backend-usage)
4. [Frontend Usage](#frontend-usage)
5. [Testing](#testing)
6. [API Reference](#api-reference)

---

## Database Setup

### 1. Run the migration

```bash
cd backend
alembic upgrade head
```

This creates:
- `roles` table with default roles: `user`, `admin`, `ops`
- `user_roles` association table
- Proper foreign keys and indices

### 2. Verify migration

```bash
# Check that tables exist
psql -U postgres -d ai_portfolio -c "\dt roles"
psql -U postgres -d ai_portfolio -c "\dt user_roles"

# Check default roles
psql -U postgres -d ai_portfolio -c "SELECT name, description FROM roles;"
```

Expected output:
```
 name  |              description
-------+----------------------------------------
 user  | Default user role with basic access
 admin | Administrator role with full access
 ops   | Operations role for system management
```

---

## Creating the First Admin

### Option 1: CLI Script (Recommended)

```bash
cd backend

# List all users
python scripts/make_admin.py --list

# Make a user admin
python scripts/make_admin.py user@example.com
```

Example output:
```
✅ Successfully assigned admin role to 'user@example.com'

User roles: admin
```

### Option 2: Direct SQL

```sql
-- Find user ID
SELECT id, email FROM users WHERE email = 'your@email.com';

-- Find admin role ID
SELECT id FROM roles WHERE name = 'admin';

-- Assign admin role
INSERT INTO user_roles (id, user_id, role_id)
VALUES (
    gen_random_uuid(),
    'USER_ID_HERE',
    (SELECT id FROM roles WHERE name = 'admin')
);
```

### Option 3: Python Script

```python
from app.database import SessionLocal
from app.models.user import User
from app.models.role import Role, UserRole

db = SessionLocal()

user = db.query(User).filter(User.email == "user@example.com").first()
admin_role = db.query(Role).filter(Role.name == "admin").first()

user_role = UserRole(user_id=user.id, role_id=admin_role.id)
db.add(user_role)
db.commit()
```

---

## Backend Usage

### Protecting Endpoints with Roles

#### Example 1: Require Admin

```python
from fastapi import APIRouter, Depends
from app.dependencies import require_admin

router = APIRouter()

@router.get("/admin/users", dependencies=[Depends(require_admin)])
def list_users():
    """Admin-only endpoint"""
    return {"users": [...]}
```

#### Example 2: Require Specific Role

```python
from app.dependencies import require_role

@router.post("/ops/tasks", dependencies=[Depends(require_role("ops"))])
def trigger_task():
    """Ops-only endpoint"""
    return {"status": "triggered"}
```

#### Example 3: Require Any of Multiple Roles

```python
from app.dependencies import require_any_role

@router.get("/management/stats", dependencies=[Depends(require_any_role(["admin", "ops"]))])
def get_stats():
    """Admin or Ops can access"""
    return {"stats": {...}}
```

#### Example 4: Get Current User with Roles

```python
from app.dependencies import get_current_user
from app.models.user import User

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Any authenticated user"""
    return {
        "email": current_user.email,
        "roles": current_user.roles
    }
```

### JWT Token Generation with Roles

```python
from app.core.jwt_auth import JWTAuth

# Get user from database
user = db.query(User).filter(User.email == email).first()

# Create token with roles
token = JWTAuth.create_access_token(
    user_id=user.id,
    email=user.email,
    roles=user.roles  # This automatically fetches roles from user_roles table
)
```

### Manual Role Checking

```python
from app.models.user import User

def my_endpoint(current_user: User = Depends(get_current_user)):
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Admin logic here
    ...
```

---

## Frontend Usage

### 1. Update Auth Store on Login

```typescript
// When user logs in, store roles
const response = await fetch('/api/auth/login', {
  method: 'POST',
  body: JSON.stringify({ email, password })
});

const data = await response.json();

// Decode JWT to get roles (or get from API response)
const tokenData = parseJWT(data.access_token);

// Update store with roles
useAuthStore.getState().setAuth(
  data.email,
  data.name,
  data.user_id,
  tokenData.roles // Pass roles
);
```

### 2. Protect Routes with RequireAdmin

```tsx
import { RequireAdmin } from '@/components/auth';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />

      {/* Admin-only route */}
      <Route
        path="/admin"
        element={
          <RequireAdmin>
            <AdminPanel />
          </RequireAdmin>
        }
      />
    </Routes>
  );
}
```

### 3. Protect Routes with Specific Role

```tsx
import { RequireRole } from '@/components/auth';

<Route
  path="/ops"
  element={
    <RequireRole role="ops">
      <OpsPanel />
    </RequireRole>
  }
/>
```

### 4. Protect Routes with Multiple Roles

```tsx
import { RequireAnyRole } from '@/components/auth';

<Route
  path="/management"
  element={
    <RequireAnyRole roles={["admin", "ops"]}>
      <ManagementPanel />
    </RequireAnyRole>
  }
/>
```

### 5. Conditional UI Based on Role

```tsx
import { useAuthStore } from '@/store/auth';

function Navigation() {
  const { isAdmin, hasRole } = useAuthStore();

  return (
    <nav>
      <Link to="/">Home</Link>

      {/* Show admin link only to admins */}
      {isAdmin() && <Link to="/admin">Admin Panel</Link>}

      {/* Show ops link to ops users */}
      {hasRole('ops') && <Link to="/ops">Operations</Link>}
    </nav>
  );
}
```

### 6. Custom Fallback for Unauthorized Access

```tsx
<RequireAdmin fallback={<AccessDenied />}>
  <AdminPanel />
</RequireAdmin>
```

---

## Testing

### Run RBAC Tests

```bash
cd backend
pytest tests/test_auth_rbac.py -v
```

### Test Coverage

The test suite covers:
- ✅ JWT token creation with roles
- ✅ JWT token decoding and role extraction
- ✅ User role assignments
- ✅ Multiple roles per user
- ✅ Admin endpoint protection
- ✅ Regular user access denial
- ✅ Unauthenticated access denial
- ✅ Role assignment/removal
- ✅ Login returns JWT with roles

### Manual Testing

#### Test 1: Register and Login

```bash
# Register new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

#### Test 2: Make User Admin

```bash
python scripts/make_admin.py test@example.com
```

#### Test 3: Access Admin Endpoint

```bash
# Get new token (now with admin role)
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' \
  | jq -r '.access_token')

# List users (admin only)
curl http://localhost:8000/api/admin/v1/users \
  -H "Authorization: Bearer $TOKEN"
```

---

## API Reference

### Admin Endpoints

All admin endpoints require `Authorization: Bearer <token>` header with admin role.

#### GET `/api/admin/v1/users`

List all users with their roles.

**Query Parameters:**
- `skip` (int, optional): Pagination offset (default: 0)
- `limit` (int, optional): Max users to return (default: 100)

**Response:**
```json
[
  {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "roles": ["user", "admin"]
  }
]
```

#### GET `/api/admin/v1/users/{user_id}`

Get specific user with roles.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "roles": ["admin"]
}
```

#### GET `/api/admin/v1/users/{user_id}/roles`

Get all roles for a user.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "admin",
    "description": "Administrator role",
    "permissions": {},
    "created_at": "2025-10-08T12:00:00",
    "updated_at": "2025-10-08T12:00:00"
  }
]
```

#### POST `/api/admin/v1/users/{user_id}/roles`

Assign a role to a user.

**Request Body:**
```json
{
  "role_name": "admin"
}
```

**Response:**
```json
{
  "message": "Role 'admin' assigned to user",
  "user_id": "uuid",
  "role": "admin"
}
```

#### DELETE `/api/admin/v1/users/{user_id}/roles/{role_name}`

Remove a role from a user.

**Response:**
```json
{
  "message": "Role 'admin' removed from user",
  "user_id": "uuid",
  "role": "admin"
}
```

#### GET `/api/admin/v1/roles`

List all available roles.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "admin",
    "description": "Administrator role",
    "permissions": {"can_manage_users": true},
    "created_at": "2025-10-08T12:00:00",
    "updated_at": "2025-10-08T12:00:00"
  }
]
```

---

## Troubleshooting

### Issue: "Admin role not found in database"

**Solution:** Run migrations
```bash
alembic upgrade head
```

### Issue: "User not found"

**Solution:** Check registered users
```bash
python scripts/make_admin.py --list
```

### Issue: "Access denied" after making user admin

**Solution:** Login again to get new JWT token with updated roles
```bash
# The old token doesn't have admin role, need to re-login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpass"}'
```

### Issue: "Cannot import require_admin"

**Solution:** Check import path
```python
from app.dependencies import require_admin  # Correct
from app.dependencies.auth import require_admin  # Also correct
```

---

## Security Best Practices

1. **Never hardcode admin credentials** - Always use environment variables
2. **Rotate JWT secrets** - Use strong, random JWT_SECRET_KEY
3. **Audit role assignments** - Log all role changes with `assigned_by`
4. **Principle of least privilege** - Only grant necessary roles
5. **Regular role review** - Periodically review user roles
6. **Secure admin CLI** - Restrict access to `make_admin.py` script

---

## Next Steps

After setting up RBAC:

1. ✅ Protect existing endpoints with role checks
2. ✅ Add frontend admin panel using `RequireAdmin`
3. ✅ Implement audit logging for role changes
4. ✅ Add granular permissions to roles (future)
5. ✅ Create role management UI (future)

---

## Files Created

### Backend
- `backend/app/models/role.py` - Role and UserRole models
- `backend/app/schemas/role.py` - Pydantic schemas
- `backend/app/dependencies/auth.py` - Auth dependencies
- `backend/app/routers/admin/users.py` - Admin endpoints
- `backend/scripts/make_admin.py` - CLI tool
- `backend/migrations/versions/add_rbac_roles_and_user_roles.py` - Migration
- `backend/tests/test_auth_rbac.py` - Tests

### Frontend
- `frontend/src/store/auth.ts` - Updated with roles
- `frontend/src/components/auth/RequireAdmin.tsx` - Role protection
- `frontend/src/components/auth/index.ts` - Exports

### Documentation
- `docs/admin/auth-setup.md` - This file

---

## Support

For issues or questions:
1. Check this documentation
2. Run tests: `pytest tests/test_auth_rbac.py -v`
3. Check logs: `/var/log/ai-portfolio/`
4. Review code: `backend/app/dependencies/auth.py`
