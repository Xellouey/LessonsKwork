"""
Тесты для моделей базы данных.
"""

import pytest
from datetime import datetime

from shared.models import User, Lesson, Course, CourseLesson, Purchase, PromoCode, AdminUser
from shared.utils import get_password_hash, verify_password


class TestUserModel:
    """Тесты модели пользователя."""
    
    def test_create_user(self, db):
        """Тест создания пользователя."""
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.id is not None
        assert user.telegram_id == 123456789
        assert user.username == "test_user"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.language_code == "en"
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
    
    def test_user_telegram_id_unique(self, db):
        """Тест уникальности telegram_id."""
        user1 = User(
            telegram_id=123456789,
            first_name="User1"
        )
        user2 = User(
            telegram_id=123456789,
            first_name="User2"
        )
        
        db.add(user1)
        db.commit()
        
        db.add(user2)
        
        with pytest.raises(Exception):  # IntegrityError
            db.commit()


class TestLessonModel:
    """Тесты модели урока."""
    
    def test_create_lesson(self, db):
        """Тест создания урока."""
        lesson = Lesson(
            title="Test Lesson",
            description="This is a test lesson",
            price=100,
            is_free=False
        )
        
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        
        assert lesson.id is not None
        assert lesson.title == "Test Lesson"
        assert lesson.description == "This is a test lesson"
        assert lesson.price == 100
        assert lesson.is_free is False
        assert lesson.is_active is True
        assert lesson.video_path is None
        assert lesson.text_content is None
        assert isinstance(lesson.created_at, datetime)
    
    def test_free_lesson(self, db):
        """Тест создания бесплатного урока."""
        lesson = Lesson(
            title="Free Lesson",
            description="This is free",
            price=0,
            is_free=True
        )
        
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        
        assert lesson.is_free is True
        assert lesson.price == 0


class TestCourseModel:
    """Тесты модели курса."""
    
    def test_create_course(self, db):
        """Тест создания курса."""
        course = Course(
            title="Test Course",
            description="This is a test course",
            total_price=500,
            discount_price=400
        )
        
        db.add(course)
        db.commit()
        db.refresh(course)
        
        assert course.id is not None
        assert course.title == "Test Course"
        assert course.total_price == 500
        assert course.discount_price == 400
        assert course.is_active is True
    
    def test_course_with_lessons(self, db):
        """Тест курса с уроками."""
        # Создаем уроки
        lesson1 = Lesson(title="Lesson 1", description="First lesson", price=100)
        lesson2 = Lesson(title="Lesson 2", description="Second lesson", price=150)
        
        db.add_all([lesson1, lesson2])
        db.commit()
        
        # Создаем курс
        course = Course(
            title="Test Course",
            description="Course with lessons",
            total_price=200
        )
        
        db.add(course)
        db.commit()
        
        # Добавляем уроки в курс
        course_lesson1 = CourseLesson(
            course_id=course.id,
            lesson_id=lesson1.id,
            order_index=1
        )
        course_lesson2 = CourseLesson(
            course_id=course.id,
            lesson_id=lesson2.id,
            order_index=2
        )
        
        db.add_all([course_lesson1, course_lesson2])
        db.commit()
        
        # Проверяем связи
        course_lessons = db.query(CourseLesson).filter(
            CourseLesson.course_id == course.id
        ).order_by(CourseLesson.order_index).all()
        
        assert len(course_lessons) == 2
        assert course_lessons[0].lesson_id == lesson1.id
        assert course_lessons[1].lesson_id == lesson2.id


class TestPurchaseModel:
    """Тесты модели покупки."""
    
    def test_create_lesson_purchase(self, db, test_user, test_lesson):
        """Тест создания покупки урока."""
        purchase = Purchase(
            user_id=test_user.id,
            lesson_id=test_lesson.id,
            payment_id="test_payment_123",
            amount=test_lesson.price,
            status="pending"
        )
        
        db.add(purchase)
        db.commit()
        db.refresh(purchase)
        
        assert purchase.id is not None
        assert purchase.user_id == test_user.id
        assert purchase.lesson_id == test_lesson.id
        assert purchase.course_id is None
        assert purchase.payment_id == "test_payment_123"
        assert purchase.amount == test_lesson.price
        assert purchase.status == "pending"
    
    def test_create_course_purchase(self, db, test_user, test_course):
        """Тест создания покупки курса."""
        purchase = Purchase(
            user_id=test_user.id,
            course_id=test_course.id,
            payment_id="test_payment_456",
            amount=test_course.total_price,
            status="completed"
        )
        
        db.add(purchase)
        db.commit()
        db.refresh(purchase)
        
        assert purchase.course_id == test_course.id
        assert purchase.lesson_id is None
        assert purchase.status == "completed"


class TestPromoCodeModel:
    """Тесты модели промокода."""
    
    def test_create_promo_code(self, db):
        """Тест создания промокода."""
        promo = PromoCode(
            code="TEST20",
            discount_percent=20,
            max_uses=100
        )
        
        db.add(promo)
        db.commit()
        db.refresh(promo)
        
        assert promo.id is not None
        assert promo.code == "TEST20"
        assert promo.discount_percent == 20
        assert promo.max_uses == 100
        assert promo.current_uses == 0
        assert promo.is_active is True
    
    def test_promo_code_is_valid_property(self, db):
        """Тест свойства is_valid промокода."""
        from datetime import datetime, timedelta
        
        # Активный промокод
        active_promo = PromoCode(
            code="ACTIVE",
            discount_percent=10,
            is_active=True
        )
        
        # Неактивный промокод
        inactive_promo = PromoCode(
            code="INACTIVE",
            discount_percent=10,
            is_active=False
        )
        
        # Истекший промокод
        expired_promo = PromoCode(
            code="EXPIRED",
            discount_percent=10,
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        
        # Промокод с превышенным лимитом использований
        overused_promo = PromoCode(
            code="OVERUSED",
            discount_percent=10,
            max_uses=5,
            current_uses=10
        )
        
        db.add_all([active_promo, inactive_promo, expired_promo, overused_promo])
        db.commit()
        
        assert active_promo.is_valid is True
        assert inactive_promo.is_valid is False
        assert expired_promo.is_valid is False
        assert overused_promo.is_valid is False


class TestAdminUserModel:
    """Тесты модели администратора."""
    
    def test_create_admin_user(self, db):
        """Тест создания администратора."""
        password = "test_password"
        hashed_password = get_password_hash(password)
        
        admin = AdminUser(
            username="admin",
            email="admin@test.com",
            hashed_password=hashed_password,
            is_superuser=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        assert admin.id is not None
        assert admin.username == "admin"
        assert admin.email == "admin@test.com"
        assert admin.is_active is True
        assert admin.is_superuser is True
        
        # Проверяем, что пароль хешируется правильно
        assert verify_password(password, admin.hashed_password) is True
        assert verify_password("wrong_password", admin.hashed_password) is False
    
    def test_admin_username_unique(self, db):
        """Тест уникальности username администратора."""
        admin1 = AdminUser(
            username="admin",
            email="admin1@test.com",
            hashed_password=get_password_hash("password1")
        )
        admin2 = AdminUser(
            username="admin",
            email="admin2@test.com",
            hashed_password=get_password_hash("password2")
        )
        
        db.add(admin1)
        db.commit()
        
        db.add(admin2)
        
        with pytest.raises(Exception):  # IntegrityError
            db.commit()
    
    def test_admin_email_unique(self, db):
        """Тест уникальности email администратора."""
        admin1 = AdminUser(
            username="admin1",
            email="admin@test.com",
            hashed_password=get_password_hash("password1")
        )
        admin2 = AdminUser(
            username="admin2",
            email="admin@test.com",
            hashed_password=get_password_hash("password2")
        )
        
        db.add(admin1)
        db.commit()
        
        db.add(admin2)
        
        with pytest.raises(Exception):  # IntegrityError
            db.commit()