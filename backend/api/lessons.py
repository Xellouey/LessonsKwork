"""
API endpoints для работы с уроками.
CRUD операции, загрузка файлов, статистика уроков.
"""

import os
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import Lesson, Purchase, User
from shared.schemas import (
    Lesson as LessonSchema,
    LessonCreate,
    LessonUpdate,
    LessonWithPurchases,
    ContentStats
)
from shared.utils import sanitize_filename, get_file_size, format_file_size
from shared.constants import (
    ALLOWED_VIDEO_EXTENSIONS, ALLOWED_TEXT_EXTENSIONS,
    MAX_VIDEO_SIZE, MAX_FILE_SIZE, VIDEO_STORAGE_PATH, TEXT_STORAGE_PATH
)
from backend.api.deps import (
    get_current_active_admin,
    get_pagination_params,
    create_pagination_response,
    PaginationParams
)
from backend.config import settings

router = APIRouter()


@router.get("/", response_model=dict, summary="Список уроков")
def get_lessons(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: str = Query(None, description="Поиск по названию или описанию"),
    is_active: bool = Query(None, description="Фильтр по статусу активности"),
    is_free: bool = Query(None, description="Фильтр по бесплатности"),
    min_price: int = Query(None, description="Минимальная цена"),
    max_price: int = Query(None, description="Максимальная цена"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение списка уроков с пагинацией и фильтрами.
    
    - **page**: Номер страницы (по умолчанию 1)
    - **size**: Размер страницы (по умолчанию 20, максимум 100)
    - **search**: Поиск по названию или описанию урока
    - **is_active**: Фильтр по статусу активности
    - **is_free**: Фильтр по бесплатности
    - **min_price**: Минимальная цена в Stars
    - **max_price**: Максимальная цена в Stars
    """
    query = db.query(Lesson)
    
    # Применение фильтров
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Lesson.title.ilike(search_filter)) |
            (Lesson.description.ilike(search_filter))
        )
    
    if is_active is not None:
        query = query.filter(Lesson.is_active == is_active)
    
    if is_free is not None:
        query = query.filter(Lesson.is_free == is_free)
    
    if min_price is not None:
        query = query.filter(Lesson.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Lesson.price <= max_price)
    
    # Подсчет общего количества
    total = query.count()
    
    # Применение пагинации и сортировка по дате создания
    lessons = query.order_by(Lesson.created_at.desc()).offset(pagination.offset).limit(pagination.size).all()
    
    return create_pagination_response(lessons, total, pagination)


@router.get("/public", response_model=dict, summary="Публичный список активных уроков")
def get_public_lessons(
    pagination: PaginationParams = Depends(get_pagination_params),
    is_free: bool = Query(None, description="Только бесплатные уроки"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение списка активных уроков без аутентификации.
    Используется для отображения в Telegram Bot.
    """
    query = db.query(Lesson).filter(Lesson.is_active == True)
    
    if is_free is not None:
        query = query.filter(Lesson.is_free == is_free)
    
    total = query.count()
    lessons = query.order_by(Lesson.created_at.desc()).offset(pagination.offset).limit(pagination.size).all()
    
    return create_pagination_response(lessons, total, pagination)


@router.get("/{lesson_id}", response_model=LessonSchema, summary="Детали урока")
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение детальной информации об уроке.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    return lesson


@router.get("/{lesson_id}/public", response_model=LessonSchema, summary="Публичные детали урока")
def get_public_lesson(
    lesson_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение публичной информации об уроке без аутентификации.
    """
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.is_active == True
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    return lesson


@router.post("/", response_model=LessonSchema, summary="Создание урока")
def create_lesson(
    lesson_data: LessonCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Создание нового урока.
    
    - **title**: Название урока
    - **description**: Описание урока
    - **price**: Цена в Telegram Stars
    - **video_path**: Путь к видеофайлу (опционально)
    - **text_content**: Текстовое содержимое (опционально)
    - **is_free**: Бесплатный урок (по умолчанию False)
    """
    lesson = Lesson(**lesson_data.dict())
    
    try:
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return lesson
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create lesson"
        )


@router.put("/{lesson_id}", response_model=LessonSchema, summary="Обновление урока")
def update_lesson(
    lesson_id: int,
    lesson_data: LessonUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Обновление данных урока.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Обновление полей
    update_data = lesson_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)
    
    try:
        db.commit()
        db.refresh(lesson)
        return lesson
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update lesson"
        )


@router.delete("/{lesson_id}", summary="Удаление урока")
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Удаление урока (мягкое удаление - деактивация).
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Проверка, есть ли активные покупки
    active_purchases = db.query(Purchase).filter(
        Purchase.lesson_id == lesson_id,
        Purchase.status == "completed"
    ).count()
    
    if active_purchases > 0:
        # Мягкое удаление - деактивация
        lesson.is_active = False
        try:
            db.commit()
            return {"message": f"Lesson deactivated (has {active_purchases} active purchases)"}
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate lesson"
            )
    else:
        # Полное удаление если нет покупок
        try:
            db.delete(lesson)
            db.commit()
            return {"message": "Lesson deleted successfully"}
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete lesson"
            )


@router.post("/{lesson_id}/upload-video", summary="Загрузка видео к уроку")
async def upload_lesson_video(
    lesson_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Загрузка видеофайла для урока.
    
    Поддерживаемые форматы: mp4, avi, mkv, mov, wmv, flv, webm
    Максимальный размер: 100 MB
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Проверка расширения файла
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )
    
    # Проверка размера файла
    content = await file.read()
    if len(content) > MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {format_file_size(MAX_VIDEO_SIZE)}"
        )
    
    # Создание директории если не существует
    os.makedirs(VIDEO_STORAGE_PATH, exist_ok=True)
    
    # Генерация имени файла
    safe_filename = sanitize_filename(file.filename)
    file_path = os.path.join(VIDEO_STORAGE_PATH, f"lesson_{lesson_id}_{safe_filename}")
    
    # Удаление старого файла если существует
    if lesson.video_path and os.path.exists(lesson.video_path):
        try:
            os.remove(lesson.video_path)
        except OSError:
            pass
    
    # Сохранение файла
    try:
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Обновление пути в базе данных
        lesson.video_path = file_path
        db.commit()
        db.refresh(lesson)
        
        return {
            "message": "Video uploaded successfully",
            "filename": safe_filename,
            "file_path": file_path,
            "file_size": len(content),
            "file_size_formatted": format_file_size(len(content))
        }
    
    except Exception as e:
        db.rollback()
        # Удаление файла если сохранение в БД не удалось
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload video"
        )


@router.delete("/{lesson_id}/video", summary="Удаление видео урока")
def delete_lesson_video(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Удаление видеофайла урока.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    if not lesson.video_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lesson has no video file"
        )
    
    # Удаление файла
    if os.path.exists(lesson.video_path):
        try:
            os.remove(lesson.video_path)
        except OSError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete video file"
            )
    
    # Обновление записи в базе данных
    lesson.video_path = None
    
    try:
        db.commit()
        return {"message": "Video deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update lesson record"
        )


@router.get("/{lesson_id}/statistics", summary="Статистика урока")
def get_lesson_statistics(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение статистики по конкретному уроку.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Статистика покупок
    purchase_stats = db.query(
        func.count(Purchase.id).label("total_purchases"),
        func.sum(Purchase.amount).label("total_revenue"),
        func.count(Purchase.id).filter(Purchase.status == "completed").label("completed_purchases")
    ).filter(Purchase.lesson_id == lesson_id).first()
    
    # Уникальные покупатели
    unique_buyers = db.query(func.count(func.distinct(Purchase.user_id))).filter(
        Purchase.lesson_id == lesson_id,
        Purchase.status == "completed"
    ).scalar()
    
    return {
        "lesson_id": lesson_id,
        "lesson_info": {
            "title": lesson.title,
            "price": lesson.price,
            "is_free": lesson.is_free,
            "is_active": lesson.is_active,
            "created_at": lesson.created_at
        },
        "purchase_statistics": {
            "total_purchases": purchase_stats.total_purchases or 0,
            "completed_purchases": purchase_stats.completed_purchases or 0,
            "total_revenue": purchase_stats.total_revenue or 0,
            "unique_buyers": unique_buyers,
            "conversion_rate": round((purchase_stats.completed_purchases or 0) / max(purchase_stats.total_purchases or 1, 1) * 100, 2)
        },
        "file_info": {
            "has_video": lesson.video_path is not None,
            "video_exists": lesson.video_path and os.path.exists(lesson.video_path),
            "video_size": get_file_size(lesson.video_path) if lesson.video_path else 0,
            "has_text_content": lesson.text_content is not None
        }
    }


@router.get("/statistics/overview", response_model=ContentStats, summary="Общая статистика уроков")
def get_lessons_overview(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение общей статистики по всем урокам.
    """
    # Статистика уроков
    total_lessons = db.query(func.count(Lesson.id)).scalar()
    active_lessons = db.query(func.count(Lesson.id)).filter(Lesson.is_active == True).scalar()
    free_lessons = db.query(func.count(Lesson.id)).filter(Lesson.is_free == True).scalar()
    paid_lessons = db.query(func.count(Lesson.id)).filter(Lesson.is_free == False).scalar()
    
    # Статистика курсов (для ContentStats)
    from shared.models import Course
    total_courses = db.query(func.count(Course.id)).scalar()
    active_courses = db.query(func.count(Course.id)).filter(Course.is_active == True).scalar()
    
    return ContentStats(
        total_lessons=total_lessons,
        active_lessons=active_lessons,
        free_lessons=free_lessons,
        paid_lessons=paid_lessons,
        total_courses=total_courses,
        active_courses=active_courses
    )


@router.get("/{lesson_id}/purchasers", response_model=dict, summary="Покупатели урока")
def get_lesson_purchasers(
    lesson_id: int,
    pagination: PaginationParams = Depends(get_pagination_params),
    status_filter: str = Query("completed", description="Статус покупки"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение списка пользователей, купивших урок.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    query = db.query(Purchase).join(User).filter(
        Purchase.lesson_id == lesson_id,
        Purchase.status == status_filter
    )
    
    total = query.count()
    purchases = query.offset(pagination.offset).limit(pagination.size).all()
    
    # Добавляем информацию о пользователях
    for purchase in purchases:
        purchase.user = db.query(User).filter(User.id == purchase.user_id).first()
    
    return create_pagination_response(purchases, total, pagination)