# ФАЗА 2: Communication System Development

## Контекст задачи
Вы - Agent 5, ответственный за создание системы коммуникации: рассылки, уведомления, поддержку пользователей и все коммуникационные каналы системы. Ваша работа начинается после завершения Agent 1 (Backend Core).

## Предварительные требования
✅ Agent 1 завершил работу - Backend API доступен  
✅ Agent 2 завершил работу - Платежная система готова  
✅ Agent 3 завершил работу - Telegram Bot функционирует  
✅ Agent 4 завершил работу - Админ-панель работает  
✅ Все API endpoints и системы интегрированы  

## Требования к процессу разработки

### Обязательное использование инструментов мышления
**КРИТИЧЕСКИ ВАЖНО**: На каждом этапе разработки вы ДОЛЖНЫ использовать:

1. **Sequential Thinking** - для стратегического планирования коммуникаций:
   - Анализируйте потребности в коммуникации
   - Планируйте коммуникационные флоу
   - Продумывайте персонализацию сообщений
   - Оптимизируйте эффективность рассылок

2. **Context7** - для исследования лучших практик:
   - Ищите примеры эффективных email marketing campaigns
   - Изучайте примеры работы с Celery и Redis
   - Находите примеры customer support automation
   - Ищите notification system design patterns

**Процесс работы**: Sequential Thinking → Context7 Research → Communication Strategy → Implementation → Testing

## Цель
Создать комплексную систему коммуникации с поддержкой массовых рассылок, персонализированных уведомлений, многоканальной поддержки пользователей и автоматизированных коммуникационных сценариев.

## Технические требования

### Основные технологии
- **Celery + Redis**: для асинхронной обработки рассылок
- **Telegram Bot API**: для отправки сообщений
- **Email (SMTP)**: для email уведомлений (опционально)
- **Template Engine**: Jinja2 для шаблонов сообщений
- **Scheduler**: для автоматических рассылок
- **WebSocket**: для real-time уведомлений в админке

### Дополнительные переменные окружения (.env)
```env
# Добавить к существующему .env файлу
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_CHANNELS=telegram,email
BROADCAST_RATE_LIMIT=30  # сообщений в секунду
SUPPORT_AUTO_REPLY=true
DEFAULT_SUPPORT_MESSAGE="Спасибо за обращение! Мы ответим в течение 24 часов."
```

## Пошаговый план разработки

### Шаг 1: Изучение существующей архитектуры (30 мин)

**🧠 Обязательно используйте Sequential Thinking для:**
- Анализа коммуникационных потребностей системы
- Планирования стратегии рассылок и уведомлений
- Проектирования системы поддержки пользователей

**📚 Обязательно используйте Context7 для поиска:**
- Communication system architecture patterns
- Async messaging best practices
- Customer engagement strategies
1. Изучить документацию от всех предыдущих агентов
2. Протестировать интеграционные точки:
   - Bot API для отправки сообщений
   - Backend API для получения пользователей
   - Admin API для управления рассылками
3. Понять структуру пользователей и их предпочтений

### Шаг 2: Настройка асинхронной обработки (60 мин)

#### Создать `communication/celery_app.py`:
```python
from celery import Celery

app = Celery('communication')
app.config_from_object('communication.celery_config')

@app.task
def send_message_to_user(user_id: int, message: str, message_type: str = "text"):
    # Отправка сообщения конкретному пользователю

@app.task
def send_broadcast_message(message: str, target_segment: str = "all"):
    # Массовая рассылка

@app.task
def send_notification(user_id: int, notification_type: str, data: dict):
    # Отправка уведомления

@app.task
def process_support_ticket(ticket_id: int):
    # Обработка тикета поддержки
```

#### Создать `communication/celery_config.py`:
```python
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Настройки маршрутизации задач
task_routes = {
    'communication.tasks.send_message_to_user': {'queue': 'messages'},
    'communication.tasks.send_broadcast_message': {'queue': 'broadcasts'},
    'communication.tasks.send_notification': {'queue': 'notifications'},
}
```

### Шаг 3: Система шаблонов сообщений (45 мин)

#### Создать `communication/templates/` структуру:
```
communication/templates/
├── notifications/
│   ├── payment_success.html
│   ├── payment_failed.html
│   ├── new_lesson_available.html
│   ├── welcome_message.html
│   └── support_response.html
├── broadcasts/
│   ├── promotional.html
│   ├── newsletter.html
│   └── system_maintenance.html
└── support/
    ├── auto_reply.html
    ├── ticket_created.html
    └── ticket_resolved.html
```

#### Создать `communication/services/template_service.py`:
```python
from jinja2 import Environment, FileSystemLoader

class TemplateService:
    def __init__(self, templates_dir: str):
        self.env = Environment(loader=FileSystemLoader(templates_dir))
    
    def render_template(self, template_name: str, **kwargs) -> str:
        # Рендеринг шаблона с данными
    
    def get_available_templates(self) -> list:
        # Получение списка доступных шаблонов
    
    def create_personalized_message(self, template_name: str, user_data: dict, extra_data: dict = None) -> str:
        # Создание персонализированного сообщения
```

### Шаг 4: Система рассылок (90 мин)

#### Создать `communication/services/broadcast_service.py`:
```python
class BroadcastService:
    def __init__(self):
        self.bot_api_client = BotAPIClient()
        self.template_service = TemplateService()
    
    async def create_broadcast(self, message_data: dict) -> str:
        # Создание новой рассылки
        # message_data: {title, content, template, target_segment, schedule_time}
    
    async def send_immediate_broadcast(self, broadcast_id: str):
        # Немедленная отправка рассылки
    
    async def schedule_broadcast(self, broadcast_id: str, send_time: datetime):
        # Планирование рассылки на определенное время
    
    async def get_target_users(self, segment: str) -> list:
        # Получение списка пользователей для рассылки
        # Сегменты: all, active, recent_buyers, free_users, language_specific
    
    async def track_broadcast_delivery(self, broadcast_id: str) -> dict:
        # Отслеживание доставки рассылки
```

#### Создать `communication/models/broadcast.py`:
```python
class Broadcast(Base):
    id: str (Primary Key, UUID)
    title: str
    content: text
    template_name: str
    target_segment: str
    status: str (draft, scheduled, sending, completed, failed)
    scheduled_time: datetime (Nullable)
    created_at: datetime
    sent_at: datetime (Nullable)
    total_recipients: int (Default: 0)
    successful_deliveries: int (Default: 0)
    failed_deliveries: int (Default: 0)
    created_by: str  # admin username
    
    # Relationships
    delivery_logs: List[BroadcastDelivery]

class BroadcastDelivery(Base):
    id: int (Primary Key)
    broadcast_id: str (Foreign Key)
    user_id: int (Foreign Key)
    status: str (pending, sent, delivered, failed)
    sent_at: datetime (Nullable)
    error_message: text (Nullable)
```

### Шаг 5: Система уведомлений (75 мин)

#### Создать `communication/services/notification_service.py`:
```python
class NotificationService:
    NOTIFICATION_TYPES = {
        'payment_success': 'Successful Payment',
        'payment_failed': 'Failed Payment',
        'new_lesson': 'New Lesson Available',
        'course_completed': 'Course Completed',
        'promo_code_available': 'New Promo Code',
        'support_response': 'Support Response',
        'system_maintenance': 'System Maintenance'
    }
    
    async def send_notification(self, user_id: int, notification_type: str, data: dict):
        # Отправка уведомления пользователю
    
    async def send_payment_notification(self, user_id: int, payment_data: dict):
        # Уведомление о платеже
    
    async def send_new_lesson_notification(self, lesson_data: dict, target_users: list = None):
        # Уведомление о новом уроке
    
    async def send_promo_notification(self, promo_data: dict, target_segment: str = "all"):
        # Уведомление о промокоде
    
    async def get_user_notification_preferences(self, user_id: int) -> dict:
        # Получение настроек уведомлений пользователя
```

#### Создать модель уведомлений в `shared/models.py`:
```python
class NotificationPreference(Base):
    id: int (Primary Key)
    user_id: int (Foreign Key)
    notification_type: str
    enabled: bool (Default: True)
    channel: str (telegram, email)  # предпочитаемый канал
    created_at: datetime
    updated_at: datetime

class NotificationLog(Base):
    id: int (Primary Key)
    user_id: int (Foreign Key)
    notification_type: str
    title: str
    content: text
    status: str (sent, delivered, failed)
    channel: str (telegram, email)
    sent_at: datetime
    delivered_at: datetime (Nullable)
    error_message: text (Nullable)
```

### Шаг 6: Система поддержки пользователей (60 мин)

#### Расширить модель `SupportTicket` в `shared/models.py`:
```python
class SupportTicket(Base):
    # Существующие поля из Agent 1
    # Добавить новые поля:
    category: str (general, payment, technical, content)
    priority: str (low, medium, high, urgent)
    assigned_to: str (Nullable)  # admin username
    tags: str (Nullable)  # comma-separated tags
    last_activity: datetime
    auto_reply_sent: bool (Default: False)
    satisfaction_rating: int (Nullable, 1-5)
    
    # Relationships
    messages: List[SupportMessage]

class SupportMessage(Base):
    id: int (Primary Key)
    ticket_id: int (Foreign Key)
    sender_type: str (user, admin, system)
    sender_id: str  # user_id or admin username
    message: text
    message_type: str (text, image, file)
    file_path: str (Nullable)
    sent_at: datetime
    read_at: datetime (Nullable)
```

#### Создать `communication/services/support_service.py`:
```python
class SupportService:
    async def create_support_ticket(self, user_id: int, subject: str, message: str, category: str = "general") -> int:
        # Создание нового тикета поддержки
    
    async def send_auto_reply(self, ticket_id: int):
        # Отправка автоответа
    
    async def assign_ticket_to_admin(self, ticket_id: int, admin_username: str):
        # Назначение тикета администратору
    
    async def add_message_to_ticket(self, ticket_id: int, sender_type: str, sender_id: str, message: str):
        # Добавление сообщения к тикету
    
    async def close_ticket(self, ticket_id: int, resolution: str):
        # Закрытие тикета
    
    async def get_ticket_statistics(self) -> dict:
        # Статистика по тикетам поддержки
    
    async def send_satisfaction_survey(self, ticket_id: int):
        # Отправка опроса удовлетворенности
```

### Шаг 7: API для админ-панели (45 мин)

#### Создать `communication/api/broadcast_api.py`:
```python
@router.get("/api/communication/broadcasts")
async def get_broadcasts(status: str = "all", page: int = 1):
    # Получение списка рассылок

@router.post("/api/communication/broadcasts")
async def create_broadcast(broadcast_data: BroadcastCreate):
    # Создание новой рассылки

@router.post("/api/communication/broadcasts/{broadcast_id}/send")
async def send_broadcast(broadcast_id: str):
    # Отправка рассылки

@router.get("/api/communication/broadcasts/{broadcast_id}/stats")
async def get_broadcast_stats(broadcast_id: str):
    # Статистика рассылки

@router.get("/api/communication/templates")
async def get_message_templates():
    # Получение доступных шаблонов
```

#### Создать `communication/api/support_api.py`:
```python
@router.get("/api/communication/support/tickets")
async def get_support_tickets(status: str = "open", assigned_to: str = None):
    # Получение тикетов поддержки

@router.get("/api/communication/support/tickets/{ticket_id}")
async def get_ticket_details(ticket_id: int):
    # Детали тикета

@router.post("/api/communication/support/tickets/{ticket_id}/messages")
async def add_ticket_message(ticket_id: int, message_data: TicketMessage):
    # Добавление сообщения к тикету

@router.put("/api/communication/support/tickets/{ticket_id}/assign")
async def assign_ticket(ticket_id: int, admin_username: str):
    # Назначение тикета

@router.put("/api/communication/support/tickets/{ticket_id}/close")
async def close_ticket(ticket_id: int, resolution: str):
    # Закрытие тикета
```

### Шаг 8: Интеграция с Telegram Bot (30 мин)

#### Создать `communication/integrations/telegram_integration.py`:
```python
class TelegramIntegration:
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
    
    async def send_message_to_user(self, user_id: int, message: str, parse_mode: str = "HTML"):
        # Отправка сообщения пользователю
    
    async def send_rich_message(self, user_id: int, text: str, keyboard: InlineKeyboardMarkup = None):
        # Отправка богатого сообщения с клавиатурой
    
    async def send_media_message(self, user_id: int, media_type: str, media_path: str, caption: str = None):
        # Отправка медиа-сообщения
    
    async def send_admin_notification(self, admin_chat_id: int, message: str):
        # Уведомление администратора
    
    async def handle_user_message_for_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Обработка сообщений пользователей для поддержки
```

### Шаг 9: Автоматизация и планировщик (45 мин)

#### Создать `communication/scheduler/automation.py`:
```python
from celery.schedules import crontab

class CommunicationAutomation:
    # Периодические задачи
    @app.task
    def send_weekly_newsletter():
        # Еженедельная рассылка новостей
    
    @app.task
    def send_abandoned_cart_reminder():
        # Напоминание о незавершенных покупках
    
    @app.task
    def send_user_engagement_campaign():
        # Кампания вовлечения неактивных пользователей
    
    @app.task
    def generate_daily_support_report():
        # Ежедневный отчет по поддержке
    
    @app.task
    def cleanup_old_notifications():
        # Очистка старых уведомлений

# Расписание задач
app.conf.beat_schedule = {
    'weekly-newsletter': {
        'task': 'communication.scheduler.automation.send_weekly_newsletter',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Понедельник 10:00
    },
    'daily-support-report': {
        'task': 'communication.scheduler.automation.generate_daily_support_report',
        'schedule': crontab(hour=9, minute=0),  # Каждый день в 9:00
    },
}
```

### Шаг 10: Аналитика и отчетность (30 мин)

#### Создать `communication/services/analytics_service.py`:
```python
class CommunicationAnalytics:
    async def get_broadcast_performance(self, period: str = "month") -> dict:
        # Эффективность рассылок
    
    async def get_notification_engagement(self) -> dict:
        # Вовлеченность по уведомлениям
    
    async def get_support_metrics(self) -> dict:
        # Метрики поддержки
    
    async def generate_communication_report(self, start_date: date, end_date: date) -> dict:
        # Генерация отчета по коммуникации
    
    async def get_user_communication_preferences_stats(self) -> dict:
        # Статистика предпочтений пользователей
```

## Структура файлов для создания

```
communication/
├── __init__.py
├── celery_app.py            # Celery приложение
├── celery_config.py         # Конфигурация Celery
├── models/
│   ├── __init__.py
│   └── broadcast.py         # Модели рассылок
├── services/
│   ├── __init__.py
│   ├── broadcast_service.py # Сервис рассылок
│   ├── notification_service.py # Сервис уведомлений
│   ├── support_service.py   # Сервис поддержки
│   ├── template_service.py  # Сервис шаблонов
│   └── analytics_service.py # Аналитика
├── api/
│   ├── __init__.py
│   ├── broadcast_api.py     # API рассылок
│   ├── support_api.py       # API поддержки
│   └── analytics_api.py     # API аналитики
├── integrations/
│   ├── __init__.py
│   ├── telegram_integration.py # Интеграция с Telegram
│   └── email_integration.py    # Email интеграция
├── scheduler/
│   ├── __init__.py
│   └── automation.py        # Автоматизация задач
├── templates/
│   ├── notifications/       # Шаблоны уведомлений
│   ├── broadcasts/          # Шаблоны рассылок
│   └── support/            # Шаблоны поддержки
└── tests/
    ├── test_broadcast_service.py
    ├── test_notification_service.py
    ├── test_support_service.py
    └── test_integrations.py
```

## Критерии готовности

### Обязательные требования:
✅ Celery worker запущен и обрабатывает задачи  
✅ Система рассылок создает и отправляет сообщения  
✅ Уведомления доставляются пользователям  
✅ Поддержка пользователей функционирует  
✅ Шаблоны сообщений работают корректно  
✅ API для админ-панели интегрировано  
✅ Автоматические задачи выполняются по расписанию  
✅ Аналитика и отчетность работают  
✅ Все каналы коммуникации протестированы  
✅ Rate limiting работает для предотвращения спама  

### Проверка готовности:
```bash
# Запуск Celery worker
celery -A communication.celery_app worker --loglevel=info

# Запуск Celery beat (планировщик)
celery -A communication.celery_app beat --loglevel=info

# Тест отправки сообщения
curl -X POST "http://localhost:8000/api/communication/test-message" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "message": "Test message"}'

# Тест создания рассылки
curl -X POST "http://localhost:8001/api/communication/broadcasts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Broadcast", "content": "Hello!", "target_segment": "all"}'

# Запуск тестов
pytest communication/tests/ -v --cov=communication
```

## Формат финальной документации

После завершения создайте `docs/agents/COMMUNICATION_COMPLETE.md`:

### Раздел 1: Реализованная функциональность
- Система массовых рассылок с сегментацией
- Персонализированные уведомления
- Многоканальная поддержка пользователей
- Автоматизированные коммуникационные сценарии
- Шаблонизация сообщений

### Раздел 2: API Reference
```python
# Примеры использования API

# Отправка рассылки
broadcast_data = {
    "title": "New Lesson Available",
    "content": "Check out our latest lesson!",
    "template": "new_lesson_notification",
    "target_segment": "active_users"
}

# Создание тикета поддержки
ticket_data = {
    "user_id": 123,
    "subject": "Payment Issue",
    "message": "I have a problem with payment",
    "category": "payment"
}
```

### Раздел 3: Интеграция со всеми компонентами

#### Integration с Bot (Agent 3):
- Обработка входящих сообщений для поддержки
- Доставка уведомлений пользователям
- Интерактивные элементы в сообщениях

#### Integration с Admin Panel (Agent 4):
- Интерфейс управления рассылками
- Дашборд поддержки пользователей
- Аналитика коммуникации

#### Integration с Payment System (Agent 2):
- Уведомления о платежах
- Промо-кампании
- Финансовые алерты

### Раздел 4: Мониторинг и метрики
```json
{
  "communication_metrics": {
    "daily_messages_sent": 1250,
    "delivery_rate": 98.5,
    "open_rate": 75.2,
    "support_response_time": "2.5 hours avg",
    "satisfaction_rating": 4.7
  }
}
```

### Раздел 5: Конфигурация продакшена
```python
# Настройки для продакшена
PRODUCTION_CONFIG = {
    "celery_workers": 4,
    "rate_limits": {
        "broadcasts": "100/hour",
        "notifications": "1000/hour",
        "support_messages": "50/hour"
    },
    "monitoring": {
        "error_alerts": True,
        "performance_monitoring": True,
        "delivery_tracking": True
    }
}
```

## Финальная интеграция системы

После завершения всех 5 агентов система будет полностью функциональной:

1. **Backend Core** (Agent 1) - обеспечивает данные и API
2. **Payment & Finance** (Agent 2) - обрабатывает платежи
3. **User Interface** (Agent 3) - взаимодействует с пользователями
4. **Administration** (Agent 4) - управляет системой
5. **Communication** (Agent 5) - обеспечивает коммуникацию

**Результат**: Полнофункциональный Telegram-бот для продажи уроков с современной архитектурой, масштабируемостью и всеми необходимыми возможностями для коммерческого использования.

**Важно**: Убедитесь, что все коммуникационные каналы работают корректно и система готова к обработке высоких нагрузок!