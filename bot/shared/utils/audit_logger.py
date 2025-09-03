"""
Система аудита и логирования финансовых операций.
Логирование всех финансовых транзакций для безопасности и отчетности.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from shared.constants import PurchaseStatus, WithdrawStatus


class AuditLogger:
    """Класс для аудита финансовых операций."""
    
    def __init__(self):
        # Создание отдельного логгера для аудита
        self.logger = logging.getLogger("financial_audit")
        self.logger.setLevel(logging.INFO)
        
        # Создание обработчика для записи в файл
        if not self.logger.handlers:
            # Файловый обработчик
            file_handler = logging.FileHandler("logs/financial_audit.log", encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # Формат для аудита
            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            
            # Консольный обработчик для важных событий
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
    
    def log_payment_created(self, payment_data: Dict[str, Any]) -> None:
        """
        Логирование создания платежа.
        
        Args:
            payment_data: Данные платежа
        """
        audit_data = {
            "action": "payment_created",
            "timestamp": datetime.utcnow().isoformat(),
            "payment_id": payment_data.get("payment_id"),
            "user_id": payment_data.get("user_id"),
            "item_id": payment_data.get("item_id"),
            "item_type": payment_data.get("item_type"),
            "amount": payment_data.get("amount"),
            "final_amount": payment_data.get("final_amount"),
            "promo_code": payment_data.get("promo_code"),
            "discount_applied": payment_data.get("discount_applied", 0)
        }
        
        self.logger.info(
            f"Payment created: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_payment_completed(
        self, 
        payment_id: str, 
        amount: int, 
        user_id: int,
        telegram_charge_id: Optional[str] = None
    ) -> None:
        """
        Логирование успешного завершения платежа.
        
        Args:
            payment_id: ID платежа
            amount: Сумма платежа
            user_id: ID пользователя
            telegram_charge_id: ID транзакции Telegram
        """
        audit_data = {
            "action": "payment_completed",
            "timestamp": datetime.utcnow().isoformat(),
            "payment_id": payment_id,
            "user_id": user_id,
            "amount": amount,
            "telegram_charge_id": telegram_charge_id,
            "status": PurchaseStatus.COMPLETED.value
        }
        
        self.logger.info(
            f"Payment completed: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_payment_failed(
        self, 
        payment_id: str, 
        error: str, 
        user_id: Optional[int] = None,
        amount: Optional[int] = None
    ) -> None:
        """
        Логирование неудачного платежа.
        
        Args:
            payment_id: ID платежа
            error: Описание ошибки
            user_id: ID пользователя
            amount: Сумма платежа
        """
        audit_data = {
            "action": "payment_failed",
            "timestamp": datetime.utcnow().isoformat(),
            "payment_id": payment_id,
            "user_id": user_id,
            "amount": amount,
            "error": error,
            "status": PurchaseStatus.FAILED.value
        }
        
        self.logger.warning(
            f"Payment failed: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_promo_code_used(
        self, 
        code: str, 
        user_id: int, 
        discount_amount: int,
        payment_id: Optional[str] = None
    ) -> None:
        """
        Логирование использования промокода.
        
        Args:
            code: Код промокода
            user_id: ID пользователя
            discount_amount: Размер скидки
            payment_id: ID платежа
        """
        audit_data = {
            "action": "promo_code_used",
            "timestamp": datetime.utcnow().isoformat(),
            "promo_code": code,
            "user_id": user_id,
            "discount_amount": discount_amount,
            "payment_id": payment_id
        }
        
        self.logger.info(
            f"Promo code used: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_withdraw_request(
        self, 
        amount: int, 
        wallet_address: Optional[str] = None,
        request_id: Optional[int] = None
    ) -> None:
        """
        Логирование запроса на вывод средств.
        
        Args:
            amount: Сумма для вывода
            wallet_address: Адрес кошелька
            request_id: ID запроса
        """
        audit_data = {
            "action": "withdraw_requested",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "amount": amount,
            "wallet_address": wallet_address,
            "status": WithdrawStatus.PENDING.value
        }
        
        self.logger.info(
            f"Withdraw requested: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_withdraw_approved(
        self, 
        request_id: int, 
        amount: int, 
        admin_username: str,
        notes: Optional[str] = None
    ) -> None:
        """
        Логирование одобрения вывода средств.
        
        Args:
            request_id: ID запроса
            amount: Сумма
            admin_username: Имя администратора
            notes: Заметки
        """
        audit_data = {
            "action": "withdraw_approved",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "amount": amount,
            "admin_username": admin_username,
            "notes": notes,
            "status": WithdrawStatus.APPROVED.value
        }
        
        self.logger.info(
            f"Withdraw approved: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_withdraw_rejected(
        self, 
        request_id: int, 
        amount: int, 
        admin_username: str,
        reason: str
    ) -> None:
        """
        Логирование отклонения вывода средств.
        
        Args:
            request_id: ID запроса
            amount: Сумма
            admin_username: Имя администратора
            reason: Причина отклонения
        """
        audit_data = {
            "action": "withdraw_rejected",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "amount": amount,
            "admin_username": admin_username,
            "reason": reason,
            "status": WithdrawStatus.REJECTED.value
        }
        
        self.logger.warning(
            f"Withdraw rejected: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_withdraw_completed(
        self, 
        request_id: int, 
        amount: int, 
        admin_username: str,
        transaction_id: Optional[str] = None
    ) -> None:
        """
        Логирование завершения вывода средств.
        
        Args:
            request_id: ID запроса
            amount: Сумма
            admin_username: Имя администратора
            transaction_id: ID транзакции
        """
        audit_data = {
            "action": "withdraw_completed",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "amount": amount,
            "admin_username": admin_username,
            "transaction_id": transaction_id,
            "status": WithdrawStatus.COMPLETED.value
        }
        
        self.logger.info(
            f"Withdraw completed: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_refund_issued(
        self, 
        payment_id: str, 
        amount: int, 
        reason: str,
        admin_username: str,
        user_id: Optional[int] = None
    ) -> None:
        """
        Логирование возврата средств.
        
        Args:
            payment_id: ID платежа
            amount: Сумма возврата
            reason: Причина возврата
            admin_username: Имя администратора
            user_id: ID пользователя
        """
        audit_data = {
            "action": "refund_issued",
            "timestamp": datetime.utcnow().isoformat(),
            "payment_id": payment_id,
            "user_id": user_id,
            "amount": amount,
            "reason": reason,
            "admin_username": admin_username,
            "status": PurchaseStatus.REFUNDED.value
        }
        
        self.logger.warning(
            f"Refund issued: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_suspicious_activity(
        self, 
        activity_type: str, 
        details: Dict[str, Any],
        severity: str = "medium"
    ) -> None:
        """
        Логирование подозрительной активности.
        
        Args:
            activity_type: Тип активности
            details: Детали активности
            severity: Уровень серьезности (low, medium, high, critical)
        """
        audit_data = {
            "action": "suspicious_activity",
            "timestamp": datetime.utcnow().isoformat(),
            "activity_type": activity_type,
            "severity": severity,
            "details": details
        }
        
        log_level = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL
        }.get(severity, logging.WARNING)
        
        self.logger.log(
            log_level,
            f"Suspicious activity: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_admin_action(
        self, 
        admin_username: str, 
        action: str, 
        target: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Логирование действий администратора.
        
        Args:
            admin_username: Имя администратора
            action: Выполненное действие
            target: Объект действия
            details: Дополнительные детали
        """
        audit_data = {
            "action": "admin_action",
            "timestamp": datetime.utcnow().isoformat(),
            "admin_username": admin_username,
            "admin_action": action,
            "target": target,
            "details": details or {}
        }
        
        self.logger.info(
            f"Admin action: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_system_event(
        self, 
        event_type: str, 
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Логирование системных событий.
        
        Args:
            event_type: Тип события
            message: Сообщение
            details: Дополнительные детали
        """
        audit_data = {
            "action": "system_event",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "message": message,
            "details": details or {}
        }
        
        self.logger.info(
            f"System event: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_webhook_received(
        self, 
        webhook_type: str, 
        success: bool,
        payment_id: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Логирование получения webhook.
        
        Args:
            webhook_type: Тип webhook
            success: Успешность обработки
            payment_id: ID платежа
            error: Описание ошибки
        """
        audit_data = {
            "action": "webhook_received",
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_type": webhook_type,
            "success": success,
            "payment_id": payment_id,
            "error": error
        }
        
        log_level = logging.INFO if success else logging.ERROR
        
        self.logger.log(
            log_level,
            f"Webhook received: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_configuration_change(
        self, 
        admin_username: str, 
        setting_name: str,
        old_value: Any, 
        new_value: Any
    ) -> None:
        """
        Логирование изменения конфигурации.
        
        Args:
            admin_username: Имя администратора
            setting_name: Название настройки
            old_value: Старое значение
            new_value: Новое значение
        """
        audit_data = {
            "action": "configuration_change",
            "timestamp": datetime.utcnow().isoformat(),
            "admin_username": admin_username,
            "setting_name": setting_name,
            "old_value": str(old_value),
            "new_value": str(new_value)
        }
        
        self.logger.warning(
            f"Configuration change: {json.dumps(audit_data, ensure_ascii=False)}"
        )
    
    def log_security_event(
        self, 
        event_type: str, 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Логирование событий безопасности.
        
        Args:
            event_type: Тип события безопасности
            ip_address: IP адрес
            user_agent: User Agent
            details: Дополнительные детали
        """
        audit_data = {
            "action": "security_event",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {}
        }
        
        self.logger.critical(
            f"Security event: {json.dumps(audit_data, ensure_ascii=False)}"
        )


# Глобальный экземпляр аудит-логгера
audit_logger = AuditLogger()


# Вспомогательные функции для удобства использования

def log_payment_created(payment_data: Dict[str, Any]) -> None:
    """Упрощенная функция для логирования создания платежа."""
    audit_logger.log_payment_created(payment_data)


def log_payment_completed(payment_id: str, amount: int, user_id: int, telegram_charge_id: Optional[str] = None) -> None:
    """Упрощенная функция для логирования завершения платежа."""
    audit_logger.log_payment_completed(payment_id, amount, user_id, telegram_charge_id)


def log_payment_failed(payment_id: str, error: str, user_id: Optional[int] = None, amount: Optional[int] = None) -> None:
    """Упрощенная функция для логирования неудачного платежа."""
    audit_logger.log_payment_failed(payment_id, error, user_id, amount)


def log_promo_code_used(code: str, user_id: int, discount_amount: int, payment_id: Optional[str] = None) -> None:
    """Упрощенная функция для логирования использования промокода."""
    audit_logger.log_promo_code_used(code, user_id, discount_amount, payment_id)


def log_withdraw_request(amount: int, wallet_address: Optional[str] = None, request_id: Optional[int] = None) -> None:
    """Упрощенная функция для логирования запроса на вывод."""
    audit_logger.log_withdraw_request(amount, wallet_address, request_id)


def log_suspicious_activity(activity_type: str, details: Dict[str, Any], severity: str = "medium") -> None:
    """Упрощенная функция для логирования подозрительной активности."""
    audit_logger.log_suspicious_activity(activity_type, details, severity)


def log_admin_action(admin_username: str, action: str, target: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Упрощенная функция для логирования действий администратора."""
    audit_logger.log_admin_action(admin_username, action, target, details)