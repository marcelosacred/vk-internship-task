import pytest

# тесты для проверки основных сценариев работы API
# - проверка эндпоинта /health
# - создание юзера - проверка, что пароль не возвращается
# - получение юзеров - сначала пустой, потом после создания - 1 юзер
# - блокировка юзера - проверка, что locktime установился
# - блокировка при отсутствии свободных юзеров - 404
# - разблокировка юзеров - проверка, что после free юзер снова доступен
# - создание дубликата юзера - 400 или 500

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_user(client, user_data):
    resp = await client.post("/api/v1/users", json=user_data)
    assert resp.status_code == 201
    data = resp.json()
    assert data["login"] == user_data["login"]
    assert "id" in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_get_users_empty(client):
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_users_after_create(client, user_data):
    await client.post("/api/v1/users", json=user_data)
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 1
    assert users[0]["login"] == user_data["login"]


@pytest.mark.asyncio
async def test_lock_user(client, user_data):
    await client.post("/api/v1/users", json=user_data)

    resp = await client.post("/api/v1/users/lock")
    assert resp.status_code == 200
    data = resp.json()
    assert data["locktime"] is not None


@pytest.mark.asyncio
async def test_lock_no_free_users(client, user_data):
    await client.post("/api/v1/users", json=user_data)
    await client.post("/api/v1/users/lock")

    # второй раз - свободных нет
    resp = await client.post("/api/v1/users/lock")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_free_users(client, user_data):
    await client.post("/api/v1/users", json=user_data)
    await client.post("/api/v1/users/lock")

    resp = await client.post("/api/v1/users/free")
    assert resp.status_code == 200

    # после free юзер снова доступен
    resp = await client.post("/api/v1/users/lock")
    assert resp.status_code == 200
    assert resp.json()["locktime"] is not None


@pytest.mark.asyncio
async def test_create_duplicate_user(client, user_data):
    await client.post("/api/v1/users", json=user_data)
    resp = await client.post("/api/v1/users", json=user_data)
    assert resp.status_code == 500 or resp.status_code == 400
