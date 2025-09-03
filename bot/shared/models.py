"""
Модели базы данных для системы продажи видеоуроков.
Все модели используют SQLAlchemy ORM.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, 
    String, Text, func, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped

Base = declarative_base()


class User(Base):
    """Модель пользователя Telegram."""
    
    __tablename__ = "users"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = Column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = Column(String(255), nullable=True)
    first_name: Mapped[str] = Column(String(255), nullable=False)
    last_name: Mapped[Optional[str]] = Column(String(255), nullable=True)
    language_code: Mapped[str] = Column(String(10), default="en", nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    purchases: Mapped[List["Purchase"]] = relationship(
        "Purchase", back_populates="user", cascade="all, delete-orphan"
    )
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"


class Lesson(Base):
    """Модель урока."""
    
    __tablename__ = "lessons"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    title: Mapped[str] = Column(String(255), nullable=False)
    description: Mapped[str] = Column(Text, nullable=False)
    price: Mapped[int] = Column(Integer, nullable=False, comment="Цена в Telegram Stars")
    video_path: Mapped[Optional[str]] = Column(String(500), nullable=True)
    text_content: Mapped[Optional[str]] = Column(Text, nullable=True)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    is_free: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    purchases: Mapped[List["Purchase"]] = relationship(
        "Purchase", back_populates="lesson", cascade="all, delete-orphan"
    )
    course_lessons: Mapped[List["CourseLesson"]] = relationship(
        "CourseLesson", back_populates="lesson", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, title='{self.title}', price={self.price})>"


class Course(Base):
    """Модель мини-курса (набор уроков)."""
    
    __tablename__ = "courses"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    title: Mapped[str] = Column(String(255), nullable=False)
    description: Mapped[str] = Column(Text, nullable=False)
    total_price: Mapped[int] = Column(Integer, nullable=False, comment="Общая цена в Telegram Stars")
    discount_price: Mapped[Optional[int]] = Column(
        Integer, nullable=True, comment="Цена со скидкой в Telegram Stars"
    )
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    course_lessons: Mapped[List["CourseLesson"]] = relationship(
        "CourseLesson", back_populates="course", cascade="all, delete-orphan"
    )
    purchases: Mapped[List["Purchase"]] = relationship(
        "Purchase", back_populates="course", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, title='{self.title}', price={self.total_price})>"


class CourseLesson(Base):
    """Связывающая таблица между курсами и уроками."""
    
    __tablename__ = "course_lessons"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = Column(Integer, ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int] = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    order_index: Mapped[int] = Column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('course_id', 'lesson_id', name='unique_course_lesson'),
        UniqueConstraint('course_id', 'order_index', name='unique_course_order'),
    )

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="course_lessons")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="course_lessons")

    def __repr__(self) -> str:
        return f"<CourseLesson(course_id={self.course_id}, lesson_id={self.lesson_id}, order={self.order_index})>"


class Purchase(Base):
    """Модель покупки."""
    
    __tablename__ = "purchases"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    course_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("courses.id"), nullable=True)
    payment_id: Mapped[str] = Column(String(255), unique=True, index=True, nullable=False)
    amount: Mapped[int] = Column(Integer, nullable=False, comment="Сумма в Telegram Stars")
    status: Mapped[str] = Column(
        String(50), 
        nullable=False, 
        default="pending",
        comment="pending, completed, failed, refunded"
    )
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="purchases")
    lesson: Mapped[Optional["Lesson"]] = relationship("Lesson", back_populates="purchases")
    course: Mapped[Optional["Course"]] = relationship("Course", back_populates="purchases")

    def __repr__(self) -> str:
        return f"<Purchase(id={self.id}, user_id={self.user_id}, amount={self.amount}, status='{self.status}')>"


class PromoCode(Base):
    """Модель промокода."""
    
    __tablename__ = "promocodes"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    code: Mapped[str] = Column(String(50), unique=True, index=True, nullable=False)
    discount_percent: Mapped[int] = Column(Integer, nullable=False, comment="Скидка в процентах")
    discount_amount: Mapped[Optional[int]] = Column(
        Integer, nullable=True, comment="Фиксированная скидка в Telegram Stars"
    )
    max_uses: Mapped[Optional[int]] = Column(
        Integer, nullable=True, comment="Максимальное количество использований"
    )
    current_uses: Mapped[int] = Column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<PromoCode(id={self.id}, code='{self.code}', discount={self.discount_percent}%)>"

    @property
    def is_valid(self) -> bool:
        """Проверка валидности промокода."""
        if not self.is_active:
            return False
        
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
            
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
            
        return True


class SupportTicket(Base):
    """Модель тикета службы поддержки."""
    
    __tablename__ = "support_tickets"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject: Mapped[str] = Column(String(255), nullable=False)
    message: Mapped[str] = Column(Text, nullable=False)
    status: Mapped[str] = Column(
        String(50), 
        nullable=False, 
        default="open",
        comment="open, in_progress, closed"
    )
    admin_response: Mapped[Optional[str]] = Column(Text, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="support_tickets")

    def __repr__(self) -> str:
        return f"<SupportTicket(id={self.id}, user_id={self.user_id}, subject='{self.subject}', status='{self.status}')>"


class WithdrawRequest(Base):
    """Модель запроса на вывод средств."""
    
    __tablename__ = "withdraw_requests"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    amount: Mapped[int] = Column(Integer, nullable=False, comment="Сумма для вывода в Telegram Stars")
    status: Mapped[str] = Column(
        String(50), 
        nullable=False, 
        default="pending",
        comment="pending, approved, completed, rejected"
    )
    telegram_wallet_address: Mapped[Optional[str]] = Column(
        String(255), nullable=True, comment="Адрес Telegram кошелька"
    )
    requested_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    processed_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = Column(Text, nullable=True, comment="Заметки администратора")
    admin_id: Mapped[Optional[int]] = Column(
        Integer, ForeignKey("admin_users.id"), nullable=True, comment="ID администратора, обработавшего запрос"
    )
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    admin: Mapped[Optional["AdminUser"]] = relationship("AdminUser", foreign_keys=[admin_id])

    def __repr__(self) -> str:
        return f"<WithdrawRequest(id={self.id}, amount={self.amount}, status='{self.status}')>"


class AdminUser(Base):
    """Модель администратора."""
    
    __tablename__ = "admin_users"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    username: Mapped[str] = Column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = Column(String(255), nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    processed_withdraws: Mapped[List["WithdrawRequest"]] = relationship(
        "WithdrawRequest", back_populates="admin", foreign_keys="WithdrawRequest.admin_id"
    )

    def __repr__(self) -> str:
        return f"<AdminUser(id={self.id}, username='{self.username}', email='{self.email}')>"


class BotSettings(Base):
    """Модель для настроек текстов и кнопок бота."""
    
    __tablename__ = "bot_settings"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    key: Mapped[str] = Column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[str] = Column(Text, nullable=False)
    description: Mapped[Optional[str]] = Column(String(255), nullable=True)
    category: Mapped[str] = Column(
        String(50), 
        nullable=False, 
        default="general",
        comment="general, buttons, messages, notifications"
    )
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<BotSettings(id={self.id}, key='{self.key}', category='{self.category}')>"