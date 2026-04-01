from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import update

from app.models.user import User

# тесты для проверки основных сценариев работы API
# - проверка эндпоинта /health
# - создание юзера - проверка, что пароль не возвращается
# - получение юзеров - сначала пустой, потом после создания - 1 юзер
# - блокировка юзера - проверка, что locktime установился
# - блокировка при отсутствии свободных юзеров - 404
# - разблокировка юзеров - проверка, что после free юзер снова доступен
# - создание дубликата юзера - 400 или 500
# - создание юзера с невалидными enum полями - 422
# - блокировка юзера, когда предыдущая блокировка уже истекла - долженся заблокировать тот же юзер, что и в первый раз
# - получение токена с неверными данными - 401
# - доступ к защищенным эндпоинтам без токена - 401
# - liveness probe - 200
# - startup probe - 200
# - readiness probe - 200

async def get_auth_headers(client):
    resp = await client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "admin"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_liveness_probe(client):
    resp = await client.get("/health/liveness")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_startup_probe(client):
    resp = await client.get("/health/startup")
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"


@pytest.mark.asyncio
async def test_readiness_probe(client):
    resp = await client.get("/health/readiness")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_create_user(client, user_data):
    headers = await get_auth_headers(client)
    resp = await client.post("/api/v1/users", json=user_data, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["login"] == user_data["login"]
    assert "id" in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_get_users_empty(client):
    headers = await get_auth_headers(client)
    resp = await client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_users_after_create(client, user_data):
    headers = await get_auth_headers(client)
    await client.post("/api/v1/users", json=user_data, headers=headers)
    resp = await client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 1
    assert users[0]["login"] == user_data["login"]


@pytest.mark.asyncio
async def test_lock_user(client, user_data):
    headers = await get_auth_headers(client)
    await client.post("/api/v1/users", json=user_data, headers=headers)

    before_lock = datetime.now(timezone.utc).replace(tzinfo=None)
    resp = await client.post("/api/v1/users/lock", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["locktime"] is not None

    locktime = datetime.fromisoformat(data["locktime"].replace("Z", "+00:00"))
    if locktime.tzinfo is not None:
        locktime = locktime.astimezone(timezone.utc).replace(tzinfo=None)
    assert locktime > before_lock


@pytest.mark.asyncio
async def test_lock_no_free_users(client, user_data):
    headers = await get_auth_headers(client)
    await client.post("/api/v1/users", json=user_data, headers=headers)
    await client.post("/api/v1/users/lock", headers=headers)

    # второй раз - свободных нет
    resp = await client.post("/api/v1/users/lock", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_free_users(client, user_data):
    headers = await get_auth_headers(client)
    await client.post("/api/v1/users", json=user_data, headers=headers)
    await client.post("/api/v1/users/lock", headers=headers)

    resp = await client.post("/api/v1/users/free", headers=headers)
    assert resp.status_code == 200

    # после free юзер снова доступен
    resp = await client.post("/api/v1/users/lock", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["locktime"] is not None


@pytest.mark.asyncio
async def test_create_duplicate_user(client, user_data):
    headers = await get_auth_headers(client)
    await client.post("/api/v1/users", json=user_data, headers=headers)
    resp = await client.post("/api/v1/users", json=user_data, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "login already exists"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("env", "dev"),
        ("domain", "beta"),
    ],
)
async def test_create_user_invalid_enums(client, user_data, field, value):
    headers = await get_auth_headers(client)
    payload = dict(user_data)
    payload[field] = value

    resp = await client.post("/api/v1/users", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_lock_user_when_previous_lock_expired(client, db_session, user_data):
    headers = await get_auth_headers(client)
    create_resp = await client.post("/api/v1/users", json=user_data, headers=headers)
    assert create_resp.status_code == 201
    user_id = UUID(create_resp.json()["id"])

    first_lock = await client.post("/api/v1/users/lock", headers=headers)
    assert first_lock.status_code == 200

    expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.execute(
        update(User).where(User.id == user_id).values(locktime=expired_at)
    )
    await db_session.commit()

    second_lock = await client.post("/api/v1/users/lock", headers=headers)
    assert second_lock.status_code == 200
    assert UUID(second_lock.json()["id"]) == user_id


@pytest.mark.asyncio
async def test_auth_invalid_credentials(client):
    resp = await client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid credentials"


@pytest.mark.asyncio
async def test_users_endpoint_requires_token(client):
    resp = await client.get("/api/v1/users")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "missing authorization token"
