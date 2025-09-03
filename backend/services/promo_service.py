"""
Сервис для работы с промокодами.
Создание, валидация, применение промокодов и управление скидками.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from shared.models import PromoCode, Purchase, User
from shared.constants import MAX_PROMO_USES, MAX_DISCOUNT_PERCENT, MIN_PRICE
from shared.schemas import PromoCodeCreate, PromoCodeUpdate, PromoCodeCheck


class PromoCodeService:
    """Сервис для работы с промокодами."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_promo_code(
        self, 
        code: str, 
        discount_percent: int = 0,
        discount_amount: Optional[int] = None,
        max_uses: Optional[int] = None,
        expires_at: Optional[datetime] = None
    ) -> PromoCode:
        """
        Создание нового промокода.
        
        Args:
            code: Код промокода
            discount_percent: Скидка в процентах
            discount_amount: Фиксированная скидка в Stars
            max_uses: Максимальное количество использований
            expires_at: Дата истечения
            
        Returns:
            PromoCode: Созданный промокод
            
        Raises:
            ValueError: При неверных параметрах
        """
        # Валидация параметров
        if not code or len(code) < 3:
            raise ValueError("Код промокода должен содержать минимум 3 символа")
        
        if discount_percent < 0 or discount_percent > MAX_DISCOUNT_PERCENT:
            raise ValueError(f"Процент скидки должен быть от 0 до {MAX_DISCOUNT_PERCENT}")
        
        if discount_amount and discount_amount < 0:
            raise ValueError("Фиксированная скидка не может быть отрицательной")
        
        if not discount_percent and not discount_amount:
            raise ValueError("Должен быть указан либо процент, либо фиксированная скидка")
        
        if max_uses and max_uses > MAX_PROMO_USES:
            raise ValueError(f"Максимальное количество использований не может превышать {MAX_PROMO_USES}")
        
        # Проверка уникальности кода
        existing_promo = self.db.query(PromoCode).filter(
            PromoCode.code == code.upper()
        ).first()
        
        if existing_promo:
            raise ValueError("Промокод с таким кодом уже существует")
        
        # Создание промокода
        promo_code = PromoCode(
            code=code.upper(),
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            max_uses=max_uses,
            expires_at=expires_at,
            current_uses=0,
            is_active=True
        )
        
        self.db.add(promo_code)
        self.db.commit()
        self.db.refresh(promo_code)
        
        return promo_code
    
    def validate_promo_code(self, code: str, user_id: Optional[int] = None) -> PromoCode:
        """
        Валидация промокода.
        
        Args:
            code: Код промокода
            user_id: ID пользователя (опционально)
            
        Returns:
            PromoCode: Валидный промокод
            
        Raises:
            ValueError: При невалидном промокоде
        """
        promo = self.db.query(PromoCode).filter(
            PromoCode.code == code.upper()
        ).first()
        
        if not promo:
            raise ValueError("Промокод не найден")
        
        if not promo.is_active:
            raise ValueError("Промокод деактивирован")
        
        if promo.expires_at and promo.expires_at < datetime.utcnow():
            raise ValueError("Промокод истек")
        
        if promo.max_uses and promo.current_uses >= promo.max_uses:
            raise ValueError("Промокод исчерпан")
        
        # Дополнительная проверка для конкретного пользователя
        if user_id:
            # Проверка, что пользователь не использовал этот промокод ранее
            # (можно добавить таблицу для отслеживания использований по пользователям)
            pass
        
        return promo
    
    def apply_discount(self, promo_code: PromoCode, amount: int) -> Dict[str, int]:
        """
        Применение скидки промокода.
        
        Args:
            promo_code: Промокод
            amount: Базовая сумма
            
        Returns:
            Dict: Информация о скидке
        """
        if promo_code.discount_amount:
            # Фиксированная скидка
            discount = min(promo_code.discount_amount, amount - MIN_PRICE)
        else:
            # Процентная скидка
            discount = (amount * promo_code.discount_percent) // 100
        
        # Убедимся, что финальная цена не меньше минимальной
        discount = min(discount, amount - MIN_PRICE)
        final_amount = max(MIN_PRICE, amount - discount)
        
        return {
            "original_amount": amount,
            "discount_amount": discount,
            "final_amount": final_amount,
            "discount_percent": (discount * 100) // amount if amount > 0 else 0
        }
    
    def use_promo_code(self, code: str, user_id: int) -> bool:
        """
        Использование промокода.
        
        Args:
            code: Код промокода
            user_id: ID пользователя
            
        Returns:
            bool: Результат использования
        """
        try:
            promo = self.validate_promo_code(code, user_id)
            
            # Увеличиваем счетчик использований
            promo.current_uses += 1
            
            # Деактивируем, если достигнут лимит
            if promo.max_uses and promo.current_uses >= promo.max_uses:
                promo.is_active = False
            
            self.db.commit()
            return True
            
        except ValueError:
            return False
    
    def get_active_promocodes(
        self, 
        limit: Optional[int] = None,
        include_expired: bool = False
    ) -> List[PromoCode]:
        """
        Получение активных промокодов.
        
        Args:
            limit: Лимит результатов
            include_expired: Включать истекшие промокоды
            
        Returns:
            List[PromoCode]: Список промокодов
        """
        query = self.db.query(PromoCode).filter(PromoCode.is_active == True)
        
        if not include_expired:
            query = query.filter(
                or_(
                    PromoCode.expires_at.is_(None),
                    PromoCode.expires_at > datetime.utcnow()
                )
            )
        
        query = query.order_by(PromoCode.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_promo_code_by_id(self, promo_id: int) -> Optional[PromoCode]:
        """Получение промокода по ID."""
        return self.db.query(PromoCode).filter(PromoCode.id == promo_id).first()
    
    def get_promo_code_by_code(self, code: str) -> Optional[PromoCode]:
        """Получение промокода по коду."""
        return self.db.query(PromoCode).filter(
            PromoCode.code == code.upper()
        ).first()
    
    def update_promo_code(
        self, 
        promo_id: int, 
        update_data: PromoCodeUpdate
    ) -> Optional[PromoCode]:
        """
        Обновление промокода.
        
        Args:
            promo_id: ID промокода
            update_data: Данные для обновления
            
        Returns:
            Optional[PromoCode]: Обновленный промокод
        """
        promo = self.get_promo_code_by_id(promo_id)
        if not promo:
            return None
        
        # Обновление полей
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            if hasattr(promo, field):
                setattr(promo, field, value)
        
        self.db.commit()
        self.db.refresh(promo)
        
        return promo
    
    def delete_promo_code(self, promo_id: int) -> bool:
        """
        Удаление (деактивация) промокода.
        
        Args:
            promo_id: ID промокода
            
        Returns:
            bool: Результат операции
        """
        promo = self.get_promo_code_by_id(promo_id)
        if not promo:
            return False
        
        promo.is_active = False
        self.db.commit()
        
        return True
    
    def get_promo_code_stats(self, promo_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение статистики использования промокода.
        
        Args:
            promo_id: ID промокода
            
        Returns:
            Optional[Dict]: Статистика промокода
        """
        promo = self.get_promo_code_by_id(promo_id)
        if not promo:
            return None
        
        # Подсчет использований (через таблицу покупок, если нужно более детальная статистика)
        total_revenue = 0  # Можно добавить подсчет экономии от промокода
        
        return {
            "promo_code": promo.code,
            "total_uses": promo.current_uses,
            "max_uses": promo.max_uses,
            "remaining_uses": (promo.max_uses - promo.current_uses) if promo.max_uses else None,
            "is_active": promo.is_active,
            "is_expired": promo.expires_at and promo.expires_at < datetime.utcnow(),
            "created_at": promo.created_at,
            "expires_at": promo.expires_at,
            "discount_percent": promo.discount_percent,
            "discount_amount": promo.discount_amount,
            "total_revenue_saved": total_revenue
        }
    
    def cleanup_expired_promocodes(self) -> int:
        """
        Очистка истекших промокодов.
        
        Returns:
            int: Количество деактивированных промокодов
        """
        expired_promos = self.db.query(PromoCode).filter(
            and_(
                PromoCode.is_active == True,
                PromoCode.expires_at < datetime.utcnow()
            )
        ).all()
        
        for promo in expired_promos:
            promo.is_active = False
        
        self.db.commit()
        
        return len(expired_promos)
    
    def generate_promo_code(
        self, 
        prefix: str = "PROMO",
        length: int = 8
    ) -> str:
        """
        Генерация уникального кода промокода.
        
        Args:
            prefix: Префикс кода
            length: Длина случайной части
            
        Returns:
            str: Уникальный код
        """
        import random
        import string
        
        while True:
            random_part = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=length)
            )
            code = f"{prefix}{random_part}"
            
            # Проверка уникальности
            existing = self.get_promo_code_by_code(code)
            if not existing:
                return code
    
    def bulk_create_promocodes(
        self,
        count: int,
        discount_percent: int,
        prefix: str = "BULK",
        max_uses: Optional[int] = 1,
        expires_at: Optional[datetime] = None
    ) -> List[PromoCode]:
        """
        Массовое создание промокодов.
        
        Args:
            count: Количество промокодов
            discount_percent: Процент скидки
            prefix: Префикс для кодов
            max_uses: Максимальное количество использований
            expires_at: Дата истечения
            
        Returns:
            List[PromoCode]: Список созданных промокодов
        """
        if count > 1000:
            raise ValueError("Нельзя создать более 1000 промокодов за раз")
        
        promocodes = []
        
        for i in range(count):
            code = self.generate_promo_code(prefix)
            
            promo = PromoCode(
                code=code,
                discount_percent=discount_percent,
                max_uses=max_uses,
                expires_at=expires_at,
                current_uses=0,
                is_active=True
            )
            
            promocodes.append(promo)
            self.db.add(promo)
        
        self.db.commit()
        
        return promocodes