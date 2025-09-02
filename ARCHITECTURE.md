# Telegram Lessons Bot - Архитектура системы

## Общее описание
Telegram-бот для продажи видеоуроков с поддержкой оплаты через Telegram Stars, административной панелью и системой многоязычности.

## Технологический стек
- **Backend**: Python 3.11+
- **Telegram Bot**: python-telegram-bot
- **Database**: SQLite (с возможностью миграции на PostgreSQL)
- **ORM**: SQLAlchemy
- **Web Framework**: FastAPI
- **Authentication**: JWT tokens
- **File Storage**: Local file system
- **Containerization**: Docker
- **Web Server**: Nginx + Uvicorn
- **Testing**: pytest
- **Documentation**: Markdown + OpenAPI/Swagger

## Архитектура системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   Admin Panel   │    │  File Storage   │
│    (Frontend)   │    │   (FastAPI)     │    │   (Local FS)    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │                      │                      │
          └──────────┬───────────┴──────────────────────┘
                     │
          ┌─────────────────┐
          │   Core Backend  │
          │   (SQLAlchemy)  │
          │   + Database    │
          └─────────────────┘
```

## Структура модулей

### 1. Backend Core (Agent 1)
- База данных и модели
- API endpoints
- Аутентификация
- Базовая бизнес-логика

### 2. Payment & Finance (Agent 2) 
- Telegram Stars интеграция
- Обработка платежей
- Финансовая отчетность

### 3. User Interface (Agent 3)
- Telegram Bot интерфейс
- Многоязычность
- Пользовательские сценарии

### 4. Administration (Agent 4)
- Web админ-панель
- Управление контентом
- Статистика

### 5. Communication (Agent 5)
- Рассылки
- Уведомления
- Поддержка

## База данных

### Основные таблицы:
- `users` - пользователи
- `lessons` - уроки
- `courses` - мини-курсы  
- `purchases` - покупки
- `payments` - платежи
- `promocodes` - промокоды
- `messages` - сообщения рассылки
- `support_tickets` - тикеты поддержки

## API Endpoints

### Authentication
- `POST /auth/login` - авторизация админа
- `POST /auth/refresh` - обновление токена

### Users
- `GET /api/users/` - список пользователей
- `GET /api/users/{user_id}` - профиль пользователя
- `GET /api/users/{user_id}/purchases` - покупки пользователя

### Content
- `GET /api/lessons/` - список уроков
- `POST /api/lessons/` - создание урока
- `PUT /api/lessons/{lesson_id}` - обновление урока
- `DELETE /api/lessons/{lesson_id}` - удаление урока

### Payments
- `POST /api/payments/create` - создание платежа
- `POST /api/payments/verify` - верификация платежа
- `GET /api/payments/stats` - статистика платежей

## Файловая структура

```
lessons-bot/
├── README.md
├── ARCHITECTURE.md
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
│
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   ├── api/
│   ├── services/
│   └── tests/
│
├── bot/
│   ├── __init__.py
│   ├── main.py
│   ├── handlers/
│   ├── keyboards/
│   ├── states/
│   ├── utils/
│   └── tests/
│
├── admin/
│   ├── __init__.py
│   ├── main.py
│   ├── routes/
│   ├── templates/
│   ├── static/
│   └── tests/
│
├── shared/
│   ├── __init__.py
│   ├── models.py
│   ├── database.py
│   ├── utils.py
│   └── constants.py
│
├── storage/
│   ├── videos/
│   ├── texts/
│   └── temp/
│
└── docs/
    ├── api.md
    ├── deployment.md
    └── agents/
```

## Стандарты разработки

### Code Style
- PEP 8 для Python
- Type hints обязательны
- Docstrings для всех функций и классов

### Git Conventions
- Conventional Commits format
- Feature branches
- PR reviews обязательны

### Testing
- Покрытие тестами > 80%
- Unit tests для всех сервисов
- Integration tests для API
- E2E tests для критических сценариев

### Documentation
- API документация через OpenAPI/Swagger
- Markdown для общей документации
- Inline комментарии для сложной логики