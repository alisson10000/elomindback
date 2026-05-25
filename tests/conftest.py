from __future__ import annotations

import os
import sys
from pathlib import Path

# Garante que `import app` funcione mesmo quando o pytest ajustar o CWD/sys.path.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("DATABASE_URL", "sqlite:///./pytest_bootstrap.db")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.audit.model import AuditLog
from app.modules.users.model import User
from app.modules.users.service import create_user
from utils import security as field_security


USE_ENV_DB = os.getenv("ELOMIND_TEST_USE_ENV_DB") == "1"
KEEP_ENV_TEST_DB = os.getenv("ELOMIND_TEST_KEEP_DB") == "1"
DIRECT_TEST_DATABASE_URL = os.getenv("ELOMIND_TEST_DATABASE_URL")
PRESERVE_TEST_DATA = os.getenv("PRESERVE_TEST_DATA") == "1"


@pytest.fixture(autouse=True)
def clear_security_cache():
    field_security._get_fernet_candidates.cache_clear()
    yield
    field_security._get_fernet_candidates.cache_clear()


def _build_admin_url(database_url: str) -> URL:
    url = make_url(database_url)
    return url.set(database=None, query={})


def _build_test_database_url(database_url: str) -> tuple[URL, str]:
    url = make_url(database_url)
    base_name = url.database or "elomind"
    test_name = f"{base_name}_pytest"
    return url.set(database=test_name), test_name


def _reset_schema(test_engine) -> None:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="session")
def test_engine():
    if not USE_ENV_DB:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        yield engine
        engine.dispose()
        return

    source_database_url = os.environ["DATABASE_URL"]
    if DIRECT_TEST_DATABASE_URL:
        direct_url = make_url(DIRECT_TEST_DATABASE_URL)
        if direct_url.get_backend_name() == "mysql" and direct_url.database:
            admin_engine = create_engine(
                _build_admin_url(DIRECT_TEST_DATABASE_URL),
                pool_pre_ping=True,
                isolation_level="AUTOCOMMIT",
            )
            try:
                with admin_engine.connect() as conn:
                    conn.exec_driver_sql(f"DROP DATABASE IF EXISTS `{direct_url.database}`")
                    conn.exec_driver_sql(
                        f"CREATE DATABASE `{direct_url.database}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
            finally:
                admin_engine.dispose()

        engine = create_engine(DIRECT_TEST_DATABASE_URL, pool_pre_ping=True)
        try:
            yield engine
        finally:
            engine.dispose()
        return
    test_database_url, test_database_name = _build_test_database_url(source_database_url)
    created_database = False
    admin_engine = create_engine(
        _build_admin_url(source_database_url),
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
    )

    try:
        try:
            with admin_engine.connect() as conn:
                conn.exec_driver_sql(f"DROP DATABASE IF EXISTS `{test_database_name}`")
                conn.exec_driver_sql(
                    f"CREATE DATABASE `{test_database_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            created_database = True
        except OperationalError as exc:
            message = str(exc).lower()
            if "access denied" not in message and "1044" not in message:
                raise
    finally:
        admin_engine.dispose()

    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()
        if created_database and not KEEP_ENV_TEST_DB:
            admin_engine = create_engine(
                _build_admin_url(source_database_url),
                pool_pre_ping=True,
                isolation_level="AUTOCOMMIT",
            )
            try:
                with admin_engine.connect() as conn:
                    conn.exec_driver_sql(f"DROP DATABASE IF EXISTS `{test_database_name}`")
            finally:
                admin_engine.dispose()


@pytest.fixture(scope="session")
def session_factory(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def preserved_audit_logs(test_engine):
    rows: list[dict] = []
    yield rows

    if not PRESERVE_TEST_DATA or not rows:
        return

    _reset_schema(test_engine)

    session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
        expire_on_commit=False,
    )()
    try:
        for row in rows:
            session.add(AuditLog(**row))
        session.commit()
    finally:
        session.close()


@pytest.fixture
def db_session(test_engine, session_factory, preserved_audit_logs):
    _reset_schema(test_engine)
    session = session_factory()
    try:
        yield session
    finally:
        if PRESERVE_TEST_DATA:
            audit_session = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=test_engine,
                expire_on_commit=False,
            )()
            try:
                for row in audit_session.query(AuditLog).order_by(AuditLog.id.asc()).all():
                    preserved_audit_logs.append(
                        {
                            "user_id": None,
                            "action": row.action,
                            "resource_type": row.resource_type,
                            "resource_id": row.resource_id,
                            "ip_address": row.ip_address,
                            "user_agent": row.user_agent,
                            "details": row.details,
                            "created_at": row.created_at,
                        }
                    )
            finally:
                audit_session.close()
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_factory(db_session):
    def factory(
        *,
        email: str = "client@example.com",
        name: str = "Client Test",
        role: str = "client",
        password: str = "StrongPass123",
    ) -> User:
        return create_user(
            db_session,
            email=email,
            name=name,
            role=role,
            password_hash=hash_password(password),
        )

    return factory


@pytest.fixture
def auth_headers():
    def factory(user: User) -> dict[str, str]:
        token = create_access_token(subject=str(user.id))
        return {"Authorization": f"Bearer {token}"}

    return factory


@pytest.fixture
def legacy_user_factory(db_session):
    def factory(
        *,
        email: str = "legacy@example.com",
        name: str = "Legacy User",
        role: str = "client",
        password: str = "StrongPass123",
    ) -> User:
        user = User(
            email_hash="",
            email_encrypted="",
            name_encrypted="",
            legacy_email=email,
            legacy_name=name,
            role=role,
            password_hash=hash_password(password),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return factory


@pytest.fixture
def force_authenticated_user():
    def factory(user: User):
        app.dependency_overrides[get_current_user] = lambda: user
        return user

    yield factory
    app.dependency_overrides.pop(get_current_user, None)
