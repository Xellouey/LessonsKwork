"""
Менеджер состояний пользователей.
Управление состояниями, переходами и данными пользователей.
"""

import json
import logging
from typing import Dict, Optional, Any, Tuple

from bot.states.user_states import BotState, UserStateData, StateContext


logger = logging.getLogger(__name__)


class StateManager:
    """Менеджер состояний пользователей."""
    
    def __init__(self, use_redis: bool = False, redis_url: Optional[str] = None):
        self.use_redis = use_redis
        self.redis_client = None
        self._memory_storage: Dict[int, UserStateData] = {}
        
        if use_redis:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url or "redis://localhost:6379")
                self.redis_client.ping()
                logger.info("✅ Connected to Redis for state management")
            except Exception as e:
                logger.warning(f"⚠️ Failed to connect to Redis: {e}. Using memory storage.")
                self.use_redis = False
    
    def get_user_state(self, user_id: int) -> Tuple[BotState, Dict[str, Any]]:
        """
        Получить текущее состояние пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple[BotState, Dict[str, Any]]: Состояние и данные пользователя
        """
        try:
            state_data = self._get_state_data(user_id)
            return state_data.state, state_data.data
        except Exception as e:
            logger.error(f"Error getting user state for {user_id}: {e}")
            return BotState.MAIN_MENU, {}
    
    def set_user_state(self, user_id: int, state: BotState, data: Optional[Dict[str, Any]] = None):
        """
        Установить состояние пользователя.
        
        Args:
            user_id: ID пользователя
            state: Новое состояние
            data: Данные состояния
        """
        try:
            state_data = self._get_state_data(user_id)
            state_data.set_state(state)
            
            if data:
                state_data.data.update(data)
            
            self._save_state_data(user_id, state_data)
            
            logger.debug(f"Set state for user {user_id}: {state.value}")
        except Exception as e:
            logger.error(f"Error setting user state for {user_id}: {e}")
    
    def update_user_data(self, user_id: int, key: str, value: Any):
        """
        Обновить данные пользователя в текущем состоянии.
        
        Args:
            user_id: ID пользователя
            key: Ключ данных
            value: Значение
        """
        try:
            state_data = self._get_state_data(user_id)
            state_data.set_data(key, value)
            self._save_state_data(user_id, state_data)
            
            logger.debug(f"Updated data for user {user_id}: {key} = {value}")
        except Exception as e:
            logger.error(f"Error updating user data for {user_id}: {e}")
    
    def get_user_data(self, user_id: int, key: str, default: Any = None) -> Any:
        """
        Получить данные пользователя.
        
        Args:
            user_id: ID пользователя
            key: Ключ данных
            default: Значение по умолчанию
            
        Returns:
            Any: Значение данных или default
        """
        try:
            state_data = self._get_state_data(user_id)
            return state_data.get_data(key, default)
        except Exception as e:
            logger.error(f"Error getting user data for {user_id}: {e}")
            return default
    
    def clear_user_state(self, user_id: int):
        """
        Очистить состояние пользователя.
        
        Args:
            user_id: ID пользователя
        """
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.delete(f"user_state:{user_id}")
            else:
                self._memory_storage.pop(user_id, None)
            
            logger.debug(f"Cleared state for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing user state for {user_id}: {e}")
    
    def go_back(self, user_id: int) -> Optional[BotState]:
        """
        Вернуть пользователя к предыдущему состоянию.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[BotState]: Предыдущее состояние или None
        """
        try:
            state_data = self._get_state_data(user_id)
            previous_state = state_data.go_back()
            
            if previous_state:
                self._save_state_data(user_id, state_data)
                logger.debug(f"User {user_id} went back to {previous_state.value}")
            
            return previous_state
        except Exception as e:
            logger.error(f"Error going back for user {user_id}: {e}")
            return None
    
    def create_context(self, user_id: int) -> StateContext:
        """
        Создать контекст состояния для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            StateContext: Контекст состояния
        """
        context = StateContext()
        _, data = self.get_user_state(user_id)
        
        # Загрузить данные в контекст
        context.lesson_id = data.get('lesson_id')
        context.course_id = data.get('course_id')
        context.payment_id = data.get('payment_id')
        context.promo_code = data.get('promo_code')
        context.selected_language = data.get('selected_language')
        context.support_message = data.get('support_message')
        context.current_page = data.get('current_page', 1)
        context.search_query = data.get('search_query')
        
        return context
    
    def save_context(self, user_id: int, context: StateContext):
        """
        Сохранить контекст в состояние пользователя.
        
        Args:
            user_id: ID пользователя
            context: Контекст состояния
        """
        context_data = context.to_dict()
        
        for key, value in context_data.items():
            self.update_user_data(user_id, key, value)
    
    def get_all_users_in_state(self, state: BotState) -> list[int]:
        """
        Получить всех пользователей в определенном состоянии.
        
        Args:
            state: Состояние для поиска
            
        Returns:
            list[int]: Список ID пользователей
        """
        users = []
        
        try:
            if self.use_redis and self.redis_client:
                # Поиск в Redis
                keys = self.redis_client.keys("user_state:*")
                for key in keys:
                    try:
                        user_id = int(key.decode().split(":")[1])
                        user_state, _ = self.get_user_state(user_id)
                        if user_state == state:
                            users.append(user_id)
                    except (ValueError, IndexError):
                        continue
            else:
                # Поиск в памяти
                for user_id, state_data in self._memory_storage.items():
                    if state_data.state == state:
                        users.append(user_id)
        except Exception as e:
            logger.error(f"Error getting users in state {state}: {e}")
        
        return users
    
    def _get_state_data(self, user_id: int) -> UserStateData:
        """Получить объект данных состояния пользователя."""
        if self.use_redis and self.redis_client:
            # Получение из Redis
            try:
                data = self.redis_client.get(f"user_state:{user_id}")
                if data:
                    return UserStateData.from_dict(json.loads(data.decode()))
            except Exception as e:
                logger.error(f"Error reading from Redis for user {user_id}: {e}")
        
        # Получение из памяти или создание нового
        return self._memory_storage.get(user_id, UserStateData())
    
    def _save_state_data(self, user_id: int, state_data: UserStateData):
        """Сохранить данные состояния пользователя."""
        if self.use_redis and self.redis_client:
            # Сохранение в Redis
            try:
                data = json.dumps(state_data.to_dict())
                self.redis_client.setex(f"user_state:{user_id}", 86400, data)  # TTL 24 часа
            except Exception as e:
                logger.error(f"Error saving to Redis for user {user_id}: {e}")
                # Fallback к памяти
                self._memory_storage[user_id] = state_data
        else:
            # Сохранение в памяти
            self._memory_storage[user_id] = state_data
    
    def cleanup_expired_states(self):
        """Очистить устаревшие состояния (только для памяти)."""
        if not self.use_redis:
            # В памяти состояния не истекают автоматически
            # Можно реализовать логику по времени, если необходимо
            pass
    
    def get_statistics(self) -> dict:
        """
        Получить статистику состояний пользователей.
        
        Returns:
            dict: Статистика по состояниям
        """
        stats = {}
        
        try:
            if self.use_redis and self.redis_client:
                keys = self.redis_client.keys("user_state:*")
                total_users = len(keys)
                
                state_counts = {}
                for key in keys:
                    try:
                        user_id = int(key.decode().split(":")[1])
                        state, _ = self.get_user_state(user_id)
                        state_counts[state.value] = state_counts.get(state.value, 0) + 1
                    except (ValueError, IndexError):
                        continue
                
                stats = {
                    'total_users': total_users,
                    'states': state_counts,
                    'storage': 'redis'
                }
            else:
                total_users = len(self._memory_storage)
                state_counts = {}
                
                for state_data in self._memory_storage.values():
                    state_counts[state_data.state.value] = state_counts.get(state_data.state.value, 0) + 1
                
                stats = {
                    'total_users': total_users,
                    'states': state_counts,
                    'storage': 'memory'
                }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            stats = {'error': str(e)}
        
        return stats