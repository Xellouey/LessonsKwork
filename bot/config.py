"""
Конфигурация Telegram бота.
Настройки, переменные окружения, валидация конфигурации.
"""

import os
from typing import List, Optional


class BotSettings:
    """Настройки Telegram бота."""
    
    def __init__(self):
        # Основные настройки бота
        self.telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.bot_username: Optional[str] = os.getenv("BOT_USERNAME")
        
        # База данных
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./lessons.db")
        
        # Языки и локализация
        self.default_language: str = os.getenv("DEFAULT_LANGUAGE", "en")
        supported_langs = os.getenv("SUPPORTED_LANGUAGES", "en,ru")
        self.supported_languages: List[str] = supported_langs.split(",")
        
        # Хранилище файлов
        self.media_storage_path: str = os.getenv("MEDIA_STORAGE_PATH", "./storage")
        self.max_file_size: int = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))  # 50MB
        
        # Административные настройки
        admin_id = os.getenv("ADMIN_CHAT_ID")
        self.admin_chat_id: Optional[int] = int(admin_id) if admin_id else None
        
        error_id = os.getenv("ERROR_LOG_CHAT_ID")
        self.error_log_chat_id: Optional[int] = int(error_id) if error_id else None
        
        self.free_lesson_id: int = int(os.getenv("FREE_LESSON_ID", "1"))
        
        # Redis для состояний (опционально)
        self.redis_url: Optional[str] = os.getenv("REDIS_URL")
        self.use_redis: bool = os.getenv("USE_REDIS", "false").lower() == "true"
        
        # Режим отладки
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # Ограничения и лимиты
        self.rate_limit_per_user: int = int(os.getenv("RATE_LIMIT_PER_USER", "30"))  # запросов в минуту
        self.max_lessons_per_page: int = int(os.getenv("MAX_LESSONS_PER_PAGE", "10"))
    
    def get_storage_path(self, path_type: str = '') -> str:
        """Получить путь к хранилищу."""
        if path_type:
            return os.path.join(self.media_storage_path, path_type)
        return self.media_storage_path
    
    def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором."""
        return bool(self.admin_chat_id and user_id == self.admin_chat_id)


# Создание экземпляра настроек
try:
    settings = BotSettings()
except Exception as e:
    print(f"❌ Error loading bot configuration: {e}")
    raise


def validate_bot_configuration() -> bool:
    """
    Валидация конфигурации бота.
    
    Returns:
        bool: True если конфигурация корректна
    """
    try:
        # Проверка токена бота
        if not settings.telegram_bot_token:
            raise ValueError("ТОКЕН НЕ УСТАНОВЛЕН")
        
        # Создание директорий для хранилища
        os.makedirs(settings.get_storage_path('videos'), exist_ok=True)
        os.makedirs(settings.get_storage_path('texts'), exist_ok=True)
        os.makedirs(settings.get_storage_path('temp'), exist_ok=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False


def get_log_config() -> dict:
    """Получить конфигурацию логирования."""
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': settings.log_level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': settings.log_level,
                'propagate': False
            }
        }
    }