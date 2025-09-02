# ФАЗА 1: Backend Core Development

## Контекст задачи
Вы - Agent 1, ответственный за создание архитектурного фундамента всей системы. Ваша работа критически важна, так как остальные 4 агента будут строить свои модули на основе созданной вами архитектуры.

## Цель
Создать backend core с базой данных, моделями, базовым API и системой аутентификации, которые будут использоваться всеми остальными компонентами системы.

## Технические требования

### Стек технологий
- **Python**: 3.11+
- **Database**: SQLite с SQLAlchemy ORM
- **Framework**: FastAPI для API endpoints
- **Authentication**: JWT tokens
- **Testing**: pytest
- **Documentation**: автогенерация через FastAPI/Swagger

### Переменные окружения (.env)
```
DATABASE_URL=sqlite:///./lessons.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
TELEGRAM_BOT_TOKEN=your-bot-token
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

## Пошаговый план разработки

### Шаг 1: Настройка проекта (30 мин)
1. Создать структуру папок согласно ARCHITECTURE.md
2. Создать `requirements.txt` с зависимостями
3. Настроить `.env` файл
4. Создать `.gitignore`

### Шаг 2: Модели базы данных (60 мин)
Создать модели в `shared/models.py`:

#### User Model
```python
class User(Base):
    id: int (Primary Key)
    telegram_id: int (Unique)
    username: str (Nullable)
    first_name: str
    last_name: str (Nullable)
    language_code: str (Default: 'en')
    is_active: bool (Default: True)
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    purchases: List[Purchase]
    support_tickets: List[SupportTicket]
```

#### Lesson Model
```python
class Lesson(Base):
    id: int (Primary Key)
    title: str
    description: text
    price: int (в звездах)
    video_path: str (Nullable)
    text_content: text (Nullable)
    is_active: bool (Default: True)
    is_free: bool (Default: False)
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    purchases: List[Purchase]
    course_lessons: List[CourseLesson]
```

#### Course Model
```python
class Course(Base):
    id: int (Primary Key)
    title: str
    description: text
    total_price: int
    discount_price: int (Nullable)
    is_active: bool (Default: True)
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    course_lessons: List[CourseLesson]
    purchases: List[Purchase]
```

#### Purchase Model
```python
class Purchase(Base):
    id: int (Primary Key)
    user_id: int (Foreign Key)
    lesson_id: int (Foreign Key, Nullable)
    course_id: int (Foreign Key, Nullable)
    payment_id: str (Unique)
    amount: int
    status: str (pending, completed, failed)
    created_at: datetime
    updated_at: datetime
```

#### PromoCode Model
```python
class PromoCode(Base):
    id: int (Primary Key)
    code: str (Unique)
    discount_percent: int
    discount_amount: int (Nullable)
    max_uses: int (Nullable)
    current_uses: int (Default: 0)
    is_active: bool (Default: True)
    expires_at: datetime (Nullable)
    created_at: datetime
```

#### SupportTicket Model
```python
class SupportTicket(Base):
    id: int (Primary Key)
    user_id: int (Foreign Key)
    subject: str
    message: text
    status: str (open, in_progress, closed)
    admin_response: text (Nullable)
    created_at: datetime
    updated_at: datetime
```

### Шаг 3: Database Connection (30 мин)
Создать `shared/database.py`:
- Подключение к SQLite
- Создание сессий
- Базовые CRUD операции

### Шаг 4: Core API Endpoints (90 мин)
Создать в `backend/api/`:

#### Users API (`users.py`)
- `GET /api/users/` - список пользователей (пагинация)
- `GET /api/users/{user_id}` - профиль пользователя
- `PUT /api/users/{user_id}` - обновление пользователя
- `GET /api/users/{user_id}/purchases` - покупки пользователя

#### Lessons API (`lessons.py`)
- `GET /api/lessons/` - список уроков (фильтры, пагинация)
- `GET /api/lessons/{lesson_id}` - детали урока
- `POST /api/lessons/` - создание урока
- `PUT /api/lessons/{lesson_id}` - обновление урока
- `DELETE /api/lessons/{lesson_id}` - удаление урока

#### Courses API (`courses.py`)
- `GET /api/courses/` - список курсов
- `GET /api/courses/{course_id}` - детали курса
- `POST /api/courses/` - создание курса
- `PUT /api/courses/{course_id}` - обновление курса
- `DELETE /api/courses/{course_id}` - удаление курса

#### Auth API (`auth.py`)
- `POST /auth/login` - авторизация администратора
- `POST /auth/refresh` - обновление JWT токена
- `POST /auth/logout` - выход из системы

### Шаг 5: Services Layer (60 мин)
Создать бизнес-логику в `backend/services/`:
- `user_service.py` - работа с пользователями
- `lesson_service.py` - работа с уроками
- `course_service.py` - работа с курсами
- `auth_service.py` - аутентификация и авторизация

### Шаг 6: Тестирование (45 мин)
Создать тесты в `backend/tests/`:
- `test_models.py` - тесты моделей
- `test_api.py` - тесты API endpoints
- `test_services.py` - тесты бизнес-логики
- Настроить тестовую базу данных

### Шаг 7: Docker Configuration (30 мин)
Создать:
- `Dockerfile` для backend
- `docker-compose.yml` для всей системы
- Настройки для разработки и продакшена

## Структура файлов для создания

```
backend/
├── __init__.py
├── main.py                 # FastAPI app
├── config.py              # Конфигурация
├── api/
│   ├── __init__.py
│   ├── deps.py            # Dependencies
│   ├── auth.py            # Auth endpoints
│   ├── users.py           # Users CRUD
│   ├── lessons.py         # Lessons CRUD
│   └── courses.py         # Courses CRUD
├── services/
│   ├── __init__.py
│   ├── auth_service.py
│   ├── user_service.py
│   ├── lesson_service.py
│   └── course_service.py
└── tests/
    ├── __init__.py
    ├── conftest.py        # Pytest config
    ├── test_models.py
    ├── test_api.py
    └── test_services.py

shared/
├── __init__.py
├── models.py              # SQLAlchemy models
├── database.py            # DB connection
├── schemas.py             # Pydantic schemas
├── utils.py               # Общие утилиты
└── constants.py           # Константы
```

## Критерии готовности

### Обязательные требования:
✅ Все модели базы данных созданы и протестированы  
✅ База данных создается автоматически при первом запуске  
✅ Все API endpoints работают и задокументированы  
✅ JWT аутентификация настроена и работает  
✅ Тесты покрывают > 80% кода  
✅ Swagger документация доступна по `/docs`  
✅ Docker контейнер собирается и запускается  
✅ Создана база данных с тестовыми данными  

### Проверка готовности:
```bash
# Запуск тестов
pytest backend/tests/ -v --cov=backend

# Запуск сервера
uvicorn backend.main:app --reload

# Проверка API документации
curl http://localhost:8000/docs

# Проверка здоровья API
curl http://localhost:8000/health
```

## Формат документации для других агентов

После завершения работы создайте документ `docs/agents/BACKEND_CORE_COMPLETE.md`:

### Раздел 1: Что реализовано
- Список созданных моделей с описанием полей
- Список API endpoints с примерами запросов
- Конфигурация аутентификации
- Структура базы данных

### Раздел 2: API Reference для других агентов
```markdown
## Users API
### GET /api/users/{user_id}
**Описание**: Получение профиля пользователя
**Параметры**: user_id (int)
**Ответ**: UserSchema object
**Пример**:
```json
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "language_code": "en",
  "created_at": "2024-01-01T00:00:00"
}
```
```

### Раздел 3: Интеграционные интерфейсы
- Как создавать пользователей из Telegram Bot
- Как проверять покупки пользователя
- Как аутентифицироваться в API
- Схемы данных для всех моделей

### Раздел 4: Инструкции для других агентов

#### Для Agent 2 (Payment & Finance):
- Используйте `Purchase` модель для записи платежей
- API endpoint `/api/purchases/create` для создания покупки
- Поле `payment_id` должно быть уникальным идентификатором от Telegram

#### Для Agent 3 (User Interface):
- Используйте `/api/users/` для работы с пользователями
- Проверяйте покупки через `/api/users/{user_id}/purchases`
- Создавайте пользователей при первом обращении

#### Для Agent 4 (Administration):
- Используйте JWT токены для аутентификации
- Endpoint `/auth/login` для получения токена
- Все CRUD операции доступны через API

#### Для Agent 5 (Communication):
- Модель `SupportTicket` для тикетов поддержки
- Список пользователей доступен через `/api/users/`
- Фильтрация пользователей по статусу активности

### Раздел 5: Что осталось для интеграции
- Настройка файлового хранилища (Agent 3, 4)
- Интеграция с Telegram Stars (Agent 2)
- Фронтенд для админ-панели (Agent 4)
- Telegram Bot handlers (Agent 3)
- Система рассылок (Agent 5)

### Раздел 6: Команды для тестирования интеграции
```bash
# Создание тестового пользователя
curl -X POST "http://localhost:8000/api/users/" \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789, "first_name": "Test"}'

# Получение токена админа
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Создание тестового урока
curl -X POST "http://localhost:8000/api/lessons/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Lesson", "description": "Test", "price": 100}'
```

## Следующие шаги
После завершения вашей работы и создания документации, остальные агенты смогут:
1. **Agent 2**: Интегрировать Telegram Stars платежи с `Purchase` моделью
2. **Agent 3**: Создать Telegram Bot используя пользователи API
3. **Agent 4**: Построить админ-панель поверх созданного API
4. **Agent 5**: Реализовать рассылки используя users API

**Важно**: Убедитесь, что API полностью функционален и задокументирован перед передачей проекта другим агентам!