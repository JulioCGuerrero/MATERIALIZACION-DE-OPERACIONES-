from pathlib import Path

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app(tmp_path: Path):
    class TestConfig:
        BASE_DIR = tmp_path
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        TESTING = True

    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
