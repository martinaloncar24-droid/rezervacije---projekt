from tests.conftest import auth_header


async def login(client, username, password):
    return await client.post(
        "/auth/login", json={"username": username, "password": password}
    )


# --- prijava -------------------------------------------------------------------


async def test_login_success_returns_both_tokens(client, admin_user):
    resp = await login(client, "testadmin", "admin123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


async def test_login_wrong_password(client, admin_user):
    resp = await login(client, "testadmin", "kriva")
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


async def test_login_unknown_user_same_response_as_wrong_password(client, admin_user):
    wrong_password = await login(client, "testadmin", "kriva")
    unknown_user = await login(client, "nepostojeci", "kriva")
    assert unknown_user.status_code == 401
    # Odgovor ne smije odati postoji li korisničko ime
    assert unknown_user.json() == wrong_password.json()


async def test_inactive_user_cannot_login(client, inactive_user):
    resp = await login(client, "neaktivan", "pass1234")
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


# --- /auth/me ------------------------------------------------------------------


async def test_me_without_token_is_401(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


async def test_me_with_invalid_token_is_401(client):
    resp = await client.get(
        "/auth/me", headers={"Authorization": "Bearer nije.pravi.token"}
    )
    assert resp.status_code == 401


async def test_me_returns_user_without_password_hash(client, guest):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "gost"
    assert body["role"] == "guest"
    # Hash lozinke nikad ne izlazi iz API-ja
    assert "password_hash" not in body


# --- obnova tokena ---------------------------------------------------------------


async def test_refresh_returns_new_tokens(client, guest):
    tokens = (await login(client, "gost", "gost1234")).json()
    resp = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_access_token_cannot_be_used_as_refresh(client, guest):
    tokens = (await login(client, "gost", "gost1234")).json()
    resp = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert resp.status_code == 401


async def test_refresh_token_cannot_be_used_as_access(client, guest):
    tokens = (await login(client, "gost", "gost1234")).json()
    resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert resp.status_code == 401


# --- registracija ----------------------------------------------------------------


async def test_register_creates_guest(client):
    resp = await client.post(
        "/auth/register", json={"username": "novi@tinel.hr", "password": "lozinka123"}
    )
    assert resp.status_code == 201
    body = resp.json()
    # Uloga se ne prima izvana: svaki novi račun je gost
    assert body["role"] == "guest"
    assert "password_hash" not in body
    # Novi račun se može odmah prijaviti
    assert (await login(client, "novi@tinel.hr", "lozinka123")).status_code == 200


async def test_register_duplicate_username_is_409(client, guest):
    resp = await client.post(
        "/auth/register", json={"username": "gost", "password": "lozinka123"}
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "duplicate"


async def test_register_short_password_is_422(client):
    resp = await client.post(
        "/auth/register", json={"username": "novi@tinel.hr", "password": "kratka"}
    )
    assert resp.status_code == 422
    assert resp.json()["errors"][0]["field"] == "password"
