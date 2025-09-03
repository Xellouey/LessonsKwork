"""
Сервис для обработки платежей и интеграции с Telegram Stars.
Основная логика создания, верификации и обработки платежей.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from shared.models import Purchase, User, Lesson, Course, PromoCode
from shared.constants import (
    PurchaseStatus, PaymentStatus, MIN_PRICE, MAX_PRICE, 
    PAYMENT_TIMEOUT_MINUTES, TELEGRAM_STARS_CURRENCY, COMMISSION_PERCENT
)
from shared.schemas import (
    PaymentCreateRequest, PaymentResponse, PaymentVerificationRequest,
    WebhookPaymentData
)


class PaymentService:
    """Сервис для работы с платежами."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_payment(
        self, 
        user_id: int, 
        item_id: int, 
        item_type: str, 
        promo_code: Optional[str] = None
    ) -> PaymentResponse:
        """
        Создание нового платежа.
        
        Args:
            user_id: ID пользователя
            item_id: ID товара (урок или курс)
            item_type: Тип товара ('lesson' или 'course')
            promo_code: Промокод (опционально)
            
        Returns:
            PaymentResponse: Данные созданного платежа
            
        Raises:
            ValueError: При неверных параметрах
            Exception: При ошибках базы данных
        """
        # Проверка пользователя
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Пользователь не найден")
        
        if not user.is_active:
            raise ValueError("Пользователь неактивен")
        
        # Получение товара и его цены
        item, base_price = self._get_item_and_price(item_id, item_type)
        if not item:
            raise ValueError(f"{item_type.capitalize()} не найден")
        
        if not item.is_active:
            raise ValueError(f"{item_type.capitalize()} неактивен")
        
        # Проверка на дублирование покупки
        if self._check_existing_purchase(user_id, item_id, item_type):
            raise ValueError("Товар уже приобретен")
        
        # Применение промокода
        discount_applied = 0
        final_price = base_price
        
        if promo_code:
            discount_applied, final_price = self._apply_promo_code(
                promo_code, base_price, user_id
            )
        
        # Создание уникального payment_id
        payment_id = self._generate_payment_id()
        
        # Создание payload для инвойса
        invoice_payload = self._create_invoice_payload(
            user_id, item_id, item_type, payment_id
        )
        
        # Создание записи о покупке
        purchase_data = {
            "user_id": user_id,
            "payment_id": payment_id,
            "amount": final_price,
            "status": PurchaseStatus.PENDING.value
        }
        
        if item_type == "lesson":
            purchase_data["lesson_id"] = item_id
        else:
            purchase_data["course_id"] = item_id
        
        purchase = Purchase(**purchase_data)
        self.db.add(purchase)
        self.db.commit()
        self.db.refresh(purchase)
        
        return PaymentResponse(
            payment_id=payment_id,
            amount=base_price,
            final_amount=final_price,
            discount_applied=discount_applied,
            invoice_payload=invoice_payload
        )
    
    def verify_payment(
        self, 
        payment_id: str, 
        telegram_payment_data: Dict[str, Any]
    ) -> bool:
        """
        Верификация платежа от Telegram.
        
        Args:
            payment_id: ID платежа
            telegram_payment_data: Данные от Telegram
            
        Returns:
            bool: Результат верификации
        """
        try:
            # Поиск покупки
            purchase = self.db.query(Purchase).filter(
                Purchase.payment_id == payment_id
            ).first()
            
            if not purchase:
                return False
            
            if purchase.status != PurchaseStatus.PENDING.value:
                return False
            
            # Проверка суммы
            telegram_amount = telegram_payment_data.get("total_amount", 0)
            if telegram_amount != purchase.amount:
                return False
            
            # Проверка валюты
            telegram_currency = telegram_payment_data.get("currency", "")
            if telegram_currency != TELEGRAM_STARS_CURRENCY:
                return False
            
            # Проверка payload
            invoice_payload = telegram_payment_data.get("invoice_payload", "")
            expected_payload = self._create_invoice_payload(
                purchase.user_id,
                purchase.lesson_id or purchase.course_id,
                "lesson" if purchase.lesson_id else "course",
                payment_id
            )
            
            if invoice_payload != expected_payload:
                return False
            
            return True
            
        except Exception:
            return False
    
    def process_successful_payment(self, purchase_id: int) -> bool:
        """
        Обработка успешного платежа.
        
        Args:
            purchase_id: ID покупки
            
        Returns:
            bool: Результат обработки
        """
        try:
            purchase = self.db.query(Purchase).filter(
                Purchase.id == purchase_id
            ).first()
            
            if not purchase:
                return False
            
            # Обновление статуса
            purchase.status = PurchaseStatus.COMPLETED.value
            purchase.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # Дополнительная логика (уведомления, аналитика и т.д.)
            self._post_payment_processing(purchase)
            
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    def handle_failed_payment(self, purchase_id: int, error: str) -> bool:
        """
        Обработка неудачного платежа.
        
        Args:
            purchase_id: ID покупки
            error: Описание ошибки
            
        Returns:
            bool: Результат обработки
        """
        try:
            purchase = self.db.query(Purchase).filter(
                Purchase.id == purchase_id
            ).first()
            
            if not purchase:
                return False
            
            purchase.status = PurchaseStatus.FAILED.value
            purchase.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    def get_user_purchases(self, user_id: int) -> List[Purchase]:
        """
        Получение покупок пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[Purchase]: Список покупок
        """
        return self.db.query(Purchase).filter(
            and_(
                Purchase.user_id == user_id,
                Purchase.status == PurchaseStatus.COMPLETED.value
            )
        ).order_by(Purchase.created_at.desc()).all()
    
    def get_payment_status(self, payment_id: str) -> Optional[str]:
        """
        Получение статуса платежа.
        
        Args:
            payment_id: ID платежа
            
        Returns:
            Optional[str]: Статус платежа
        """
        purchase = self.db.query(Purchase).filter(
            Purchase.payment_id == payment_id
        ).first()
        
        return purchase.status if purchase else None
    
    def cancel_expired_payments(self) -> int:
        """
        Отмена просроченных платежей.
        
        Returns:
            int: Количество отмененных платежей
        """
        expiry_time = datetime.utcnow() - timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)
        
        expired_purchases = self.db.query(Purchase).filter(
            and_(
                Purchase.status == PurchaseStatus.PENDING.value,
                Purchase.created_at < expiry_time
            )
        ).all()
        
        for purchase in expired_purchases:
            purchase.status = PurchaseStatus.FAILED.value
            purchase.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return len(expired_purchases)
    
    def _get_item_and_price(self, item_id: int, item_type: str) -> tuple:
        """Получение товара и его цены."""
        if item_type == "lesson":
            item = self.db.query(Lesson).filter(Lesson.id == item_id).first()
            price = item.price if item else 0
        elif item_type == "course":
            item = self.db.query(Course).filter(Course.id == item_id).first()
            price = item.discount_price or item.total_price if item else 0
        else:
            raise ValueError("Неподдерживаемый тип товара")
        
        return item, price
    
    def _check_existing_purchase(
        self, 
        user_id: int, 
        item_id: int, 
        item_type: str
    ) -> bool:
        """Проверка существующей покупки."""
        query = self.db.query(Purchase).filter(
            and_(
                Purchase.user_id == user_id,
                Purchase.status == PurchaseStatus.COMPLETED.value
            )
        )
        
        if item_type == "lesson":
            query = query.filter(Purchase.lesson_id == item_id)
        else:
            query = query.filter(Purchase.course_id == item_id)
        
        return query.first() is not None
    
    def _apply_promo_code(
        self, 
        code: str, 
        base_price: int, 
        user_id: int
    ) -> tuple[int, int]:
        """
        Применение промокода.
        
        Returns:
            tuple: (размер скидки, финальная цена)
        """
        promo = self.db.query(PromoCode).filter(
            PromoCode.code == code.upper()
        ).first()
        
        if not promo or not promo.is_valid:
            raise ValueError("Промокод недействителен")
        
        # Проверка лимитов использования
        if promo.max_uses and promo.current_uses >= promo.max_uses:
            raise ValueError("Промокод исчерпан")
        
        # Расчет скидки
        if promo.discount_amount:
            discount = min(promo.discount_amount, base_price)
        else:
            discount = (base_price * promo.discount_percent) // 100
        
        final_price = max(MIN_PRICE, base_price - discount)
        
        # Увеличение счетчика использований
        promo.current_uses += 1
        self.db.commit()
        
        return discount, final_price
    
    def _generate_payment_id(self) -> str:
        """Генерация уникального ID платежа."""
        return f"pay_{uuid.uuid4().hex[:16]}"
    
    def _create_invoice_payload(
        self, 
        user_id: int, 
        item_id: int, 
        item_type: str, 
        payment_id: str
    ) -> str:
        """Создание payload для инвойса."""
        payload_data = {
            "user_id": user_id,
            "item_id": item_id,
            "item_type": item_type,
            "payment_id": payment_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(payload_data, ensure_ascii=False)
    
    def _post_payment_processing(self, purchase: Purchase) -> None:
        """Дополнительная обработка после успешного платежа."""
        # Здесь можно добавить:
        # - Отправку уведомлений
        # - Обновление аналитики
        # - Интеграцию с внешними системами
        pass