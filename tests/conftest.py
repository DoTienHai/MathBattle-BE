"""
Pytest configuration and fixtures for testing.
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.models import Base, User
from app.main import app
from app.database.connection import get_db
from app.config import settings
from app.utils.security import PasswordHasher
from httpx import AsyncClient

# Test database URL (in-memory SQLite or separate test database)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_db():
    """Create test database and tables."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def async_client(test_db):
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def verified_user(test_db):
    """
    Fixture: Create a verified, active user in database.
    
    Used for successful login tests.
    """
    async with test_db() as session:
        password = "SecurePass123!"
        password_hash = PasswordHasher.hash_password(password)
        
        user = User(
            email="verified@example.com",
            password_hash=password_hash,
            full_name="Verified User",
            is_verified=True,
            is_active=True,
            account_locked_until=None,
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        user.plain_password = password
        return user


@pytest_asyncio.fixture
async def unverified_user(test_db):
    """
    Fixture: Create an unverified (email not verified) user.
    
    Used to test EMAIL_NOT_VERIFIED error response.
    """
    async with test_db() as session:
        password = "SecurePass123!"
        password_hash = PasswordHasher.hash_password(password)
        
        user = User(
            email="unverified@example.com",
            password_hash=password_hash,
            full_name="Unverified User",
            is_verified=False,
            is_active=True,
            account_locked_until=None,
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        user.plain_password = password
        return user


@pytest_asyncio.fixture
async def inactive_user(test_db):
    """
    Fixture: Create an inactive (suspended) user.
    
    Used to test ACCOUNT_INACTIVE error response.
    """
    async with test_db() as session:
        password = "SecurePass123!"
        password_hash = PasswordHasher.hash_password(password)
        
        user = User(
            email="inactive@example.com",
            password_hash=password_hash,
            full_name="Inactive User",
            is_verified=True,
            is_active=False,
            account_locked_until=None,
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        user.plain_password = password
        return user


@pytest_asyncio.fixture
async def locked_user(test_db):
    """
    Fixture: Create a locked (temporarily suspended) user.
    
    Used to test ACCOUNT_LOCKED error response.
    """
    async with test_db() as session:
        password = "SecurePass123!"
        password_hash = PasswordHasher.hash_password(password)
        
        locked_until = datetime.utcnow() + timedelta(minutes=15)
        
        user = User(
            email="locked@example.com",
            password_hash=password_hash,
            full_name="Locked User",
            is_verified=True,
            is_active=True,
            account_locked_until=locked_until,
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        user.plain_password = password
        return user


@pytest_asyncio.fixture
async def expired_locked_user(test_db):
    """
    Fixture: Create a user whose lock has expired.
    
    Used to test that expired locks don't prevent login.
    """
    async with test_db() as session:
        password = "SecurePass123!"
        password_hash = PasswordHasher.hash_password(password)
        
        locked_until = datetime.utcnow() - timedelta(minutes=5)
        
        user = User(
            email="expired_lock@example.com",
            password_hash=password_hash,
            full_name="Expired Lock User",
            is_verified=True,
            is_active=True,
            account_locked_until=locked_until,
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        user.plain_password = password
        return user


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
