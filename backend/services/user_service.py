"""
Сервис для работы с пользователями.
"""

from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from shared.models import User, Purchase


class UserService:
    """Сервис для работы с пользователями."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_or_create_user(
        self, 
        telegram_id: int, 
        username: Optional[str] = None,
        first_name: str = "",
        last_name: Optional[str] = None,
        language_code: str = "en"
    ) -> User:
        """Найти пользователя по telegram_id или создать нового."""
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if user:
            # Обновляем информацию если что-то изменилось
            updated = False
            if user.username != username:
                user.username = username
                updated = True
            if user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if user.language_code != language_code:
                user.language_code = language_code
                updated = True
            
            if updated:
                self.db.commit()
                self.db.refresh(user)
            
            return user
        
        # Создаем нового пользователя
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID."""
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()
    
    def get_user_purchases(
        self, 
        user_id: int, 
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Purchase], int]:
        """Получение покупок пользователя."""
        query = self.db.query(Purchase).filter(Purchase.user_id == user_id)
        
        if status:
            query = query.filter(Purchase.status == status)
        
        total = query.count()
        purchases = query.order_by(Purchase.created_at.desc()).offset(offset).limit(limit).all()
        
        return purchases, total
    
    def get_user_statistics(self, user_id: int) -> dict:
        """Получение статистики пользователя."""
        # Базовая информация о пользователе
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}
        
        # Статистика покупок
        purchase_stats = self.db.query(
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.amount).label("total_spent"),
            func.count(Purchase.id).filter(Purchase.status == "completed").label("completed_purchases")
        ).filter(Purchase.user_id == user_id).first()
        
        # Покупки по типам
        lessons_purchased = self.db.query(func.count(Purchase.id)).filter(
            and_(
                Purchase.user_id == user_id,
                Purchase.lesson_id.isnot(None),
                Purchase.status == "completed"
            )
        ).scalar()
        
        courses_purchased = self.db.query(func.count(Purchase.id)).filter(
            and_(
                Purchase.user_id == user_id,
                Purchase.course_id.isnot(None),
                Purchase.status == "completed"
            )
        ).scalar()
        
        return {
            "user_info": {
                "id": user.id,
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
                "lessons_purchased": lessons_purchased or 0,
                "courses_purchased": courses_purchased or 0
            }
        }
    
    def update_user_language(self, telegram_id: int, language_code: str) -> bool:
        """Обновление языка пользователя."""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        
        user.language_code = language_code
        
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """Деактивация пользователя."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = False
        
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def get_users_overview(self) -> dict:
        """Получение общей статистики пользователей."""
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Общая статистика
        total_users = self.db.query(func.count(User.id)).scalar()
        active_users = self.db.query(func.count(User.id)).filter(User.is_active == True).scalar()
        
        # Новые пользователи
        new_users_today = self.db.query(func.count(User.id)).filter(
            User.created_at >= today
        ).scalar()
        new_users_this_week = self.db.query(func.count(User.id)).filter(
            User.created_at >= week_ago
        ).scalar()
        new_users_this_month = self.db.query(func.count(User.id)).filter(
            User.created_at >= month_ago
        ).scalar()
        
        return {
            "total_users": total_users or 0,
            "active_users": active_users or 0,
            "new_users_today": new_users_today or 0,
            "new_users_this_week": new_users_this_week or 0,
            "new_users_this_month": new_users_this_month or 0
        }