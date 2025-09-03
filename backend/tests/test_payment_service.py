"""
Тесты для сервиса платежей.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session

from backend.services.payment_service import PaymentService
from shared.models import User, Lesson, Course, Purchase, PromoCode
from shared.constants import PurchaseStatus, MIN_PRICE
from shared.schemas import PaymentCreateRequest


class TestPaymentService:
    """Тесты для PaymentService."""
    
    @pytest.fixture
    def db_session(self):
        """Мок сессии базы данных."""
        return MagicMock(spec=Session)
    
    @pytest.fixture
    def payment_service(self, db_session):
        """Экземпляр PaymentService для тестов."""
        return PaymentService(db_session)
    
    @pytest.fixture
    def sample_user(self):
        """Тестовый пользователь."""
        return User(
            id=1,
            telegram_id=123456789,
            first_name="Test User",
            is_active=True
        )
    
    @pytest.fixture
    def sample_lesson(self):
        """Тестовый урок."""
        return Lesson(
            id=1,
            title="Test Lesson",
            description="Test Description",
            price=100,
            is_active=True
        )
    
    @pytest.fixture
    def sample_course(self):
        """Тестовый курс."""
        return Course(
            id=1,
            title="Test Course",
            description="Test Description",
            total_price=500,
            discount_price=400,
            is_active=True
        )
    
    @pytest.fixture
    def sample_promo_code(self):
        """Тестовый промокод."""
        return PromoCode(
            id=1,
            code="TEST10",
            discount_percent=10,
            is_active=True,
            current_uses=0,
            max_uses=100
        )
    
    def test_create_payment_success_lesson(self, payment_service, db_session, sample_user, sample_lesson):
        """Тест успешного создания платежа за урок."""
        # Настройка моков
        db_session.query().filter().first.side_effect = [
            sample_user,  # Поиск пользователя
            sample_lesson,  # Поиск урока
            None  # Проверка существующей покупки
        ]
        
        # Выполнение
        result = payment_service.create_payment(
            user_id=1,
            item_id=1,
            item_type="lesson"
        )
        
        # Проверки
        assert result.amount == 100
        assert result.final_amount == 100
        assert result.discount_applied == 0
        assert result.payment_id.startswith("pay_")
        
        # Проверка сохранения в БД
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
    
    def test_create_payment_success_course(self, payment_service, db_session, sample_user, sample_course):
        """Тест успешного создания платежа за курс."""
        # Настройка моков
        db_session.query().filter().first.side_effect = [
            sample_user,  # Поиск пользователя
            sample_course,  # Поиск курса
            None  # Проверка существующей покупки
        ]
        
        # Выполнение
        result = payment_service.create_payment(
            user_id=1,
            item_id=1,
            item_type="course"
        )
        
        # Проверки
        assert result.amount == 500
        assert result.final_amount == 400  # Цена со скидкой
        assert result.discount_applied == 0
    
    def test_create_payment_with_promo_code(self, payment_service, db_session, sample_user, sample_lesson, sample_promo_code):
        """Тест создания платежа с промокодом."""
        # Настройка моков
        db_session.query().filter().first.side_effect = [
            sample_user,  # Поиск пользователя
            sample_lesson,  # Поиск урока
            None,  # Проверка существующей покупки
            sample_promo_code  # Поиск промокода
        ]
        
        # Выполнение
        result = payment_service.create_payment(
            user_id=1,
            item_id=1,
            item_type="lesson",
            promo_code="TEST10"
        )
        
        # Проверки
        assert result.amount == 100
        assert result.final_amount == 90  # 100 - 10%
        assert result.discount_applied == 10
    
    def test_create_payment_user_not_found(self, payment_service, db_session):
        """Тест создания платежа с несуществующим пользователем."""
        # Настройка моков
        db_session.query().filter().first.return_value = None
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Пользователь не найден"):
            payment_service.create_payment(
                user_id=999,
                item_id=1,
                item_type="lesson"
            )
    
    def test_create_payment_user_inactive(self, payment_service, db_session, sample_user):
        """Тест создания платежа с неактивным пользователем."""
        # Неактивный пользователь
        sample_user.is_active = False
        db_session.query().filter().first.return_value = sample_user
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Пользователь неактивен"):
            payment_service.create_payment(
                user_id=1,
                item_id=1,
                item_type="lesson"
            )
    
    def test_create_payment_lesson_not_found(self, payment_service, db_session, sample_user):
        """Тест создания платежа с несуществующим уроком."""
        # Настройка моков
        db_session.query().filter().first.side_effect = [
            sample_user,  # Поиск пользователя
            None  # Урок не найден
        ]
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Lesson не найден"):
            payment_service.create_payment(
                user_id=1,
                item_id=999,
                item_type="lesson"
            )
    
    def test_create_payment_already_purchased(self, payment_service, db_session, sample_user, sample_lesson):
        """Тест создания платежа за уже купленный товар."""
        # Существующая покупка
        existing_purchase = Purchase(
            id=1,
            user_id=1,
            lesson_id=1,
            status=PurchaseStatus.COMPLETED.value
        )
        
        # Настройка моков
        db_session.query().filter().first.side_effect = [
            sample_user,  # Поиск пользователя
            sample_lesson,  # Поиск урока
            existing_purchase  # Существующая покупка
        ]
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Товар уже приобретен"):
            payment_service.create_payment(
                user_id=1,
                item_id=1,
                item_type="lesson"
            )
    
    def test_verify_payment_success(self, payment_service, db_session):
        """Тест успешной верификации платежа."""
        # Тестовая покупка
        purchase = Purchase(
            id=1,
            payment_id="pay_test123",
            amount=100,
            status=PurchaseStatus.PENDING.value,
            user_id=1,
            lesson_id=1
        )
        
        db_session.query().filter().first.return_value = purchase
        
        # Данные от Telegram
        telegram_data = {
            "total_amount": 100,
            "currency": "XTR",
            "invoice_payload": '{"user_id": 1, "item_id": 1, "item_type": "lesson", "payment_id": "pay_test123", "timestamp": "2024-01-01T00:00:00"}'
        }
        
        # Выполнение
        result = payment_service.verify_payment("pay_test123", telegram_data)
        
        # Проверка
        assert result is True
    
    def test_verify_payment_wrong_amount(self, payment_service, db_session):
        """Тест верификации платежа с неверной суммой."""
        # Тестовая покупка
        purchase = Purchase(
            id=1,
            payment_id="pay_test123",
            amount=100,
            status=PurchaseStatus.PENDING.value,
            user_id=1,
            lesson_id=1
        )
        
        db_session.query().filter().first.return_value = purchase
        
        # Данные от Telegram с неверной суммой
        telegram_data = {
            "total_amount": 200,  # Неверная сумма
            "currency": "XTR",
            "invoice_payload": '{"user_id": 1, "item_id": 1, "item_type": "lesson", "payment_id": "pay_test123", "timestamp": "2024-01-01T00:00:00"}'
        }
        
        # Выполнение
        result = payment_service.verify_payment("pay_test123", telegram_data)
        
        # Проверка
        assert result is False
    
    def test_process_successful_payment(self, payment_service, db_session):
        """Тест обработки успешного платежа."""
        # Тестовая покупка
        purchase = Purchase(
            id=1,
            payment_id="pay_test123",
            status=PurchaseStatus.PENDING.value
        )
        
        db_session.query().filter().first.return_value = purchase
        
        # Выполнение
        result = payment_service.process_successful_payment(1)
        
        # Проверки
        assert result is True
        assert purchase.status == PurchaseStatus.COMPLETED.value
        db_session.commit.assert_called_once()
    
    def test_handle_failed_payment(self, payment_service, db_session):
        """Тест обработки неудачного платежа."""
        # Тестовая покупка
        purchase = Purchase(
            id=1,
            payment_id="pay_test123",
            status=PurchaseStatus.PENDING.value
        )
        
        db_session.query().filter().first.return_value = purchase
        
        # Выполнение
        result = payment_service.handle_failed_payment(1, "Test error")
        
        # Проверки
        assert result is True
        assert purchase.status == PurchaseStatus.FAILED.value
        db_session.commit.assert_called_once()
    
    def test_get_user_purchases(self, payment_service, db_session):
        """Тест получения покупок пользователя."""
        # Тестовые покупки
        purchases = [
            Purchase(id=1, user_id=1, status=PurchaseStatus.COMPLETED.value),
            Purchase(id=2, user_id=1, status=PurchaseStatus.COMPLETED.value)
        ]
        
        db_session.query().filter().order_by().all.return_value = purchases
        
        # Выполнение
        result = payment_service.get_user_purchases(1)
        
        # Проверка
        assert len(result) == 2
        assert all(p.status == PurchaseStatus.COMPLETED.value for p in result)
    
    def test_cancel_expired_payments(self, payment_service, db_session):
        """Тест отмены просроченных платежей."""
        # Просроченные покупки
        expired_purchases = [
            Purchase(id=1, status=PurchaseStatus.PENDING.value),
            Purchase(id=2, status=PurchaseStatus.PENDING.value)
        ]
        
        db_session.query().filter().all.return_value = expired_purchases
        
        # Выполнение
        result = payment_service.cancel_expired_payments()
        
        # Проверки
        assert result == 2
        assert all(p.status == PurchaseStatus.FAILED.value for p in expired_purchases)
        db_session.commit.assert_called_once()
    
    def test_invalid_item_type(self, payment_service, db_session, sample_user):
        """Тест создания платежа с неверным типом товара."""
        db_session.query().filter().first.return_value = sample_user
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Неподдерживаемый тип товара"):
            payment_service.create_payment(
                user_id=1,
                item_id=1,
                item_type="invalid_type"
            )
    
    @patch('uuid.uuid4')
    def test_generate_payment_id(self, mock_uuid, payment_service):
        """Тест генерации ID платежа."""
        mock_uuid.return_value.hex = "1234567890abcdef1234567890abcdef"
        
        payment_id = payment_service._generate_payment_id()
        
        assert payment_id == "pay_1234567890abcdef"
    
    def test_create_invoice_payload(self, payment_service):
        """Тест создания payload для инвойса."""
        with patch('json.dumps') as mock_dumps:
            mock_dumps.return_value = '{"test": "data"}'
            
            result = payment_service._create_invoice_payload(1, 2, "lesson", "pay_123")
            
            assert result == '{"test": "data"}'
            mock_dumps.assert_called_once()


class TestPaymentServiceIntegration:
    """Интеграционные тесты для PaymentService."""
    
    def test_full_payment_flow(self):
        """Тест полного потока платежа."""
        # Этот тест требует настройки реальной БД
        # Здесь можно добавить интеграционные тесты с pytest-asyncio
        pass