import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import Base, engine, SessionLocal
from app.core.config import settings

@pytest.fixture(autouse=True, scope="session")
def setup_db():
    # fresh db for tests
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def client(monkeypatch):
    # disable meta hiding for tests
    settings.ALLOW_DEV_DEBUG_META = True
    return TestClient(app)
