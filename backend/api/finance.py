"""
API endpoints для финансовой отчетности и аналитики.
Доходы, статистика, экспорт отчетов, топ продаж.
"""

import io
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.schemas import (
    DailyRevenueStats, MonthlyStats, TopSellingItem, 
    WithdrawableAmount, ErrorResponse
)
from backend.services.finance_service import FinanceService
from backend.api.deps import get_current_active_admin, get_current_superuser

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/daily/{target_date}",
    response_model=DailyRevenueStats,
    summary="Дневная статистика доходов",
    description="Получение подробной статистики доходов за указанную дату"
)
async def get_daily_revenue(
    target_date: date,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение статистики доходов за день.
    
    Включает:
    - Общий доход
    - Количество покупок
    - Успешные и неуспешные транзакции
    - Средняя покупка
    - Топ уроков за день
    """
    try:
        finance_service = FinanceService(db)
        daily_stats = finance_service.get_daily_revenue(target_date)
        
        logger.info(f"Daily revenue stats requested for {target_date} by admin {current_admin.username}")
        
        return daily_stats
        
    except Exception as e:
        logger.error(f"Error getting daily revenue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения дневной статистики"
        )


@router.get(
    "/monthly/{year}/{month}",
    response_model=MonthlyStats,
    summary="Месячная статистика",
    description="Получение подробной статистики за месяц с разбивкой по дням"
)
async def get_monthly_stats(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение месячной статистики.
    
    Включает:
    - Общие показатели за месяц
    - Разбивка по дням
    - Рост по сравнению с предыдущим месяцем
    """
    try:
        # Валидация параметров
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Месяц должен быть от 1 до 12"
            )
        
        if year < 2020 or year > datetime.now().year + 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный год"
            )
        
        finance_service = FinanceService(db)
        monthly_stats = finance_service.get_monthly_stats(year, month)
        
        logger.info(f"Monthly stats requested for {year}-{month} by admin {current_admin.username}")
        
        return monthly_stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monthly stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения месячной статистики"
        )


@router.get(
    "/top-lessons",
    response_model=List[TopSellingItem],
    summary="Топ продаваемых уроков",
    description="Получение списка самых продаваемых уроков"
)
async def get_top_selling_lessons(
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    days: Optional[int] = Query(None, ge=1, le=365, description="Период в днях"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение топа продаваемых уроков.
    
    Параметры:
    - limit: количество результатов
    - days: период в днях (если не указан - за все время)
    """
    try:
        finance_service = FinanceService(db)
        top_lessons = finance_service.get_top_selling_lessons(limit=limit, days=days)
        
        period_text = f"за {days} дней" if days else "за все время"
        logger.info(f"Top lessons requested {period_text} by admin {current_admin.username}")
        
        return top_lessons
        
    except Exception as e:
        logger.error(f"Error getting top lessons: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения топа уроков"
        )


@router.get(
    "/withdrawable",
    response_model=WithdrawableAmount,
    summary="Доступная сумма для вывода",
    description="Расчет доступной суммы для вывода с учетом комиссий"
)
async def get_withdrawable_amount(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_superuser)
):
    """
    Получение информации о доступной сумме для вывода.
    
    Требует права суперпользователя.
    """
    try:
        finance_service = FinanceService(db)
        withdrawable = finance_service.calculate_withdrawable_amount()
        
        logger.info(f"Withdrawable amount requested by admin {current_admin.username}")
        
        return withdrawable
        
    except Exception as e:
        logger.error(f"Error calculating withdrawable amount: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка расчета доступной суммы"
        )


@router.get(
    "/analytics",
    summary="Аналитика доходов",
    description="Подробная аналитика доходов за указанный период"
)
async def get_revenue_analytics(
    period_days: int = Query(30, ge=1, le=365, description="Период в днях"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение подробной аналитики доходов.
    
    Включает:
    - Доходы по дням
    - Статистика по типам товаров
    - Топ пользователей
    - Общие показатели
    """
    try:
        finance_service = FinanceService(db)
        analytics = finance_service.get_revenue_analytics(period_days=period_days)
        
        logger.info(f"Revenue analytics requested for {period_days} days by admin {current_admin.username}")
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting revenue analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения аналитики"
        )


@router.get(
    "/export",
    summary="Экспорт финансового отчета",
    description="Экспорт финансового отчета в формате CSV или JSON"
)
async def export_financial_report(
    start_date: date = Query(..., description="Начальная дата"),
    end_date: date = Query(..., description="Конечная дата"),
    format_type: str = Query("csv", pattern="^(csv|json)$", description="Формат экспорта"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Экспорт финансового отчета.
    
    Поддерживаемые форматы:
    - CSV: для работы в Excel
    - JSON: для программной обработки
    """
    try:
        # Валидация дат
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Начальная дата не может быть больше конечной"
            )
        
        # Лимит на период (максимум 1 год)
        if (end_date - start_date).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Максимальный период экспорта - 365 дней"
            )
        
        finance_service = FinanceService(db)
        report_content = finance_service.export_financial_report(
            start_date=start_date,
            end_date=end_date,
            format_type=format_type
        )
        
        # Определение типа контента и имени файла
        if format_type == "csv":
            media_type = "text/csv"
            filename = f"financial_report_{start_date}_{end_date}.csv"
        else:
            media_type = "application/json"
            filename = f"financial_report_{start_date}_{end_date}.json"
        
        logger.info(f"Financial report exported ({format_type}) for {start_date}-{end_date} by admin {current_admin.username}")
        
        # Возврат файла для скачивания
        return StreamingResponse(
            io.StringIO(report_content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting financial report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка экспорта отчета"
        )


@router.get(
    "/user/{user_id}/lifetime-value",
    summary="Пожизненная ценность пользователя",
    description="Расчет пожизненной ценности конкретного пользователя"
)
async def get_user_lifetime_value(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение пожизненной ценности пользователя.
    """
    try:
        # Проверка существования пользователя
        from shared.models import User
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        finance_service = FinanceService(db)
        lifetime_value = finance_service.get_user_lifetime_value(user_id)
        
        return {
            "user_id": user_id,
            "user_name": user.first_name,
            "username": user.username,
            "lifetime_value": lifetime_value,
            "calculated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user lifetime value: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка расчета пожизненной ценности"
        )


@router.get(
    "/overview",
    summary="Общий обзор финансов",
    description="Краткий обзор ключевых финансовых показателей"
)
async def get_finance_overview(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение общего обзора финансовых показателей.
    
    Возвращает ключевые метрики для дашборда.
    """
    try:
        finance_service = FinanceService(db)
        
        # Сегодняшняя статистика
        today = datetime.now().date()
        today_stats = finance_service.get_daily_revenue(today)
        
        # Статистика за месяц
        current_year = today.year
        current_month = today.month
        monthly_stats = finance_service.get_monthly_stats(current_year, current_month)
        
        # Доступная сумма для вывода
        withdrawable = finance_service.calculate_withdrawable_amount()
        
        # Топ уроков за неделю
        top_lessons_week = finance_service.get_top_selling_lessons(limit=5, days=7)
        
        overview = {
            "today": {
                "revenue": today_stats.total_revenue,
                "purchases": today_stats.total_purchases,
                "completed_purchases": today_stats.completed_purchases
            },
            "this_month": {
                "revenue": monthly_stats.total_revenue,
                "purchases": monthly_stats.total_purchases,
                "growth_rate": monthly_stats.growth_rate
            },
            "withdrawable": {
                "available_amount": withdrawable.available_amount,
                "total_revenue": withdrawable.total_revenue,
                "pending_withdraws": withdrawable.pending_withdraws
            },
            "top_lessons_week": top_lessons_week[:3],  # Только топ 3
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return overview
        
    except Exception as e:
        logger.error(f"Error getting finance overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения обзора финансов"
        )


@router.get(
    "/trends",
    summary="Тренды доходов",
    description="Анализ трендов доходов за различные периоды"
)
async def get_revenue_trends(
    period: str = Query("month", pattern="^(week|month|quarter|year)$", description="Период анализа"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение трендов доходов за различные периоды.
    """
    try:
        from datetime import timedelta
        
        # Определение периода в днях
        period_mapping = {
            "week": 7,
            "month": 30,
            "quarter": 90,
            "year": 365
        }
        
        days = period_mapping[period]
        
        finance_service = FinanceService(db)
        analytics = finance_service.get_revenue_analytics(period_days=days)
        
        # Анализ тренда
        daily_revenues = analytics["daily_revenues"]
        
        if len(daily_revenues) >= 2:
            # Простой анализ тренда
            first_half = daily_revenues[:len(daily_revenues)//2]
            second_half = daily_revenues[len(daily_revenues)//2:]
            
            first_half_avg = sum(d["revenue"] for d in first_half) / len(first_half)
            second_half_avg = sum(d["revenue"] for d in second_half) / len(second_half)
            
            trend = "growing" if second_half_avg > first_half_avg else "declining"
            trend_percent = ((second_half_avg - first_half_avg) / max(first_half_avg, 1)) * 100
        else:
            trend = "stable"
            trend_percent = 0
        
        return {
            "period": period,
            "days_analyzed": days,
            "trend": trend,
            "trend_percent": round(trend_percent, 2),
            "total_revenue": analytics["total_revenue"],
            "average_daily_revenue": analytics["average_daily_revenue"],
            "daily_data": daily_revenues,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting revenue trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка анализа трендов"
        )