"""
Тесты для основных обработчиков бота.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Chat, Message, CallbackQuery
from telegram.ext import ContextTypes

from bot.handlers.main_handlers import MainHandlers
from bot.utils.state_manager import StateManager
from bot.states.user_states import BotState


@pytest.fixture
def state_manager():
    """Создать тестовый менеджер состояний."""
    return StateManager(use_redis=False)


@pytest.fixture
def main_handlers(state_manager):
    """Создать тестовые основные обработчики."""
    return MainHandlers(state_manager)


@pytest.fixture
def mock_user():
    """Создать тестового пользователя."""
    return User(
        id=12345,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
        language_code="en"
    )


@pytest.fixture
def mock_chat():
    """Создать тестовый чат."""
    return Chat(id=12345, type="private")


@pytest.fixture
def mock_context():
    """Создать тестовый контекст."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    return context


class TestMainHandlers:
    """Тесты для основных обработчиков."""
    
    @pytest.mark.asyncio
    async def test_start_command_new_user(self, main_handlers, mock_user, mock_chat, mock_context):
        """Тест команды /start для нового пользователя."""
        # Подготовка
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()
        
        update = MagicMock(spec=Update)
        update.effective_user = mock_user
        update.effective_chat = mock_chat
        update.message = message
        
        # Mock API клиента
        with patch.object(main_handlers, 'api_client') as mock_api:
            mock_api.create_or_find_user = AsyncMock(return_value={
                'id': 1,
                'telegram_id': mock_user.id,
                'first_name': mock_user.first_name
            })
            
            # Выполнение
            await main_handlers.start_command(update, mock_context)
            
            # Проверки
            mock_api.create_or_find_user.assert_called_once()
            message.reply_text.assert_called_once()
            
            # Проверить, что состояние установлено
            state, _ = main_handlers.state_manager.get_user_state(mock_user.id)
            assert state == BotState.MAIN_MENU
    
    @pytest.mark.asyncio
    async def test_main_menu_callback_browse_lessons(self, main_handlers, mock_user, mock_context):
        """Тест коллбэка перехода к каталогу уроков."""
        # Подготовка
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = "menu:browse_lessons"
        
        update = MagicMock(spec=Update)
        update.effective_user = mock_user
        update.callback_query = query
        
        # Mock API клиента
        with patch.object(main_handlers, 'api_client') as mock_api:
            mock_api.get_public_lessons = AsyncMock(return_value={
                'items': [
                    {
                        'id': 1,
                        'title': 'Test Lesson',
                        'price': 100,
                        'is_free': False
                    }
                ],
                'pages': 1
            })
            
            # Выполнение
            await main_handlers.main_menu_callback(update, mock_context)
            
            # Проверки
            query.answer.assert_called_once()
            query.edit_message_text.assert_called_once()
            mock_api.get_public_lessons.assert_called_once()
            
            # Проверить состояние
            state, _ = main_handlers.state_manager.get_user_state(mock_user.id)
            assert state == BotState.BROWSE_LESSONS
    
    @pytest.mark.asyncio
    async def test_main_menu_callback_my_lessons_empty(self, main_handlers, mock_user, mock_context):
        """Тест коллбэка "Мои уроки" для пользователя без покупок."""
        # Подготовка
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = "menu:my_lessons"
        
        update = MagicMock(spec=Update)
        update.effective_user = mock_user
        update.callback_query = query
        
        # Mock API клиента
        with patch.object(main_handlers, 'api_client') as mock_api:
            mock_api.get_user_purchases = AsyncMock(return_value=[])
            
            # Выполнение
            await main_handlers.main_menu_callback(update, mock_context)
            
            # Проверки
            query.answer.assert_called_once()
            query.edit_message_text.assert_called_once()
            
            # Проверить, что показано сообщение о пустом списке
            call_args = query.edit_message_text.call_args
            assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_language_callback(self, main_handlers, mock_user, mock_context):
        """Тест смены языка."""
        # Подготовка
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = "language:set:ru"
        
        update = MagicMock(spec=Update)
        update.effective_user = mock_user
        update.callback_query = query
        
        # Mock i18n
        with patch('bot.handlers.main_handlers.i18n') as mock_i18n:
            mock_i18n.set_user_language = AsyncMock(return_value=True)
            
            # Выполнение
            await main_handlers.language_callback(update, mock_context)
            
            # Проверки
            query.answer.assert_called_once()
            query.edit_message_text.assert_called_once()
            mock_i18n.set_user_language.assert_called_once_with(mock_user.id, "ru")


class TestStateManager:
    """Тесты для менеджера состояний."""
    
    def test_set_and_get_user_state(self, state_manager):
        """Тест установки и получения состояния пользователя."""
        user_id = 12345
        
        # Установить состояние
        state_manager.set_user_state(user_id, BotState.BROWSE_LESSONS, {'page': 1})
        
        # Получить состояние
        state, data = state_manager.get_user_state(user_id)
        
        assert state == BotState.BROWSE_LESSONS
        assert data.get('page') == 1
    
    def test_update_user_data(self, state_manager):
        """Тест обновления данных пользователя."""
        user_id = 12345
        
        # Установить начальное состояние
        state_manager.set_user_state(user_id, BotState.PAYMENT_PROCESS)
        
        # Обновить данные
        state_manager.update_user_data(user_id, 'lesson_id', 42)
        state_manager.update_user_data(user_id, 'price', 100)
        
        # Проверить данные
        lesson_id = state_manager.get_user_data(user_id, 'lesson_id')
        price = state_manager.get_user_data(user_id, 'price')
        
        assert lesson_id == 42
        assert price == 100
    
    def test_clear_user_state(self, state_manager):
        """Тест очистки состояния пользователя."""
        user_id = 12345
        
        # Установить состояние
        state_manager.set_user_state(user_id, BotState.PAYMENT_PROCESS, {'test': 'data'})
        
        # Очистить состояние
        state_manager.clear_user_state(user_id)
        
        # Проверить, что состояние сброшено
        state, data = state_manager.get_user_state(user_id)
        assert state == BotState.MAIN_MENU  # По умолчанию
        assert data == {}
    
    def test_go_back(self, state_manager):
        """Тест возврата к предыдущему состоянию."""
        user_id = 12345
        
        # Установить начальное состояние
        state_manager.set_user_state(user_id, BotState.MAIN_MENU)
        
        # Перейти в другое состояние
        state_manager.set_user_state(user_id, BotState.BROWSE_LESSONS)
        
        # Вернуться назад
        previous_state = state_manager.go_back(user_id)
        
        assert previous_state == BotState.MAIN_MENU
        
        # Проверить текущее состояние
        current_state, _ = state_manager.get_user_state(user_id)
        assert current_state == BotState.MAIN_MENU