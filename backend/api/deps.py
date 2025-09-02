"""
Dependencies для FastAPI endpoints.
Аутентификация, авторизация и получение сессии базы данных.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import AdminUser
from shared.schemas import TokenData
from backend.config import settings

# Настройка схемы безопасности
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание JWT токена."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Верификация JWT токена."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    return token_data


def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AdminUser:
    """Получение текущего администратора."""
    token_data = verify_token(credentials.credentials)
    
    user = db.query(AdminUser).filter(AdminUser.username == token_data.username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def get_current_active_admin(
    current_user: AdminUser = Depends(get_current_admin_user)
) -> AdminUser:
    """Получение активного администратора."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_current_superuser(
    current_user: AdminUser = Depends(get_current_admin_user)
) -> AdminUser:
    """Получение суперпользователя."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[AdminUser]:
    """Получение текущего пользователя (опционально)."""
    if credentials is None:
        return None
    
    try:
        token_data = verify_token(credentials.credentials)
        user = db.query(AdminUser).filter(AdminUser.username == token_data.username).first()
        return user if user and user.is_active else None
    except HTTPException:
        return None


def check_permissions(required_permission: str):
    """Декоратор для проверки разрешений."""
    def permission_checker(current_user: AdminUser = Depends(get_current_admin_user)):
        # В будущем здесь можно добавить систему ролей и разрешений
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not active"
            )
        return current_user
    
    return permission_checker


class PaginationParams:
    """Параметры пагинации."""
    
    def __init__(
        self,
        page: int = 1,
        size: int = 20
    ):
        if page < 1:
            page = 1
        if size < 1:
            size = 1
        if size > settings.max_page_size:
            size = settings.max_page_size
            
        self.page = page
        self.size = size
        self.offset = (page - 1) * size


def get_pagination_params(
    page: int = 1,
    size: int = 20
) -> PaginationParams:
    """Dependency для получения параметров пагинации."""
    return PaginationParams(page=page, size=size)


def create_pagination_response(items: list, total: int, params: PaginationParams) -> dict:
    """Создание ответа с пагинацией."""
    pages = (total + params.size - 1) // params.size
    
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "size": params.size,
        "pages": pages
    }


def validate_content_type(content_type: str):
    """Валидация типа контента."""
    allowed_types = [
        "application/json",
        "multipart/form-data",
        "application/x-www-form-urlencoded"
    ]
    
    if not any(content_type.startswith(allowed_type) for allowed_type in allowed_types):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported media type"
        )


def rate_limit_key_func(request):
    """Функция для генерации ключа rate limiting."""
    # В будущем можно добавить более сложную логику
    return f"rate_limit:{request.client.host}"