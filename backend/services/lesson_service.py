"""
Сервис для работы с уроками.
"""

import os
from typing import List, Optional, Tuple

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from shared.models import Lesson, Purchase, User
from shared.utils import sanitize_filename, get_file_size
from shared.constants import VIDEO_STORAGE_PATH


class LessonService:
    """Сервис для работы с уроками."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_lesson(
        self,
        title: str,
        description: str,
        price: int,
        video_path: Optional[str] = None,
        text_content: Optional[str] = None,
        is_free: bool = False
    ) -> Lesson:
        """Создание нового урока."""
        lesson = Lesson(
            title=title,
            description=description,
            price=price,
            video_path=video_path,
            text_content=text_content,
            is_free=is_free
        )
        
        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        
        return lesson
    
    def get_lesson_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """Получение урока по ID."""
        return self.db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    def get_active_lessons(
        self,
        search: Optional[str] = None,
        is_free: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Lesson], int]:
        """Получение списка активных уроков."""
        query = self.db.query(Lesson).filter(Lesson.is_active == True)
        
        # Применение фильтров
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (Lesson.title.ilike(search_filter)) |
                (Lesson.description.ilike(search_filter))
            )
        
        if is_free is not None:
            query = query.filter(Lesson.is_free == is_free)
        
        total = query.count()
        lessons = query.order_by(Lesson.created_at.desc()).offset(offset).limit(limit).all()
        
        return lessons, total
    
    def update_lesson(
        self,
        lesson_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[int] = None,
        video_path: Optional[str] = None,
        text_content: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_free: Optional[bool] = None
    ) -> Optional[Lesson]:
        """Обновление урока."""
        lesson = self.get_lesson_by_id(lesson_id)
        if not lesson:
            return None
        
        # Обновление полей
        if title is not None:
            lesson.title = title
        if description is not None:
            lesson.description = description
        if price is not None:
            lesson.price = price
        if video_path is not None:
            lesson.video_path = video_path
        if text_content is not None:
            lesson.text_content = text_content
        if is_active is not None:
            lesson.is_active = is_active
        if is_free is not None:
            lesson.is_free = is_free
        
        try:
            self.db.commit()
            self.db.refresh(lesson)
            return lesson
        except Exception:
            self.db.rollback()
            return None
    
    def delete_lesson(self, lesson_id: int) -> bool:
        """Удаление урока (мягкое удаление)."""
        lesson = self.get_lesson_by_id(lesson_id)
        if not lesson:
            return False
        
        # Проверка активных покупок
        active_purchases = self.db.query(Purchase).filter(
            and_(
                Purchase.lesson_id == lesson_id,
                Purchase.status == "completed"
            )
        ).count()
        
        if active_purchases > 0:
            # Мягкое удаление
            lesson.is_active = False
        else:
            # Полное удаление
            self.db.delete(lesson)
        
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def save_video_file(self, lesson_id: int, filename: str, content: bytes) -> Optional[str]:
        """Сохранение видеофайла урока."""
        # Создание директории
        os.makedirs(VIDEO_STORAGE_PATH, exist_ok=True)
        
        # Генерация безопасного имени файла
        safe_filename = sanitize_filename(filename)
        file_path = os.path.join(VIDEO_STORAGE_PATH, f"lesson_{lesson_id}_{safe_filename}")
        
        try:
            # Удаление старого файла если существует
            lesson = self.get_lesson_by_id(lesson_id)
            if lesson and lesson.video_path and os.path.exists(lesson.video_path):
                os.remove(lesson.video_path)
            
            # Сохранение нового файла
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Обновление пути в базе данных
            if lesson:
                lesson.video_path = file_path
                self.db.commit()
            
            return file_path
        except Exception:
            self.db.rollback()
            return None
    
    def delete_video_file(self, lesson_id: int) -> bool:
        """Удаление видеофайла урока."""
        lesson = self.get_lesson_by_id(lesson_id)
        if not lesson or not lesson.video_path:
            return False
        
        try:
            # Удаление файла
            if os.path.exists(lesson.video_path):
                os.remove(lesson.video_path)
            
            # Обновление записи в БД
            lesson.video_path = None
            self.db.commit()
            
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def get_lesson_statistics(self, lesson_id: int) -> dict:
        """Получение статистики урока."""
        lesson = self.get_lesson_by_id(lesson_id)
        if not lesson:
            return {}
        
        # Статистика покупок
        purchase_stats = self.db.query(
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.amount).label("total_revenue"),
            func.count(Purchase.id).filter(Purchase.status == "completed").label("completed_purchases")
        ).filter(Purchase.lesson_id == lesson_id).first()
        
        # Уникальные покупатели
        unique_buyers = self.db.query(func.count(func.distinct(Purchase.user_id))).filter(
            and_(
                Purchase.lesson_id == lesson_id,
                Purchase.status == "completed"
            )
        ).scalar()
        
        return {
            "lesson_info": {
                "id": lesson.id,
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
                "unique_buyers": unique_buyers or 0,
                "conversion_rate": round(
                    (purchase_stats.completed_purchases or 0) / 
                    max(purchase_stats.total_purchases or 1, 1) * 100, 2
                )
            },
            "file_info": {
                "has_video": lesson.video_path is not None,
                "video_exists": lesson.video_path and os.path.exists(lesson.video_path),
                "video_size": get_file_size(lesson.video_path) if lesson.video_path else 0,
                "has_text_content": lesson.text_content is not None
            }
        }
    
    def check_user_access(self, lesson_id: int, user_id: int) -> bool:
        """Проверка доступа пользователя к уроку."""
        lesson = self.get_lesson_by_id(lesson_id)
        if not lesson or not lesson.is_active:
            return False
        
        # Бесплатные уроки доступны всем
        if lesson.is_free:
            return True
        
        # Проверка покупки
        purchase = self.db.query(Purchase).filter(
            and_(
                Purchase.user_id == user_id,
                Purchase.lesson_id == lesson_id,
                Purchase.status == "completed"
            )
        ).first()
        
        return purchase is not None