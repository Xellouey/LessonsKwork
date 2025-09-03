"""
Главное FastAPI приложение.
Инициализация, роутинг, middleware, обработка ошибок.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.database import init_database, check_database_connection, get_database_info
from shared import helper_functions as utils
from shared.database import get_db
from backend.config import settings, validate_environment, create_directories, get_cors_settings, get_api_settings
from backend.api import auth, users, lessons, courses, payments, promocodes, finance

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    logger.info("🚀 Запуск приложения Lessons Bot API")
    
    try:
        # Валидация конфигурации
        validate_environment()
        logger.info("✅ Конфигурация валидна")
        
        # Создание директорий
        create_directories()
        logger.info("✅ Директории созданы")
        
        # Инициализация базы данных
        init_database()
        logger.info("✅ База данных инициализирована")
        
        # Создание тестовых данных в режиме разработки
        if settings.is_development:
            try:
                db = next(get_db())
                utils.create_sample_data(db)
                db.close()
                logger.info("✅ Тестовые данные созданы")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось создать тестовые данные: {e}")
        
        logger.info("🎉 Приложение успешно запущено")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске приложения: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Завершение работы приложения")


# Создание FastAPI приложения
app = FastAPI(
    lifespan=lifespan,
    **get_api_settings()
)

# Добавление CORS middleware
app.add_middleware(
    CORSMiddleware,
    **get_cors_settings()
)


# Обработчики ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP ошибок."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    """Обработчик Starlette HTTP ошибок."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error", 
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Validation failed",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик общих ошибок."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "Internal server error occurred"
        }
    )


# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware для логирования HTTP запросов."""
    import time
    
    start_time = time.time()
    
    # Логирование входящего запроса
    if settings.debug:
        logger.info(f"📥 {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Логирование времени обработки
    process_time = time.time() - start_time
    if settings.debug:
        logger.info(f"📤 {request.method} {request.url} - {response.status_code} ({process_time:.3f}s)")
    
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Основные маршруты
@app.get("/", summary="Корневой эндпоинт")
async def root():
    """Корневой эндпоинт API."""
    return {
        "message": "Lessons Bot API",
        "version": settings.app_version,
        "status": "running",
        "docs_url": "/docs" if settings.debug else None
    }


@app.get("/health", summary="Проверка здоровья системы")
async def health_check():
    """
    Проверка здоровья системы.
    Возвращает статус всех критичных компонентов.
    """
    from datetime import datetime
    
    # Проверка базы данных
    db_connected = check_database_connection()
    db_info = get_database_info() if db_connected else {}
    
    # Проверка файловой системы
    storage_accessible = os.path.exists(settings.storage_path) and os.access(settings.storage_path, os.W_OK)
    
    # Общий статус
    overall_status = "healthy" if db_connected and storage_accessible else "unhealthy"
    
    health_info = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "components": {
            "database": {
                "status": "connected" if db_connected else "disconnected",
                "details": db_info
            },
            "storage": {
                "status": "accessible" if storage_accessible else "inaccessible",
                "path": settings.storage_path
            }
        }
    }
    
    status_code = status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(content=health_info, status_code=status_code)


@app.get("/info", summary="Информация о системе")
async def system_info():
    """Получение информации о системе."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "database_url": settings.database_url.split("://")[0] + "://***",  # Скрываем детали
        "api_prefix": settings.api_v1_prefix,
        "features": {
            "authentication": True,
            "file_upload": True,
            "cors_enabled": True,
            "docs_enabled": settings.debug
        }
    }


# Подключение роутеров API
app.include_router(
    auth.router,
    prefix=settings.auth_prefix,
    tags=["Authentication"]
)

app.include_router(
    users.router,
    prefix=f"{settings.api_v1_prefix}/users",
    tags=["Users"]
)

app.include_router(
    lessons.router,
    prefix=f"{settings.api_v1_prefix}/lessons",
    tags=["Lessons"]
)

app.include_router(
    courses.router,
    prefix=f"{settings.api_v1_prefix}/courses",
    tags=["Courses"]
)

app.include_router(
    payments.router,
    prefix=f"{settings.api_v1_prefix}/payments",
    tags=["Payments"]
)

app.include_router(
    promocodes.router,
    prefix=f"{settings.api_v1_prefix}/promocodes",
    tags=["Promocodes"]
)

app.include_router(
    finance.router,
    prefix=f"{settings.api_v1_prefix}/finance",
    tags=["Finance"]
)


# Маршрут для статистики (общий)
@app.get(f"{settings.api_v1_prefix}/statistics", summary="Общая статистика системы")
async def get_system_statistics():
    """
    Получение общей статистики системы.
    Требует аутентификацию администратора.
    """
    from backend.api.deps import get_current_active_admin
    from fastapi import Depends
    from shared.database import get_db
    from sqlalchemy.orm import Session
    from backend.services.user_service import UserService
    from backend.services.lesson_service import LessonService
    
    def get_stats(
        current_user = Depends(get_current_active_admin),
        db: Session = Depends(get_db)
    ):
        user_service = UserService(db)
        lesson_service = LessonService(db)
        
        # Статистика пользователей
        user_stats = user_service.get_users_overview()
        
        # Статистика контента (упрощенная версия)
        from sqlalchemy import func
        from shared.models import Lesson, Course, Purchase
        
        content_stats = {
            "total_lessons": db.query(func.count(Lesson.id)).scalar() or 0,
            "active_lessons": db.query(func.count(Lesson.id)).filter(Lesson.is_active == True).scalar() or 0,
            "total_courses": db.query(func.count(Course.id)).scalar() or 0,
            "active_courses": db.query(func.count(Course.id)).filter(Course.is_active == True).scalar() or 0
        }
        
        # Статистика продаж
        sales_stats = db.query(
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.amount).label("total_revenue"),
            func.count(Purchase.id).filter(Purchase.status == "completed").label("completed_purchases")
        ).first()
        
        return {
            "user_statistics": user_stats,
            "content_statistics": content_stats,
            "sales_statistics": {
                "total_purchases": sales_stats.total_purchases or 0,
                "completed_purchases": sales_stats.completed_purchases or 0,
                "total_revenue": sales_stats.total_revenue or 0
            }
        }
    
    return get_stats


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )