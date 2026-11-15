import pytest
from freezegun import freeze_time

from tests.conftest import START, add_reservation, auth_header

# START = 20.12.2026. u 19:00 UTC (vidi conftest.py)
START_ISO = "2026-12-20T19:00:00+00:00"


@pytest.fixture(autouse=True)
def default_time():
    """Zadano vrijeme svih testova u datoteci: 01.12.2026., dakle prije dolaska.

    Bez zamrznutog vremena ishod testova ovisio bi o danu pokretanja.
    Test koji provjerava granicu roka postavlja svoje vrijeme s @freeze_time.
    """
    with freeze_time("2026-12-01 10:00:00"):
        yield


def body(table, start=START_ISO, guests=2):
    return {"table_id": table.id, "start_time": start, "guests": guests}


# --- stvaranje -------------------------------------------------------------------


async def test_guest_creates_reservation(client, guest, table):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post("/reservations/", json=body(table), headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "active"
    # Vlasnik dolazi iz tokena, ne iz tijela zahtjeva
    assert data["user_id"] == guest.id
    # Povezani stol u odgovoru, sužen na broj i lokaciju
    assert data["table"] == {"number": 1, "location": "terasa"}


async def test_admin_cannot_create_reservation(client, admin_user, table):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post("/reservations/", json=body(table), headers=headers)
    assert resp.status_code == 403


async def test_unknown_table_is_404(client, guest):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(
        "/reservations/",
        json={"table_id": 9999, "start_time": START_ISO, "guests": 2},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_start_time_without_timezone_is_422(client, guest, table):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(
        "/reservations/",
        json=body(table, start="2026-12-20T19:00:00"),
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["errors"][0]["field"] == "start_time"


# --- pravilo: kapacitet ------------------------------------------------------------


async def test_guests_equal_to_capacity_is_allowed(client, guest, table):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(
        "/reservations/", json=body(table, guests=4), headers=headers
    )
    assert resp.status_code == 201


async def test_guests_over_capacity_is_400(client, guest, table):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(
        "/reservations/", json=body(table, guests=5), headers=headers
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "over_capacity"


# --- pravilo: rezervacija u budućnosti ------------------------------------------------


async def test_reservation_in_past_is_400(client, guest, table):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(
        "/reservations/",
        json=body(table, start="2026-11-30T19:00:00+00:00"),
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "start_in_past"


# --- pravilo: bez preklapanja ------------------------------------------------------


async def test_overlapping_reservation_is_409(client, db, guest, other_guest, table):
    await add_reservation(db, other_guest, table)
    headers = await auth_header(client, "gost", "gost1234")
    # 19:00 je zauzeto do 21:00, pa 20:59 upada u isti termin
    resp = await client.post(
        "/reservations/",
        json=body(table, start="2026-12-20T20:59:00+00:00"),
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "table_taken"


async def test_reservation_exactly_two_hours_later_is_allowed(
    client, db, guest, other_guest, table
):
    await add_reservation(db, other_guest, table)
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(
        "/reservations/",
        json=body(table, start="2026-12-20T21:00:00+00:00"),
        headers=headers,
    )
    assert resp.status_code == 201


async def test_cancelled_reservation_does_not_block_table(
    client, db, guest, other_guest, table
):
    await add_reservation(db, other_guest, table, status="cancelled")
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post("/reservations/", json=body(table), headers=headers)
    assert resp.status_code == 201


# --- vlasništvo -----------------------------------------------------------------


async def test_guest_cannot_read_other_guests_reservation(
    client, db, guest, other_guest, table
):
    reservation = await add_reservation(db, other_guest, table)
    headers = await auth_header(client, "gost", "gost1234")
    # Oznaku tuđe rezervacije je pogodio, ali do zapisa ne smije
    resp = await client.get(f"/reservations/{reservation.id}", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_guest_list_contains_only_own_reservations(
    client, db, guest, other_guest, table
):
    mine = await add_reservation(db, guest, table)
    await add_reservation(db, other_guest, table, start_time=START.replace(hour=12))
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.get("/reservations/", headers=headers)
    assert resp.status_code == 200
    # Popis se ne odbija nego sužava
    assert [r["id"] for r in resp.json()] == [mine.id]


async def test_admin_sees_all_reservations(
    client, db, admin_user, guest, other_guest, table
):
    await add_reservation(db, guest, table)
    await add_reservation(db, other_guest, table, start_time=START.replace(hour=12))
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.get("/reservations/", headers=headers)
    assert len(resp.json()) == 2


async def test_list_filter_by_status(client, db, admin_user, guest, table):
    await add_reservation(db, guest, table)
    await add_reservation(
        db, guest, table, start_time=START.replace(hour=12), status="cancelled"
    )
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.get("/reservations/?status=cancelled", headers=headers)
    assert [r["status"] for r in resp.json()] == ["cancelled"]


async def test_unknown_reservation_is_404(client, guest):
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.get("/reservations/9999", headers=headers)
    assert resp.status_code == 404


# --- pravilo: rok otkazivanja (2 h prije dolaska) ----------------------------


async def test_guest_cancels_own_reservation_in_time(client, db, guest, table):
    reservation = await add_reservation(db, guest, table)
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(f"/reservations/{reservation.id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@freeze_time("2026-12-20 16:59:59")
async def test_cancel_one_second_before_deadline_is_allowed(client, db, guest, table):
    reservation = await add_reservation(db, guest, table)
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(f"/reservations/{reservation.id}/cancel", headers=headers)
    assert resp.status_code == 200


@freeze_time("2026-12-20 17:00:00")
async def test_cancel_exactly_at_deadline_is_400(client, db, guest, table):
    reservation = await add_reservation(db, guest, table)
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(f"/reservations/{reservation.id}/cancel", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "cancel_deadline_passed"


@freeze_time("2026-12-20 18:00:00")
async def test_admin_can_cancel_after_deadline(client, db, admin_user, guest, table):
    reservation = await add_reservation(db, guest, table)
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post(f"/reservations/{reservation.id}/cancel", headers=headers)
    assert resp.status_code == 200


async def test_guest_cannot_cancel_other_guests_reservation(
    client, db, guest, other_guest, table
):
    reservation = await add_reservation(db, other_guest, table)
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(f"/reservations/{reservation.id}/cancel", headers=headers)
    assert resp.status_code == 403


async def test_cancel_twice_is_400(client, db, guest, table):
    reservation = await add_reservation(db, guest, table)
    headers = await auth_header(client, "gost", "gost1234")
    await client.post(f"/reservations/{reservation.id}/cancel", headers=headers)
    resp = await client.post(f"/reservations/{reservation.id}/cancel", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "not_active"


# --- pravilo: gost nije došao (30 min nakon dolaska) --------------------------


@freeze_time("2026-12-20 19:29:59")
async def test_no_show_before_grace_period_is_400(client, db, admin_user, guest, table):
    reservation = await add_reservation(db, guest, table)
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post(f"/reservations/{reservation.id}/no-show", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "too_early"


@freeze_time("2026-12-20 19:30:00")
async def test_no_show_exactly_after_grace_period(client, db, admin_user, guest, table):
    reservation = await add_reservation(db, guest, table)
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post(f"/reservations/{reservation.id}/no-show", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_show"


@freeze_time("2026-12-20 20:00:00")
async def test_guest_cannot_mark_no_show(client, db, guest, table):
    reservation = await add_reservation(db, guest, table)
    headers = await auth_header(client, "gost", "gost1234")
    resp = await client.post(f"/reservations/{reservation.id}/no-show", headers=headers)
    assert resp.status_code == 403


@freeze_time("2026-12-20 20:00:00")
async def test_cancelled_reservation_cannot_be_no_show(
    client, db, admin_user, guest, table
):
    reservation = await add_reservation(db, guest, table, status="cancelled")
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post(f"/reservations/{reservation.id}/no-show", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "not_active"
