import io
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Expediente, Folio, Usuario


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


def test_empresa_nueva_aparece_como_activa_en_listado(client):
    empresa = _crear_empresa(client, nombre="Empresa Activa", rfc="EAC010101AAA")
    assert empresa["activo"] is True
    assert empresa["onboarding_status"] == "borrador"

    res = client.get("/api/empresas")
    assert res.status_code == 200
    items = res.get_json()
    creada = next(item for item in items if item["id"] == empresa["id"])
    assert creada["activo"] is True
    assert creada["nombre"] == "Empresa Activa"
    assert creada["rfc"] == "EAC010101AAA"


def test_empresa_documento_onboarding_acepta_archivo_desde_multipart(client):
    empresa = _crear_empresa(client, nombre="Empresa Archivo", rfc="EAR010101AAA")
    res = client.post(
        f"/api/empresas/{empresa['id']}/documentos",
        data={
            "tipo": "constancia_fiscal",
            "nombre_archivo": "constancia_fiscal.pdf",
            "usuario": "pytest",
            "archivo": (io.BytesIO(b"pdf-demo"), "constancia_fiscal.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["ok"] is True

    status = client.get(f"/api/empresas/{empresa['id']}/onboarding/status")
    assert status.status_code == 200
    detalle = status.get_json()["documentos"]["detalle"]
    constancia = next(doc for doc in detalle if doc["tipo"] == "constancia_fiscal")
    assert constancia["id"] is not None
    assert constancia["presente"] is True
    assert constancia["estado_validacion"] == "pendiente"


def test_empresa_puede_listar_varias_cuentas_bancarias(client):
    empresa = _crear_empresa(client, nombre="Empresa Cuentas", rfc="ECU010101AAA")
    for banco, clabe in [("BBVA", "012345678901234561"), ("Banorte", "012345678901234562")]:
        res = client.post(
            f"/api/empresas/{empresa['id']}/cuentas-bancarias",
            json={
                "banco": banco,
                "titular": "Empresa Cuentas SA",
                "clabe": clabe,
                "moneda": "MXN",
                "validada": True,
                "usuario": "pytest",
            },
        )
        assert res.status_code == 201

    cuentas = client.get(f"/api/empresas/{empresa['id']}/cuentas-bancarias")
    assert cuentas.status_code == 200
    items = cuentas.get_json()
    assert len(items) == 2
    assert {item["banco"] for item in items} == {"BBVA", "Banorte"}
    assert all(item["validada"] is True for item in items)


def test_empresa_puede_actualizar_nombre_rfc_y_tipo(client):
    empresa = _crear_empresa(client, nombre="Empresa Original", rfc="EOR010101AAA")
    res = client.patch(
        f"/api/empresas/{empresa['id']}",
        json={
            "nombre": "Empresa Editada",
            "rfc": "EDI010101AAA",
            "tipo_empresa": "industrial",
            "usuario": "pytest",
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["nombre"] == "Empresa Editada"
    assert data["rfc"] == "EDI010101AAA"
    assert data["tipo_empresa"] == "industrial"


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
        ext = "xml" if doc["tipo"] == "cfdi_xml" else "pdf"
        res = client.post(
            f"/api/documentos/{doc['id']}/subir",
            json={"nombre_archivo": f"{doc['tipo']}.{ext}", "url": f"/tmp/{doc['tipo']}.{ext}", "subido_por": "pytest"},
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


def test_policy_simulation_and_publish_changes_gate_threshold(client):
    empresa = _crear_empresa(client, nombre="Empresa Policy", rfc="EPO010101AAA")
    proveedor = _crear_proveedor(client, nombre="Policy SA", rfc="PLY010101AAA", tipo="limpieza", monto=10000, repse=False, fisico=False)
    _crear_folio(client, proveedor["id"], empresa["id"], numero="90100", presupuesto=30000, periodo="2026-04")

    res_sim = client.post(
        f"/api/empresas/{empresa['id']}/policy/simulate",
        json={"parametros": {"gates": {"min_completitud_para_pago": 80.0}}},
    )
    assert res_sim.status_code == 200
    sim = res_sim.get_json()
    assert sim["expedientes_evaluados"] >= 1

    draft = client.post(
        f"/api/empresas/{empresa['id']}/policy/draft",
        json={"parametros": {"gates": {"min_completitud_para_pago": 80.0}}, "usuario": "pytest"},
    )
    assert draft.status_code == 201
    version_id = draft.get_json()["draft_version_id"]

    pub = client.post(f"/api/empresas/{empresa['id']}/policy/publish/{version_id}")
    assert pub.status_code == 200

    folios = client.get("/api/folios").get_json()
    folio = next(x for x in folios if x["numero"] == "90100")
    detalle = client.get(f"/api/folios/{folio['id']}").get_json()
    doc = detalle["documentos"][0]
    ext = "xml" if doc["tipo"] == "cfdi_xml" else "pdf"
    up = client.post(
        f"/api/documentos/{doc['id']}/subir",
        json={"nombre_archivo": f"{doc['tipo']}.{ext}", "url": f"/tmp/{doc['tipo']}.{ext}", "subido_por": "pytest"},
    )
    assert up.status_code == 200

    comp = client.get(f"/api/expedientes/{detalle['expediente_id']}/completitud")
    assert comp.status_code == 200
    data = comp.get_json()
    assert data["min_completitud_requerida"] == 80.0


def test_proveedor_con_empresa_requiere_policy_publicada(client):
    empresa = _crear_empresa(client, nombre="Empresa Sin Policy", rfc="ESP010101AAA")
    res = client.post(
        "/api/proveedores",
        json={
            "nombre": "Proveedor Bloq",
            "rfc": "PBL010101AAA",
            "tipo": "limpieza",
            "monto": 12000,
            "repse": False,
            "tiene_fisico": False,
            "empresa_id": empresa["id"],
            "tipo_empresa": "servicios",
        },
    )
    assert res.status_code == 409
    data = res.get_json()
    assert "política activa publicada" in data["error"]

    status = client.get(f"/api/empresas/{empresa['id']}/policy/status")
    assert status.status_code == 200
    st = status.get_json()
    assert st["has_active_published_policy"] is False


def test_solo_administracion_puede_registrar_empresas_y_proveedores(tmp_path):
    class AuthzConfig:
        BASE_DIR = Path(tmp_path)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'authz.db'}"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        TESTING = True

    app = create_app(AuthzConfig)
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Usuario(email="admin@test.local", nombre="Admin", rol="administracion", password="x", activo=True),
                Usuario(email="conta@test.local", nombre="Conta", rol="contabilidad", password="x", activo=True),
            ]
        )
        db.session.commit()

    app.config["TESTING"] = False
    with app.test_client() as client:
        headers_admin = {"X-Auth-Email": "admin@test.local", "X-Auth-Role": "administracion"}
        headers_conta = {"X-Auth-Email": "conta@test.local", "X-Auth-Role": "contabilidad"}

        res_emp_forbidden = client.post(
            "/api/empresas",
            json={"nombre": "Empresa Bloqueada", "rfc": "EBL010101AAA"},
            headers=headers_conta,
        )
        assert res_emp_forbidden.status_code == 403

        res_emp_ok = client.post(
            "/api/empresas",
            json={"nombre": "Empresa Admin", "rfc": "EAD010101AAA"},
            headers=headers_admin,
        )
        assert res_emp_ok.status_code == 201
        empresa = res_emp_ok.get_json()

        res_emp_patch_ok = client.patch(
            f"/api/empresas/{empresa['id']}",
            json={"nombre": "Empresa Admin Editada", "usuario": "admin"},
            headers=headers_admin,
        )
        assert res_emp_patch_ok.status_code == 200

        res_prov_forbidden = client.post(
            "/api/proveedores",
            json={
                "nombre": "Proveedor Bloqueado",
                "rfc": "PBA010101AAA",
                "tipo": "limpieza",
                "monto": 10000,
                "repse": False,
                "tiene_fisico": False,
            },
            headers=headers_conta,
        )
        assert res_prov_forbidden.status_code == 403

        res_prov_ok = client.post(
            "/api/proveedores",
            json={
                "nombre": "Proveedor Admin",
                "rfc": "PAD010101AAA",
                "tipo": "limpieza",
                "monto": 10000,
                "repse": False,
                "tiene_fisico": False,
            },
            headers=headers_admin,
        )
        assert res_prov_ok.status_code == 201

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_administracion_puede_subir_politica_y_activar_empresa(tmp_path):
    class PolicyUploadConfig:
        BASE_DIR = Path(tmp_path)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'policy_upload.db'}"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        TESTING = True

    app = create_app(PolicyUploadConfig)
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Usuario(email="admin@test.local", nombre="Admin", rol="administracion", password="x", activo=True),
                Usuario(email="conta@test.local", nombre="Conta", rol="contabilidad", password="x", activo=True),
            ]
        )
        db.session.commit()

    app.config["TESTING"] = False
    with app.test_client() as client:
        headers_admin = {"X-Auth-Email": "admin@test.local", "X-Auth-Role": "administracion"}
        headers_conta = {"X-Auth-Email": "conta@test.local", "X-Auth-Role": "contabilidad"}

        res_emp = client.post(
            "/api/empresas",
            json={"nombre": "Empresa Policy Upload", "rfc": "EPU010101AAA"},
            headers=headers_admin,
        )
        assert res_emp.status_code == 201
        empresa = res_emp.get_json()

        status_before = client.get(f"/api/empresas/{empresa['id']}/policy/status")
        assert status_before.status_code == 200
        assert status_before.get_json()["has_active_published_policy"] is False

        forbidden = client.post(
            f"/api/empresas/{empresa['id']}/policy/upload",
            data={
                "usuario": "conta",
                "nota_cambio": "Intento sin permiso",
                "archivo": (io.BytesIO(b"policy-demo"), "politica_conta.pdf"),
            },
            content_type="multipart/form-data",
            headers=headers_conta,
        )
        assert forbidden.status_code == 403

        upload = client.post(
            f"/api/empresas/{empresa['id']}/policy/upload",
            data={
                "usuario": "admin",
                "nota_cambio": "Politica operativa vigente",
                "archivo": (io.BytesIO(b"policy-demo"), "politica_empresa.pdf"),
            },
            content_type="multipart/form-data",
            headers=headers_admin,
        )
        assert upload.status_code == 201
        payload = upload.get_json()
        assert payload["policy_status"]["has_active_published_policy"] is True
        assert payload["documento"]["url"].endswith("/politica_empresa.pdf")

        status_after = client.get(f"/api/empresas/{empresa['id']}/policy/status")
        assert status_after.status_code == 200
        assert status_after.get_json()["has_active_published_policy"] is True

        policy = client.get(f"/api/empresas/{empresa['id']}/policy", headers=headers_admin)
        assert policy.status_code == 200
        assert policy.get_json()["active_version"]["documento"]["nombre_archivo"] == "politica_empresa.pdf"

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_empresa_con_politica_activa_permite_registro_y_autoregistro_proveedor(tmp_path):
    class PolicyGateConfig:
        BASE_DIR = Path(tmp_path)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'policy_gate.db'}"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        TESTING = True

    app = create_app(PolicyGateConfig)
    with app.app_context():
        db.create_all()
        db.session.add(Usuario(email="admin@test.local", nombre="Admin", rol="administracion", password="x", activo=True))
        db.session.commit()

    app.config["TESTING"] = False
    with app.test_client() as client:
        headers_admin = {"X-Auth-Email": "admin@test.local", "X-Auth-Role": "administracion"}

        res_emp = client.post(
            "/api/empresas",
            json={"nombre": "Empresa Gate", "rfc": "EGA010101AAA"},
            headers=headers_admin,
        )
        assert res_emp.status_code == 201
        empresa = res_emp.get_json()

        upload = client.post(
            f"/api/empresas/{empresa['id']}/policy/upload",
            data={
                "usuario": "admin",
                "nota_cambio": "Politica activa para alta proveedor",
                "archivo": (io.BytesIO(b"policy-demo"), "politica_gate.pdf"),
            },
            content_type="multipart/form-data",
            headers=headers_admin,
        )
        assert upload.status_code == 201

        manual = client.post(
            "/api/proveedores",
            json={
                "nombre": "Proveedor Gate",
                "rfc": "PGA010101AAA",
                "tipo": "limpieza",
                "monto": 12000,
                "repse": False,
                "tiene_fisico": False,
                "empresa_id": empresa["id"],
                "tipo_empresa": "servicios",
            },
            headers=headers_admin,
        )
        assert manual.status_code == 201

        self_register = client.post(
            "/api/proveedores/self-register",
            json={
                "nombre": "Proveedor Auto Gate",
                "rfc": "PAG010101AAA",
                "tipo": "limpieza",
                "monto": 12000,
                "repse": False,
                "tiene_fisico": False,
                "empresa_id": empresa["id"],
            },
        )
        assert self_register.status_code == 201

    with app.app_context():
        db.session.remove()
        db.drop_all()
