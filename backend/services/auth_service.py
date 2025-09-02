"""
Сервис для работы с аутентификацией и администраторами.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from shared.models import AdminUser
from shared.utils import verify_password, get_password_hash


class AuthService:
    """Сервис аутентификации."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_user(self, username: str, password: str) -> Optional[AdminUser]:
        """Аутентификация пользователя по username и паролю."""
        user = self.db.query(AdminUser).filter(AdminUser.username == username).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def create_admin_user(
        self, 
        username: str, 
        email: str, 
        password: str, 
        is_superuser: bool = False
    ) -> AdminUser:
        """Создание нового администратора."""
        # Проверка уникальности username
        existing_user = self.db.query(AdminUser).filter(
            AdminUser.username == username
        ).first()
        
        if existing_user:
            raise ValueError("Username already exists")
        
        # Проверка уникальности email
        existing_email = self.db.query(AdminUser).filter(
            AdminUser.email == email
        ).first()
        
        if existing_email:
            raise ValueError("Email already exists")
        
        # Создание пользователя
        admin_user = AdminUser(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_superuser=is_superuser
        )
        
        self.db.add(admin_user)
        self.db.commit()
        self.db.refresh(admin_user)
        
        return admin_user
    
    def change_password(self, user: AdminUser, new_password: str) -> bool:
        """Смена пароля пользователя."""
        user.hashed_password = get_password_hash(new_password)
        
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def deactivate_user(self, user: AdminUser) -> bool:
        """Деактивация пользователя."""
        user.is_active = False
        
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def get_user_by_username(self, username: str) -> Optional[AdminUser]:
        """Получение пользователя по username."""
        return self.db.query(AdminUser).filter(AdminUser.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[AdminUser]:
        """Получение пользователя по email."""
        return self.db.query(AdminUser).filter(AdminUser.email == email).first()