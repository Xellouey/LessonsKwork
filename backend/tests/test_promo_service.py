"""
Тесты для сервиса промокодов.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from backend.services.promo_service import PromoCodeService
from shared.models import PromoCode
from shared.schemas import PromoCodeCreate, PromoCodeUpdate


class TestPromoCodeService:
    """Тесты для PromoCodeService."""
    
    @pytest.fixture
    def db_session(self):
        """Мок сессии базы данных."""
        return MagicMock(spec=Session)
    
    @pytest.fixture
    def promo_service(self, db_session):
        """Экземпляр PromoCodeService для тестов."""
        return PromoCodeService(db_session)
    
    @pytest.fixture
    def sample_promo_code(self):
        """Тестовый промокод."""
        return PromoCode(
            id=1,
            code="TEST10",
            discount_percent=10,
            is_active=True,
            current_uses=0,
            max_uses=100,
            created_at=datetime.utcnow()
        )
    
    def test_create_promo_code_success(self, promo_service, db_session):
        """Тест успешного создания промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = None  # Промокод не существует
        
        # Выполнение
        result = promo_service.create_promo_code(
            code="TEST10",
            discount_percent=10,
            max_uses=100
        )
        
        # Проверки
        assert result.code == "TEST10"
        assert result.discount_percent == 10
        assert result.max_uses == 100
        assert result.is_active is True
        
        # Проверка сохранения в БД
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once()
    
    def test_create_promo_code_duplicate(self, promo_service, db_session, sample_promo_code):
        """Тест создания дублирующегося промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Промокод с таким кодом уже существует"):
            promo_service.create_promo_code(
                code="TEST10",
                discount_percent=10
            )
    
    def test_create_promo_code_invalid_code(self, promo_service, db_session):
        """Тест создания промокода с некорректным кодом."""
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Код промокода должен содержать минимум 3 символа"):
            promo_service.create_promo_code(
                code="AB",
                discount_percent=10
            )
    
    def test_create_promo_code_invalid_discount(self, promo_service, db_session):
        """Тест создания промокода с некорректной скидкой."""
        # Настройка моков
        db_session.query().filter().first.return_value = None
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Процент скидки должен быть от 0 до"):
            promo_service.create_promo_code(
                code="TEST101",
                discount_percent=101
            )
    
    def test_create_promo_code_no_discount(self, promo_service, db_session):
        """Тест создания промокода без скидки."""
        # Настройка моков
        db_session.query().filter().first.return_value = None
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Должен быть указан либо процент, либо фиксированная скидка"):
            promo_service.create_promo_code(
                code="TEST",
                discount_percent=0
            )
    
    def test_validate_promo_code_success(self, promo_service, db_session, sample_promo_code):
        """Тест успешной валидации промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Выполнение
        result = promo_service.validate_promo_code("TEST10")
        
        # Проверки
        assert result == sample_promo_code
    
    def test_validate_promo_code_not_found(self, promo_service, db_session):
        """Тест валидации несуществующего промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = None
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Промокод не найден"):
            promo_service.validate_promo_code("NOTFOUND")
    
    def test_validate_promo_code_inactive(self, promo_service, db_session, sample_promo_code):
        """Тест валидации неактивного промокода."""
        # Неактивный промокод
        sample_promo_code.is_active = False
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Промокод деактивирован"):
            promo_service.validate_promo_code("TEST10")
    
    def test_validate_promo_code_expired(self, promo_service, db_session, sample_promo_code):
        """Тест валидации истекшего промокода."""
        # Истекший промокод
        sample_promo_code.expires_at = datetime.utcnow() - timedelta(days=1)
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Промокод истек"):
            promo_service.validate_promo_code("TEST10")
    
    def test_validate_promo_code_exhausted(self, promo_service, db_session, sample_promo_code):
        """Тест валидации исчерпанного промокода."""
        # Исчерпанный промокод
        sample_promo_code.current_uses = 100
        sample_promo_code.max_uses = 100
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Промокод исчерпан"):
            promo_service.validate_promo_code("TEST10")
    
    def test_apply_discount_percent(self, promo_service, sample_promo_code):
        """Тест применения процентной скидки."""
        # Выполнение
        result = promo_service.apply_discount(sample_promo_code, 100)
        
        # Проверки
        assert result["original_amount"] == 100
        assert result["discount_amount"] == 10  # 10% от 100
        assert result["final_amount"] == 90
        assert result["discount_percent"] == 10
    
    def test_apply_discount_fixed_amount(self, promo_service):
        """Тест применения фиксированной скидки."""
        # Промокод с фиксированной скидкой
        promo_code = PromoCode(
            code="FIXED20",
            discount_percent=0,
            discount_amount=20,
            is_active=True
        )
        
        # Выполнение
        result = promo_service.apply_discount(promo_code, 100)
        
        # Проверки
        assert result["original_amount"] == 100
        assert result["discount_amount"] == 20
        assert result["final_amount"] == 80
        assert result["discount_percent"] == 20
    
    def test_apply_discount_min_price_limit(self, promo_service):
        """Тест ограничения минимальной цены при применении скидки."""
        # Промокод с большой скидкой
        promo_code = PromoCode(
            code="BIG90",
            discount_percent=90,
            is_active=True
        )
        
        # Выполнение с маленькой суммой
        result = promo_service.apply_discount(promo_code, 10)
        
        # Проверки - финальная сумма не должна быть меньше MIN_PRICE (1)
        assert result["final_amount"] >= 1
    
    def test_use_promo_code_success(self, promo_service, db_session, sample_promo_code):
        """Тест успешного использования промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Выполнение
        result = promo_service.use_promo_code("TEST10", 1)
        
        # Проверки
        assert result is True
        assert sample_promo_code.current_uses == 1
        db_session.commit.assert_called_once()
    
    def test_use_promo_code_failure(self, promo_service, db_session):
        """Тест неудачного использования промокода."""
        # Настройка моков - промокод не найден
        db_session.query().filter().first.return_value = None
        
        # Выполнение
        result = promo_service.use_promo_code("NOTFOUND", 1)
        
        # Проверки
        assert result is False
    
    def test_use_promo_code_deactivates_when_exhausted(self, promo_service, db_session, sample_promo_code):
        """Тест деактивации промокода при исчерпании."""
        # Промокод с одним оставшимся использованием
        sample_promo_code.current_uses = 99
        sample_promo_code.max_uses = 100
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Выполнение
        result = promo_service.use_promo_code("TEST10", 1)
        
        # Проверки
        assert result is True
        assert sample_promo_code.current_uses == 100
        assert sample_promo_code.is_active is False
    
    def test_get_active_promocodes(self, promo_service, db_session):
        """Тест получения активных промокодов."""
        # Тестовые промокоды
        active_promos = [
            PromoCode(id=1, code="ACTIVE1", is_active=True),
            PromoCode(id=2, code="ACTIVE2", is_active=True)
        ]
        
        db_session.query().filter().filter().order_by().all.return_value = active_promos
        
        # Выполнение
        result = promo_service.get_active_promocodes()
        
        # Проверки
        assert len(result) == 2
        assert all(promo.is_active for promo in result)
    
    def test_get_active_promocodes_with_limit(self, promo_service, db_session):
        """Тест получения активных промокодов с лимитом."""
        # Настройка мока с лимитом
        mock_query = db_session.query().filter().filter().order_by()
        mock_query.limit.return_value.all.return_value = []
        
        # Выполнение
        promo_service.get_active_promocodes(limit=5)
        
        # Проверка вызова лимита
        mock_query.limit.assert_called_once_with(5)
    
    def test_update_promo_code_success(self, promo_service, db_session, sample_promo_code):
        """Тест успешного обновления промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Данные для обновления
        update_data = PromoCodeUpdate(
            discount_percent=15,
            is_active=False
        )
        
        # Выполнение
        result = promo_service.update_promo_code(1, update_data)
        
        # Проверки
        assert result == sample_promo_code
        assert sample_promo_code.discount_percent == 15
        assert sample_promo_code.is_active is False
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once()
    
    def test_update_promo_code_not_found(self, promo_service, db_session):
        """Тест обновления несуществующего промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = None
        
        # Выполнение
        result = promo_service.update_promo_code(999, PromoCodeUpdate())
        
        # Проверки
        assert result is None
    
    def test_delete_promo_code_success(self, promo_service, db_session, sample_promo_code):
        """Тест успешного удаления промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Выполнение
        result = promo_service.delete_promo_code(1)
        
        # Проверки
        assert result is True
        assert sample_promo_code.is_active is False
        db_session.commit.assert_called_once()
    
    def test_delete_promo_code_not_found(self, promo_service, db_session):
        """Тест удаления несуществующего промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = None
        
        # Выполнение
        result = promo_service.delete_promo_code(999)
        
        # Проверки
        assert result is False
    
    def test_get_promo_code_stats(self, promo_service, db_session, sample_promo_code):
        """Тест получения статистики промокода."""
        # Настройка моков
        db_session.query().filter().first.return_value = sample_promo_code
        
        # Выполнение
        result = promo_service.get_promo_code_stats(1)
        
        # Проверки
        assert result is not None
        assert result["promo_code"] == "TEST10"
        assert result["total_uses"] == 0
        assert result["max_uses"] == 100
        assert result["remaining_uses"] == 100
        assert result["is_active"] is True
        assert result["is_expired"] is False
    
    def test_cleanup_expired_promocodes(self, promo_service, db_session):
        """Тест очистки истекших промокодов."""
        # Истекшие промокоды
        expired_promos = [
            PromoCode(id=1, code="EXPIRED1", is_active=True, expires_at=datetime.utcnow() - timedelta(days=1)),
            PromoCode(id=2, code="EXPIRED2", is_active=True, expires_at=datetime.utcnow() - timedelta(days=2))
        ]
        
        db_session.query().filter().all.return_value = expired_promos
        
        # Выполнение
        result = promo_service.cleanup_expired_promocodes()
        
        # Проверки
        assert result == 2
        assert all(not promo.is_active for promo in expired_promos)
        db_session.commit.assert_called_once()
    
    def test_generate_promo_code(self, promo_service, db_session):
        """Тест генерации уникального промокода."""
        # Настройка моков - первая попытка находит существующий код
        db_session.query().filter().first.side_effect = [
            PromoCode(code="PROMO12345678"),  # Существующий код
            None  # Уникальный код
        ]
        
        # Выполнение
        result = promo_service.generate_promo_code("PROMO", 8)
        
        # Проверки
        assert result.startswith("PROMO")
        assert len(result) == 13  # PROMO + 8 символов
    
    def test_bulk_create_promocodes(self, promo_service, db_session):
        """Тест массового создания промокодов."""
        # Настройка моков - все коды уникальны
        db_session.query().filter().first.return_value = None
        
        # Выполнение
        result = promo_service.bulk_create_promocodes(
            count=5,
            discount_percent=10,
            prefix="BULK"
        )
        
        # Проверки
        assert len(result) == 5
        assert all(promo.discount_percent == 10 for promo in result)
        assert all(promo.code.startswith("BULK") for promo in result)
        assert db_session.add.call_count == 5
        db_session.commit.assert_called_once()
    
    def test_bulk_create_promocodes_limit(self, promo_service, db_session):
        """Тест ограничения массового создания промокодов."""
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Нельзя создать более 1000 промокодов за раз"):
            promo_service.bulk_create_promocodes(
                count=1001,
                discount_percent=10
            )