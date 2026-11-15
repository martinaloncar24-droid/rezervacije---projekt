from app.models import DiningTable
from tests.conftest import add_reservation, auth_header

# --- čitanje -------------------------------------------------------------------


async def test_list_tables_requires_login(client, table):
    resp = await client.get("/tables/")
    assert resp.status_code == 401


async def test_guest_can_list_tables(client, guest, table):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.get("/tables/", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == [
        {"id": table.id, "number": 1, "capacity": 4, "location": "terasa"}
    ]


async def test_list_tables_pagination_and_filter(client, db, guest):
    for number, location in [(1, "terasa"), (2, "terasa"), (3, "ulica")]:
        db.add(DiningTable(number=number, capacity=4, location=location))
    await db.commit()
    headers = await auth_header(client, "gost", "gost1234")

    resp = await client.get("/tables/?limit=1&offset=1", headers=headers)
    assert [t["number"] for t in resp.json()] == [2]

    resp = await client.get("/tables/?location=ulica", headers=headers)
    assert [t["number"] for t in resp.json()] == [3]


async def test_limit_over_100_is_422(client, guest):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.get("/tables/?limit=101", headers=headers)
    assert resp.status_code == 422


async def test_get_unknown_table_is_404(client, guest):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.get("/tables/9999", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


# --- uloge: samo admin mijenja stolove ----------------------------------------------


async def test_guest_cannot_create_table(client, guest):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(
        "/tables/",
        json={"number": 9, "capacity": 4, "location": "terasa"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_admin_creates_table(client, admin_user):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post(
        "/tables/",
        json={"number": 9, "capacity": 6, "location": "ulica"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["number"] == 9


async def test_duplicate_table_number_is_409(client, admin_user, table):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post(
        "/tables/",
        json={"number": 1, "capacity": 2, "location": "ulica"},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "duplicate"


async def test_unknown_location_is_422(client, admin_user):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post(
        "/tables/",
        json={"number": 9, "capacity": 4, "location": "krov"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["errors"][0]["field"] == "location"


async def test_admin_updates_only_sent_fields(client, admin_user, table):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.patch(
        f"/tables/{table.id}", json={"capacity": 8}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["capacity"] == 8
    # Polja koja nisu poslana ostaju nepromijenjena
    assert body["location"] == "terasa"


async def test_update_with_null_is_422(client, admin_user, table):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.patch(
        f"/tables/{table.id}", json={"capacity": None}, headers=headers
    )
    assert resp.status_code == 422


async def test_guest_cannot_delete_table(client, guest, table):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.delete(f"/tables/{table.id}", headers=headers)
    assert resp.status_code == 403


async def test_admin_deletes_table_without_reservations(client, admin_user, table):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.delete(f"/tables/{table.id}", headers=headers)
    assert resp.status_code == 204
    resp = await client.get(f"/tables/{table.id}", headers=headers)
    assert resp.status_code == 404


async def test_table_with_reservations_cannot_be_deleted(
    client, db, admin_user, guest, table
):
    await add_reservation(db, guest, table)
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.delete(f"/tables/{table.id}", headers=headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "table_has_reservations"
