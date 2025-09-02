"""
API endpoints для работы с курсами.
CRUD операции, управление уроками в курсе, статистика курсов.
"""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import Course, Lesson, CourseLesson, Purchase, User
from shared.schemas import (
    Course as CourseSchema,
    CourseCreate,
    CourseUpdate,
    CourseWithLessons,
    Lesson as LessonSchema
)
from backend.api.deps import (
    get_current_active_admin,
    get_pagination_params,
    create_pagination_response,
    PaginationParams
)

router = APIRouter()


@router.get("/", response_model=dict, summary="Список курсов")
def get_courses(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: str = Query(None, description="Поиск по названию или описанию"),
    is_active: bool = Query(None, description="Фильтр по статусу активности"),
    min_price: int = Query(None, description="Минимальная цена"),
    max_price: int = Query(None, description="Максимальная цена"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение списка курсов с пагинацией и фильтрами.
    
    - **page**: Номер страницы (по умолчанию 1)
    - **size**: Размер страницы (по умолчанию 20, максимум 100)
    - **search**: Поиск по названию или описанию курса
    - **is_active**: Фильтр по статусу активности
    - **min_price**: Минимальная цена в Stars
    - **max_price**: Максимальная цена в Stars
    """
    query = db.query(Course)
    
    # Применение фильтров
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Course.title.ilike(search_filter)) |
            (Course.description.ilike(search_filter))
        )
    
    if is_active is not None:
        query = query.filter(Course.is_active == is_active)
    
    if min_price is not None:
        query = query.filter(Course.total_price >= min_price)
    
    if max_price is not None:
        query = query.filter(Course.total_price <= max_price)
    
    # Подсчет общего количества
    total = query.count()
    
    # Применение пагинации и сортировка по дате создания
    courses = query.order_by(Course.created_at.desc()).offset(pagination.offset).limit(pagination.size).all()
    
    return create_pagination_response(courses, total, pagination)


@router.get("/public", response_model=dict, summary="Публичный список активных курсов")
def get_public_courses(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение списка активных курсов без аутентификации.
    Используется для отображения в Telegram Bot.
    """
    query = db.query(Course).filter(Course.is_active == True)
    
    total = query.count()
    courses = query.order_by(Course.created_at.desc()).offset(pagination.offset).limit(pagination.size).all()
    
    # Добавляем количество уроков для каждого курса
    for course in courses:
        course.lessons_count = db.query(func.count(CourseLesson.lesson_id)).filter(
            CourseLesson.course_id == course.id
        ).scalar()
    
    return create_pagination_response(courses, total, pagination)


@router.get("/{course_id}", response_model=CourseWithLessons, summary="Детали курса")
def get_course(
    course_id: int,
    include_lessons: bool = Query(True, description="Включить список уроков"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение детальной информации о курсе.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if include_lessons:
        # Получаем уроки курса в правильном порядке
        course_lessons = db.query(CourseLesson).join(Lesson).filter(
            CourseLesson.course_id == course_id,
            Lesson.is_active == True
        ).order_by(CourseLesson.order_index).all()
        
        course.lessons = [cl.lesson for cl in course_lessons]
        course.lessons_count = len(course.lessons)
    else:
        course.lessons = []
        course.lessons_count = 0
    
    return course


@router.get("/{course_id}/public", response_model=CourseWithLessons, summary="Публичные детали курса")
def get_public_course(
    course_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение публичной информации о курсе без аутентификации.
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_active == True
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Получаем активные уроки курса
    course_lessons = db.query(CourseLesson).join(Lesson).filter(
        CourseLesson.course_id == course_id,
        Lesson.is_active == True
    ).order_by(CourseLesson.order_index).all()
    
    course.lessons = [cl.lesson for cl in course_lessons]
    course.lessons_count = len(course.lessons)
    
    return course


@router.post("/", response_model=CourseSchema, summary="Создание курса")
def create_course(
    course_data: CourseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Создание нового курса.
    
    - **title**: Название курса
    - **description**: Описание курса
    - **total_price**: Общая цена в Telegram Stars
    - **discount_price**: Цена со скидкой (опционально)
    - **lesson_ids**: Список ID уроков для добавления в курс
    """
    # Создаем курс без уроков
    course_dict = course_data.dict()
    lesson_ids = course_dict.pop('lesson_ids', [])
    
    course = Course(**course_dict)
    
    try:
        db.add(course)
        db.commit()
        db.refresh(course)
        
        # Добавляем уроки в курс
        if lesson_ids:
            for idx, lesson_id in enumerate(lesson_ids):
                # Проверяем существование урока
                lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
                if lesson:
                    course_lesson = CourseLesson(
                        course_id=course.id,
                        lesson_id=lesson_id,
                        order_index=idx + 1
                    )
                    db.add(course_lesson)
            
            db.commit()
        
        return course
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course"
        )


@router.put("/{course_id}", response_model=CourseSchema, summary="Обновление курса")
def update_course(
    course_id: int,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Обновление данных курса.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Обновление полей
    update_data = course_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)
    
    try:
        db.commit()
        db.refresh(course)
        return course
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update course"
        )


@router.delete("/{course_id}", summary="Удаление курса")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Удаление курса (мягкое удаление - деактивация).
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Проверка, есть ли активные покупки
    active_purchases = db.query(Purchase).filter(
        Purchase.course_id == course_id,
        Purchase.status == "completed"
    ).count()
    
    if active_purchases > 0:
        # Мягкое удаление - деактивация
        course.is_active = False
        try:
            db.commit()
            return {"message": f"Course deactivated (has {active_purchases} active purchases)"}
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate course"
            )
    else:
        # Полное удаление если нет покупок
        try:
            # Удаляем связи с уроками
            db.query(CourseLesson).filter(CourseLesson.course_id == course_id).delete()
            # Удаляем курс
            db.delete(course)
            db.commit()
            return {"message": "Course deleted successfully"}
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete course"
            )


@router.get("/{course_id}/lessons", response_model=List[LessonSchema], summary="Уроки курса")
def get_course_lessons(
    course_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение списка уроков в курсе в правильном порядке.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    course_lessons = db.query(CourseLesson).join(Lesson).filter(
        CourseLesson.course_id == course_id
    ).order_by(CourseLesson.order_index).all()
    
    return [cl.lesson for cl in course_lessons]


@router.post("/{course_id}/lessons", summary="Добавление урока в курс")
def add_lesson_to_course(
    course_id: int,
    lesson_id: int,
    order_index: int = Query(None, description="Позиция урока в курсе"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Добавление урока в курс.
    
    - **lesson_id**: ID урока для добавления
    - **order_index**: Позиция урока в курсе (опционально)
    """
    # Проверка существования курса
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Проверка существования урока
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Проверка, что урок еще не добавлен в курс
    existing = db.query(CourseLesson).filter(
        CourseLesson.course_id == course_id,
        CourseLesson.lesson_id == lesson_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lesson already in course"
        )
    
    # Определение позиции урока
    if order_index is None:
        max_order = db.query(func.max(CourseLesson.order_index)).filter(
            CourseLesson.course_id == course_id
        ).scalar()
        order_index = (max_order or 0) + 1
    
    # Создание связи
    course_lesson = CourseLesson(
        course_id=course_id,
        lesson_id=lesson_id,
        order_index=order_index
    )
    
    try:
        db.add(course_lesson)
        db.commit()
        return {"message": "Lesson added to course successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add lesson to course"
        )


@router.delete("/{course_id}/lessons/{lesson_id}", summary="Удаление урока из курса")
def remove_lesson_from_course(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Удаление урока из курса.
    """
    course_lesson = db.query(CourseLesson).filter(
        CourseLesson.course_id == course_id,
        CourseLesson.lesson_id == lesson_id
    ).first()
    
    if not course_lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found in course"
        )
    
    try:
        db.delete(course_lesson)
        db.commit()
        return {"message": "Lesson removed from course successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove lesson from course"
        )


@router.put("/{course_id}/lessons/reorder", summary="Изменение порядка уроков в курсе")
def reorder_course_lessons(
    course_id: int,
    lesson_order: List[dict],  # [{"lesson_id": 1, "order_index": 1}, ...]
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Изменение порядка уроков в курсе.
    
    Ожидает список объектов с lesson_id и order_index.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    try:
        for item in lesson_order:
            lesson_id = item.get("lesson_id")
            order_index = item.get("order_index")
            
            if lesson_id is None or order_index is None:
                continue
                
            course_lesson = db.query(CourseLesson).filter(
                CourseLesson.course_id == course_id,
                CourseLesson.lesson_id == lesson_id
            ).first()
            
            if course_lesson:
                course_lesson.order_index = order_index
        
        db.commit()
        return {"message": "Lessons reordered successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder lessons"
        )


@router.get("/{course_id}/statistics", summary="Статистика курса")
def get_course_statistics(
    course_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение статистики по конкретному курсу.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Статистика покупок
    purchase_stats = db.query(
        func.count(Purchase.id).label("total_purchases"),
        func.sum(Purchase.amount).label("total_revenue"),
        func.count(Purchase.id).filter(Purchase.status == "completed").label("completed_purchases")
    ).filter(Purchase.course_id == course_id).first()
    
    # Уникальные покупатели
    unique_buyers = db.query(func.count(func.distinct(Purchase.user_id))).filter(
        Purchase.course_id == course_id,
        Purchase.status == "completed"
    ).scalar()
    
    # Количество уроков в курсе
    lessons_count = db.query(func.count(CourseLesson.lesson_id)).filter(
        CourseLesson.course_id == course_id
    ).scalar()
    
    return {
        "course_id": course_id,
        "course_info": {
            "title": course.title,
            "total_price": course.total_price,
            "discount_price": course.discount_price,
            "is_active": course.is_active,
            "created_at": course.created_at,
            "lessons_count": lessons_count
        },
        "purchase_statistics": {
            "total_purchases": purchase_stats.total_purchases or 0,
            "completed_purchases": purchase_stats.completed_purchases or 0,
            "total_revenue": purchase_stats.total_revenue or 0,
            "unique_buyers": unique_buyers,
            "conversion_rate": round((purchase_stats.completed_purchases or 0) / max(purchase_stats.total_purchases or 1, 1) * 100, 2)
        }
    }


@router.get("/{course_id}/purchasers", response_model=dict, summary="Покупатели курса")
def get_course_purchasers(
    course_id: int,
    pagination: PaginationParams = Depends(get_pagination_params),
    status_filter: str = Query("completed", description="Статус покупки"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
) -> Any:
    """
    Получение списка пользователей, купивших курс.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    query = db.query(Purchase).join(User).filter(
        Purchase.course_id == course_id,
        Purchase.status == status_filter
    )
    
    total = query.count()
    purchases = query.offset(pagination.offset).limit(pagination.size).all()
    
    # Добавляем информацию о пользователях
    for purchase in purchases:
        purchase.user = db.query(User).filter(User.id == purchase.user_id).first()
    
    return create_pagination_response(purchases, total, pagination)