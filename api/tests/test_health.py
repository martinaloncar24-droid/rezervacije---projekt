async def test_health(client):
    resp = await client.get("/health/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_unknown_route_has_same_error_shape(client):
    resp = await client.get("/nepostojeca-ruta")
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
