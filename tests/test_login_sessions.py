import pytest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

import login_sessions
from db import Base, enable_foreign_keys
from models import LoginSession, User


@pytest.fixture
def session_database(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'sessions.db').as_posix()}"
    )
    event.listen(engine, "connect", enable_foreign_keys)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user = User(
            username="session_tester",
            password_hash="unused-in-session-unit-tests",
        )
        db.add(user)
        db.commit()
        user_id = user.id

    try:
        yield engine, user_id
    finally:
        engine.dispose()


def test_session_survives_reopening_database(session_database):
    engine, user_id = session_database

    with Session(engine) as db:
        token = login_sessions.create_login_session(db, user_id)
        db.commit()

    # 换一个数据库连接，仍应识别这个会话。
    with Session(engine) as db:
        active = login_sessions.get_active_session(db, token)

        assert active is not None
        assert active.user_id == user_id
        assert active.token_hash != token
        assert active.token_hash == login_sessions.hash_session_token(token)
        assert len(active.token_hash) == 64


def test_session_expires_at_deadline(session_database, monkeypatch):
    engine, user_id = session_database

    monkeypatch.setattr(login_sessions, "now_timestamp", lambda: 1000)

    with Session(engine) as db:
        token = login_sessions.create_login_session(db, user_id)
        db.commit()

    deadline = 1000 + login_sessions.SESSION_TTL_SECONDS

    with Session(engine) as db:
        monkeypatch.setattr(
            login_sessions, "now_timestamp", lambda: deadline - 1
        )
        assert login_sessions.get_active_session(db, token) is not None

        monkeypatch.setattr(
            login_sessions, "now_timestamp", lambda: deadline
        )
        assert login_sessions.get_active_session(db, token) is None


def test_logout_revokes_only_current_session(session_database):
    engine, user_id = session_database

    with Session(engine) as db:
        first = login_sessions.create_login_session(db, user_id)
        second = login_sessions.create_login_session(db, user_id)
        db.commit()

        assert first != second

        login_sessions.revoke_login_session(db, first)
        db.commit()

    with Session(engine) as db:
        assert login_sessions.get_active_session(db, first) is None
        assert login_sessions.get_active_session(db, second) is not None

        stored = db.get(
            LoginSession,
            login_sessions.hash_session_token(first),
        )
        assert stored is not None
        assert stored.revoked_at is not None

        # 重复退出不应报错。
        login_sessions.revoke_login_session(db, first)
        db.commit()


@pytest.mark.parametrize("token", [
    "",
    "invalid",
    "A" * 43,
])
def test_unknown_or_malformed_token_is_rejected(
    session_database, token
):
    engine, _ = session_database

    with Session(engine) as db:
        assert login_sessions.get_active_session(db, token) is None