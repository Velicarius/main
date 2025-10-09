"""
API Providers Admin Router
Provides CRUD operations for API providers and credentials
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.admin import ApiProvider, ApiCredential
from app.schemas.admin.api_provider import (
    ApiProviderSchema,
    ApiProviderCreate,
    ApiProviderUpdate,
    ApiCredentialSchema,
    ApiCredentialCreate,
    ApiCredentialUpdate
)
from app.dependencies.auth import require_admin

router = APIRouter(
    prefix="/api/admin/v1/api-providers",
    tags=["admin", "api-providers"]
)


# API Providers endpoints

@router.get("", response_model=List[ApiProviderSchema])
def list_api_providers(
    type: str | None = None,
    is_enabled: bool | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get all API providers with optional filtering"""
    query = db.query(ApiProvider)

    if type:
        query = query.filter(ApiProvider.type == type)
    if is_enabled is not None:
        query = query.filter(ApiProvider.is_enabled == is_enabled)

    providers = query.order_by(ApiProvider.priority, ApiProvider.name).all()
    return providers


@router.get("/{provider_id}", response_model=ApiProviderSchema)
def get_api_provider(
    provider_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a specific API provider by ID"""
    provider = db.query(ApiProvider).filter(ApiProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API provider {provider_id} not found"
        )
    return provider


@router.post("", response_model=ApiProviderSchema, status_code=status.HTTP_201_CREATED)
def create_api_provider(
    provider_data: ApiProviderCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Create a new API provider"""
    # Check if name already exists
    existing = db.query(ApiProvider).filter(ApiProvider.name == provider_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API provider with name '{provider_data.name}' already exists"
        )

    provider = ApiProvider(**provider_data.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.patch("/{provider_id}", response_model=ApiProviderSchema)
def update_api_provider(
    provider_id: UUID,
    provider_data: ApiProviderUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Update an API provider"""
    provider = db.query(ApiProvider).filter(ApiProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API provider {provider_id} not found"
        )

    # Update only provided fields
    update_data = provider_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)

    db.commit()
    db.refresh(provider)
    return provider


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_provider(
    provider_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """
    Soft delete an API provider
    Sets deleted_at timestamp and is_enabled=False
    """
    provider = db.query(ApiProvider).filter(ApiProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API provider {provider_id} not found"
        )

    from datetime import datetime, timezone
    provider.deleted_at = datetime.now(timezone.utc)
    provider.is_enabled = False

    db.commit()
    return None


# API Credentials endpoints

@router.get("/{provider_id}/credentials", response_model=List[ApiCredentialSchema])
def list_credentials_for_provider(
    provider_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get all credentials for a specific provider"""
    provider = db.query(ApiProvider).filter(ApiProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API provider {provider_id} not found"
        )

    return provider.credentials


@router.post("/{provider_id}/credentials", response_model=ApiCredentialSchema, status_code=status.HTTP_201_CREATED)
def create_credential(
    provider_id: UUID,
    credential_data: ApiCredentialCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Create a new credential for a provider"""
    provider = db.query(ApiProvider).filter(ApiProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API provider {provider_id} not found"
        )

    credential = ApiCredential(
        provider_id=provider_id,
        **credential_data.model_dump()
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


@router.patch("/credentials/{credential_id}", response_model=ApiCredentialSchema)
def update_credential(
    credential_id: UUID,
    credential_data: ApiCredentialUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Update a credential"""
    credential = db.query(ApiCredential).filter(ApiCredential.id == credential_id).first()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential {credential_id} not found"
        )

    # Update only provided fields
    update_data = credential_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(credential, field, value)

    db.commit()
    db.refresh(credential)
    return credential


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """
    Soft delete a credential
    Sets deleted_at timestamp and status='revoked'
    """
    credential = db.query(ApiCredential).filter(ApiCredential.id == credential_id).first()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential {credential_id} not found"
        )

    from datetime import datetime, timezone
    credential.deleted_at = datetime.now(timezone.utc)
    credential.status = 'revoked'

    db.commit()
    return None
