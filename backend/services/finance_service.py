"""
Сервис для финансовой отчетности и аналитики.
Расчет доходов, статистики продаж, топ товаров и вывода средств.
"""

import csv
import io
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract, desc

from shared.models import Purchase, Lesson, Course, User, WithdrawRequest
from shared.constants import PurchaseStatus, COMMISSION_PERCENT, MIN_WITHDRAW_AMOUNT
from shared.schemas import (
    DailyRevenueStats, MonthlyStats, TopSellingItem, WithdrawableAmount
)


class FinanceService:
    """Сервис для работы с финансовой отчетностью."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_daily_revenue(self, target_date: date) -> DailyRevenueStats:
        """
        Получение статистики доходов за день.
        
        Args:
            target_date: Дата для анализа
            
        Returns:
            DailyRevenueStats: Статистика за день
        """
        # Определение временных границ дня
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        # Запрос статистики за день
        daily_stats = self.db.query(
            func.count(Purchase.id).label("total_purchases"),
            func.coalesce(func.sum(Purchase.amount), 0).label("total_revenue"),
            func.count(Purchase.id).filter(Purchase.status == PurchaseStatus.COMPLETED.value).label("completed_purchases"),
            func.count(Purchase.id).filter(Purchase.status == PurchaseStatus.FAILED.value).label("failed_purchases")
        ).filter(
            and_(
                Purchase.created_at >= start_of_day,
                Purchase.created_at <= end_of_day
            )
        ).first()
        
        # Расчет средней покупки
        average_purchase = 0
        if daily_stats.completed_purchases > 0:
            completed_revenue = self.db.query(
                func.coalesce(func.sum(Purchase.amount), 0)
            ).filter(
                and_(
                    Purchase.created_at >= start_of_day,
                    Purchase.created_at <= end_of_day,
                    Purchase.status == PurchaseStatus.COMPLETED.value
                )
            ).scalar()
            
            average_purchase = completed_revenue / daily_stats.completed_purchases
        
        # Топ уроков за день
        top_lessons = self._get_top_lessons_for_period(start_of_day, end_of_day, limit=5)
        
        return DailyRevenueStats(
            date=target_date.isoformat(),
            total_revenue=daily_stats.total_revenue,
            total_purchases=daily_stats.total_purchases,
            completed_purchases=daily_stats.completed_purchases,
            failed_purchases=daily_stats.failed_purchases,
            average_purchase=round(average_purchase, 2),
            top_lessons=top_lessons
        )
    
    def get_monthly_stats(self, year: int, month: int) -> MonthlyStats:
        """
        Получение месячной статистики.
        
        Args:
            year: Год
            month: Месяц
            
        Returns:
            MonthlyStats: Месячная статистика
        """
        # Определение границ месяца
        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_of_month = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        # Общая статистика за месяц
        monthly_totals = self.db.query(
            func.count(Purchase.id).label("total_purchases"),
            func.coalesce(func.sum(Purchase.amount), 0).label("total_revenue")
        ).filter(
            and_(
                Purchase.created_at >= start_of_month,
                Purchase.created_at <= end_of_month,
                Purchase.status == PurchaseStatus.COMPLETED.value
            )
        ).first()
        
        # Статистика по дням
        daily_breakdown = []
        current_date = start_of_month.date()
        end_date = end_of_month.date()
        
        while current_date <= end_date:
            daily_stats = self.get_daily_revenue(current_date)
            daily_breakdown.append(daily_stats)
            current_date += timedelta(days=1)
        
        # Расчет роста по сравнению с предыдущим месяцем
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        
        prev_month_revenue = self._get_month_revenue(prev_year, prev_month)
        growth_rate = 0
        
        if prev_month_revenue > 0:
            growth_rate = ((monthly_totals.total_revenue - prev_month_revenue) / prev_month_revenue) * 100
        
        return MonthlyStats(
            year=year,
            month=month,
            total_revenue=monthly_totals.total_revenue,
            total_purchases=monthly_totals.total_purchases,
            daily_breakdown=daily_breakdown,
            growth_rate=round(growth_rate, 2)
        )
    
    def get_top_selling_lessons(self, limit: int = 10, days: Optional[int] = None) -> List[TopSellingItem]:
        """
        Получение топа продаваемых уроков.
        
        Args:
            limit: Количество результатов
            days: Период в днях (если не указан - за все время)
            
        Returns:
            List[TopSellingItem]: Топ продаж
        """
        query = self.db.query(
            Lesson.id,
            Lesson.title,
            Lesson.price,
            func.count(Purchase.id).label("sales_count"),
            func.coalesce(func.sum(Purchase.amount), 0).label("total_revenue")
        ).join(
            Purchase, Purchase.lesson_id == Lesson.id
        ).filter(
            Purchase.status == PurchaseStatus.COMPLETED.value
        )
        
        # Фильтрация по периоду
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Purchase.created_at >= start_date)
        
        results = query.group_by(
            Lesson.id, Lesson.title, Lesson.price
        ).order_by(
            desc("sales_count"), desc("total_revenue")
        ).limit(limit).all()
        
        top_items = []
        for result in results:
            top_items.append(TopSellingItem(
                item_id=result.id,
                item_type="lesson",
                title=result.title,
                sales_count=result.sales_count,
                total_revenue=result.total_revenue,
                price=result.price
            ))
        
        return top_items
    
    def get_user_lifetime_value(self, user_id: int) -> float:
        """
        Расчет пожизненной ценности пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            float: Пожизненная ценность
        """
        total_spent = self.db.query(
            func.coalesce(func.sum(Purchase.amount), 0)
        ).filter(
            and_(
                Purchase.user_id == user_id,
                Purchase.status == PurchaseStatus.COMPLETED.value
            )
        ).scalar()
        
        return float(total_spent or 0)
    
    def export_financial_report(
        self, 
        start_date: date, 
        end_date: date,
        format_type: str = "csv"
    ) -> str:
        """
        Экспорт финансового отчета.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            format_type: Формат экспорта (csv, json)
            
        Returns:
            str: Содержимое отчета
        """
        # Получение данных для отчета
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        purchases = self.db.query(Purchase).filter(
            and_(
                Purchase.created_at >= start_datetime,
                Purchase.created_at <= end_datetime,
                Purchase.status == PurchaseStatus.COMPLETED.value
            )
        ).order_by(Purchase.created_at.desc()).all()
        
        if format_type == "csv":
            return self._generate_csv_report(purchases, start_date, end_date)
        elif format_type == "json":
            return self._generate_json_report(purchases, start_date, end_date)
        else:
            raise ValueError("Неподдерживаемый формат экспорта")
    
    def calculate_withdrawable_amount(self) -> WithdrawableAmount:
        """
        Расчет доступной суммы для вывода.
        
        Returns:
            WithdrawableAmount: Информация о доступных средствах
        """
        # Общий доход
        total_revenue = self.db.query(
            func.coalesce(func.sum(Purchase.amount), 0)
        ).filter(
            Purchase.status == PurchaseStatus.COMPLETED.value
        ).scalar()
        
        # Сумма всех выводов
        total_withdraws = self.db.query(
            func.coalesce(func.sum(WithdrawRequest.amount), 0)
        ).filter(
            WithdrawRequest.status.in_(["approved", "completed"])
        ).scalar()
        
        # Ожидающие выводы
        pending_withdraws = self.db.query(
            func.coalesce(func.sum(WithdrawRequest.amount), 0)
        ).filter(
            WithdrawRequest.status == "pending"
        ).scalar()
        
        # Расчет комиссии
        commission_amount = (total_revenue * COMMISSION_PERCENT) // 100
        
        # Доступная сумма
        available_amount = total_revenue - total_withdraws - pending_withdraws - commission_amount
        available_amount = max(0, available_amount)
        
        return WithdrawableAmount(
            total_revenue=total_revenue,
            total_withdraws=total_withdraws,
            pending_withdraws=pending_withdraws,
            available_amount=available_amount,
            commission_amount=commission_amount
        )
    
    def get_revenue_analytics(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Получение аналитики доходов за период.
        
        Args:
            period_days: Период в днях
            
        Returns:
            Dict: Аналитика доходов
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Доходы по дням
        daily_revenues = self.db.query(
            func.date(Purchase.created_at).label("date"),
            func.coalesce(func.sum(Purchase.amount), 0).label("revenue"),
            func.count(Purchase.id).label("purchases_count")
        ).filter(
            and_(
                Purchase.created_at >= start_date,
                Purchase.created_at <= end_date,
                Purchase.status == PurchaseStatus.COMPLETED.value
            )
        ).group_by(
            func.date(Purchase.created_at)
        ).order_by("date").all()
        
        # Статистика по типам товаров
        item_type_stats = self._get_item_type_statistics(start_date, end_date)
        
        # Топ пользователей
        top_users = self._get_top_users_by_revenue(period_days, limit=10)
        
        return {
            "period_days": period_days,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "daily_revenues": [
                {
                    "date": str(item.date),
                    "revenue": item.revenue,
                    "purchases_count": item.purchases_count
                }
                for item in daily_revenues
            ],
            "item_type_statistics": item_type_stats,
            "top_users": top_users,
            "total_revenue": sum(item.revenue for item in daily_revenues),
            "total_purchases": sum(item.purchases_count for item in daily_revenues),
            "average_daily_revenue": sum(item.revenue for item in daily_revenues) / max(1, len(daily_revenues))
        }
    
    def _get_month_revenue(self, year: int, month: int) -> int:
        """Получение дохода за месяц."""
        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_of_month = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        revenue = self.db.query(
            func.coalesce(func.sum(Purchase.amount), 0)
        ).filter(
            and_(
                Purchase.created_at >= start_of_month,
                Purchase.created_at <= end_of_month,
                Purchase.status == PurchaseStatus.COMPLETED.value
            )
        ).scalar()
        
        return revenue or 0
    
    def _get_top_lessons_for_period(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Получение топа уроков за период."""
        results = self.db.query(
            Lesson.id,
            Lesson.title,
            func.count(Purchase.id).label("sales_count")
        ).join(
            Purchase, Purchase.lesson_id == Lesson.id
        ).filter(
            and_(
                Purchase.created_at >= start_date,
                Purchase.created_at <= end_date,
                Purchase.status == PurchaseStatus.COMPLETED.value
            )
        ).group_by(
            Lesson.id, Lesson.title
        ).order_by(
            desc("sales_count")
        ).limit(limit).all()
        
        return [
            {
                "id": result.id,
                "title": result.title,
                "sales_count": result.sales_count
            }
            for result in results
        ]
    
    def _get_item_type_statistics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Статистика по типам товаров."""
        # Статистика по урокам
        lesson_stats = self.db.query(
            func.count(Purchase.id).label("count"),
            func.coalesce(func.sum(Purchase.amount), 0).label("revenue")
        ).filter(
            and_(
                Purchase.created_at >= start_date,
                Purchase.created_at <= end_date,
                Purchase.status == PurchaseStatus.COMPLETED.value,
                Purchase.lesson_id.is_not(None)
            )
        ).first()
        
        # Статистика по курсам
        course_stats = self.db.query(
            func.count(Purchase.id).label("count"),
            func.coalesce(func.sum(Purchase.amount), 0).label("revenue")
        ).filter(
            and_(
                Purchase.created_at >= start_date,
                Purchase.created_at <= end_date,
                Purchase.status == PurchaseStatus.COMPLETED.value,
                Purchase.course_id.is_not(None)
            )
        ).first()
        
        return {
            "lessons": {
                "count": lesson_stats.count or 0,
                "revenue": lesson_stats.revenue or 0
            },
            "courses": {
                "count": course_stats.count or 0,
                "revenue": course_stats.revenue or 0
            }
        }
    
    def _get_top_users_by_revenue(self, period_days: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Топ пользователей по доходам."""
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        results = self.db.query(
            User.id,
            User.first_name,
            User.username,
            func.count(Purchase.id).label("purchases_count"),
            func.coalesce(func.sum(Purchase.amount), 0).label("total_spent")
        ).join(
            Purchase, Purchase.user_id == User.id
        ).filter(
            and_(
                Purchase.created_at >= start_date,
                Purchase.status == PurchaseStatus.COMPLETED.value
            )
        ).group_by(
            User.id, User.first_name, User.username
        ).order_by(
            desc("total_spent")
        ).limit(limit).all()
        
        return [
            {
                "user_id": result.id,
                "first_name": result.first_name,
                "username": result.username,
                "purchases_count": result.purchases_count,
                "total_spent": result.total_spent
            }
            for result in results
        ]
    
    def _generate_csv_report(
        self, 
        purchases: List[Purchase], 
        start_date: date, 
        end_date: date
    ) -> str:
        """Генерация CSV отчета."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow([
            "ID покупки",
            "Дата",
            "Пользователь ID",
            "Тип товара",
            "ID товара",
            "Сумма",
            "Статус",
            "Payment ID"
        ])
        
        # Данные
        for purchase in purchases:
            item_type = "lesson" if purchase.lesson_id else "course"
            item_id = purchase.lesson_id or purchase.course_id
            
            writer.writerow([
                purchase.id,
                purchase.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                purchase.user_id,
                item_type,
                item_id,
                purchase.amount,
                purchase.status,
                purchase.payment_id
            ])
        
        # Итоги
        total_amount = sum(p.amount for p in purchases)
        writer.writerow([])
        writer.writerow(["Итого:", "", "", "", "", total_amount, "", ""])
        writer.writerow(["Период:", f"{start_date} - {end_date}", "", "", "", "", "", ""])
        writer.writerow(["Количество:", len(purchases), "", "", "", "", "", ""])
        
        return output.getvalue()
    
    def _generate_json_report(
        self, 
        purchases: List[Purchase], 
        start_date: date, 
        end_date: date
    ) -> str:
        """Генерация JSON отчета."""
        import json
        
        report_data = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_purchases": len(purchases),
                "total_amount": sum(p.amount for p in purchases)
            },
            "purchases": []
        }
        
        for purchase in purchases:
            item_type = "lesson" if purchase.lesson_id else "course"
            item_id = purchase.lesson_id or purchase.course_id
            
            report_data["purchases"].append({
                "id": purchase.id,
                "created_at": purchase.created_at.isoformat(),
                "user_id": purchase.user_id,
                "item_type": item_type,
                "item_id": item_id,
                "amount": purchase.amount,
                "status": purchase.status,
                "payment_id": purchase.payment_id
            })
        
        return json.dumps(report_data, ensure_ascii=False, indent=2)