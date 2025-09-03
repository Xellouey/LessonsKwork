"""
API endpoints для управления промокодами.
Создание, валидация, применение и управление промокодами.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.schemas import (
    PromoCodeCreate, PromoCodeUpdate, PromoCode as PromoCodeSchema,
    PromoCodeCheck, ErrorResponse
)
from shared.models import PromoCode
from backend.services.promo_service import PromoCodeService
from backend.api.deps import (
    get_current_active_admin, get_pagination_params, 
    PaginationParams, create_pagination_response
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=PromoCodeSchema,
    summary="Создание промокода",
    description="Создает новый промокод с заданными параметрами скидки"
)
async def create_promo_code(
    promo_data: PromoCodeCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Создание нового промокода.
    
    Требует права администратора.
    """
    try:
        promo_service = PromoCodeService(db)
        
        promo_code = promo_service.create_promo_code(
            code=promo_data.code,
            discount_percent=promo_data.discount_percent,
            discount_amount=promo_data.discount_amount,
            max_uses=promo_data.max_uses,
            expires_at=promo_data.expires_at
        )
        
        logger.info(f"Promo code created: {promo_code.code} by admin {current_admin.username}")
        
        return promo_code
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating promo code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания промокода"
        )


@router.get(
    "/",
    summary="Список промокодов",
    description="Получение списка всех промокодов с пагинацией"
)
async def get_promocodes(
    pagination: PaginationParams = Depends(get_pagination_params),
    include_expired: bool = Query(False, description="Включать истекшие промокоды"),
    active_only: bool = Query(True, description="Только активные промокоды"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение списка промокодов (только для администраторов).
    """
    try:
        from sqlalchemy import and_, or_
        
        query = db.query(PromoCode)
        
        # Фильтрация по активности
        if active_only:
            query = query.filter(PromoCode.is_active == True)
        
        # Фильтрация по истечению
        if not include_expired:
            query = query.filter(
                or_(
                    PromoCode.expires_at.is_(None),
                    PromoCode.expires_at > datetime.utcnow()
                )
            )
        
        # Подсчет общего количества
        total = query.count()
        
        # Получение промокодов с пагинацией
        promocodes = query.order_by(PromoCode.created_at.desc())\
            .offset(pagination.offset)\
            .limit(pagination.size)\
            .all()
        
        return create_pagination_response(promocodes, total, pagination)
        
    except Exception as e:
        logger.error(f"Error getting promocodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения списка промокодов"
        )


@router.get(
    "/{promo_id}",
    response_model=PromoCodeSchema,
    summary="Получение промокода",
    description="Получение промокода по ID"
)
async def get_promo_code(
    promo_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение промокода по ID.
    """
    try:
        promo_service = PromoCodeService(db)
        promo_code = promo_service.get_promo_code_by_id(promo_id)
        
        if not promo_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Промокод не найден"
            )
        
        return promo_code
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting promo code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения промокода"
        )


@router.put(
    "/{promo_id}",
    response_model=PromoCodeSchema,
    summary="Обновление промокода",
    description="Обновление параметров промокода"
)
async def update_promo_code(
    promo_id: int,
    update_data: PromoCodeUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Обновление промокода.
    """
    try:
        promo_service = PromoCodeService(db)
        
        updated_promo = promo_service.update_promo_code(promo_id, update_data)
        
        if not updated_promo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Промокод не найден"
            )
        
        logger.info(f"Promo code updated: {updated_promo.code} by admin {current_admin.username}")
        
        return updated_promo
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating promo code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления промокода"
        )


@router.delete(
    "/{promo_id}",
    summary="Удаление промокода",
    description="Деактивация промокода"
)
async def delete_promo_code(
    promo_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Удаление (деактивация) промокода.
    """
    try:
        promo_service = PromoCodeService(db)
        
        success = promo_service.delete_promo_code(promo_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Промокод не найден"
            )
        
        logger.info(f"Promo code deleted: ID {promo_id} by admin {current_admin.username}")
        
        return {"message": "Промокод успешно деактивирован"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting promo code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления промокода"
        )


@router.post(
    "/validate",
    summary="Валидация промокода",
    description="Проверка валидности промокода и расчет скидки"
)
async def validate_promo_code(
    validation_request: PromoCodeCheck,
    db: Session = Depends(get_db)
):
    """
    Валидация промокода и расчет скидки.
    
    Публичный endpoint для проверки промокодов из Telegram Bot.
    """
    try:
        promo_service = PromoCodeService(db)
        
        # Валидация промокода
        promo_code = promo_service.validate_promo_code(validation_request.code)
        
        # Получение цены товара для расчета скидки
        if validation_request.item_type == "lesson":
            from shared.models import Lesson
            item = db.query(Lesson).filter(Lesson.id == validation_request.item_id).first()
            base_price = item.price if item else 0
        elif validation_request.item_type == "course":
            from shared.models import Course
            item = db.query(Course).filter(Course.id == validation_request.item_id).first()
            base_price = item.discount_price or item.total_price if item else 0
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неподдерживаемый тип товара"
            )
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Товар не найден"
            )
        
        # Расчет скидки
        discount_info = promo_service.apply_discount(promo_code, base_price)
        
        return {
            "valid": True,
            "promo_code": promo_code.code,
            "discount_percent": promo_code.discount_percent,
            "discount_amount": promo_code.discount_amount,
            "original_price": discount_info["original_amount"],
            "discount_value": discount_info["discount_amount"],
            "final_price": discount_info["final_amount"],
            "expires_at": promo_code.expires_at.isoformat() if promo_code.expires_at else None,
            "remaining_uses": (promo_code.max_uses - promo_code.current_uses) if promo_code.max_uses else None
        }
        
    except ValueError as e:
        return {
            "valid": False,
            "error": str(e)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating promo code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка валидации промокода"
        )


@router.get(
    "/{promo_id}/stats",
    summary="Статистика промокода",
    description="Получение статистики использования промокода"
)
async def get_promo_code_stats(
    promo_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение статистики промокода.
    """
    try:
        promo_service = PromoCodeService(db)
        stats = promo_service.get_promo_code_stats(promo_id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Промокод не найден"
            )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting promo code stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статистики промокода"
        )


@router.post(
    "/bulk-create",
    summary="Массовое создание промокодов",
    description="Создание множества промокодов с одинаковыми параметрами"
)
async def bulk_create_promocodes(
    count: int = Query(..., ge=1, le=1000, description="Количество промокодов"),
    discount_percent: int = Query(..., ge=1, le=100, description="Процент скидки"),
    prefix: str = Query("BULK", description="Префикс для кодов"),
    max_uses: Optional[int] = Query(1, description="Максимальное количество использований"),
    expires_hours: Optional[int] = Query(None, description="Истечение через часов"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Массовое создание промокодов.
    """
    try:
        from datetime import timedelta
        
        promo_service = PromoCodeService(db)
        
        expires_at = None
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        promocodes = promo_service.bulk_create_promocodes(
            count=count,
            discount_percent=discount_percent,
            prefix=prefix,
            max_uses=max_uses,
            expires_at=expires_at
        )
        
        logger.info(f"Bulk created {len(promocodes)} promo codes by admin {current_admin.username}")
        
        return {
            "message": f"Создано {len(promocodes)} промокодов",
            "count": len(promocodes),
            "codes": [promo.code for promo in promocodes[:10]],  # Показываем только первые 10
            "total_created": len(promocodes)
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error bulk creating promo codes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка массового создания промокодов"
        )


@router.post(
    "/cleanup-expired",
    summary="Очистка истекших промокодов",
    description="Деактивация всех истекших промокодов"
)
async def cleanup_expired_promocodes(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Очистка истекших промокодов.
    """
    try:
        promo_service = PromoCodeService(db)
        
        # Запуск очистки в фоне
        background_tasks.add_task(
            _cleanup_expired_promocodes_task,
            promo_service,
            current_admin.username
        )
        
        return {
            "message": "Задача очистки истекших промокодов запущена",
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"Error starting cleanup task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка запуска задачи очистки"
        )


@router.get(
    "/public/check/{code}",
    summary="Публичная проверка промокода",
    description="Публичная проверка существования и валидности промокода"
)
async def public_check_promo_code(
    code: str,
    db: Session = Depends(get_db)
):
    """
    Публичная проверка промокода (для Telegram Bot).
    
    Возвращает базовую информацию без чувствительных данных.
    """
    try:
        promo_service = PromoCodeService(db)
        
        try:
            promo_code = promo_service.validate_promo_code(code)
            
            return {
                "exists": True,
                "valid": True,
                "discount_percent": promo_code.discount_percent,
                "discount_amount": promo_code.discount_amount,
                "expires_at": promo_code.expires_at.isoformat() if promo_code.expires_at else None
            }
            
        except ValueError as e:
            return {
                "exists": True,
                "valid": False,
                "error": str(e)
            }
            
    except Exception as e:
        logger.error(f"Error checking promo code publicly: {e}")
        return {
            "exists": False,
            "valid": False,
            "error": "Промокод не найден"
        }


# Background tasks

async def _cleanup_expired_promocodes_task(
    promo_service: PromoCodeService,
    admin_username: str
):
    """Задача очистки истекших промокодов."""
    try:
        cleaned_count = promo_service.cleanup_expired_promocodes()
        logger.info(f"Cleaned up {cleaned_count} expired promo codes by admin {admin_username}")
    except Exception as e:
        logger.error(f"Error during promo codes cleanup: {e}")