"""
Конфигурация базы данных и создание сессий.
Управление подключениями к SQLite и создание таблиц.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy import text

from .models import Base

# Получение URL базы данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lessons.db")

# Создание движка базы данных
if DATABASE_URL.startswith("sqlite"):
    # Специальные настройки для SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,  # Разрешить использование в многопоточности
            "timeout": 20,  # Таймаут подключения
        },
        poolclass=StaticPool,  # Использовать статичный пул соединений
        echo=os.getenv("DEBUG", "false").lower() == "true"  # Логирование SQL запросов в режиме отладки
    )
else:
    # Настройки для PostgreSQL и других БД
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Создание всех таблиц в базе данных."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency для получения сессии базы данных.
    Используется в FastAPI endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseManager:
    """Менеджер для работы с базой данных."""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def create_tables(self):
        """Создание всех таблиц."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Удаление всех таблиц (используется для тестов)."""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Получение новой сессии базы данных."""
        return self.SessionLocal()
    
    def close_session(self, session: Session):
        """Закрытие сессии."""
        session.close()


# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()


def init_database():
    """
    Инициализация базы данных.
    Создает таблицы и добавляет начальные данные если необходимо.
    """
    from .utils import create_admin_user
    
    # Создание таблиц
    create_tables()
    
    # Создание администратора по умолчанию
    try:
        db = SessionLocal()
        create_admin_user(db)
        db.close()
        print("✅ База данных инициализирована успешно")
    except Exception as e:
        print(f"⚠️ Ошибка при инициализации базы данных: {e}")


def check_database_connection() -> bool:
    """
    Проверка подключения к базе данных.
    Возвращает True если подключение успешно.
    """
    try:
        db = SessionLocal()
        # Выполняем простой запрос для проверки соединения
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return False


def get_database_info() -> dict:
    """
    Получение информации о базе данных.
    Возвращает словарь с информацией о подключении.
    """
    connected = check_database_connection()
    return {
        "database_url": DATABASE_URL,
        "engine": str(engine.url),
        "connected": connected,
        "tables_created": list(Base.metadata.tables.keys()) if connected else []
    }