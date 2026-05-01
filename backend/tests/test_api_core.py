from app.extensions import db
from app.models import Expediente, Folio


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


def _crear_empresa(client, nombre="Empresa Test", rfc="EMT010101AAA"):
    res = client.post("/api/empresas", json={"nombre": nombre, "rfc": rfc})
    assert res.status_code == 201
    return res.get_json()


def _crear_folio(client, proveedor_id, empresa_id, numero="90001", presupuesto=50000, periodo="2026-04", fecha_limite_entrega=None):
    payload = {
        "numero": numero,
        "proveedor_id": proveedor_id,
        "empresa_id": empresa_id,
        "presupuesto": presupuesto,
        "periodo": periodo,
    }
    if fecha_limite_entrega:
        payload["fecha_limite_entrega"] = fecha_limite_entrega
    res = client.post("/api/folios", json=payload)
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
    empresa = _crear_empresa(client)
    proveedor = _crear_proveedor(client, nombre="Bloq SA", rfc="BLQ010101AAA", tipo="outsourcing", monto=200000, repse=True)
    _crear_folio(client, proveedor["id"], empresa["id"], numero="90002", presupuesto=100000)

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
    empresa = _crear_empresa(client, nombre="Empresa N1", rfc="EN1010101AAA")
    proveedor = _crear_proveedor(client, nombre="N1 SA", rfc="NIV010101AAA", tipo="limpieza", monto=10000, repse=False, fisico=False)
    _crear_folio(client, proveedor["id"], empresa["id"], numero="90003", presupuesto=20000)

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


def test_reporte_niveles_incluye_folios_sin_expediente(client):
    empresa = _crear_empresa(client, nombre="Empresa SinExp", rfc="ESE010101AAA")
    proveedor = _crear_proveedor(client, nombre="SinExp SA", rfc="SXP010101AAA", tipo="limpieza", monto=10000, repse=False, fisico=False)
    _crear_folio(client, proveedor["id"], empresa["id"], numero="90004", presupuesto=25000)

    with client.application.app_context():
        folio = Folio.query.filter_by(numero="90004").first()
        expediente = Expediente.query.filter_by(folio_id=folio.id).first()
        db.session.delete(expediente)
        db.session.commit()

    res = client.get("/api/reportes/nivel")
    assert res.status_code == 200
    data = res.get_json()
    assert any(item["folio"] == "90004" for item in data["items"])


def test_ciclo_mensual_genera_expedientes_por_empresa(client):
    empresa = _crear_empresa(client, nombre="Empresa Ciclo", rfc="ECI010101AAA")
    proveedor = _crear_proveedor(client, nombre="Ciclo SA", rfc="CIC010101AAA", tipo="limpieza", monto=10000, repse=False, fisico=False)
    _crear_folio(client, proveedor["id"], empresa["id"], numero="90005", presupuesto=30000, periodo="2026-04")

    res = client.post("/api/folios/ciclo-mensual", json={"empresa_id": empresa["id"], "periodo": "2026-05"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["folios_creados"] == 1
    assert data["items"][0]["periodo"] == "2026-05"


def test_efos_bloquea_registro_proveedor(client):
    res = client.post("/api/efos/cargar", json={"rfcs": ["EFO010101AAA"], "fuente": "sat-demo"})
    assert res.status_code == 200

    res2 = client.post(
        "/api/proveedores",
        json={
            "nombre": "EFOS SA",
            "rfc": "EFO010101AAA",
            "tipo": "limpieza",
            "monto": 10000,
            "repse": False,
            "tiene_fisico": False,
        },
    )
    assert res2.status_code == 409


def test_generador_alertas_detecta_vencimiento(client):
    empresa = _crear_empresa(client, nombre="Empresa Alertas", rfc="EAL010101AAA")
    proveedor = _crear_proveedor(client, nombre="Alert SA", rfc="ALT010101AAA", tipo="limpieza", monto=10000, repse=False, fisico=False)
    _crear_folio(
        client,
        proveedor["id"],
        empresa["id"],
        numero="90006",
        presupuesto=30000,
        periodo="2026-01",
        fecha_limite_entrega="2026-01-10",
    )

    res = client.post("/api/alertas/generar", json={"periodo": "2026-01"})
    assert res.status_code == 200
    lst = client.get("/api/alertas?periodo=2026-01&estado=activa")
    assert lst.status_code == 200
    items = lst.get_json()
    assert len(items) >= 1
