"""
Конфигурация приложения.
Загрузка переменных окружения и настройки приложения.
"""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Database
    database_url: str = "sqlite:///./lessons.db"
    
    # Security
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Telegram Bot
    telegram_bot_token: str = "your-bot-token-here"
    
    # Admin
    admin_username: str = "admin"
    admin_password: str = "admin123"
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ]
    
    # API
    api_v1_prefix: str = "/api/v1"
    auth_prefix: str = "/auth"
    admin_prefix: str = "/admin"
    
    # File storage
    storage_path: str = "storage"
    max_file_size: int = 50 * 1024 * 1024  # 50 MB
    max_video_size: int = 100 * 1024 * 1024  # 100 MB
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # Application info
    app_name: str = "Lessons Bot API"
    app_version: str = "1.0.0"
    app_description: str = "API для Telegram бота по продаже видеоуроков"
    
    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Парсинг CORS origins из строки или списка."""
        if isinstance(v, str):
            if v.startswith('[') and v.endswith(']'):
                # JSON format
                import json
                return json.loads(v)
            else:
                # Comma-separated format
                return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        """Валидация секретного ключа."""
        if len(v) < 32:
            raise ValueError("Секретный ключ должен быть не менее 32 символов")
        return v
    
    @property
    def is_development(self) -> bool:
        """Проверка режима разработки."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Проверка продакшн режима."""
        return self.environment.lower() == "production"
    
    @property
    def database_config(self) -> dict:
        """Конфигурация базы данных."""
        if self.database_url.startswith("sqlite"):
            return {
                "connect_args": {"check_same_thread": False, "timeout": 20},
                "echo": self.debug
            }
        else:
            return {"echo": self.debug}
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Создание глобального экземпляра настроек
settings = Settings()


def get_settings() -> Settings:
    """Функция для получения настроек (используется в dependency injection)."""
    return settings


def validate_environment():
    """Валидация переменных окружения."""
    errors = []
    
    # Проверка обязательных переменных для продакшна
    if settings.is_production:
        if settings.secret_key == "your-secret-key-here":
            errors.append("SECRET_KEY должен быть изменен в продакшне")
        
        if settings.telegram_bot_token == "your-bot-token-here":
            errors.append("TELEGRAM_BOT_TOKEN должен быть установлен")
        
        if settings.admin_password == "admin123":
            errors.append("ADMIN_PASSWORD должен быть изменен в продакшне")
    
    if errors:
        raise ValueError("Ошибки конфигурации:\n" + "\n".join(f"- {error}" for error in errors))


def create_directories():
    """Создание необходимых директорий."""
    directories = [
        settings.storage_path,
        f"{settings.storage_path}/videos",
        f"{settings.storage_path}/texts", 
        f"{settings.storage_path}/temp"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def get_database_url() -> str:
    """Получение URL базы данных."""
    return settings.database_url


def get_cors_settings() -> dict:
    """Получение настроек CORS."""
    return {
        "allow_origins": settings.allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
    }


def get_jwt_settings() -> dict:
    """Получение настроек JWT."""
    return {
        "secret_key": settings.secret_key,
        "algorithm": settings.algorithm,
        "access_token_expire_minutes": settings.access_token_expire_minutes,
    }


def get_file_settings() -> dict:
    """Получение настроек файлов."""
    return {
        "storage_path": settings.storage_path,
        "max_file_size": settings.max_file_size,
        "max_video_size": settings.max_video_size,
    }


def get_api_settings() -> dict:
    """Получение настроек API."""
    return {
        "title": settings.app_name,
        "description": settings.app_description,
        "version": settings.app_version,
        "docs_url": "/docs" if settings.debug else None,
        "redoc_url": "/redoc" if settings.debug else None,
        "openapi_url": "/openapi.json" if settings.debug else None,
    }