"""
API endpoints для работы с пользователями.
CRUD операции, получение покупок пользователя, статистика.
"""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import User, Purchase, Lesson, Course
from shared.schemas import (
    User as UserSchema, 
    UserCreate, 
    UserUpdate, 
    UserWithPurchases,
    Purchase as PurchaseSchema,
    UserStats
)
from backend.api.deps import (
    get_current_active_admin, 
    get_pagination_params, 
    create_pagination_response,
    PaginationParams
)

router = APIRouter()


@router.get("/", response_model=dict, summary="Список пользователей")
def get_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: str = Query(None, description="Поиск по имени или username"),
    is_active: bool = Query(None, description="Фильтр по статусу активности"),
    language_code: str = Query(None, description="Фильтр по языку"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение списка пользователей с пагинацией и фильтрами.
    
    - **page**: Номер страницы (по умолчанию 1)
    - **size**: Размер страницы (по умолчанию 20, максимум 100)
    - **search**: Поиск по имени или username
    - **is_active**: Фильтр по статусу активности
    - **language_code**: Фильтр по языку пользователя
    """
    query = db.query(User)
    
    # Применение фильтров
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.first_name.ilike(search_filter)) |
            (User.last_name.ilike(search_filter)) |
            (User.username.ilike(search_filter))
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if language_code:
        query = query.filter(User.language_code == language_code)
    
    # Подсчет общего количества
    total = query.count()
    
    # Применение пагинации
    users = query.offset(pagination.offset).limit(pagination.size).all()
    
    return create_pagination_response(users, total, pagination)


@router.get("/{user_id}", response_model=UserSchema, summary="Профиль пользователя")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение профиля пользователя по ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.get("/telegram/{telegram_id}", response_model=UserSchema, summary="Пользователь по Telegram ID")
def get_user_by_telegram_id(
    telegram_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение пользователя по Telegram ID.
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/", response_model=UserSchema, summary="Создание пользователя")
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Создание нового пользователя.
    
    - **telegram_id**: Уникальный Telegram ID
    - **username**: Username в Telegram (опционально)
    - **first_name**: Имя пользователя
    - **last_name**: Фамилия (опционально)
    - **language_code**: Код языка (по умолчанию 'en')
    """
    # Проверка уникальности telegram_id
    existing_user = db.query(User).filter(User.telegram_id == user_data.telegram_id).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this Telegram ID already exists"
        )
    
    # Создание пользователя
    user = User(**user_data.dict())
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.put("/{user_id}", response_model=UserSchema, summary="Обновление пользователя")
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Обновление данных пользователя.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Обновление полей
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/{user_id}", summary="Удаление пользователя")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Удаление пользователя (мягкое удаление - деактивация).
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Мягкое удаление - деактивация пользователя
    user.is_active = False
    
    try:
        db.commit()
        return {"message": "User deactivated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )


@router.get("/{user_id}/purchases", response_model=dict, summary="Покупки пользователя")
def get_user_purchases(
    user_id: int,
    pagination: PaginationParams = Depends(get_pagination_params),
    status_filter: str = Query(None, description="Фильтр по статусу покупки"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение списка покупок пользователя.
    
    - **user_id**: ID пользователя
    - **page**: Номер страницы
    - **size**: Размер страницы
    - **status_filter**: Фильтр по статусу (pending, completed, failed, refunded)
    """
    # Проверка существования пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    query = db.query(Purchase).filter(Purchase.user_id == user_id)
    
    # Применение фильтра по статусу
    if status_filter:
        query = query.filter(Purchase.status == status_filter)
    
    # Подсчет общего количества
    total = query.count()
    
    # Применение пагинации и загрузка связанных данных
    purchases = query.offset(pagination.offset).limit(pagination.size).all()
    
    # Добавление информации об уроках и курсах
    for purchase in purchases:
        if purchase.lesson_id:
            purchase.lesson = db.query(Lesson).filter(Lesson.id == purchase.lesson_id).first()
        if purchase.course_id:
            purchase.course = db.query(Course).filter(Course.id == purchase.course_id).first()
    
    return create_pagination_response(purchases, total, pagination)


@router.get("/{user_id}/statistics", summary="Статистика пользователя")
def get_user_statistics(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение статистики по конкретному пользователю.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Статистика покупок
    purchase_stats = db.query(
        func.count(Purchase.id).label("total_purchases"),
        func.sum(Purchase.amount).label("total_spent"),
        func.count(Purchase.id).filter(Purchase.status == "completed").label("completed_purchases")
    ).filter(Purchase.user_id == user_id).first()
    
    # Количество купленных уроков и курсов
    lessons_purchased = db.query(func.count(Purchase.id)).filter(
        Purchase.user_id == user_id,
        Purchase.lesson_id.isnot(None),
        Purchase.status == "completed"
    ).scalar()
    
    courses_purchased = db.query(func.count(Purchase.id)).filter(
        Purchase.user_id == user_id,
        Purchase.course_id.isnot(None),
        Purchase.status == "completed"
    ).scalar()
    
    return {
        "user_id": user_id,
        "user_info": {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "language_code": user.language_code,
            "is_active": user.is_active,
            "created_at": user.created_at
        },
        "purchase_statistics": {
            "total_purchases": purchase_stats.total_purchases or 0,
            "completed_purchases": purchase_stats.completed_purchases or 0,
            "total_spent": purchase_stats.total_spent or 0,
            "lessons_purchased": lessons_purchased,
            "courses_purchased": courses_purchased
        }
    }


@router.get("/statistics/overview", response_model=UserStats, summary="Общая статистика пользователей")
def get_users_overview(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение общей статистики по всем пользователям.
    """
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Общая статистика
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    
    # Новые пользователи
    new_users_today = db.query(func.count(User.id)).filter(User.created_at >= today).scalar()
    new_users_this_week = db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar()
    new_users_this_month = db.query(func.count(User.id)).filter(User.created_at >= month_ago).scalar()
    
    return UserStats(
        total_users=total_users,
        active_users=active_users,
        new_users_today=new_users_today,
        new_users_this_week=new_users_this_week,
        new_users_this_month=new_users_this_month
    )


@router.post("/find-or-create", response_model=UserSchema, summary="Найти или создать пользователя")
def find_or_create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Найти пользователя по telegram_id или создать нового.
    Этот endpoint может использоваться Telegram Bot без аутентификации.
    """
    # Поиск существующего пользователя
    existing_user = db.query(User).filter(User.telegram_id == user_data.telegram_id).first()
    
    if existing_user:
        # Обновляем информацию если что-то изменилось
        updated = False
        if existing_user.username != user_data.username:
            existing_user.username = user_data.username
            updated = True
        if existing_user.first_name != user_data.first_name:
            existing_user.first_name = user_data.first_name
            updated = True
        if existing_user.last_name != user_data.last_name:
            existing_user.last_name = user_data.last_name
            updated = True
        if existing_user.language_code != user_data.language_code:
            existing_user.language_code = user_data.language_code
            updated = True
        
        if updated:
            try:
                db.commit()
                db.refresh(existing_user)
            except Exception:
                db.rollback()
        
        return existing_user
    
    # Создание нового пользователя
    user = User(**user_data.dict())
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )