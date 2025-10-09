"""
Pydantic schemas for Role and UserRole models
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
import uuid


class RoleBase(BaseModel):
    """Base schema for Role"""
    name: str = Field(..., min_length=1, max_length=50, description="Role name (e.g., 'admin', 'user')")
    description: Optional[str] = Field(None, max_length=255, description="Role description")
    permissions: Optional[dict] = Field(default_factory=dict, description="Granular permissions JSON")


class RoleCreate(RoleBase):
    """Schema for creating a new role"""
    pass


class RoleUpdate(BaseModel):
    """Schema for updating a role"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    permissions: Optional[dict] = None


class RoleSchema(RoleBase):
    """Complete role schema with ID and timestamps"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserRoleBase(BaseModel):
    """Base schema for UserRole"""
    user_id: uuid.UUID
    role_id: uuid.UUID


class UserRoleCreate(UserRoleBase):
    """Schema for assigning a role to a user"""
    assigned_by: Optional[uuid.UUID] = None


class UserRoleSchema(UserRoleBase):
    """Complete user-role schema"""
    id: uuid.UUID
    assigned_at: datetime
    assigned_by: Optional[uuid.UUID]

    class Config:
        from_attributes = True


class UserWithRoles(BaseModel):
    """User schema with roles included"""
    id: uuid.UUID
    email: str
    name: Optional[str]
    roles: List[str] = Field(default_factory=list, description="List of role names")

    class Config:
        from_attributes = True


class AssignRoleRequest(BaseModel):
    """Request schema for assigning a role"""
    role_name: str = Field(..., description="Name of the role to assign (e.g., 'admin', 'user')")


class RemoveRoleRequest(BaseModel):
    """Request schema for removing a role"""
    role_name: str = Field(..., description="Name of the role to remove")


class RolePermissionsCheck(BaseModel):
    """Schema for checking role permissions"""
    role_name: str
    has_permission: bool
    permissions: dict = Field(default_factory=dict)
