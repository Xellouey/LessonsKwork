"""
Тесты для API endpoints.
"""

import pytest
from fastapi import status


class TestHealthEndpoints:
    """Тесты для health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Тест корневого endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"
    
    def test_health_check(self, client):
        """Тест health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "components" in data
        assert "database" in data["components"]
        assert "storage" in data["components"]
    
    def test_system_info(self, client):
        """Тест system info endpoint."""
        response = client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "features" in data


class TestAuthEndpoints:
    """Тесты для authentication endpoints."""
    
    def test_login_success(self, client, admin_user):
        """Тест успешной авторизации."""
        login_data = {
            "username": admin_user.username,
            "password": "test_password"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, admin_user):
        """Тест авторизации с неверным паролем."""
        login_data = {
            "username": admin_user.username,
            "password": "wrong_password"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
    
    def test_login_nonexistent_user(self, client):
        """Тест авторизации несуществующего пользователя."""
        login_data = {
            "username": "nonexistent",
            "password": "password"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
    
    def test_get_current_user(self, client, auth_headers):
        """Тест получения текущего пользователя."""
        response = client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "username" in data
        assert "email" in data
        assert "is_active" in data
        assert "is_superuser" in data
    
    def test_unauthorized_access(self, client):
        """Тест доступа без авторизации."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_refresh_token(self, client, auth_headers):
        """Тест обновления токена."""
        response = client.post("/auth/refresh", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
    
    def test_logout(self, client, auth_headers):
        """Тест выхода из системы."""
        response = client.post("/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestUsersEndpoints:
    """Тесты для users endpoints."""
    
    def test_get_users(self, client, auth_headers, test_user):
        """Тест получения списка пользователей."""
        response = client.get("/api/v1/users/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) >= 1
    
    def test_get_user_by_id(self, client, auth_headers, test_user):
        """Тест получения пользователя по ID."""
        response = client.get(f"/api/v1/users/{test_user.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["telegram_id"] == test_user.telegram_id
        assert data["first_name"] == test_user.first_name
    
    def test_get_nonexistent_user(self, client, auth_headers):
        """Тест получения несуществующего пользователя."""
        response = client.get("/api/v1/users/99999", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_create_user(self, client, auth_headers):
        """Тест создания пользователя."""
        user_data = {
            "telegram_id": 987654321,
            "username": "new_user",
            "first_name": "New",
            "last_name": "User",
            "language_code": "ru"
        }
        
        response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["telegram_id"] == user_data["telegram_id"]
        assert data["username"] == user_data["username"]
        assert data["first_name"] == user_data["first_name"]
    
    def test_create_duplicate_user(self, client, auth_headers, test_user):
        """Тест создания пользователя с существующим telegram_id."""
        user_data = {
            "telegram_id": test_user.telegram_id,
            "first_name": "Duplicate"
        }
        
        response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
        
        assert response.status_code == 400
    
    def test_find_or_create_user(self, client):
        """Тест поиска или создания пользователя."""
        user_data = {
            "telegram_id": 111222333,
            "first_name": "Auto",
            "last_name": "Created"
        }
        
        # Первый вызов - создание
        response = client.post("/api/v1/users/find-or-create", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        user_id = data["id"]
        
        # Второй вызов - поиск существующего
        response = client.post("/api/v1/users/find-or-create", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id  # Тот же пользователь


class TestLessonsEndpoints:
    """Тесты для lessons endpoints."""
    
    def test_get_lessons(self, client, auth_headers, test_lesson):
        """Тест получения списка уроков."""
        response = client.get("/api/v1/lessons/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1
    
    def test_get_public_lessons(self, client, test_lesson):
        """Тест получения публичного списка уроков."""
        response = client.get("/api/v1/lessons/public")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1
    
    def test_get_lesson_by_id(self, client, auth_headers, test_lesson):
        """Тест получения урока по ID."""
        response = client.get(f"/api/v1/lessons/{test_lesson.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_lesson.id
        assert data["title"] == test_lesson.title
    
    def test_create_lesson(self, client, auth_headers):
        """Тест создания урока."""
        lesson_data = {
            "title": "New Lesson",
            "description": "A new lesson for testing",
            "price": 200,
            "is_free": False
        }
        
        response = client.post("/api/v1/lessons/", json=lesson_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == lesson_data["title"]
        assert data["price"] == lesson_data["price"]
    
    def test_update_lesson(self, client, auth_headers, test_lesson):
        """Тест обновления урока."""
        update_data = {
            "title": "Updated Lesson",
            "price": 250
        }
        
        response = client.put(
            f"/api/v1/lessons/{test_lesson.id}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["price"] == update_data["price"]
    
    def test_delete_lesson(self, client, auth_headers, test_lesson):
        """Тест удаления урока."""
        response = client.delete(f"/api/v1/lessons/{test_lesson.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestCoursesEndpoints:
    """Тесты для courses endpoints."""
    
    def test_get_courses(self, client, auth_headers, test_course):
        """Тест получения списка курсов."""
        response = client.get("/api/v1/courses/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1
    
    def test_get_course_by_id(self, client, auth_headers, test_course):
        """Тест получения курса по ID."""
        response = client.get(f"/api/v1/courses/{test_course.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_course.id
        assert data["title"] == test_course.title
        assert "lessons" in data
    
    def test_create_course(self, client, auth_headers, test_lesson):
        """Тест создания курса."""
        course_data = {
            "title": "New Course",
            "description": "A new course for testing",
            "total_price": 1000,
            "discount_price": 800,
            "lesson_ids": [test_lesson.id]
        }
        
        response = client.post("/api/v1/courses/", json=course_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == course_data["title"]
        assert data["total_price"] == course_data["total_price"]