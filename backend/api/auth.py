"""
API endpoints для аутентификации.
Авторизация, получение и обновление токенов.
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import AdminUser
from shared.schemas import Token, LoginRequest, ChangePasswordRequest, AdminUser as AdminUserSchema
from shared import helper_functions as utils
from backend.api.deps import (
    create_access_token, get_current_admin_user, get_current_active_admin
)
from backend.config import settings

router = APIRouter()


@router.post("/login", response_model=Token, summary="Авторизация администратора")
def login_for_access_token(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Авторизация администратора и получение JWT токена.
    
    - **username**: Имя пользователя администратора
    - **password**: Пароль администратора
    
    Возвращает JWT токен для доступа к API.
    """
    # Поиск пользователя в базе данных
    user = db.query(AdminUser).filter(AdminUser.username == login_data.username).first()
    
    # Проверка существования пользователя и пароля
    if not user or not utils.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверка активности пользователя
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Создание токена
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60  # в секундах
    }


@router.post("/login/oauth", response_model=Token, summary="OAuth2 авторизация")
def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 совместимая авторизация.
    Используется для совместимости с автогенерируемыми клиентами.
    """
    user = db.query(AdminUser).filter(AdminUser.username == form_data.username).first()
    
    if not user or not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }


@router.post("/refresh", response_model=Token, summary="Обновление токена")
def refresh_token(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Обновление JWT токена.
    Требует действующий токен для получения нового.
    """
    # Проверка активности пользователя
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Создание нового токена
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }


@router.post("/logout", summary="Выход из системы")
def logout(
    current_user: AdminUser = Depends(get_current_admin_user)
) -> Any:
    """
    Выход из системы.
    
    В данной реализации JWT токены stateless, поэтому фактический logout
    происходит на стороне клиента путем удаления токена.
    В будущем можно добавить blacklist токенов.
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=AdminUserSchema, summary="Профиль текущего пользователя")
def get_current_user_profile(
    current_user: AdminUser = Depends(get_current_active_admin)
) -> Any:
    """
    Получение профиля текущего авторизованного администратора.
    """
    return current_user


@router.post("/change-password", summary="Смена пароля")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: AdminUser = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
) -> Any:
    """
    Смена пароля текущего пользователя.
    
    - **current_password**: Текущий пароль
    - **new_password**: Новый пароль (минимум 6 символов)
    """
    # Проверка текущего пароля
    if not utils.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Проверка, что новый пароль отличается от текущего
    if utils.verify_password(password_data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Обновление пароля
    current_user.hashed_password = utils.get_password_hash(password_data.new_password)
    
    try:
        db.commit()
        db.refresh(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
    
    return {"message": "Password updated successfully"}


@router.post("/verify-token", summary="Проверка токена")
def verify_current_token(
    current_user: AdminUser = Depends(get_current_admin_user)
) -> Any:
    """
    Проверка валидности текущего токена.
    
    Возвращает информацию о пользователе, если токен валиден.
    Полезно для проверки токена без получения полного профиля.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser
    }


@router.get("/permissions", summary="Права доступа пользователя")
def get_user_permissions(
    current_user: AdminUser = Depends(get_current_active_admin)
) -> Any:
    """
    Получение списка прав доступа текущего пользователя.
    
    В данной версии используется простая система:
    - Обычные администраторы имеют базовые права
    - Суперпользователи имеют все права
    """
    base_permissions = [
        "read_users",
        "read_lessons", 
        "read_courses",
        "read_purchases",
        "read_support_tickets"
    ]
    
    admin_permissions = [
        "create_lessons",
        "update_lessons",
        "create_courses", 
        "update_courses",
        "update_support_tickets"
    ]
    
    superuser_permissions = [
        "delete_lessons",
        "delete_courses",
        "create_admin_users",
        "update_admin_users",
        "delete_admin_users",
        "manage_system"
    ]
    
    permissions = base_permissions.copy()
    
    if current_user.is_active:
        permissions.extend(admin_permissions)
    
    if current_user.is_superuser:
        permissions.extend(superuser_permissions)
    
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "is_superuser": current_user.is_superuser,
        "permissions": permissions
    }