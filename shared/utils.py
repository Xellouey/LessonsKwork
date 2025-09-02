"""
Утилиты для работы с базой данных и общие функции.
"""

import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .models import AdminUser, User, Lesson, Course

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширование пароля."""
    return pwd_context.hash(password)


def create_admin_user(db: Session) -> Optional[AdminUser]:
    """
    Создание администратора по умолчанию.
    Создает только если администратор не существует.
    """
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_email = f"{admin_username}@lessons-bot.local"
    
    # Проверяем, существует ли уже администратор
    existing_admin = db.query(AdminUser).filter(
        AdminUser.username == admin_username
    ).first()
    
    if existing_admin:
        print(f"✅ Администратор '{admin_username}' уже существует")
        return existing_admin
    
    # Создаем нового администратора
    admin_user = AdminUser(
        username=admin_username,
        email=admin_email,
        hashed_password=get_password_hash(admin_password),
        is_active=True,
        is_superuser=True
    )
    
    try:
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"✅ Создан администратор: {admin_username}")
        return admin_user
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка создания администратора: {e}")
        return None


def create_sample_data(db: Session) -> None:
    """Создание тестовых данных для разработки."""
    
    # Создаем тестового пользователя
    test_user = db.query(User).filter(User.telegram_id == 123456789).first()
    if not test_user:
        test_user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en"
        )
        db.add(test_user)
    
    # Создаем тестовые уроки
    lessons_data = [
        {
            "title": "Введение в Python",
            "description": "Основы программирования на Python для начинающих",
            "price": 100,
            "is_free": True
        },
        {
            "title": "Работа с базами данных",
            "description": "Изучаем SQLAlchemy и работу с базами данных",
            "price": 150
        },
        {
            "title": "Создание веб-приложений с FastAPI",
            "description": "Разработка REST API с использованием FastAPI",
            "price": 200
        }
    ]
    
    for lesson_data in lessons_data:
        existing_lesson = db.query(Lesson).filter(
            Lesson.title == lesson_data["title"]
        ).first()
        
        if not existing_lesson:
            lesson = Lesson(**lesson_data)
            db.add(lesson)
    
    # Создаем тестовый курс
    course_exists = db.query(Course).filter(
        Course.title == "Полный курс Python разработки"
    ).first()
    
    if not course_exists:
        course = Course(
            title="Полный курс Python разработки",
            description="Комплексный курс по изучению Python от основ до продвинутых тем",
            total_price=400,
            discount_price=300
        )
        db.add(course)
    
    try:
        db.commit()
        print("✅ Тестовые данные созданы")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка создания тестовых данных: {e}")


def format_datetime(dt: datetime) -> str:
    """Форматирование даты и времени для отображения."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def generate_payment_id(user_id: int, item_type: str, item_id: int) -> str:
    """
    Генерация уникального идентификатора платежа.
    
    Args:
        user_id: ID пользователя
        item_type: Тип покупки ('lesson' или 'course')
        item_id: ID урока или курса
    """
    timestamp = datetime.utcnow().timestamp()
    data = f"{user_id}_{item_type}_{item_id}_{timestamp}"
    return hashlib.md5(data.encode()).hexdigest()


def calculate_discount_price(original_price: int, discount_percent: int, discount_amount: Optional[int] = None) -> int:
    """
    Расчет цены со скидкой.
    
    Args:
        original_price: Оригинальная цена
        discount_percent: Процент скидки
        discount_amount: Фиксированная сумма скидки (опционально)
    """
    if discount_amount:
        return max(0, original_price - discount_amount)
    
    discount = (original_price * discount_percent) // 100
    return max(0, original_price - discount)


def is_email_valid(email: str) -> bool:
    """Простая проверка валидности email."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_filename(filename: str) -> str:
    """
    Очистка имени файла от опасных символов.
    
    Args:
        filename: Исходное имя файла
    
    Returns:
        Безопасное имя файла
    """
    import re
    # Удаляем опасные символы
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Ограничиваем длину
    if len(safe_filename) > 255:
        name, ext = os.path.splitext(safe_filename)
        safe_filename = name[:255-len(ext)] + ext
    
    return safe_filename


def get_file_size(file_path: str) -> int:
    """
    Получение размера файла в байтах.
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        Размер файла в байтах или 0 если файл не найден
    """
    try:
        return os.path.getsize(file_path)
    except (OSError, FileNotFoundError):
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    Форматирование размера файла для отображения.
    
    Args:
        size_bytes: Размер в байтах
    
    Returns:
        Отформатированная строка (например, "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"