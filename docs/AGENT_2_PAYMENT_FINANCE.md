# ФАЗА 2: Payment & Finance Development

## Контекст задачи
Вы - Agent 2, ответственный за интеграцию платежной системы Telegram Stars, обработку платежей и финансовую отчетность. Ваша работа начинается после завершения Agent 1 (Backend Core).

## Предварительные требования
✅ Agent 1 завершил работу и создал документацию `BACKEND_CORE_COMPLETE.md`  
✅ Backend API запущен и доступен по адресу `http://localhost:8000`  
✅ База данных создана с моделями `Purchase`, `User`, `Lesson`, `Course`  
✅ API endpoints для пользователей и уроков работают  

## Цель
Создать полнофункциональную платежную систему с интеграцией Telegram Stars, обработкой промокодов, финансовой отчетностью и выводом средств.

## Требования к процессу разработки

### Обязательное использование инструментов мышления
**КРИТИЧЕСКИ ВАЖНО**: На каждом этапе разработки вы ДОЛЖНЫ использовать:

1. **Sequential Thinking** - для анализа и планирования каждого шага:
   - Перед началом каждого шага используйте sequential thinking для анализа задачи
   - Разбейте сложные задачи на более простые подзадачи
   - Продумайте возможные проблемы и их решения
   - Убедитесь в правильности подхода перед реализацией

2. **Context7** - для поиска актуальной документации и примеров:
   - Ищите документацию по Telegram Stars API
   - Изучайте примеры интеграции платежных систем
   - Находите best practices для финансовых систем
   - Ищите примеры работы с промокодами и скидками

**Процесс работы**: Sequential Thinking → Context7 Research → Implementation → Testing

## Технические требования

### Основные технологии
- **Python Telegram Bot API**: для обработки платежей
- **Telegram Stars API**: для проведения транзакций
- **SQLAlchemy**: для работы с платежными данными
- **Celery**: для асинхронной обработки платежей (опционально)
- **Logging**: для аудита финансовых операций

### Дополнительные переменные окружения (.env)
```
# Добавить к существующему .env файлу
TELEGRAM_PAYMENT_PROVIDER_TOKEN=your-payment-provider-token
WEBHOOK_URL=https://your-domain.com/webhook
TELEGRAM_STARS_WEBHOOK_SECRET=your-webhook-secret
FINANCIAL_REPORT_EMAIL=admin@example.com
WITHDRAW_MIN_AMOUNT=1000
COMMISSION_PERCENT=5
```

## Пошаговый план разработки

### Шаг 1: Изучение существующей архитектуры (30 мин)

**🧠 Обязательно используйте Sequential Thinking для:**
- Анализа архитектуры Backend Core от Agent 1
- Планирования интеграции с существующими API
- Выявления потенциальных проблем интеграции

**📚 Обязательно используйте Context7 для поиска:**
- Документации Telegram Stars API
- Примеров интеграции платежных систем с FastAPI
- Best practices для обработки платежей
1. Изучить `BACKEND_CORE_COMPLETE.md` от Agent 1
2. Проверить работоспособность API endpoints:
   - `GET /api/users/`
   - `GET /api/lessons/`
   - `POST /auth/login`
3. Понять структуру моделей `Purchase`, `User`, `Lesson`
4. Проверить подключение к базе данных

### Шаг 2: Настройка платежной системы (60 мин)

**🧠 Sequential Thinking для:**
- Проектирования архитектуры платежной системы
- Планирования обработки ошибок и исключений
- Анализа безопасности платежных процессов

**📚 Context7 для поиска:**
- Telegram Payment API documentation
- Python libraries для работы с платежами
- Примеры безопасной обработки финансовых данных

#### Создать `backend/services/payment_service.py`:
```python
class PaymentService:
    def create_payment(self, user_id: int, item_id: int, item_type: str, promo_code: str = None)
    def verify_payment(self, payment_id: str, telegram_payment_data: dict)
    def process_successful_payment(self, purchase_id: int)
    def handle_failed_payment(self, purchase_id: int, error: str)
    def apply_promo_code(self, code: str, amount: int) -> int
    def get_user_purchases(self, user_id: int) -> List[Purchase]
```

#### Создать `backend/api/payments.py`:
- `POST /api/payments/create` - создание платежа
- `POST /api/payments/webhook` - обработка webhook от Telegram
- `GET /api/payments/{payment_id}` - статус платежа
- `POST /api/payments/verify` - верификация платежа
- `GET /api/payments/stats` - статистика платежей

### Шаг 3: Интеграция с Telegram Stars (90 мин)

**🧠 Sequential Thinking для:**
- Понимания workflow Telegram Stars платежей
- Планирования обработки webhook'ов
- Анализа сценариев успешных и неуспешных платежей

**📚 Context7 для поиска:**
- Telegram Stars API complete guide
- Webhook handling best practices
- Python telegram bot payment examples

#### Создать `bot/handlers/payment_handlers.py`:
```python
# Обработчики для платежей в Telegram Bot
async def handle_pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE)
async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE)
async def send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int)
async def create_course_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: int)
```

#### Создать `bot/utils/payment_utils.py`:
```python
def create_invoice_payload(user_id: int, item_id: int, item_type: str) -> str
def parse_invoice_payload(payload: str) -> dict
def calculate_final_price(base_price: int, promo_code: str = None) -> int
def format_price_message(price: int, currency: str = "XTR") -> str
```

### Шаг 4: Система промокодов (45 мин)

**🧠 Sequential Thinking для:**
- Проектирования гибкой системы скидок
- Планирования валидации и ограничений промокодов
- Анализа производительности при большом количестве кодов

**📚 Context7 для поиска:**
- Promo code system design patterns
- Database optimization for discount systems
- Security best practices for promotional codes

#### Расширить `backend/services/promo_service.py`:
```python
class PromoCodeService:
    def validate_promo_code(self, code: str) -> PromoCode
    def apply_discount(self, promo_code: PromoCode, amount: int) -> int
    def use_promo_code(self, code: str, user_id: int) -> bool
    def get_active_promocodes(self) -> List[PromoCode]
    def create_promo_code(self, code: str, discount_percent: int, max_uses: int) -> PromoCode
```

#### Создать API endpoints в `backend/api/promocodes.py`:
- `GET /api/promocodes/` - список промокодов
- `POST /api/promocodes/` - создание промокода
- `PUT /api/promocodes/{code}` - обновление промокода
- `DELETE /api/promocodes/{code}` - деактивация промокода
- `POST /api/promocodes/validate` - валидация промокода

### Шаг 5: Финансовая отчетность (60 мин)

**🧠 Sequential Thinking для:**
- Проектирования структуры финансовых отчетов
- Планирования агрегации данных для аналитики
- Анализа требований к производительности отчетов

**📚 Context7 для поиска:**
- Financial reporting system design
- Data aggregation patterns in Python
- Dashboard and analytics best practices

#### Создать `backend/services/finance_service.py`:
```python
class FinanceService:
    def get_daily_revenue(self, date: date) -> dict
    def get_monthly_stats(self, year: int, month: int) -> dict
    def get_top_selling_lessons(self, limit: int = 10) -> List[dict]
    def get_user_lifetime_value(self, user_id: int) -> float
    def export_financial_report(self, start_date: date, end_date: date) -> str
    def calculate_withdrawable_amount(self) -> int
```

#### Создать API endpoints в `backend/api/finance.py`:
- `GET /api/finance/daily/{date}` - дневная статистика
- `GET /api/finance/monthly/{year}/{month}` - месячная статистика
- `GET /api/finance/top-lessons` - топ продаж
- `GET /api/finance/export` - экспорт отчета
- `POST /api/finance/withdraw` - запрос на вывод средств

### Шаг 6: Система вывода средств (45 мин)

**🧠 Sequential Thinking для:**
- Планирования безопасного процесса вывода средств
- Анализа требований к верификации и одобрению
- Проектирования системы уведомлений о статусе вывода

**📚 Context7 для поиска:**
- Withdrawal system security patterns
- Telegram Wallet integration examples
- Financial transaction approval workflows

#### Создать модель `WithdrawRequest` в `shared/models.py`:
```python
class WithdrawRequest(Base):
    id: int (Primary Key)
    amount: int
    status: str (pending, approved, completed, rejected)
    telegram_wallet_address: str
    requested_at: datetime
    processed_at: datetime (Nullable)
    notes: text (Nullable)
```

#### Создать `backend/services/withdraw_service.py`:
```python
class WithdrawService:
    def create_withdraw_request(self, amount: int, wallet_address: str) -> WithdrawRequest
    def approve_withdraw(self, request_id: int) -> bool
    def process_withdraw(self, request_id: int) -> bool
    def get_pending_withdraws(self) -> List[WithdrawRequest]
```

### Шаг 7: Аудит и логирование (30 мин)

**🧠 Sequential Thinking для:**
- Планирования комплексной системы аудита
- Анализа требований к логированию финансовых операций
- Проектирования системы алертов и мониторинга

**📚 Context7 для поиска:**
- Financial audit logging best practices
- Python logging patterns for financial systems
- Security monitoring and alerting systems

#### Создать `backend/utils/audit_logger.py`:
```python
class AuditLogger:
    def log_payment_created(self, payment_data: dict)
    def log_payment_completed(self, payment_id: str, amount: int)
    def log_payment_failed(self, payment_id: str, error: str)
    def log_promo_code_used(self, code: str, user_id: int)
    def log_withdraw_request(self, amount: int, user: str)
```

### Шаг 8: Тестирование платежей (60 мин)

**🧠 Sequential Thinking для:**
- Планирования comprehensive test suite для платежей
- Анализа edge cases и error scenarios
- Проектирования mock-тестов для внешних API

**📚 Context7 для поиска:**
- Payment system testing strategies
- Python testing frameworks for financial apps
- Mock testing patterns for payment APIs

#### Создать тесты в `backend/tests/`:
- `test_payment_service.py` - тесты платежной логики
- `test_promo_codes.py` - тесты промокодов
- `test_finance_api.py` - тесты финансовых API
- `test_telegram_payments.py` - мок-тесты Telegram интеграции

#### Настроить тестовые платежи:
```python
# Тестовые сценарии
def test_successful_lesson_purchase()
def test_course_purchase_with_promo()
def test_payment_failure_handling()
def test_duplicate_payment_prevention()
def test_withdraw_request_creation()
```

## Структура файлов для создания

```
backend/
├── api/
│   ├── payments.py           # Платежные API
│   ├── promocodes.py         # API промокодов
│   └── finance.py            # Финансовые API
├── services/
│   ├── payment_service.py    # Платежная логика
│   ├── promo_service.py      # Промокоды
│   ├── finance_service.py    # Финансы
│   └── withdraw_service.py   # Выводы
└── tests/
    ├── test_payment_service.py
    ├── test_promo_codes.py
    ├── test_finance_api.py
    └── test_telegram_payments.py

bot/
├── handlers/
│   └── payment_handlers.py   # Обработчики платежей
└── utils/
    └── payment_utils.py      # Утилиты платежей

shared/
├── models.py                 # Добавить WithdrawRequest
└── utils/
    └── audit_logger.py       # Аудит логи
```

## Критерии готовности

### Обязательные требования:
✅ Интеграция с Telegram Stars работает корректно  
✅ Создание платежей через API функционирует  
✅ Webhook обработка настроена и тестирована  
✅ Система промокодов полностью работает  
✅ Финансовая отчетность генерируется корректно  
✅ Система вывода средств реализована  
✅ Все платежи логируются для аудита  
✅ Тесты покрывают > 85% кода модуля  

### Проверка готовности:
```bash
# Тест создания платежа
curl -X POST "http://localhost:8000/api/payments/create" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "lesson_id": 1, "promo_code": "TEST10"}'

# Тест валидации промокода
curl -X POST "http://localhost:8000/api/promocodes/validate" \
  -H "Content-Type: application/json" \
  -d '{"code": "TEST10", "amount": 100}'

# Тест финансовой статистики
curl -X GET "http://localhost:8000/api/finance/daily/2024-01-01" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Запуск платежных тестов
pytest backend/tests/test_payment_service.py -v
```

## Формат документации для других агентов

После завершения создайте `docs/agents/PAYMENT_FINANCE_COMPLETE.md`:

### Раздел 1: Реализованная функциональность
- Подробное описание платежной системы
- API endpoints для платежей с примерами
- Схема работы промокодов
- Финансовые отчеты и их использование

### Раздел 2: Интеграционные интерфейсы

#### Для Agent 3 (User Interface):
```python
# Создание платежа для пользователя
payment_data = {
    "user_id": telegram_user.id,
    "lesson_id": lesson.id,
    "promo_code": user_promo_code  # optional
}
response = requests.post("/api/payments/create", json=payment_data)

# Проверка покупок пользователя
purchases = requests.get(f"/api/users/{user_id}/purchases")
```

#### Для Agent 4 (Administration):
```python
# Получение финансовой статистики
daily_stats = requests.get("/api/finance/daily/2024-01-01")
monthly_stats = requests.get("/api/finance/monthly/2024/1")

# Управление промокодами
promo_data = {
    "code": "NEWUSER20",
    "discount_percent": 20,
    "max_uses": 100
}
requests.post("/api/promocodes/", json=promo_data)
```

#### Для Agent 5 (Communication):
```python
# Уведомления о платежах
payment_notifications = {
    "successful_payment": "✅ Платеж успешно обработан!",
    "failed_payment": "❌ Ошибка при обработке платежа",
    "promo_applied": "🎉 Промокод применен! Скидка: {discount}%"
}
```

### Раздел 3: Webhook Configuration
```python
# Настройка webhook для Telegram
WEBHOOK_CONFIG = {
    "url": "https://your-domain.com/api/payments/webhook",
    "secret_token": "your-webhook-secret",
    "allowed_updates": ["pre_checkout_query", "message"]
}
```

### Раздел 4: Тестовые данные
```sql
-- Тестовые промокоды
INSERT INTO promocodes (code, discount_percent, max_uses, is_active) 
VALUES ('TEST10', 10, 100, true);

-- Тестовые платежи
INSERT INTO purchases (user_id, lesson_id, amount, status) 
VALUES (1, 1, 100, 'completed');
```

### Раздел 5: Мониторинг и алерты
- Настройка мониторинга неудачных платежей
- Алерты при превышении лимитов
- Ежедневные отчеты по доходам

### Раздел 6: Безопасность
- Валидация webhook signatures
- Rate limiting для платежных API
- Логирование подозрительной активности

## Следующие шаги для других агентов

### Agent 3 (User Interface):
- Интегрировать кнопки оплаты в Telegram Bot
- Добавить обработку промокодов в пользовательском интерфейсе
- Реализовать уведомления о успешных/неудачных платежах

### Agent 4 (Administration):
- Добавить финансовые дашборды в админ-панель
- Создать интерфейс управления промокодами
- Реализовать систему запросов на вывод средств

### Agent 5 (Communication):
- Настроить уведомления о платежах
- Создать рассылки о новых промокодах
- Реализовать поддержку по платежным вопросам

**Важно**: Убедитесь, что все платежные процессы логируются и webhook от Telegram обрабатывается корректно!