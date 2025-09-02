"""
Конфигурация pytest и фикстуры для тестов.
"""

import os
import pytest
import tempfile
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database import get_db
from shared.models import Base
from backend.main import app


# Создание тестовой базы данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override для получения тестовой базы данных."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def db():
    """Фикстура для тестовой базы данных."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Фикстура для тестового клиента FastAPI."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def temp_storage():
    """Фикстура для временного хранилища файлов."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Установка временного пути для хранилища
        original_storage_path = os.environ.get("STORAGE_PATH")
        os.environ["STORAGE_PATH"] = temp_dir
        
        yield temp_dir
        
        # Восстановление оригинального пути
        if original_storage_path:
            os.environ["STORAGE_PATH"] = original_storage_path
        elif "STORAGE_PATH" in os.environ:
            del os.environ["STORAGE_PATH"]


@pytest.fixture
def admin_user(db):
    """Фикстура для создания тестового администратора."""
    from shared.models import AdminUser
    from shared.utils import get_password_hash
    
    admin = AdminUser(
        username="test_admin",
        email="test@example.com",
        hashed_password=get_password_hash("test_password"),
        is_active=True,
        is_superuser=True
    )
    
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    return admin


@pytest.fixture
def auth_headers(client, admin_user):
    """Фикстура для получения заголовков аутентификации."""
    login_data = {
        "username": admin_user.username,
        "password": "test_password"
    }
    
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    
    token_data = response.json()
    token = token_data["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user(db):
    """Фикстура для создания тестового пользователя."""
    from shared.models import User
    
    user = User(
        telegram_id=123456789,
        username="test_user",
        first_name="Test",
        last_name="User",
        language_code="en"
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@pytest.fixture
def test_lesson(db):
    """Фикстура для создания тестового урока."""
    from shared.models import Lesson
    
    lesson = Lesson(
        title="Test Lesson",
        description="This is a test lesson",
        price=100,
        is_free=False,
        is_active=True
    )
    
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    
    return lesson


@pytest.fixture
def test_course(db, test_lesson):
    """Фикстура для создания тестового курса."""
    from shared.models import Course, CourseLesson
    
    course = Course(
        title="Test Course",
        description="This is a test course",
        total_price=500,
        discount_price=400,
        is_active=True
    )
    
    db.add(course)
    db.commit()
    db.refresh(course)
    
    # Добавляем урок в курс
    course_lesson = CourseLesson(
        course_id=course.id,
        lesson_id=test_lesson.id,
        order_index=1
    )
    
    db.add(course_lesson)
    db.commit()
    
    return course