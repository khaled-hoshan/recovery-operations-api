from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import Base, get_db
from app import models
from app.main import app
import pytest
from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config

engine = create_engine(settings.TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session")
def setup_test_database():
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes["database_url"] = settings.TEST_DATABASE_URL

    command.upgrade(alembic_cfg, "head")

    yield


@pytest.fixture()
def db_session(setup_test_database):
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(
        bind=connection, join_transaction_mode="create_savepoint"
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def override_get_db(db_session):
    def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client(override_get_db):
    with TestClient(app) as test_client:
        yield test_client
