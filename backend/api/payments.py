"""
API endpoints для обработки платежей и интеграции с Telegram Stars.
Создание платежей, webhook обработка, верификация.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.schemas import (
    PaymentCreateRequest, PaymentResponse, PaymentVerificationRequest,
    WebhookPaymentData, Purchase as PurchaseSchema, ErrorResponse
)
from backend.services.payment_service import PaymentService
from backend.api.deps import get_current_active_admin, get_pagination_params, PaginationParams

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/create",
    response_model=PaymentResponse,
    summary="Создание платежа",
    description="Создает новый платеж для покупки урока или курса с возможностью применения промокода"
)
async def create_payment(
    payment_request: PaymentCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Создание нового платежа.
    
    Поддерживает:
    - Покупку отдельных уроков
    - Покупку курсов
    - Применение промокодов
    - Валидацию пользователей и товаров
    """
    try:
        payment_service = PaymentService(db)
        
        payment_response = payment_service.create_payment(
            user_id=payment_request.user_id,
            item_id=payment_request.item_id,
            item_type=payment_request.item_type,
            promo_code=payment_request.promo_code
        )
        
        logger.info(f"Payment created: {payment_response.payment_id} for user {payment_request.user_id}")
        
        return payment_response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.post(
    "/webhook",
    summary="Webhook для обработки платежей от Telegram",
    description="Обрабатывает уведомления о платежах от Telegram Stars"
)
async def payment_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint для обработки платежей от Telegram.
    
    Обрабатывает:
    - Успешные платежи
    - Неудачные платежи
    - Отмененные платежи
    """
    try:
        # Получение данных webhook
        webhook_data = await request.json()
        
        # Валидация webhook signature (в production должна быть включена)
        # webhook_signature = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        # if not _validate_webhook_signature(webhook_data, webhook_signature):
        #     raise HTTPException(status_code=403, detail="Invalid webhook signature")
        
        payment_service = PaymentService(db)
        
        # Обработка различных типов уведомлений
        update_type = webhook_data.get("update_type")
        
        if update_type == "successful_payment":
            background_tasks.add_task(
                _process_successful_payment_webhook,
                webhook_data,
                payment_service
            )
        elif update_type == "pre_checkout_query":
            # Обработка pre-checkout запроса
            pre_checkout_query = webhook_data.get("pre_checkout_query", {})
            invoice_payload = pre_checkout_query.get("invoice_payload", "")
            
            # Валидация платежа
            is_valid = _validate_pre_checkout(invoice_payload, payment_service)
            
            return JSONResponse(
                content={"ok": is_valid},
                status_code=200
            )
        
        return JSONResponse(content={"ok": True}, status_code=200)
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return JSONResponse(
            content={"ok": False, "error": str(e)},
            status_code=500
        )


@router.post(
    "/verify",
    summary="Верификация платежа",
    description="Верифицирует платеж с данными от Telegram"
)
async def verify_payment(
    verification_request: PaymentVerificationRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Ручная верификация платежа администратором.
    """
    try:
        payment_service = PaymentService(db)
        
        # Создание данных для верификации
        telegram_data = {
            "total_amount": verification_request.amount if hasattr(verification_request, 'amount') else 0,
            "currency": "XTR",
            "telegram_payment_charge_id": verification_request.telegram_payment_charge_id,
            "provider_payment_charge_id": verification_request.provider_payment_charge_id,
            "invoice_payload": verification_request.payment_id
        }
        
        is_valid = payment_service.verify_payment(
            verification_request.payment_id,
            telegram_data
        )
        
        if is_valid:
            return {"verified": True, "message": "Платеж верифицирован"}
        else:
            return {"verified": False, "message": "Платеж не прошел верификацию"}
            
    except Exception as e:
        logger.error(f"Payment verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка верификации платежа"
        )


@router.get(
    "/{payment_id}",
    response_model=Dict[str, Any],
    summary="Получение статуса платежа",
    description="Возвращает текущий статус указанного платежа"
)
async def get_payment_status(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """
    Получение статуса платежа по его ID.
    """
    try:
        payment_service = PaymentService(db)
        
        status = payment_service.get_payment_status(payment_id)
        
        if status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Платеж не найден"
            )
        
        return {
            "payment_id": payment_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статуса платежа"
        )


@router.get(
    "/",
    summary="Список платежей",
    description="Получение списка всех платежей с пагинацией (только для администраторов)"
)
async def get_payments(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Получение списка всех платежей (администраторский endpoint).
    """
    try:
        from shared.models import Purchase
        from backend.api.deps import create_pagination_response
        
        # Подсчет общего количества
        total = db.query(Purchase).count()
        
        # Получение платежей с пагинацией
        purchases = db.query(Purchase)\
            .order_by(Purchase.created_at.desc())\
            .offset(pagination.offset)\
            .limit(pagination.size)\
            .all()
        
        # Преобразование в схемы
        purchases_data = []
        for purchase in purchases:
            purchase_dict = {
                "id": purchase.id,
                "payment_id": purchase.payment_id,
                "user_id": purchase.user_id,
                "lesson_id": purchase.lesson_id,
                "course_id": purchase.course_id,
                "amount": purchase.amount,
                "status": purchase.status,
                "created_at": purchase.created_at.isoformat(),
                "updated_at": purchase.updated_at.isoformat()
            }
            purchases_data.append(purchase_dict)
        
        return create_pagination_response(purchases_data, total, pagination)
        
    except Exception as e:
        logger.error(f"Error getting payments list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения списка платежей"
        )


@router.post(
    "/cleanup-expired",
    summary="Очистка просроченных платежей",
    description="Отменяет просроченные платежи (только для администраторов)"
)
async def cleanup_expired_payments(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_active_admin)
):
    """
    Очистка просроченных платежей.
    """
    try:
        payment_service = PaymentService(db)
        
        # Запуск очистки в фоне
        background_tasks.add_task(
            _cleanup_expired_payments_task,
            payment_service
        )
        
        return {
            "message": "Задача очистки просроченных платежей запущена",
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"Error starting cleanup task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка запуска задачи очистки"
        )


# Background tasks

async def _process_successful_payment_webhook(
    webhook_data: Dict[str, Any],
    payment_service: PaymentService
):
    """Обработка успешного платежа в фоне."""
    try:
        successful_payment = webhook_data.get("message", {}).get("successful_payment", {})
        
        if not successful_payment:
            logger.error("No successful_payment data in webhook")
            return
        
        # Извлечение данных платежа
        invoice_payload = successful_payment.get("invoice_payload", "")
        telegram_payment_charge_id = successful_payment.get("telegram_payment_charge_id", "")
        
        # Парсинг payload для получения payment_id
        import json
        try:
            payload_data = json.loads(invoice_payload)
            payment_id = payload_data.get("payment_id")
        except (json.JSONDecodeError, AttributeError):
            logger.error(f"Invalid invoice payload: {invoice_payload}")
            return
        
        if not payment_id:
            logger.error("No payment_id in invoice payload")
            return
        
        # Поиск покупки
        from shared.models import Purchase
        purchase = payment_service.db.query(Purchase).filter(
            Purchase.payment_id == payment_id
        ).first()
        
        if not purchase:
            logger.error(f"Purchase not found for payment_id: {payment_id}")
            return
        
        # Обновление статуса
        success = payment_service.process_successful_payment(purchase.id)
        
        if success:
            logger.info(f"Successfully processed payment: {payment_id}")
        else:
            logger.error(f"Failed to process payment: {payment_id}")
            
    except Exception as e:
        logger.error(f"Error processing successful payment webhook: {e}")


async def _cleanup_expired_payments_task(payment_service: PaymentService):
    """Задача очистки просроченных платежей."""
    try:
        canceled_count = payment_service.cancel_expired_payments()
        logger.info(f"Canceled {canceled_count} expired payments")
    except Exception as e:
        logger.error(f"Error during payment cleanup: {e}")


def _validate_pre_checkout(invoice_payload: str, payment_service: PaymentService) -> bool:
    """Валидация pre-checkout запроса."""
    try:
        import json
        
        payload_data = json.loads(invoice_payload)
        payment_id = payload_data.get("payment_id")
        
        if not payment_id:
            return False
        
        # Проверка существования и статуса платежа
        status = payment_service.get_payment_status(payment_id)
        return status == "pending"
        
    except Exception as e:
        logger.error(f"Pre-checkout validation error: {e}")
        return False


def _validate_webhook_signature(data: Dict[str, Any], signature: str) -> bool:
    """Валидация подписи webhook (для production)."""
    # В production здесь должна быть реализована валидация HMAC подписи
    # используя webhook secret token
    return True  # Временно отключено для разработки