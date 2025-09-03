"""
Сервис для управления выводом средств.
Создание заявок, одобрение, обработка выводов средств.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from shared.models import WithdrawRequest, Purchase, AdminUser
from shared.constants import (
    WithdrawStatus, PurchaseStatus, MIN_WITHDRAW_AMOUNT, 
    MAX_WITHDRAW_AMOUNT, COMMISSION_PERCENT
)
from shared.schemas import WithdrawRequestCreate, WithdrawRequestUpdate


class WithdrawService:
    """Сервис для работы с выводом средств."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_withdraw_request(
        self, 
        amount: int, 
        wallet_address: Optional[str] = None,
        notes: Optional[str] = None
    ) -> WithdrawRequest:
        """
        Создание заявки на вывод средств.
        
        Args:
            amount: Сумма для вывода
            wallet_address: Адрес кошелька
            notes: Дополнительные заметки
            
        Returns:
            WithdrawRequest: Созданная заявка
            
        Raises:
            ValueError: При неверных параметрах
        """
        # Валидация суммы
        if amount < MIN_WITHDRAW_AMOUNT:
            raise ValueError(f"Минимальная сумма для вывода: {MIN_WITHDRAW_AMOUNT} Stars")
        
        if amount > MAX_WITHDRAW_AMOUNT:
            raise ValueError(f"Максимальная сумма для вывода: {MAX_WITHDRAW_AMOUNT} Stars")
        
        # Проверка доступности средств
        available_amount = self._calculate_available_amount()
        
        if amount > available_amount:
            raise ValueError(f"Недостаточно средств. Доступно: {available_amount} Stars")
        
        # Создание заявки
        withdraw_request = WithdrawRequest(
            amount=amount,
            status=WithdrawStatus.PENDING.value,
            telegram_wallet_address=wallet_address,
            notes=notes,
            requested_at=datetime.utcnow()
        )
        
        self.db.add(withdraw_request)
        self.db.commit()
        self.db.refresh(withdraw_request)
        
        return withdraw_request
    
    def approve_withdraw(self, request_id: int, admin_id: int, notes: Optional[str] = None) -> bool:
        """
        Одобрение заявки на вывод.
        
        Args:
            request_id: ID заявки
            admin_id: ID администратора
            notes: Заметки администратора
            
        Returns:
            bool: Результат операции
        """
        try:
            withdraw_request = self.get_withdraw_request_by_id(request_id)
            
            if not withdraw_request:
                return False
            
            if withdraw_request.status != WithdrawStatus.PENDING.value:
                return False
            
            # Повторная проверка доступности средств
            available_amount = self._calculate_available_amount()
            
            if withdraw_request.amount > available_amount:
                # Автоматическое отклонение при недостатке средств
                withdraw_request.status = WithdrawStatus.REJECTED.value
                withdraw_request.notes = f"Недостаточно средств. Доступно: {available_amount} Stars"
                withdraw_request.admin_id = admin_id
                withdraw_request.processed_at = datetime.utcnow()
                self.db.commit()
                return False
            
            # Одобрение заявки
            withdraw_request.status = WithdrawStatus.APPROVED.value
            withdraw_request.admin_id = admin_id
            withdraw_request.processed_at = datetime.utcnow()
            
            if notes:
                withdraw_request.notes = notes
            
            self.db.commit()
            
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    def reject_withdraw(self, request_id: int, admin_id: int, reason: str) -> bool:
        """
        Отклонение заявки на вывод.
        
        Args:
            request_id: ID заявки
            admin_id: ID администратора
            reason: Причина отклонения
            
        Returns:
            bool: Результат операции
        """
        try:
            withdraw_request = self.get_withdraw_request_by_id(request_id)
            
            if not withdraw_request:
                return False
            
            if withdraw_request.status != WithdrawStatus.PENDING.value:
                return False
            
            withdraw_request.status = WithdrawStatus.REJECTED.value
            withdraw_request.admin_id = admin_id
            withdraw_request.notes = reason
            withdraw_request.processed_at = datetime.utcnow()
            
            self.db.commit()
            
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    def process_withdraw(self, request_id: int, admin_id: int) -> bool:\n        \"\"\"\n        Обработка (выполнение) вывода средств.\n        \n        Args:\n            request_id: ID заявки\n            admin_id: ID администратора\n            \n        Returns:\n            bool: Результат операции\n        \"\"\"\n        try:\n            withdraw_request = self.get_withdraw_request_by_id(request_id)\n            \n            if not withdraw_request:\n                return False\n            \n            if withdraw_request.status != WithdrawStatus.APPROVED.value:\n                return False\n            \n            # Здесь должна быть интеграция с Telegram Wallet API\n            # Для демонстрации просто меняем статус\n            \n            withdraw_request.status = WithdrawStatus.COMPLETED.value\n            withdraw_request.admin_id = admin_id\n            withdraw_request.processed_at = datetime.utcnow()\n            \n            self.db.commit()\n            \n            return True\n            \n        except Exception:\n            self.db.rollback()\n            return False\n    \n    def get_pending_withdraws(self, limit: Optional[int] = None) -> List[WithdrawRequest]:\n        \"\"\"\n        Получение ожидающих заявок на вывод.\n        \n        Args:\n            limit: Лимит результатов\n            \n        Returns:\n            List[WithdrawRequest]: Список заявок\n        \"\"\"\n        query = self.db.query(WithdrawRequest).filter(\n            WithdrawRequest.status == WithdrawStatus.PENDING.value\n        ).order_by(WithdrawRequest.requested_at)\n        \n        if limit:\n            query = query.limit(limit)\n        \n        return query.all()\n    \n    def get_withdraw_request_by_id(self, request_id: int) -> Optional[WithdrawRequest]:\n        \"\"\"\n        Получение заявки по ID.\n        \n        Args:\n            request_id: ID заявки\n            \n        Returns:\n            Optional[WithdrawRequest]: Заявка или None\n        \"\"\"\n        return self.db.query(WithdrawRequest).filter(\n            WithdrawRequest.id == request_id\n        ).first()\n    \n    def get_withdraw_requests(\n        self, \n        status: Optional[str] = None,\n        limit: Optional[int] = None,\n        offset: Optional[int] = None\n    ) -> List[WithdrawRequest]:\n        \"\"\"\n        Получение списка заявок на вывод.\n        \n        Args:\n            status: Фильтр по статусу\n            limit: Лимит результатов\n            offset: Смещение\n            \n        Returns:\n            List[WithdrawRequest]: Список заявок\n        \"\"\"\n        query = self.db.query(WithdrawRequest)\n        \n        if status:\n            query = query.filter(WithdrawRequest.status == status)\n        \n        query = query.order_by(desc(WithdrawRequest.requested_at))\n        \n        if offset:\n            query = query.offset(offset)\n        \n        if limit:\n            query = query.limit(limit)\n        \n        return query.all()\n    \n    def get_withdraw_statistics(self) -> Dict[str, Any]:\n        \"\"\"\n        Получение статистики по выводам.\n        \n        Returns:\n            Dict: Статистика выводов\n        \"\"\"\n        # Статистика по статусам\n        status_stats = self.db.query(\n            WithdrawRequest.status,\n            func.count(WithdrawRequest.id).label(\"count\"),\n            func.coalesce(func.sum(WithdrawRequest.amount), 0).label(\"total_amount\")\n        ).group_by(WithdrawRequest.status).all()\n        \n        # Общая статистика\n        total_stats = self.db.query(\n            func.count(WithdrawRequest.id).label(\"total_requests\"),\n            func.coalesce(func.sum(WithdrawRequest.amount), 0).label(\"total_amount\")\n        ).first()\n        \n        # Статистика за последние 30 дней\n        thirty_days_ago = datetime.utcnow() - timedelta(days=30)\n        recent_stats = self.db.query(\n            func.count(WithdrawRequest.id).label(\"recent_requests\"),\n            func.coalesce(func.sum(WithdrawRequest.amount), 0).label(\"recent_amount\")\n        ).filter(\n            WithdrawRequest.requested_at >= thirty_days_ago\n        ).first()\n        \n        # Формирование статистики по статусам\n        status_breakdown = {}\n        for stat in status_stats:\n            status_breakdown[stat.status] = {\n                \"count\": stat.count,\n                \"amount\": stat.total_amount\n            }\n        \n        return {\n            \"total_requests\": total_stats.total_requests,\n            \"total_amount\": total_stats.total_amount,\n            \"recent_requests_30d\": recent_stats.recent_requests,\n            \"recent_amount_30d\": recent_stats.recent_amount,\n            \"status_breakdown\": status_breakdown,\n            \"available_amount\": self._calculate_available_amount()\n        }\n    \n    def update_withdraw_request(\n        self, \n        request_id: int, \n        update_data: WithdrawRequestUpdate,\n        admin_id: Optional[int] = None\n    ) -> Optional[WithdrawRequest]:\n        \"\"\"\n        Обновление заявки на вывод.\n        \n        Args:\n            request_id: ID заявки\n            update_data: Данные для обновления\n            admin_id: ID администратора\n            \n        Returns:\n            Optional[WithdrawRequest]: Обновленная заявка\n        \"\"\"\n        withdraw_request = self.get_withdraw_request_by_id(request_id)\n        \n        if not withdraw_request:\n            return None\n        \n        # Обновление полей\n        update_dict = update_data.model_dump(exclude_unset=True)\n        \n        for field, value in update_dict.items():\n            if hasattr(withdraw_request, field):\n                setattr(withdraw_request, field, value)\n        \n        # Обновление информации об администраторе\n        if admin_id:\n            withdraw_request.admin_id = admin_id\n        \n        withdraw_request.updated_at = datetime.utcnow()\n        \n        self.db.commit()\n        self.db.refresh(withdraw_request)\n        \n        return withdraw_request\n    \n    def calculate_withdraw_limits(self) -> Dict[str, int]:\n        \"\"\"\n        Расчет лимитов для вывода.\n        \n        Returns:\n            Dict: Информация о лимитах\n        \"\"\"\n        available_amount = self._calculate_available_amount()\n        \n        return {\n            \"min_withdraw\": MIN_WITHDRAW_AMOUNT,\n            \"max_withdraw\": min(MAX_WITHDRAW_AMOUNT, available_amount),\n            \"available_amount\": available_amount,\n            \"pending_amount\": self._calculate_pending_withdraws()\n        }\n    \n    def get_withdraw_history(\n        self, \n        days: int = 30,\n        status: Optional[str] = None\n    ) -> List[Dict[str, Any]]:\n        \"\"\"\n        Получение истории выводов за период.\n        \n        Args:\n            days: Количество дней для анализа\n            status: Фильтр по статусу\n            \n        Returns:\n            List[Dict]: История выводов\n        \"\"\"\n        start_date = datetime.utcnow() - timedelta(days=days)\n        \n        query = self.db.query(WithdrawRequest).filter(\n            WithdrawRequest.requested_at >= start_date\n        )\n        \n        if status:\n            query = query.filter(WithdrawRequest.status == status)\n        \n        withdraws = query.order_by(desc(WithdrawRequest.requested_at)).all()\n        \n        history = []\n        for withdraw in withdraws:\n            admin_name = None\n            if withdraw.admin_id:\n                admin = self.db.query(AdminUser).filter(\n                    AdminUser.id == withdraw.admin_id\n                ).first()\n                admin_name = admin.username if admin else \"Unknown\"\n            \n            history.append({\n                \"id\": withdraw.id,\n                \"amount\": withdraw.amount,\n                \"status\": withdraw.status,\n                \"requested_at\": withdraw.requested_at.isoformat(),\n                \"processed_at\": withdraw.processed_at.isoformat() if withdraw.processed_at else None,\n                \"admin_name\": admin_name,\n                \"notes\": withdraw.notes,\n                \"wallet_address\": withdraw.telegram_wallet_address\n            })\n        \n        return history\n    \n    def _calculate_available_amount(self) -> int:\n        \"\"\"\n        Расчет доступной суммы для вывода.\n        \n        Returns:\n            int: Доступная сумма\n        \"\"\"\n        # Общий доход\n        total_revenue = self.db.query(\n            func.coalesce(func.sum(Purchase.amount), 0)\n        ).filter(\n            Purchase.status == PurchaseStatus.COMPLETED.value\n        ).scalar() or 0\n        \n        # Уже выведенные средства\n        total_withdraws = self.db.query(\n            func.coalesce(func.sum(WithdrawRequest.amount), 0)\n        ).filter(\n            WithdrawRequest.status.in_([WithdrawStatus.APPROVED.value, WithdrawStatus.COMPLETED.value])\n        ).scalar() or 0\n        \n        # Ожидающие выводы\n        pending_withdraws = self.db.query(\n            func.coalesce(func.sum(WithdrawRequest.amount), 0)\n        ).filter(\n            WithdrawRequest.status == WithdrawStatus.PENDING.value\n        ).scalar() or 0\n        \n        # Комиссия платформы\n        commission = (total_revenue * COMMISSION_PERCENT) // 100\n        \n        # Доступная сумма\n        available = total_revenue - total_withdraws - pending_withdraws - commission\n        \n        return max(0, available)\n    \n    def _calculate_pending_withdraws(self) -> int:\n        \"\"\"\n        Расчет суммы ожидающих выводов.\n        \n        Returns:\n            int: Сумма ожидающих выводов\n        \"\"\"\n        return self.db.query(\n            func.coalesce(func.sum(WithdrawRequest.amount), 0)\n        ).filter(\n            WithdrawRequest.status == WithdrawStatus.PENDING.value\n        ).scalar() or 0\n    \n    def cleanup_old_rejected_requests(self, days: int = 90) -> int:\n        \"\"\"\n        Очистка старых отклоненных заявок.\n        \n        Args:\n            days: Возраст заявок в днях\n            \n        Returns:\n            int: Количество удаленных заявок\n        \"\"\"\n        cutoff_date = datetime.utcnow() - timedelta(days=days)\n        \n        old_requests = self.db.query(WithdrawRequest).filter(\n            and_(\n                WithdrawRequest.status == WithdrawStatus.REJECTED.value,\n                WithdrawRequest.processed_at < cutoff_date\n            )\n        ).all()\n        \n        for request in old_requests:\n            self.db.delete(request)\n        \n        self.db.commit()\n        \n        return len(old_requests)