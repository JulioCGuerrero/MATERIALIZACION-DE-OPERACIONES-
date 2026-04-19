def _crear_proveedor(client, nombre="Proveedor Test", rfc="TST010101AAA", tipo="limpieza", monto=10000, repse=False, fisico=False):
    res = client.post(
        "/api/proveedores",
        json={
            "nombre": nombre,
            "rfc": rfc,
            "tipo": tipo,
            "monto": monto,
            "repse": repse,
            "tiene_fisico": fisico,
        },
    )
    assert res.status_code == 201
    return res.get_json()


def _crear_folio(client, proveedor_id, numero="90001", presupuesto=50000, periodo="2026-04"):
    res = client.post(
        "/api/folios",
        json={
            "numero": numero,
            "proveedor_id": proveedor_id,
            "presupuesto": presupuesto,
            "periodo": periodo,
        },
    )
    assert res.status_code == 201
    return res.get_json()


def test_clasificador_monto_alto_nivel_4(client):
    res = client.post(
        "/api/clasificar",
        json={"tipo": "limpieza", "monto": 600000, "repse": False, "tiene_fisico": False},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["nivel"] == 4
    assert data["riesgo"] == "critico"


def test_traspaso_bloqueado_si_expediente_incompleto(client):
    proveedor = _crear_proveedor(client, nombre="Bloq SA", rfc="BLQ010101AAA", tipo="outsourcing", monto=200000, repse=True)
    folio = _crear_folio(client, proveedor["id"], numero="90002", presupuesto=100000)

    folios = client.get("/api/folios").get_json()
    f = next(x for x in folios if x["numero"] == "90002")

    res = client.post(
        "/api/traspasos",
        json={
            "folio_id": f["id"],
            "monto": 1000,
            "banco_origen": "Banorte",
            "fecha": "2026-04-19",
        },
    )
    assert res.status_code == 403
    data = res.get_json()
    assert "documentos_faltantes" in data["detalle"]


def test_subir_documentos_libera_pago_al_100(client):
    proveedor = _crear_proveedor(client, nombre="N1 SA", rfc="NIV010101AAA", tipo="limpieza", monto=10000, repse=False, fisico=False)
    _crear_folio(client, proveedor["id"], numero="90003", presupuesto=20000)

    folios = client.get("/api/folios").get_json()
    folio = next(x for x in folios if x["numero"] == "90003")
    detalle = client.get(f"/api/folios/{folio['id']}").get_json()

    for doc in detalle["documentos"]:
        res = client.post(
            f"/api/documentos/{doc['id']}/subir",
            json={"nombre_archivo": f"{doc['tipo']}.pdf", "url": f"/tmp/{doc['tipo']}.pdf", "subido_por": "pytest"},
        )
        assert res.status_code == 200

    comp = client.get(f"/api/expedientes/{detalle['expediente_id']}/completitud")
    assert comp.status_code == 200
    data = comp.get_json()
    assert data["completitud"] == 100.0
    assert data["puede_pagar"] is True
