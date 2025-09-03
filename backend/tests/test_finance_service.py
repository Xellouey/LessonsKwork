"""
Тесты для финансового сервиса.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from backend.services.finance_service import FinanceService
from shared.models import Purchase, Lesson, Course, User, WithdrawRequest
from shared.constants import PurchaseStatus


class TestFinanceService:
    """Тесты для FinanceService."""
    
    @pytest.fixture
    def db_session(self):
        """Мок сессии базы данных."""
        return MagicMock(spec=Session)
    
    @pytest.fixture
    def finance_service(self, db_session):
        """Экземпляр FinanceService для тестов."""
        return FinanceService(db_session)
    
    def test_get_daily_revenue(self, finance_service, db_session):
        """Тест получения дневной статистики доходов."""
        # Настройка мока для основной статистики
        mock_stats = MagicMock()
        mock_stats.total_purchases = 10
        mock_stats.total_revenue = 1000
        mock_stats.completed_purchases = 8
        mock_stats.failed_purchases = 2
        
        # Настройка мока для completed revenue
        db_session.query().filter().scalar.return_value = 800
        
        # Первый вызов query возвращает основную статистику
        db_session.query().filter().first.return_value = mock_stats
        
        # Мок для топ уроков
        with patch.object(finance_service, '_get_top_lessons_for_period') as mock_top_lessons:
            mock_top_lessons.return_value = [
                {"id": 1, "title": "Test Lesson", "sales_count": 5}
            ]
            
            # Выполнение
            target_date = date(2024, 1, 1)
            result = finance_service.get_daily_revenue(target_date)
            
            # Проверки
            assert result.date == "2024-01-01"
            assert result.total_revenue == 1000
            assert result.total_purchases == 10
            assert result.completed_purchases == 8
            assert result.failed_purchases == 2
            assert result.average_purchase == 100.0  # 800 / 8
            assert len(result.top_lessons) == 1
    
    def test_get_monthly_stats(self, finance_service, db_session):
        """Тест получения месячной статистики."""
        # Настройка мока для месячных итогов
        mock_monthly = MagicMock()
        mock_monthly.total_purchases = 100
        mock_monthly.total_revenue = 10000
        
        db_session.query().filter().first.return_value = mock_monthly
        
        # Мок для предыдущего месяца
        with patch.object(finance_service, '_get_month_revenue') as mock_prev_revenue:
            mock_prev_revenue.return_value = 8000
            
            # Мок для ежедневной разбивки
            with patch.object(finance_service, 'get_daily_revenue') as mock_daily:
                mock_daily.return_value = MagicMock(
                    date="2024-01-01",
                    total_revenue=300,
                    total_purchases=3
                )
                
                # Выполнение
                result = finance_service.get_monthly_stats(2024, 1)
                
                # Проверки
                assert result.year == 2024
                assert result.month == 1
                assert result.total_revenue == 10000
                assert result.total_purchases == 100
                assert result.growth_rate == 25.0  # ((10000 - 8000) / 8000) * 100
                assert len(result.daily_breakdown) == 31  # Январь имеет 31 день
    
    def test_get_top_selling_lessons(self, finance_service, db_session):
        """Тест получения топа продаваемых уроков."""
        # Мок результатов запроса
        mock_results = [
            MagicMock(id=1, title="Lesson 1", price=100, sales_count=10, total_revenue=1000),
            MagicMock(id=2, title="Lesson 2", price=200, sales_count=5, total_revenue=1000)
        ]
        
        db_session.query().join().filter().group_by().order_by().limit().all.return_value = mock_results
        
        # Выполнение
        result = finance_service.get_top_selling_lessons(limit=5, days=30)
        
        # Проверки
        assert len(result) == 2
        assert result[0].item_id == 1
        assert result[0].title == "Lesson 1"
        assert result[0].sales_count == 10
        assert result[0].total_revenue == 1000
        assert result[0].item_type == "lesson"
    
    def test_get_user_lifetime_value(self, finance_service, db_session):
        """Тест расчета пожизненной ценности пользователя."""
        # Настройка мока
        db_session.query().filter().scalar.return_value = 500
        
        # Выполнение
        result = finance_service.get_user_lifetime_value(1)
        
        # Проверки
        assert result == 500.0
    
    def test_get_user_lifetime_value_no_purchases(self, finance_service, db_session):
        """Тест расчета пожизненной ценности пользователя без покупок."""
        # Настройка мока
        db_session.query().filter().scalar.return_value = None
        
        # Выполнение
        result = finance_service.get_user_lifetime_value(1)
        
        # Проверки
        assert result == 0.0
    
    def test_calculate_withdrawable_amount(self, finance_service, db_session):
        """Тест расчета доступной суммы для вывода."""
        # Настройка моков для последовательных вызовов scalar
        db_session.query().filter().scalar.side_effect = [
            10000,  # total_revenue
            2000,   # total_withdraws
            500     # pending_withdraws
        ]
        
        # Выполнение
        result = finance_service.calculate_withdrawable_amount()
        
        # Проверки
        assert result.total_revenue == 10000
        assert result.total_withdraws == 2000
        assert result.pending_withdraws == 500
        assert result.commission_amount == 500  # 5% от 10000
        assert result.available_amount == 7000  # 10000 - 2000 - 500 - 500
    
    def test_export_financial_report_csv(self, finance_service, db_session):
        """Тест экспорта финансового отчета в CSV."""
        # Мок покупок
        mock_purchases = [
            MagicMock(
                id=1,
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                user_id=1,
                lesson_id=1,
                course_id=None,
                amount=100,
                status=PurchaseStatus.COMPLETED.value,
                payment_id="pay_123"
            )
        ]
        
        db_session.query().filter().order_by().all.return_value = mock_purchases
        
        # Выполнение
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        result = finance_service.export_financial_report(start_date, end_date, "csv")
        
        # Проверки
        assert isinstance(result, str)
        assert "ID покупки" in result  # Заголовок CSV
        assert "100" in result  # Сумма
        assert "Итого:" in result
    
    def test_export_financial_report_json(self, finance_service, db_session):
        """Тест экспорта финансового отчета в JSON."""
        # Мок покупок
        mock_purchases = [
            MagicMock(
                id=1,
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                user_id=1,
                lesson_id=1,
                course_id=None,
                amount=100,
                status=PurchaseStatus.COMPLETED.value,
                payment_id="pay_123"
            )
        ]
        
        db_session.query().filter().order_by().all.return_value = mock_purchases
        
        # Выполнение
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        result = finance_service.export_financial_report(start_date, end_date, "json")
        
        # Проверки
        assert isinstance(result, str)
        assert '"period"' in result
        assert '"total_purchases": 1' in result
        assert '"total_amount": 100' in result
    
    def test_export_financial_report_invalid_format(self, finance_service, db_session):
        """Тест экспорта отчета с неподдерживаемым форматом."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Выполнение и проверка
        with pytest.raises(ValueError, match="Неподдерживаемый формат экспорта"):
            finance_service.export_financial_report(start_date, end_date, "xml")
    
    def test_get_revenue_analytics(self, finance_service, db_session):
        """Тест получения аналитики доходов."""
        # Мок ежедневных доходов
        mock_daily_revenues = [
            MagicMock(date=date(2024, 1, 1), revenue=100, purchases_count=2),
            MagicMock(date=date(2024, 1, 2), revenue=200, purchases_count=3)
        ]
        
        db_session.query().filter().group_by().order_by().all.return_value = mock_daily_revenues
        
        # Моки для других методов
        with patch.object(finance_service, '_get_item_type_statistics') as mock_item_stats:
            mock_item_stats.return_value = {
                "lessons": {"count": 3, "revenue": 200},
                "courses": {"count": 2, "revenue": 100}
            }
            
            with patch.object(finance_service, '_get_top_users_by_revenue') as mock_top_users:
                mock_top_users.return_value = [
                    {"user_id": 1, "first_name": "John", "total_spent": 150}
                ]
                
                # Выполнение
                result = finance_service.get_revenue_analytics(period_days=30)
                
                # Проверки
                assert result["period_days"] == 30
                assert len(result["daily_revenues"]) == 2
                assert result["total_revenue"] == 300  # 100 + 200
                assert result["total_purchases"] == 5  # 2 + 3
                assert result["average_daily_revenue"] == 150.0  # 300 / 2
                assert "item_type_statistics" in result
                assert "top_users" in result
    
    def test_get_month_revenue(self, finance_service, db_session):
        """Тест получения дохода за месяц."""
        # Настройка мока
        db_session.query().filter().scalar.return_value = 5000
        
        # Выполнение
        result = finance_service._get_month_revenue(2024, 1)
        
        # Проверки
        assert result == 5000
    
    def test_get_month_revenue_december(self, finance_service, db_session):
        """Тест получения дохода за декабрь (переход года)."""
        # Настройка мока
        db_session.query().filter().scalar.return_value = 8000
        
        # Выполнение
        result = finance_service._get_month_revenue(2024, 12)
        
        # Проверки
        assert result == 8000
    
    def test_get_top_lessons_for_period(self, finance_service, db_session):
        """Тест получения топа уроков за период."""
        # Мок результатов
        mock_results = [
            MagicMock(id=1, title="Lesson 1", sales_count=10),
            MagicMock(id=2, title="Lesson 2", sales_count=8)
        ]
        
        db_session.query().join().filter().group_by().order_by().limit().all.return_value = mock_results
        
        # Выполнение
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        result = finance_service._get_top_lessons_for_period(start_date, end_date, limit=5)
        
        # Проверки
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["title"] == "Lesson 1"
        assert result[0]["sales_count"] == 10
    
    def test_get_item_type_statistics(self, finance_service, db_session):
        """Тест получения статистики по типам товаров."""
        # Настройка моков для последовательных вызовов
        mock_lesson_stats = MagicMock(count=5, revenue=500)
        mock_course_stats = MagicMock(count=3, revenue=900)
        
        db_session.query().filter().first.side_effect = [
            mock_lesson_stats,
            mock_course_stats
        ]
        
        # Выполнение
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        result = finance_service._get_item_type_statistics(start_date, end_date)
        
        # Проверки
        assert result["lessons"]["count"] == 5
        assert result["lessons"]["revenue"] == 500
        assert result["courses"]["count"] == 3
        assert result["courses"]["revenue"] == 900
    
    def test_get_top_users_by_revenue(self, finance_service, db_session):
        """Тест получения топа пользователей по доходам."""
        # Мок результатов
        mock_results = [
            MagicMock(
                id=1,
                first_name="John",
                username="john_doe",
                purchases_count=5,
                total_spent=500
            ),
            MagicMock(
                id=2,
                first_name="Jane",
                username="jane_doe",
                purchases_count=3,
                total_spent=300
            )
        ]
        
        db_session.query().join().filter().group_by().order_by().limit().all.return_value = mock_results
        
        # Выполнение
        result = finance_service._get_top_users_by_revenue(period_days=30, limit=10)
        
        # Проверки
        assert len(result) == 2
        assert result[0]["user_id"] == 1
        assert result[0]["first_name"] == "John"
        assert result[0]["username"] == "john_doe"
        assert result[0]["purchases_count"] == 5
        assert result[0]["total_spent"] == 500
    
    def test_generate_csv_report(self, finance_service):
        """Тест генерации CSV отчета."""
        # Мок покупок
        purchases = [
            MagicMock(
                id=1,
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                user_id=1,
                lesson_id=1,
                course_id=None,
                amount=100,
                status=PurchaseStatus.COMPLETED.value,
                payment_id="pay_123"
            )
        ]
        
        # Выполнение
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        result = finance_service._generate_csv_report(purchases, start_date, end_date)
        
        # Проверки
        assert "ID покупки,Дата,Пользователь ID" in result
        assert "1,2024-01-01 10:00:00,1,lesson,1,100,completed,pay_123" in result
        assert "Итого:,,,,,100,," in result
        assert "Период:,2024-01-01 - 2024-01-31" in result
        assert "Количество:,1" in result
    
    def test_generate_json_report(self, finance_service):
        """Тест генерации JSON отчета."""
        # Мок покупок
        purchases = [
            MagicMock(
                id=1,
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                user_id=1,
                lesson_id=1,
                course_id=None,
                amount=100,
                status=PurchaseStatus.COMPLETED.value,
                payment_id="pay_123"
            )
        ]
        
        # Выполнение
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        result = finance_service._generate_json_report(purchases, start_date, end_date)
        
        # Проверки
        import json
        data = json.loads(result)
        
        assert data["period"]["start_date"] == "2024-01-01"
        assert data["period"]["end_date"] == "2024-01-31"
        assert data["summary"]["total_purchases"] == 1
        assert data["summary"]["total_amount"] == 100
        assert len(data["purchases"]) == 1
        assert data["purchases"][0]["id"] == 1