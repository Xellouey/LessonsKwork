"""
Константы и перечисления для системы.
"""

from enum import Enum


class PurchaseStatus(str, Enum):
    """Статусы покупок."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class SupportTicketStatus(str, Enum):
    """Статусы тикетов поддержки."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class WithdrawStatus(str, Enum):
    """Статусы запросов на вывод."""
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"


class PaymentStatus(str, Enum):
    """Статусы платежей."""
    CREATED = "created"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class LanguageCode(str, Enum):
    """Поддерживаемые языки."""
    ENGLISH = "en"
    RUSSIAN = "ru"
    UKRAINIAN = "uk"


class FileType(str, Enum):
    """Типы файлов."""
    VIDEO = "video"
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"


# Лимиты и ограничения
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_TEXT_LENGTH = 10000  # Максимальная длина текстового контента

# Пагинация
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Цены в Telegram Stars
MIN_PRICE = 1
MAX_PRICE = 10000

# JWT токены
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Промокоды
MAX_PROMO_USES = 1000
MAX_DISCOUNT_PERCENT = 100

# Платежи и вывод средств
MIN_WITHDRAW_AMOUNT = 100  # Минимальная сумма для вывода
MAX_WITHDRAW_AMOUNT = 50000  # Максимальная сумма для вывода
COMMISSION_PERCENT = 5  # Комиссия платформы в процентах
PAYMENT_TIMEOUT_MINUTES = 30  # Таймаут для платежа
TELEGRAM_STARS_CURRENCY = "XTR"  # Валюта Telegram Stars

# Файловые пути
STORAGE_PATH = "storage"
VIDEO_STORAGE_PATH = f"{STORAGE_PATH}/videos"
TEXT_STORAGE_PATH = f"{STORAGE_PATH}/texts"
TEMP_STORAGE_PATH = f"{STORAGE_PATH}/temp"

# Поддерживаемые форматы файлов
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
ALLOWED_TEXT_EXTENSIONS = {".txt", ".md", ".pdf", ".doc", ".docx"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# Telegram ограничения
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_MAX_CAPTION_LENGTH = 1024
TELEGRAM_MAX_BUTTON_TEXT_LENGTH = 64

# API ограничения
API_RATE_LIMIT_PER_MINUTE = 60
API_RATE_LIMIT_PER_HOUR = 1000

# Валидация
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 50
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 100
MIN_TITLE_LENGTH = 1
MAX_TITLE_LENGTH = 255
MIN_DESCRIPTION_LENGTH = 1
MAX_DESCRIPTION_LENGTH = 5000

# Сообщения об ошибках
ERROR_MESSAGES = {
    "user_not_found": "Пользователь не найден",
    "lesson_not_found": "Урок не найден", 
    "course_not_found": "Курс не найден",
    "purchase_not_found": "Покупка не найдена",
    "invalid_credentials": "Неверные учетные данные",
    "access_denied": "Доступ запрещен",
    "insufficient_permissions": "Недостаточно прав",
    "invalid_payment": "Недействительный платеж",
    "promo_code_invalid": "Промокод недействителен",
    "promo_code_expired": "Промокод истек",
    "promo_code_used": "Промокод уже использован",
    "file_too_large": "Файл слишком большой",
    "invalid_file_format": "Неподдерживаемый формат файла",
    "database_error": "Ошибка базы данных",
    "internal_error": "Внутренняя ошибка сервера",
}

# Сообщения об успехе
SUCCESS_MESSAGES = {
    "user_created": "Пользователь создан успешно",
    "lesson_created": "Урок создан успешно",
    "course_created": "Курс создан успешно",
    "purchase_completed": "Покупка завершена успешно",
    "payment_processed": "Платеж обработан успешно",
    "file_uploaded": "Файл загружен успешно",
    "promo_code_applied": "Промокод применен успешно",
}

# Настройки по умолчанию
DEFAULT_SETTINGS = {
    "language": LanguageCode.ENGLISH,
    "currency": "STARS",
    "timezone": "UTC",
    "page_size": DEFAULT_PAGE_SIZE,
    "auto_backup": True,
    "debug_mode": False,
}

# API endpoints
API_V1_PREFIX = "/api/v1"
AUTH_PREFIX = "/auth"
ADMIN_PREFIX = "/admin"

# CORS настройки
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
]

ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["*"]

# Логирование
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = "INFO"

# Кеширование
CACHE_TTL_SECONDS = 300  # 5 минут
CACHE_MAX_SIZE = 1000

# Метрики и мониторинг
METRICS_ENABLED = True
HEALTH_CHECK_ENDPOINT = "/health"
METRICS_ENDPOINT = "/metrics"

# Версия API
API_VERSION = "1.0.0"
APP_VERSION = "1.0.0"