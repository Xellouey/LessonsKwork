"""
Состояния пользователей в Telegram боте.
Определяет различные состояния и переходы между ними.
"""

from enum import Enum
from typing import Dict, Any, Optional, NamedTuple


class BotState(str, Enum):
    """Перечисление состояний бота."""
    
    # Основные состояния
    MAIN_MENU = "main_menu"
    BROWSE_LESSONS = "browse_lessons"
    VIEW_LESSON = "view_lesson"
    MY_LESSONS = "my_lessons"
    
    # Настройки
    LANGUAGE_SELECTION = "language_selection"
    SETTINGS = "settings"
    
    # Платежи и покупки
    PAYMENT_PROCESS = "payment_process"
    PROMO_CODE_INPUT = "promo_code_input"
    PAYMENT_CONFIRMATION = "payment_confirmation"
    
    # Поддержка
    SUPPORT_CONTACT = "support_contact"
    SUPPORT_MESSAGE_INPUT = "support_message_input"
    
    # Админские функции (если пользователь админ)
    ADMIN_PANEL = "admin_panel"
    ADMIN_BROADCAST = "admin_broadcast"
    
    # Специальные состояния
    WAITING_FOR_INPUT = "waiting_for_input"
    ERROR_STATE = "error_state"


class StateTransition(NamedTuple):
    """Переход между состояниями."""
    from_state: BotState
    to_state: BotState
    trigger: str
    condition: Optional[str] = None


class UserStateData:
    """Данные пользователя в текущем состоянии."""
    
    def __init__(self, state: BotState = BotState.MAIN_MENU, data: Optional[Dict[str, Any]] = None):
        self.state = state
        self.data = data or {}
        self.previous_state: Optional[BotState] = None
    
    def set_state(self, new_state: BotState, preserve_data: bool = False):
        """Установить новое состояние."""
        self.previous_state = self.state
        self.state = new_state
        
        if not preserve_data:
            self.data = {}
    
    def set_data(self, key: str, value: Any):
        """Установить данные."""
        self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Получить данные."""
        return self.data.get(key, default)
    
    def clear_data(self):
        """Очистить данные состояния."""
        self.data = {}
    
    def go_back(self) -> Optional[BotState]:
        """Вернуться к предыдущему состоянию."""
        if self.previous_state:
            prev = self.previous_state
            self.previous_state = self.state
            self.state = prev
            return prev
        return None
    
    def to_dict(self) -> dict:
        """Конвертировать в словарь для сериализации."""
        return {
            'state': self.state.value,
            'data': self.data,
            'previous_state': self.previous_state.value if self.previous_state else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserStateData':
        """Создать из словаря."""
        instance = cls(
            state=BotState(data.get('state', BotState.MAIN_MENU.value)),
            data=data.get('data', {})
        )
        
        prev_state = data.get('previous_state')
        if prev_state:
            instance.previous_state = BotState(prev_state)
        
        return instance


# Определение возможных переходов между состояниями
ALLOWED_TRANSITIONS = [
    # Из главного меню
    StateTransition(BotState.MAIN_MENU, BotState.BROWSE_LESSONS, "browse_lessons"),
    StateTransition(BotState.MAIN_MENU, BotState.MY_LESSONS, "my_lessons"),
    StateTransition(BotState.MAIN_MENU, BotState.SUPPORT_CONTACT, "support"),
    StateTransition(BotState.MAIN_MENU, BotState.LANGUAGE_SELECTION, "language"),
    StateTransition(BotState.MAIN_MENU, BotState.SETTINGS, "settings"),
    
    # Из каталога уроков
    StateTransition(BotState.BROWSE_LESSONS, BotState.VIEW_LESSON, "select_lesson"),
    StateTransition(BotState.BROWSE_LESSONS, BotState.MAIN_MENU, "back_to_menu"),
    
    # Из просмотра урока
    StateTransition(BotState.VIEW_LESSON, BotState.PAYMENT_PROCESS, "buy_lesson"),
    StateTransition(BotState.VIEW_LESSON, BotState.BROWSE_LESSONS, "back_to_catalog"),
    StateTransition(BotState.VIEW_LESSON, BotState.MAIN_MENU, "back_to_menu"),
    
    # Процесс покупки
    StateTransition(BotState.PAYMENT_PROCESS, BotState.PROMO_CODE_INPUT, "enter_promo"),
    StateTransition(BotState.PAYMENT_PROCESS, BotState.PAYMENT_CONFIRMATION, "confirm_payment"),
    StateTransition(BotState.PROMO_CODE_INPUT, BotState.PAYMENT_CONFIRMATION, "promo_entered"),
    StateTransition(BotState.PAYMENT_CONFIRMATION, BotState.MY_LESSONS, "payment_success"),
    StateTransition(BotState.PAYMENT_CONFIRMATION, BotState.VIEW_LESSON, "payment_failed"),
    
    # Мои уроки
    StateTransition(BotState.MY_LESSONS, BotState.VIEW_LESSON, "view_purchased_lesson"),
    StateTransition(BotState.MY_LESSONS, BotState.MAIN_MENU, "back_to_menu"),
    
    # Поддержка
    StateTransition(BotState.SUPPORT_CONTACT, BotState.SUPPORT_MESSAGE_INPUT, "send_message"),
    StateTransition(BotState.SUPPORT_MESSAGE_INPUT, BotState.MAIN_MENU, "message_sent"),
    
    # Настройки
    StateTransition(BotState.LANGUAGE_SELECTION, BotState.MAIN_MENU, "language_selected"),
    StateTransition(BotState.SETTINGS, BotState.MAIN_MENU, "back_to_menu"),
    
    # Универсальные переходы
    StateTransition(BotState.ERROR_STATE, BotState.MAIN_MENU, "reset"),
]


def get_allowed_transitions(from_state: BotState) -> list[StateTransition]:
    """Получить разрешенные переходы из состояния."""
    return [t for t in ALLOWED_TRANSITIONS if t.from_state == from_state]


def can_transition(from_state: BotState, to_state: BotState, trigger: str) -> bool:
    """Проверить, возможен ли переход между состояниями."""
    for transition in ALLOWED_TRANSITIONS:
        if (transition.from_state == from_state and 
            transition.to_state == to_state and 
            transition.trigger == trigger):
            return True
    return False


def get_next_state(current_state: BotState, trigger: str) -> Optional[BotState]:
    """Получить следующее состояние по триггеру."""
    for transition in ALLOWED_TRANSITIONS:
        if transition.from_state == current_state and transition.trigger == trigger:
            return transition.to_state
    return None


class StateContext:
    """Контекст для передачи данных между состояниями."""
    
    def __init__(self):
        self.lesson_id: Optional[int] = None
        self.course_id: Optional[int] = None
        self.payment_id: Optional[str] = None
        self.promo_code: Optional[str] = None
        self.selected_language: Optional[str] = None
        self.support_message: Optional[str] = None
        self.current_page: int = 1
        self.search_query: Optional[str] = None
    
    def clear(self):
        """Очистить контекст."""
        self.__init__()
    
    def to_dict(self) -> dict:
        """Конвертировать в словарь."""
        return {
            key: value for key, value in self.__dict__.items() 
            if value is not None
        }