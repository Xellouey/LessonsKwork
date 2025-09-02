# ФАЗА 2: Administration Panel Development

## Контекст задачи
Вы - Agent 4, ответственный за создание веб-административной панели для управления контентом, пользователями, статистикой и всеми аспектами системы. Ваша работа начинается после завершения Agent 1 (Backend Core).

## Предварительные требования
✅ Agent 1 завершил работу - Backend API доступен  
✅ Agent 2 завершил работу - Платежная система готова  
✅ Agent 3 завершил работу - Telegram Bot функционирует  
✅ Все API endpoints протестированы и работают  
✅ JWT аутентификация настроена  

## Требования к процессу разработки

### Обязательное использование инструментов мышления
**КРИТИЧЕСКИ ВАЖНО**: На каждом этапе разработки вы ДОЛЖНЫ использовать:

1. **Sequential Thinking** - для проектирования UX админ-панели:
   - Анализируйте потребности администраторов
   - Планируйте workflow для каждой функции
   - Продумывайте интуитивную навигацию
   - Оптимизируйте производительность интерфейса

2. **Context7** - для исследования и поиска лучших практик:
   - Ищите примеры modern admin dashboard design
   - Изучайте FastAPI + HTML best practices
   - Находите примеры file upload implementations
   - Ищите responsive design patterns

**Процесс работы**: Sequential Thinking → Context7 Research → UI/UX Design → Implementation → Testing

## Цель
Создать современную, интуитивную веб-панель администратора с полным функционалом управления контентом, пользователями, финансами и статистикой системы.

## Технические требования

### Основные технологии
- **Frontend**: HTML, CSS, JavaScript (Vanilla или библиотека по выбору)
- **Backend**: FastAPI (уже настроен Agent 1)
- **Templates**: Jinja2 templates
- **CSS Framework**: Bootstrap 5 или Tailwind CSS
- **Charts**: Chart.js для графиков и статистики
- **File Upload**: Поддержка drag & drop для медиафайлов

### Дополнительные переменные окружения (.env)
```env
# Добавить к существующему .env файлу
ADMIN_PANEL_HOST=localhost
ADMIN_PANEL_PORT=8001
STATIC_FILES_PATH=./admin/static
TEMPLATES_PATH=./admin/templates
UPLOAD_MAX_SIZE=100MB
ALLOWED_VIDEO_FORMATS=mp4,mov,avi
ALLOWED_IMAGE_FORMATS=jpg,jpeg,png,gif
```

## Пошаговый план разработки

### Шаг 1: Изучение существующей архитектуры (30 мин)

**🧠 Обязательно используйте Sequential Thinking для:**
- Анализа требований к админ-панели
- Планирования интеграции с существующими API
- Проектирования user experience администратора

**📚 Обязательно используйте Context7 для поиска:**
- Admin dashboard design best practices
- FastAPI admin panel implementations
- Modern web interface patterns
1. Изучить документацию от всех предыдущих агентов
2. Протестировать все API endpoints:
   - Аутентификация: `POST /auth/login`
   - Пользователи: `GET /api/users/`
   - Уроки: `GET /api/lessons/`
   - Платежи: `GET /api/payments/stats`
3. Понять структуру данных и разрешения

### Шаг 2: Настройка FastAPI приложения для админки (45 мин)

**🧠 Sequential Thinking для:**
- Проектирования модульной архитектуры админки
- Планирования системы маршрутизации
- Анализа требований к производительности

**📚 Context7 для поиска:**
- FastAPI application structure patterns
- Web admin panel architecture examples
- Template engine integration best practices

#### Создать `admin/main.py`:
```python
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(title="Lessons Bot Admin Panel")
app.mount("/static", StaticFiles(directory="admin/static"), name="static")
templates = Jinja2Templates(directory="admin/templates")

# Middleware для проверки аутентификации
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Проверка JWT токена для всех admin маршрутов
```

#### Создать `admin/config.py`:
```python
from pydantic import BaseSettings

class AdminSettings(BaseSettings):
    host: str = "localhost"
    port: int = 8001
    debug: bool = True
    static_path: str = "./admin/static"
    templates_path: str = "./admin/templates"
    
    class Config:
        env_file = ".env"
```

### Шаг 3: Система аутентификации и безопасность (60 мин)

#### Создать `admin/auth/auth_service.py`:
```python
class AdminAuthService:
    async def login(self, username: str, password: str) -> dict:
        # Аутентификация администратора через Backend API
    
    async def verify_token(self, token: str) -> bool:
        # Верификация JWT токена
    
    async def refresh_token(self, refresh_token: str) -> str:
        # Обновление токена
    
    async def logout(self, token: str) -> bool:
        # Выход из системы
```

#### Создать `admin/routes/auth.py`:
```python
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Страница входа в админку

@router.post("/login")
async def login_process(username: str, password: str):
    # Обработка логина

@router.get("/dashboard")
async def dashboard(request: Request, user: dict = Depends(get_current_admin)):
    # Главная страница админки
```

### Шаг 4: Dashboard и статистика (75 мин)

#### Создать `admin/routes/dashboard.py`:
```python
class DashboardRoutes:
    @router.get("/dashboard")
    async def main_dashboard(request: Request):
        # Главная страница с общей статистикой
        stats = {
            "total_users": await get_users_count(),
            "total_lessons": await get_lessons_count(),
            "total_revenue": await get_total_revenue(),
            "today_sales": await get_today_sales(),
            "active_users_week": await get_active_users_week(),
            "top_lessons": await get_top_selling_lessons(5)
        }
    
    @router.get("/api/dashboard/stats")
    async def dashboard_api_stats():
        # API для получения статистики в JSON для графиков
```

#### Создать `admin/templates/dashboard.html`:
```html
<!-- Дашборд с графиками и метриками -->
<div class="row">
    <div class="col-md-3">
        <div class="card bg-primary text-white">
            <div class="card-body">
                <h4>{{stats.total_users}}</h4>
                <p>Total Users</p>
            </div>
        </div>
    </div>
    <!-- Аналогично для других метрик -->
</div>

<!-- Графики с Chart.js -->
<canvas id="revenueChart"></canvas>
<canvas id="usersChart"></canvas>
```

### Шаг 5: Управление уроками и контентом (90 мин)

#### Создать `admin/routes/lessons.py`:
```python
class LessonsRoutes:
    @router.get("/lessons")
    async def lessons_list(request: Request, page: int = 1, search: str = None):
        # Список всех уроков с пагинацией и поиском
    
    @router.get("/lessons/create")
    async def create_lesson_form(request: Request):
        # Форма создания нового урока
    
    @router.post("/lessons/create")
    async def create_lesson_process(lesson_data: dict, video_file: UploadFile):
        # Обработка создания урока с загрузкой файлов
    
    @router.get("/lessons/{lesson_id}/edit")
    async def edit_lesson_form(request: Request, lesson_id: int):
        # Форма редактирования урока
    
    @router.post("/lessons/{lesson_id}/edit")
    async def edit_lesson_process(lesson_id: int, lesson_data: dict):
        # Обработка редактирования урока
    
    @router.delete("/lessons/{lesson_id}")
    async def delete_lesson(lesson_id: int):
        # Удаление урока
```

#### Создать `admin/templates/lessons/`:
- `list.html` - список уроков с таблицей
- `create.html` - форма создания урока
- `edit.html` - форма редактирования урока

#### Создать `admin/utils/file_manager.py`:
```python
class FileManager:
    async def upload_video(self, lesson_id: int, video_file: UploadFile) -> str:
        # Загрузка и сохранение видеофайла
    
    async def upload_thumbnail(self, lesson_id: int, image_file: UploadFile) -> str:
        # Загрузка миниатюры урока
    
    async def delete_lesson_files(self, lesson_id: int):
        # Удаление всех файлов урока
    
    async def get_file_info(self, file_path: str) -> dict:
        # Получение информации о файле (размер, длительность)
```

### Шаг 6: Управление пользователями (60 мин)

#### Создать `admin/routes/users.py`:
```python
class UsersRoutes:
    @router.get("/users")
    async def users_list(request: Request, page: int = 1, search: str = None, status: str = "all"):
        # Список пользователей с фильтрами
    
    @router.get("/users/{user_id}")
    async def user_detail(request: Request, user_id: int):
        # Детальная информация о пользователе
    
    @router.post("/users/{user_id}/toggle-status")
    async def toggle_user_status(user_id: int):
        # Активация/деактивация пользователя
    
    @router.get("/users/{user_id}/purchases")
    async def user_purchases(request: Request, user_id: int):
        # История покупок пользователя
    
    @router.post("/users/{user_id}/refund")
    async def refund_purchase(user_id: int, purchase_id: int):
        # Возврат средств за покупку
```

#### Создать `admin/templates/users/`:
- `list.html` - список пользователей
- `detail.html` - профиль пользователя
- `purchases.html` - покупки пользователя

### Шаг 7: Финансовое управление (75 мин)

#### Создать `admin/routes/finance.py`:
```python
class FinanceRoutes:
    @router.get("/finance")
    async def finance_dashboard(request: Request):
        # Финансовый дашборд
    
    @router.get("/finance/payments")
    async def payments_list(request: Request, status: str = "all", date_from: str = None):
        # Список всех платежей
    
    @router.get("/finance/withdrawals")
    async def withdrawals_list(request: Request):
        # Список запросов на вывод средств
    
    @router.post("/finance/withdrawals/{request_id}/approve")
    async def approve_withdrawal(request_id: int):
        # Одобрение запроса на вывод
    
    @router.get("/finance/reports")
    async def financial_reports(request: Request, period: str = "month"):
        # Финансовые отчеты
    
    @router.get("/finance/export")
    async def export_financial_data(format: str = "csv", period: str = "month"):
        # Экспорт финансовых данных
```

### Шаг 8: Управление промокодами (45 мин)

#### Создать `admin/routes/promocodes.py`:
```python
class PromocodesRoutes:
    @router.get("/promocodes")
    async def promocodes_list(request: Request):
        # Список всех промокодов
    
    @router.post("/promocodes/create")
    async def create_promocode(promo_data: dict):
        # Создание нового промокода
    
    @router.put("/promocodes/{code}")
    async def update_promocode(code: str, promo_data: dict):
        # Обновление промокода
    
    @router.delete("/promocodes/{code}")
    async def deactivate_promocode(code: str):
        # Деактивация промокода
    
    @router.get("/promocodes/analytics")
    async def promocodes_analytics(request: Request):
        # Аналитика использования промокодов
```

### Шаг 9: Система уведомлений и логов (30 мин)

#### Создать `admin/routes/system.py`:
```python
class SystemRoutes:
    @router.get("/system/logs")
    async def system_logs(request: Request, level: str = "all"):
        # Просмотр системных логов
    
    @router.get("/system/notifications")
    async def notifications_center(request: Request):
        # Центр уведомлений
    
    @router.post("/system/broadcast")
    async def send_broadcast(message: str, target: str = "all"):
        # Отправка рассылки пользователям
    
    @router.get("/system/settings")
    async def system_settings(request: Request):
        # Настройки системы
```

### Шаг 10: Интерфейс и UX (60 мин)

#### Создать базовые шаблоны в `admin/templates/`:
- `base.html` - базовый шаблон
- `navbar.html` - навигационная панель
- `sidebar.html` - боковое меню
- `footer.html` - подвал

#### Создать стили в `admin/static/css/admin.css`:
```css
/* Кастомные стили для админки */
.admin-sidebar {
    /* Стили сайдбара */
}

.stats-card {
    /* Стили для карточек статистики */
}

.data-table {
    /* Стили для таблиц данных */
}
```

#### Создать JavaScript в `admin/static/js/admin.js`:
```javascript
// Инициализация графиков
function initCharts() {
    // Chart.js графики для статистики
}

// AJAX запросы для обновления данных
function updateDashboard() {
    // Обновление дашборда без перезагрузки
}

// Обработка форм
function setupForms() {
    // Валидация форм и AJAX отправка
}
```

## Структура файлов для создания

```
admin/
├── main.py                   # Основной FastAPI app
├── config.py                 # Конфигурация админки
├── auth/
│   ├── __init__.py
│   └── auth_service.py       # Сервис аутентификации
├── routes/
│   ├── __init__.py
│   ├── auth.py              # Маршруты аутентификации
│   ├── dashboard.py         # Дашборд
│   ├── lessons.py           # Управление уроками
│   ├── users.py             # Управление пользователями
│   ├── finance.py           # Финансы
│   ├── promocodes.py        # Промокоды
│   └── system.py            # Системные функции
├── utils/
│   ├── __init__.py
│   ├── file_manager.py      # Управление файлами
│   ├── decorators.py        # Декораторы безопасности
│   └── helpers.py           # Вспомогательные функции
├── templates/
│   ├── base.html            # Базовый шаблон
│   ├── login.html           # Страница входа
│   ├── dashboard.html       # Дашборд
│   ├── lessons/
│   │   ├── list.html
│   │   ├── create.html
│   │   └── edit.html
│   ├── users/
│   │   ├── list.html
│   │   └── detail.html
│   ├── finance/
│   │   ├── dashboard.html
│   │   ├── payments.html
│   │   └── reports.html
│   └── system/
│       ├── logs.html
│       └── settings.html
├── static/
│   ├── css/
│   │   ├── bootstrap.min.css
│   │   └── admin.css
│   ├── js/
│   │   ├── bootstrap.min.js
│   │   ├── chart.min.js
│   │   └── admin.js
│   └── images/
└── tests/
    ├── test_auth.py
    ├── test_routes.py
    └── test_file_manager.py
```

## Критерии готовности

### Обязательные требования:
✅ Админ-панель доступна по адресу http://localhost:8001  
✅ JWT аутентификация работает корректно  
✅ Дашборд отображает актуальную статистику  
✅ CRUD операции для уроков функционируют  
✅ Загрузка медиафайлов работает (drag & drop)  
✅ Управление пользователями реализовано  
✅ Финансовые отчеты генерируются  
✅ Система промокодов управляется через интерфейс  
✅ Responsive дизайн на разных устройствах  
✅ Все формы имеют валидацию  

### Проверка готовности:
```bash
# Запуск админ-панели
cd admin/
uvicorn main:app --host localhost --port 8001 --reload

# Проверка доступности
curl http://localhost:8001/login

# Проверка API endpoints
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Тестирование
pytest admin/tests/ -v --cov=admin
```

## Формат документации для других агентов

После завершения создайте `docs/agents/ADMINISTRATION_COMPLETE.md`:

### Раздел 1: Реализованная функциональность
- Подробное описание всех страниц админки
- API endpoints админ-панели
- Система разрешений и ролей
- Интерфейс управления контентом

### Раздел 2: Интеграция с существующими системами

#### Backend API Integration:
```python
# Примеры запросов к Backend API из админки
async def get_lessons_for_admin():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "http://localhost:8000/api/lessons/",
            headers={"Authorization": f"Bearer {admin_token}"}
        ) as response:
            return await response.json()
```

#### File Management Integration:
```python
# Загрузка файлов уроков
UPLOAD_CONFIG = {
    "max_file_size": "100MB",
    "allowed_video_formats": ["mp4", "mov", "avi"],
    "storage_path": "./storage/",
    "thumbnail_generation": True
}
```

### Раздел 3: Административные функции

#### Контент-менеджмент:
- Создание и редактирование уроков
- Загрузка видео и миниатюр
- Управление ценами и доступностью
- Организация в курсы

#### Пользователи:
- Просмотр профилей и активности
- Управление статусом аккаунтов
- История покупок и платежей
- Поддержка пользователей

#### Финансы:
- Мониторинг доходов и трат
- Управление выводом средств
- Отчеты и аналитика
- Налоговые документы

### Раздел 4: Настройки системы
```json
{
  "admin_settings": {
    "session_timeout": 3600,
    "max_upload_size": "100MB",
    "backup_frequency": "daily",
    "notification_email": "admin@example.com"
  },
  "ui_settings": {
    "theme": "light",
    "language": "en",
    "items_per_page": 20,
    "charts_refresh_interval": 30
  }
}
```

### Раздел 5: Интеграция с Agent 5 (Communication)

#### Рассылки из админки:
```python
# Отправка рассылки через админ-панель
BROADCAST_INTEGRATION = {
    "endpoint": "/system/broadcast",
    "targets": ["all_users", "active_users", "recent_buyers"],
    "message_types": ["text", "rich_text", "promotional"]
}
```

#### Уведомления администратора:
```python
# Настройка уведомлений
ADMIN_NOTIFICATIONS = {
    "new_user_registration": True,
    "payment_completed": True,
    "payment_failed": True,
    "support_ticket_created": True,
    "daily_revenue_report": True
}
```

### Раздел 6: Мониторинг и логирование
- Логи действий администратора
- Мониторинг производительности системы
- Алерты о критических событиях
- Резервное копирование данных

### Раздел 7: Безопасность
- Двухфакторная аутентификация (планы)
- Логирование всех административных действий
- IP-ограничения для доступа
- Регулярная смена паролей

## Следующие шаги для Agent 5 (Communication)

### Интеграция рассылок:
- Подключить систему рассылок к админ-панели
- Создать интерфейс для массовых уведомлений
- Реализовать шаблоны сообщений
- Настроить автоматические уведомления

### Поддержка пользователей:
- Интегрировать тикеты поддержки в админку
- Создать интерфейс для ответов пользователям
- Настроить уведомления о новых обращениях
- Реализовать систему FAQ

**Важно**: Убедитесь, что все административные действия логируются и система безопасна для использования в продакшене!