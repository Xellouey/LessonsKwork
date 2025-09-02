"""
Pydantic схемы для валидации данных и API документации.
Определяют структуру входящих и исходящих данных для API endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from .constants import (
    MIN_PRICE, MAX_PRICE, MIN_TITLE_LENGTH, MAX_TITLE_LENGTH,
    MIN_DESCRIPTION_LENGTH, MAX_DESCRIPTION_LENGTH, 
    PurchaseStatus, SupportTicketStatus, LanguageCode
)


# ========== Base Schemas ==========

class BaseSchema(BaseModel):
    """Базовая схема с общими настройками."""
    
    class Config:
        from_attributes = True
        use_enum_values = True


# ========== User Schemas ==========

class UserBase(BaseSchema):
    """Базовая схема пользователя."""
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: str = Field(..., min_length=1, max_length=255, description="Имя пользователя")
    last_name: Optional[str] = Field(None, max_length=255, description="Фамилия пользователя")
    language_code: str = Field(default="en", description="Код языка пользователя")


class UserCreate(UserBase):
    """Схема для создания пользователя."""
    pass


class UserUpdate(BaseSchema):
    """Схема для обновления пользователя."""
    username: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, min_length=1, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    language_code: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)


class User(UserBase):
    """Схема пользователя для ответа."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserWithPurchases(User):
    """Схема пользователя с покупками."""
    purchases: List["Purchase"] = []


# ========== Lesson Schemas ==========

class LessonBase(BaseSchema):
    """Базовая схема урока."""
    title: str = Field(..., min_length=MIN_TITLE_LENGTH, max_length=MAX_TITLE_LENGTH)
    description: str = Field(..., min_length=MIN_DESCRIPTION_LENGTH, max_length=MAX_DESCRIPTION_LENGTH)
    price: int = Field(..., ge=MIN_PRICE, le=MAX_PRICE, description="Цена в Telegram Stars")
    video_path: Optional[str] = Field(None, description="Путь к видеофайлу")
    text_content: Optional[str] = Field(None, description="Текстовое содержимое урока")
    is_free: bool = Field(default=False, description="Бесплатный урок")


class LessonCreate(LessonBase):
    """Схема для создания урока."""
    pass


class LessonUpdate(BaseSchema):
    """Схема для обновления урока."""
    title: Optional[str] = Field(None, min_length=MIN_TITLE_LENGTH, max_length=MAX_TITLE_LENGTH)
    description: Optional[str] = Field(None, min_length=MIN_DESCRIPTION_LENGTH, max_length=MAX_DESCRIPTION_LENGTH)
    price: Optional[int] = Field(None, ge=MIN_PRICE, le=MAX_PRICE)
    video_path: Optional[str] = None
    text_content: Optional[str] = None
    is_active: Optional[bool] = None
    is_free: Optional[bool] = None


class Lesson(LessonBase):
    """Схема урока для ответа."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LessonWithPurchases(Lesson):
    """Схема урока с информацией о покупках."""
    purchases_count: int = 0
    total_revenue: int = 0


# ========== Course Schemas ==========

class CourseBase(BaseSchema):
    """Базовая схема курса."""
    title: str = Field(..., min_length=MIN_TITLE_LENGTH, max_length=MAX_TITLE_LENGTH)
    description: str = Field(..., min_length=MIN_DESCRIPTION_LENGTH, max_length=MAX_DESCRIPTION_LENGTH)
    total_price: int = Field(..., ge=MIN_PRICE, le=MAX_PRICE, description="Общая цена в Telegram Stars")
    discount_price: Optional[int] = Field(None, ge=0, le=MAX_PRICE, description="Цена со скидкой")


class CourseCreate(CourseBase):
    """Схема для создания курса."""
    lesson_ids: List[int] = Field(default=[], description="Список ID уроков в курсе")


class CourseUpdate(BaseSchema):
    """Схема для обновления курса."""
    title: Optional[str] = Field(None, min_length=MIN_TITLE_LENGTH, max_length=MAX_TITLE_LENGTH)
    description: Optional[str] = Field(None, min_length=MIN_DESCRIPTION_LENGTH, max_length=MAX_DESCRIPTION_LENGTH)
    total_price: Optional[int] = Field(None, ge=MIN_PRICE, le=MAX_PRICE)
    discount_price: Optional[int] = Field(None, ge=0, le=MAX_PRICE)
    is_active: Optional[bool] = None


class Course(CourseBase):
    """Схема курса для ответа."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CourseWithLessons(Course):
    """Схема курса с уроками."""
    lessons: List[Lesson] = []
    lessons_count: int = 0


# ========== Purchase Schemas ==========

class PurchaseBase(BaseSchema):
    """Базовая схема покупки."""
    amount: int = Field(..., ge=MIN_PRICE, description="Сумма в Telegram Stars")


class PurchaseCreate(PurchaseBase):
    """Схема для создания покупки."""
    user_id: int
    lesson_id: Optional[int] = None
    course_id: Optional[int] = None
    payment_id: str = Field(..., description="Уникальный ID платежа от Telegram")
    
    @validator('lesson_id', 'course_id')
    def validate_purchase_item(cls, v, values):
        """Проверка, что указан либо урок, либо курс."""
        lesson_id = values.get('lesson_id')
        course_id = values.get('course_id')
        
        if not lesson_id and not course_id:
            raise ValueError('Должен быть указан либо lesson_id, либо course_id')
        
        if lesson_id and course_id:
            raise ValueError('Нельзя указывать одновременно lesson_id и course_id')
        
        return v


class PurchaseUpdate(BaseSchema):
    """Схема для обновления покупки."""
    status: Optional[PurchaseStatus] = None


class Purchase(PurchaseBase):
    """Схема покупки для ответа."""
    id: int
    user_id: int
    lesson_id: Optional[int]
    course_id: Optional[int]
    payment_id: str
    status: PurchaseStatus
    created_at: datetime
    updated_at: datetime


class PurchaseWithDetails(Purchase):
    """Схема покупки с деталями."""
    user: Optional[User] = None
    lesson: Optional[Lesson] = None
    course: Optional[Course] = None


# ========== PromoCode Schemas ==========

class PromoCodeBase(BaseSchema):
    """Базовая схема промокода."""
    code: str = Field(..., min_length=3, max_length=50, description="Код промокода")
    discount_percent: int = Field(..., ge=0, le=100, description="Процент скидки")
    discount_amount: Optional[int] = Field(None, ge=0, description="Фиксированная скидка в Stars")
    max_uses: Optional[int] = Field(None, ge=1, description="Максимальное количество использований")
    expires_at: Optional[datetime] = Field(None, description="Дата истечения")


class PromoCodeCreate(PromoCodeBase):
    """Схема для создания промокода."""
    pass


class PromoCodeUpdate(BaseSchema):
    """Схема для обновления промокода."""
    discount_percent: Optional[int] = Field(None, ge=0, le=100)
    discount_amount: Optional[int] = Field(None, ge=0)
    max_uses: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class PromoCode(PromoCodeBase):
    """Схема промокода для ответа."""
    id: int
    current_uses: int
    is_active: bool
    created_at: datetime


class PromoCodeCheck(BaseSchema):
    """Схема для проверки промокода."""
    code: str
    item_type: str = Field(..., pattern="^(lesson|course)$")
    item_id: int


# ========== Support Ticket Schemas ==========

class SupportTicketBase(BaseSchema):
    """Базовая схема тикета поддержки."""
    subject: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=5000)


class SupportTicketCreate(SupportTicketBase):
    """Схема для создания тикета."""
    user_id: int


class SupportTicketUpdate(BaseSchema):
    """Схема для обновления тикета."""
    status: Optional[SupportTicketStatus] = None
    admin_response: Optional[str] = Field(None, max_length=5000)


class SupportTicket(SupportTicketBase):
    """Схема тикета для ответа."""
    id: int
    user_id: int
    status: SupportTicketStatus
    admin_response: Optional[str]
    created_at: datetime
    updated_at: datetime


class SupportTicketWithUser(SupportTicket):
    """Схема тикета с информацией о пользователе."""
    user: Optional[User] = None


# ========== Admin User Schemas ==========

class AdminUserBase(BaseSchema):
    """Базовая схема администратора."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class AdminUserCreate(AdminUserBase):
    """Схема для создания администратора."""
    password: str = Field(..., min_length=6, max_length=100)
    is_superuser: bool = Field(default=False)


class AdminUserUpdate(BaseSchema):
    """Схема для обновления администратора."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class AdminUser(AdminUserBase):
    """Схема администратора для ответа."""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


# ========== Authentication Schemas ==========

class Token(BaseSchema):
    """Схема токена."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseSchema):
    """Схема данных токена."""
    username: Optional[str] = None


class LoginRequest(BaseSchema):
    """Схема запроса авторизации."""
    username: str
    password: str


class ChangePasswordRequest(BaseSchema):
    """Схема запроса смены пароля."""
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


# ========== Pagination Schemas ==========

class PaginationParams(BaseSchema):
    """Параметры пагинации."""
    page: int = Field(default=1, ge=1, description="Номер страницы")
    size: int = Field(default=20, ge=1, le=100, description="Размер страницы")


class PaginatedResponse(BaseSchema):
    """Схема пагинированного ответа."""
    items: List[BaseSchema]
    total: int
    page: int
    size: int
    pages: int


# ========== Statistics Schemas ==========

class UserStats(BaseSchema):
    """Статистика пользователей."""
    total_users: int
    active_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int


class SalesStats(BaseSchema):
    """Статистика продаж."""
    total_purchases: int
    total_revenue: int
    purchases_today: int
    revenue_today: int
    purchases_this_week: int
    revenue_this_week: int
    purchases_this_month: int
    revenue_this_month: int


class ContentStats(BaseSchema):
    """Статистика контента."""
    total_lessons: int
    active_lessons: int
    free_lessons: int
    paid_lessons: int
    total_courses: int
    active_courses: int


class SystemStats(BaseSchema):
    """Общая статистика системы."""
    user_stats: UserStats
    sales_stats: SalesStats
    content_stats: ContentStats


# ========== File Upload Schemas ==========

class FileUploadResponse(BaseSchema):
    """Ответ загрузки файла."""
    filename: str
    file_path: str
    file_size: int
    file_type: str
    uploaded_at: datetime


class FileInfo(BaseSchema):
    """Информация о файле."""
    filename: str
    file_path: str
    file_size: int
    file_size_formatted: str
    file_type: str
    exists: bool


# ========== Error Schemas ==========

class ErrorResponse(BaseSchema):
    """Схема ошибки."""
    error: str
    message: str
    details: Optional[dict] = None


class ValidationErrorResponse(BaseSchema):
    """Схема ошибки валидации."""
    error: str = "validation_error"
    message: str
    details: List[dict]


# ========== Health Check Schema ==========

class HealthCheckResponse(BaseSchema):
    """Схема проверки здоровья системы."""
    status: str
    timestamp: datetime
    version: str
    database: dict
    services: dict


# Обновляем forward references
UserWithPurchases.model_rebuild()
LessonWithPurchases.model_rebuild()
CourseWithLessons.model_rebuild()
PurchaseWithDetails.model_rebuild()
SupportTicketWithUser.model_rebuild()