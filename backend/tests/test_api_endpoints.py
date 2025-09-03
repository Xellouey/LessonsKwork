"""
Тесты для API endpoints платежной системы.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, date

from backend.main import app
from shared.models import Purchase, PromoCode, User, Lesson


class TestPaymentAPI:
    """Тесты для API платежей."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    @pytest.fixture
    def admin_token(self):
        """Мок JWT токена администратора."""
        return "test_admin_token"
    
    @pytest.fixture
    def auth_headers(self, admin_token):
        """Заголовки с авторизацией."""
        return {"Authorization": f"Bearer {admin_token}"}
    
    @patch('backend.api.payments.PaymentService')
    def test_create_payment_success(self, mock_payment_service, client):
        """Тест успешного создания платежа."""
        # Настройка мока
        mock_service_instance = mock_payment_service.return_value
        mock_service_instance.create_payment.return_value = MagicMock(
            payment_id="pay_test123",
            amount=100,
            final_amount=90,
            discount_applied=10,
            invoice_payload='{"test": "data"}'
        )
        
        # Данные запроса
        payment_data = {
            "user_id": 1,
            "item_id": 1,
            "item_type": "lesson",
            "promo_code": "TEST10"
        }
        
        # Выполнение запроса
        response = client.post("/api/v1/payments/create", json=payment_data)
        
        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["payment_id"] == "pay_test123"
        assert data["amount"] == 100
        assert data["final_amount"] == 90
        assert data["discount_applied"] == 10
    
    @patch('backend.api.payments.PaymentService')
    def test_create_payment_validation_error(self, mock_payment_service, client):
        """Тест создания платежа с ошибкой валидации."""
        # Настройка мока для генерации ошибки
        mock_service_instance = mock_payment_service.return_value
        mock_service_instance.create_payment.side_effect = ValueError("Пользователь не найден")
        
        # Данные запроса
        payment_data = {
            "user_id": 999,
            "item_id": 1,
            "item_type": "lesson"
        }
        
        # Выполнение запроса
        response = client.post("/api/v1/payments/create", json=payment_data)
        
        # Проверки
        assert response.status_code == 400
        assert "Пользователь не найден" in response.json()["detail"]
    
    @patch('backend.api.payments.PaymentService')
    def test_get_payment_status_success(self, mock_payment_service, client):
        """Тест получения статуса платежа."""
        # Настройка мока
        mock_service_instance = mock_payment_service.return_value
        mock_service_instance.get_payment_status.return_value = "completed"
        
        # Выполнение запроса
        response = client.get("/api/v1/payments/pay_test123")
        
        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["payment_id"] == "pay_test123"
        assert data["status"] == "completed"
        assert "timestamp" in data
    
    @patch('backend.api.payments.PaymentService')
    def test_get_payment_status_not_found(self, mock_payment_service, client):
        """Тест получения статуса несуществующего платежа."""
        # Настройка мока
        mock_service_instance = mock_payment_service.return_value
        mock_service_instance.get_payment_status.return_value = None
        
        # Выполнение запроса
        response = client.get("/api/v1/payments/pay_notfound")
        
        # Проверки
        assert response.status_code == 404
        assert "Платеж не найден" in response.json()["detail"]
    
    def test_payment_webhook_successful_payment(self, client):
        """Тест webhook для успешного платежа."""
        # Данные webhook
        webhook_data = {
            "update_type": "successful_payment",
            "message": {
                "successful_payment": {
                    "invoice_payload": '{"payment_id": "pay_test123", "user_id": 1}',
                    "telegram_payment_charge_id": "tg_charge_123"
                }
            }
        }
        
        # Выполнение запроса
        response = client.post("/api/v1/payments/webhook", json=webhook_data)
        
        # Проверки
        assert response.status_code == 200
        assert response.json()["ok"] is True
    
    def test_payment_webhook_pre_checkout(self, client):
        """Тест webhook для pre-checkout запроса."""
        # Данные webhook
        webhook_data = {
            "update_type": "pre_checkout_query",
            "pre_checkout_query": {
                "invoice_payload": '{"payment_id": "pay_test123"}'
            }
        }
        
        with patch('backend.api.payments._validate_pre_checkout') as mock_validate:
            mock_validate.return_value = True
            
            # Выполнение запроса
            response = client.post("/api/v1/payments/webhook", json=webhook_data)
            
            # Проверки
            assert response.status_code == 200
            assert response.json()["ok"] is True


class TestPromoCodeAPI:
    """Тесты для API промокодов."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Заголовки с авторизацией."""
        return {"Authorization": "Bearer test_token"}
    
    @patch('backend.api.promocodes.get_current_active_admin')
    @patch('backend.api.promocodes.PromoCodeService')
    def test_create_promo_code_success(self, mock_promo_service, mock_auth, client, auth_headers):
        """Тест успешного создания промокода."""
        # Настройка моков
        mock_auth.return_value = MagicMock(username="admin")
        mock_service_instance = mock_promo_service.return_value
        mock_service_instance.create_promo_code.return_value = MagicMock(
            id=1,
            code="TEST10",
            discount_percent=10,
            discount_amount=None,
            max_uses=100,
            current_uses=0,
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=None
        )
        
        # Данные запроса
        promo_data = {
            "code": "TEST10",
            "discount_percent": 10,
            "max_uses": 100
        }
        
        # Выполнение запроса
        response = client.post("/api/v1/promocodes/", json=promo_data, headers=auth_headers)
        
        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "TEST10"
        assert data["discount_percent"] == 10
        assert data["is_active"] is True
    
    @patch('backend.api.promocodes.PromoCodeService')
    def test_validate_promo_code_success(self, mock_promo_service, client):
        """Тест успешной валидации промокода."""
        # Настройка мока
        mock_service_instance = mock_promo_service.return_value
        mock_promo_code = MagicMock(
            code="TEST10",
            discount_percent=10,
            discount_amount=None,
            expires_at=None,
            max_uses=100,
            current_uses=50
        )
        mock_service_instance.validate_promo_code.return_value = mock_promo_code
        mock_service_instance.apply_discount.return_value = {
            "original_amount": 100,
            "discount_amount": 10,
            "final_amount": 90
        }
        
        # Мок для поиска урока
        with patch('backend.api.promocodes.db') as mock_db:
            mock_lesson = MagicMock(price=100)
            mock_db.query().filter().first.return_value = mock_lesson
            
            # Данные запроса
            validation_data = {
                "code": "TEST10",
                "item_type": "lesson",
                "item_id": 1
            }
            
            # Выполнение запроса
            response = client.post("/api/v1/promocodes/validate", json=validation_data)
            
            # Проверки
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["promo_code"] == "TEST10"
            assert data["original_price"] == 100
            assert data["final_price"] == 90
    
    @patch('backend.api.promocodes.PromoCodeService')
    def test_validate_promo_code_invalid(self, mock_promo_service, client):
        """Тест валидации недействительного промокода."""
        # Настройка мока для генерации ошибки
        mock_service_instance = mock_promo_service.return_value
        mock_service_instance.validate_promo_code.side_effect = ValueError("Промокод не найден")
        
        # Данные запроса
        validation_data = {
            "code": "INVALID",
            "item_type": "lesson",
            "item_id": 1
        }
        
        # Выполнение запроса
        response = client.post("/api/v1/promocodes/validate", json=validation_data)
        
        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "Промокод не найден" in data["error"]
    
    def test_public_check_promo_code_valid(self, client):
        """Тест публичной проверки валидного промокода."""
        with patch('backend.api.promocodes.PromoCodeService') as mock_promo_service:
            # Настройка мока
            mock_service_instance = mock_promo_service.return_value
            mock_promo_code = MagicMock(
                discount_percent=10,
                discount_amount=None,
                expires_at=None
            )
            mock_service_instance.validate_promo_code.return_value = mock_promo_code
            
            # Выполнение запроса
            response = client.get("/api/v1/promocodes/public/check/TEST10")
            
            # Проверки
            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is True
            assert data["valid"] is True
            assert data["discount_percent"] == 10
    
    def test_public_check_promo_code_invalid(self, client):
        """Тест публичной проверки недействительного промокода."""
        with patch('backend.api.promocodes.PromoCodeService') as mock_promo_service:
            # Настройка мока для генерации ошибки
            mock_service_instance = mock_promo_service.return_value
            mock_service_instance.validate_promo_code.side_effect = ValueError("Промокод не найден")
            
            # Выполнение запроса
            response = client.get("/api/v1/promocodes/public/check/INVALID")
            
            # Проверки
            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is True
            assert data["valid"] is False
            assert "Промокод не найден" in data["error"]


class TestFinanceAPI:
    """Тесты для API финансов."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Заголовки с авторизацией."""
        return {"Authorization": "Bearer test_token"}
    
    @patch('backend.api.finance.get_current_active_admin')
    @patch('backend.api.finance.FinanceService')
    def test_get_daily_revenue(self, mock_finance_service, mock_auth, client, auth_headers):
        """Тест получения дневной статистики."""
        # Настройка моков
        mock_auth.return_value = MagicMock(username="admin")
        mock_service_instance = mock_finance_service.return_value
        mock_service_instance.get_daily_revenue.return_value = MagicMock(
            date="2024-01-01",
            total_revenue=1000,
            total_purchases=10,
            completed_purchases=8,
            failed_purchases=2,
            average_purchase=125.0,
            top_lessons=[]
        )
        
        # Выполнение запроса
        response = client.get("/api/v1/finance/daily/2024-01-01", headers=auth_headers)
        
        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2024-01-01"
        assert data["total_revenue"] == 1000
        assert data["total_purchases"] == 10
    
    @patch('backend.api.finance.get_current_active_admin')
    @patch('backend.api.finance.FinanceService')
    def test_get_monthly_stats(self, mock_finance_service, mock_auth, client, auth_headers):
        """Тест получения месячной статистики."""
        # Настройка моков
        mock_auth.return_value = MagicMock(username="admin")
        mock_service_instance = mock_finance_service.return_value
        mock_service_instance.get_monthly_stats.return_value = MagicMock(
            year=2024,
            month=1,
            total_revenue=30000,
            total_purchases=300,
            daily_breakdown=[],
            growth_rate=15.5
        )
        
        # Выполнение запроса
        response = client.get("/api/v1/finance/monthly/2024/1", headers=auth_headers)
        
        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2024
        assert data["month"] == 1
        assert data["total_revenue"] == 30000
        assert data["growth_rate"] == 15.5
    
    @patch('backend.api.finance.get_current_active_admin')
    @patch('backend.api.finance.FinanceService')
    def test_get_top_selling_lessons(self, mock_finance_service, mock_auth, client, auth_headers):
        """Тест получения топа продаваемых уроков."""
        # Настройка моков
        mock_auth.return_value = MagicMock(username="admin")
        mock_service_instance = mock_finance_service.return_value
        mock_service_instance.get_top_selling_lessons.return_value = [
            MagicMock(
                item_id=1,
                item_type="lesson",
                title="Top Lesson",
                sales_count=50,
                total_revenue=5000,
                price=100
            )
        ]
        
        # Выполнение запроса
        response = client.get("/api/v1/finance/top-lessons?limit=10&days=30", headers=auth_headers)
        
        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["item_id"] == 1
        assert data[0]["title"] == "Top Lesson"
        assert data[0]["sales_count"] == 50
    
    def test_monthly_stats_invalid_month(self, client, auth_headers):
        """Тест месячной статистики с некорректным месяцем."""
        with patch('backend.api.finance.get_current_active_admin'):
            # Выполнение запроса
            response = client.get("/api/v1/finance/monthly/2024/13", headers=auth_headers)
            
            # Проверки
            assert response.status_code == 400
            assert "Месяц должен быть от 1 до 12" in response.json()["detail"]
    
    @patch('backend.api.finance.get_current_superuser')
    @patch('backend.api.finance.FinanceService')
    def test_get_withdrawable_amount(self, mock_finance_service, mock_auth, client, auth_headers):
        """Тест получения доступной суммы для вывода."""
        # Настройка моков
        mock_auth.return_value = MagicMock(username="superuser")
        mock_service_instance = mock_finance_service.return_value
        mock_service_instance.calculate_withdrawable_amount.return_value = MagicMock(
            total_revenue=100000,
            total_withdraws=20000,
            pending_withdraws=5000,
            available_amount=70000,
            commission_amount=5000
        )
        
        # Выполнение запроса
        response = client.get("/api/v1/finance/withdrawable", headers=auth_headers)
        
        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["total_revenue"] == 100000
        assert data["available_amount"] == 70000
        assert data["commission_amount"] == 5000