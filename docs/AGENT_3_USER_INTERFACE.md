# ФАЗА 2: User Interface Development

## Контекст задачи
Вы - Agent 3, ответственный за создание пользовательского интерфейса Telegram бота, многоязычность и все пользовательские сценарии взаимодействия. Ваша работа начинается после завершения Agent 1 (Backend Core).

## Предварительные требования
✅ Agent 1 завершил работу - Backend API доступен  
✅ Agent 2 завершил работу - Платежная система готова  
✅ Документация `BACKEND_CORE_COMPLETE.md` изучена  
✅ Документация `PAYMENT_FINANCE_COMPLETE.md` изучена  
✅ API endpoints для пользователей, уроков и платежей работают  

## Цель
Создать полнофункциональный Telegram Bot с интуитивным интерфейсом, поддержкой многоязычности, каталогом уроков, личным кабинетом и интеграцией с платежной системой.

## Технические требования

### Основные технологии
- **python-telegram-bot**: главная библиотека для бота
- **SQLAlchemy**: для работы с пользователями (через API)
- **aiofiles**: для работы с медиафайлами
- **Babel**: для интернационализации
- **Redis**: для хранения состояний пользователей (опционально)

### Дополнительные переменные окружения (.env)
```env
# Добавить к существующему .env файлу
TELEGRAM_BOT_TOKEN=your-bot-token-here
BOT_USERNAME=your_bot_username
DEFAULT_LANGUAGE=en
SUPPORTED_LANGUAGES=en,ru,es,fr
MEDIA_STORAGE_PATH=./storage
FREE_LESSON_ID=1
ADMIN_CHAT_ID=your-telegram-admin-id
ERROR_LOG_CHAT_ID=your-error-log-chat-id
```

## Пошаговый план разработки

### Шаг 1: Изучение существующей архитектуры (30 мин)
1. Изучить документацию от Agent 1 и Agent 2
2. Протестировать API endpoints:
   - Создание пользователя: `POST /api/users/`
   - Получение уроков: `GET /api/lessons/`
   - Создание платежа: `POST /api/payments/create`
3. Понять структуру моделей и платежных процессов

### Шаг 2: Архитектура бота и состояния (45 мин)

#### Создать `bot/states/user_states.py`:
```python
from enum import Enum

class BotState(Enum):
    MAIN_MENU = "main_menu"
    BROWSE_LESSONS = "browse_lessons"
    VIEW_LESSON = "view_lesson"
    MY_LESSONS = "my_lessons"
    LANGUAGE_SELECTION = "language_selection"
    PAYMENT_PROCESS = "payment_process"
    SUPPORT_CONTACT = "support_contact"
    PROMO_CODE_INPUT = "promo_code_input"
```

#### Создать `bot/utils/state_manager.py`:
```python
class StateManager:
    def set_user_state(self, user_id: int, state: BotState, data: dict = None)
    def get_user_state(self, user_id: int) -> tuple[BotState, dict]
    def clear_user_state(self, user_id: int)
    def update_user_data(self, user_id: int, key: str, value: any)
```

### Шаг 3: Система многоязычности (60 мин)

#### Создать структуру локализации в `bot/locales/`:
```
bot/locales/
├── en/
│   └── messages.json
├── ru/
│   └── messages.json
├── es/
│   └── messages.json
└── fr/
    └── messages.json
```

#### Создать `bot/locales/en/messages.json`:
```json
{
  "welcome": "🎓 Welcome to Lessons Bot!\n\nHere you can purchase and view educational video lessons.\n\nChoose an action:",
  "main_menu": {
    "browse_lessons": "📚 Browse Lessons",
    "my_lessons": "👤 My Lessons",
    "support": "🆘 Support",
    "language": "🌐 Language"
  },
  "lessons": {
    "catalog_title": "📚 Lessons Catalog",
    "price": "💰 Price: {price} ⭐",
    "buy_button": "💳 Buy for {price} ⭐",
    "free_lesson": "🎁 Free Lesson",
    "view_lesson": "👁️ View Lesson"
  },
  "payments": {
    "processing": "⏳ Processing payment...",
    "success": "✅ Payment successful! Lesson added to 'My Lessons'",
    "failed": "❌ Payment failed. Please try again.",
    "promo_code": "🎫 Enter promo code (optional):",
    "promo_applied": "🎉 Promo code applied! Discount: {discount}%"
  },
  "my_lessons": {
    "title": "👤 My Lessons",
    "empty": "📭 You haven't purchased any lessons yet.\n\nBrowse our catalog to find interesting content!",
    "lesson_item": "📖 {title}"
  },
  "support": {
    "contact": "📞 Contact Support",
    "message": "💬 Send Message to Admin"
  }
}
```

#### Создать `bot/utils/i18n.py`:
```python
class Internationalization:
    def __init__(self):
        self.translations = {}
        self.load_translations()
    
    def load_translations(self)
    def get_text(self, key: str, lang: str = "en", **kwargs) -> str
    def get_user_language(self, user_id: int) -> str
    def set_user_language(self, user_id: int, language: str)
    def get_available_languages(self) -> list
```

### Шаг 4: Клавиатуры и интерфейс (45 мин)

#### Создать `bot/keyboards/main_keyboards.py`:
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class MainKeyboards:
    @staticmethod
    def main_menu(lang: str = "en") -> InlineKeyboardMarkup:
        # Главное меню с кнопками
    
    @staticmethod
    def lessons_catalog(lessons: list, page: int = 1, lang: str = "en") -> InlineKeyboardMarkup:
        # Каталог уроков с пагинацией
    
    @staticmethod
    def lesson_detail(lesson: dict, user_purchased: bool, lang: str = "en") -> InlineKeyboardMarkup:
        # Детали урока с кнопкой покупки
    
    @staticmethod
    def my_lessons(lessons: list, page: int = 1, lang: str = "en") -> InlineKeyboardMarkup:
        # Мои уроки
    
    @staticmethod
    def language_selection() -> InlineKeyboardMarkup:
        # Выбор языка
    
    @staticmethod
    def payment_confirmation(lesson: dict, final_price: int, lang: str = "en") -> InlineKeyboardMarkup:
        # Подтверждение платежа
```

### Шаг 5: Основные обработчики команд (90 мин)

#### Создать `bot/handlers/main_handlers.py`:
```python
class MainHandlers:
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Команда /start - регистрация пользователя и главное меню
    
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Обработка кнопок главного меню
    
    async def browse_lessons_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Просмотр каталога уроков
    
    async def lesson_detail_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Детали конкретного урока
    
    async def my_lessons_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Мои уроки пользователя
    
    async def language_selection_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Выбор языка интерфейса
```

#### Создать `bot/handlers/lesson_handlers.py`:
```python
class LessonHandlers:
    async def view_purchased_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Просмотр купленного урока
    
    async def send_lesson_content(self, user_id: int, lesson_id: int):
        # Отправка контента урока (видео + текст)
    
    async def handle_free_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Обработка бесплатного лид-магнита
    
    async def search_lessons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Поиск уроков по названию
```

### Шаг 6: Интеграция с платежной системой (75 мин)

#### Создать `bot/handlers/payment_handlers.py`:
```python
class PaymentHandlers:
    async def initiate_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Инициация платежа за урок
    
    async def handle_promo_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Обработка ввода промокода
    
    async def create_invoice(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int, promo_code: str = None):
        # Создание инвойса для Telegram Stars
    
    async def pre_checkout_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Обработка pre_checkout_query
    
    async def successful_payment_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Обработка успешного платежа
```

#### Интеграция с API платежей:
```python
class PaymentAPIClient:
    async def create_payment(self, user_id: int, lesson_id: int, promo_code: str = None) -> dict:
        # Создание платежа через API Agent 2
    
    async def verify_payment(self, payment_id: str) -> bool:
        # Верификация платежа
    
    async def get_user_purchases(self, user_id: int) -> list:
        # Получение покупок пользователя
```

### Шаг 7: Файловое хранилище и контент (45 мин)

#### Создать `bot/utils/content_manager.py`:
```python
class ContentManager:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
    
    async def store_lesson_video(self, lesson_id: int, video_data: bytes) -> str:
        # Сохранение видео урока
    
    async def store_lesson_text(self, lesson_id: int, text_content: str) -> str:
        # Сохранение текстового контента
    
    async def get_lesson_content(self, lesson_id: int) -> dict:
        # Получение контента урока
    
    async def send_video_to_user(self, bot, user_id: int, video_path: str, caption: str = None):
        # Отправка видео пользователю
    
    async def send_text_to_user(self, bot, user_id: int, text_content: str):
        # Отправка текста пользователю
```

### Шаг 8: Система поддержки и обратной связи (30 мин)

**🧠 Sequential Thinking для:**
- Проектирования интуитивного support flow
- Анализа частых проблем пользователей

**📚 Context7 для поиска:**
- Customer support bot implementations
- Automated response systems

#### Создать `bot/handlers/support_handlers.py`:
```python
class SupportHandlers:
    async def contact_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Связь с поддержкой
    
    async def send_message_to_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Отправка сообщения администратору
    
    async def handle_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Обработка сообщений пользователей
    
    async def admin_reply_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Ответы администратора пользователям
```

### Шаг 9: Основной файл бота (30 мин)

#### Создать `bot/main.py`:
```python
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler

def setup_handlers(app: Application):
    # Настройка всех обработчиков
    app.add_handler(CommandHandler("start", MainHandlers().start_command))
    app.add_handler(CallbackQueryHandler(MainHandlers().main_menu_callback, pattern="^main_menu"))
    app.add_handler(CallbackQueryHandler(LessonHandlers().view_lesson, pattern="^lesson_"))
    app.add_handler(PreCheckoutQueryHandler(PaymentHandlers().pre_checkout_query_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, PaymentHandlers().successful_payment_handler))

async def main():
    # Главная функция запуска бота
    app = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(app)
    await app.run_polling()
```

### Шаг 10: Тестирование интерфейса (60 мин)

**🧠 Sequential Thinking для:**
- Планирования comprehensive testing strategy
- Анализа edge cases и error scenarios
- Проектирования user acceptance tests

**📚 Context7 для поиска:**
- Telegram bot testing frameworks
- Automated testing strategies for bots
- User interface testing best practices

#### Создать тесты в `bot/tests/`:
- `test_main_handlers.py` - тесты основных обработчиков
- `test_payment_flow.py` - тесты платежного процесса
- `test_i18n.py` - тесты многоязычности
- `test_content_manager.py` - тесты работы с контентом

## Структура файлов для создания

```
bot/
├── main.py                   # Основной файл бота
├── config.py                 # Конфигурация бота
├── handlers/
│   ├── __init__.py
│   ├── main_handlers.py      # Основные обработчики
│   ├── lesson_handlers.py    # Обработчики уроков
│   ├── payment_handlers.py   # Обработчики платежей
│   └── support_handlers.py   # Обработчики поддержки
├── keyboards/
│   ├── __init__.py
│   └── main_keyboards.py     # Клавиатуры интерфейса
├── states/
│   ├── __init__.py
│   └── user_states.py        # Состояния пользователей
├── utils/
│   ├── __init__.py
│   ├── i18n.py              # Интернационализация
│   ├── state_manager.py     # Управление состояниями
│   ├── content_manager.py   # Управление контентом
│   └── api_client.py        # Клиент для Backend API
├── locales/
│   ├── en/messages.json     # Английские тексты
│   ├── ru/messages.json     # Русские тексты
│   ├── es/messages.json     # Испанские тексты
│   └── fr/messages.json     # Французские тексты
└── tests/
    ├── test_main_handlers.py
    ├── test_payment_flow.py
    ├── test_i18n.py
    └── test_content_manager.py

storage/
├── videos/                   # Видео уроков
├── texts/                    # Текстовые материалы
└── temp/                     # Временные файлы
```

## Критерии готовности

### Обязательные требования:
✅ Telegram Bot запускается и отвечает на команды  
✅ Многоязычность работает корректно (минимум EN, RU)  
✅ Каталог уроков отображается с пагинацией  
✅ Покупка уроков через Telegram Stars работает  
✅ Личный кабинет "Мои уроки" функционирует  
✅ Бесплатный лид-магнит доступен всем пользователям  
✅ Система поддержки принимает сообщения  
✅ Промокоды применяются корректно  
✅ Контент доставляется только купившим  
✅ Все состояния пользователей управляются корректно  

### Проверка готовности:
```bash
# Запуск бота
cd bot/
python main.py

# Тестирование команд в Telegram:
# /start - должно показать главное меню
# Кнопка "Browse Lessons" - должен показать каталог
# Покупка урока - должен создать инвойс
# "My Lessons" - должен показать купленные уроки

# Запуск тестов
pytest bot/tests/ -v --cov=bot
```

## Формат документации для других агентов

После завершения создайте `docs/agents/USER_INTERFACE_COMPLETE.md`:

### Раздел 1: Реализованная функциональность
- Полное описание пользовательского интерфейса
- Схема состояний и переходов пользователя
- Список поддерживаемых языков
- Примеры диалогов с ботом

### Раздел 2: Интеграция с Backend API
```python
# Примеры использования API в боте
# Создание нового пользователя
user_data = {
    "telegram_id": update.effective_user.id,
    "username": update.effective_user.username,
    "first_name": update.effective_user.first_name,
    "language_code": update.effective_user.language_code
}
requests.post("http://localhost:8000/api/users/", json=user_data)

# Получение покупок пользователя
purchases = requests.get(f"http://localhost:8000/api/users/{user_id}/purchases")
```

### Раздел 3: Система контента и файлов
```python
# Структура хранения файлов
STORAGE_STRUCTURE = {
    "videos": "./storage/videos/{lesson_id}/",
    "texts": "./storage/texts/{lesson_id}/",
    "thumbnails": "./storage/thumbnails/{lesson_id}/"
}

# Формат метаданных урока
LESSON_METADATA = {
    "video_duration": "duration in seconds",
    "file_size": "size in bytes", 
    "quality": "720p/1080p",
    "format": "mp4/mov"
}
```

### Раздел 4: Пользовательские сценарии
1. **Новый пользователь**: /start → выбор языка → бесплатный урок → каталог
2. **Покупка урока**: каталог → детали урока → ввод промокода → оплата → доступ
3. **Просмотр купленного**: мои уроки → выбор урока → просмотр контента
4. **Поддержка**: поддержка → сообщение админу → ответ от админа

### Раздел 5: Конфигурация для других агентов

#### Для Agent 4 (Administration):
```python
# Интерфейс для управления контентом
ADMIN_INTEGRATION = {
    "content_upload_endpoint": "/admin/upload-lesson",
    "user_management": "/admin/users",
    "analytics_data": "/admin/bot-analytics"
}
```

#### Для Agent 5 (Communication):
```python
# Интерфейс для рассылок
BROADCAST_INTEGRATION = {
    "send_message_to_user": "bot.send_message(user_id, text)",
    "send_message_to_all": "broadcast_service.send_to_all(message)",
    "user_segments": ["active_users", "recent_buyers", "free_users"]
}
```

### Раздел 6: Многоязычность
```json
{
  "supported_languages": ["en", "ru", "es", "fr"],
  "default_language": "en",
  "fallback_language": "en",
  "translation_keys": 45,
  "coverage": "100%"
}
```

### Раздел 7: Мониторинг и логи
- Логирование всех действий пользователей
- Трекинг ошибок и исключений
- Метрики использования функций
- Статистика по языкам и регионам

## Следующие шаги для других агентов

### Agent 4 (Administration):
- Создать веб-интерфейс для загрузки контента уроков
- Реализовать просмотр активности пользователей
- Добавить управление текстами интерфейса
- Создать аналитику по использованию бота

### Agent 5 (Communication):
- Интегрировать рассылки с существующими пользователями
- Создать персонализированные уведомления
- Реализовать автоответы поддержки
- Настроить уведомления администратора

**Важно**: Убедитесь, что бот корректно обрабатывает все состояния пользователей и интегрируется с платежной системой Agent 2!