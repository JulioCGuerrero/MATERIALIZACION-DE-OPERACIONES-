from itertools import islice
from calendar import monthrange
from copy import deepcopy
from datetime import date, datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    Documento,
    Empresa,
    EmpresaCuentaBancaria,
    EmpresaDocumento,
    EmpresaCredencial,
    Expediente,
    Folio,
    PolicySet,
    PolicyVersion,
    Proveedor,
    ProveedorCredencial,
    Traspaso,
    Usuario,
)
from app.services.bloqueo import calcular_completitud
from app.services.catalogo import DOCS_BY_LEVEL
from app.services.demo_uploads import ensure_demo_document_file, ensure_demo_empresa_document_file
from app.services.document_review import aplicar_validacion_documento
from app.services.onboarding_empresas import DOCS_REQUERIDOS_EMPRESA, REGLAS_NEGOCIO_REQUERIDAS
from app.services.policy_engine import DEFAULT_POLICY

app = create_app()

PROVEEDORES = [
    {
        "nombre": "Limpiadores SA",
        "rfc": "LSA010101AAA",
        "tipo": "outsourcing",
        "nivel": 3,
        "banco": "Banorte",
        "cuenta": "4821",
        "repse": False,
        "tiene_fisico": False,
    },
    {
        "nombre": "Insumos Alfa",
        "rfc": "IAL010101BBB",
        "tipo": "materia",
        "nivel": 2,
        "banco": "BBVA",
        "cuenta": "2210",
        "repse": False,
        "tiene_fisico": True,
    },
    {
        "nombre": "TechServ",
        "rfc": "TSV010101CCC",
        "tipo": "consultoria",
        "nivel": 3,
        "banco": "BBVA",
        "cuenta": "8832",
        "repse": True,
        "tiene_fisico": False,
    },
    {
        "nombre": "Mant. Delta",
        "rfc": "MDE010101DDD",
        "tipo": "construccion",
        "nivel": 4,
        "banco": None,
        "cuenta": None,
        "repse": True,
        "tiene_fisico": True,
    },
]

EMPRESAS = [
    {"nombre": "Batia", "rfc": "BAT010101AAA", "tipo_empresa": "servicios"},
    {"nombre": "Grupo Norte", "rfc": "GRN010101BBB", "tipo_empresa": "industrial"},
]

EMPRESAS_ONBOARDING = {
    "Batia": {
        "documentos": {
            "constancia_fiscal": "constancia_fiscal_batia.pdf",
            "acta_constitutiva": "acta_constitutiva_batia.pdf",
            "poder_representante": "poder_representante_batia.pdf",
            "identificacion_representante": "identificacion_representante_batia.pdf",
            "comprobante_domicilio_fiscal": "comprobante_domicilio_batia.pdf",
            "opinion_32d": "opinion_32d_batia.pdf",
            "estado_cuenta_bancario": "estado_cuenta_bancario_batia.pdf",
            "politica_autorizacion_pagos": "politica_autorizacion_pagos_batia.pdf",
        },
        "cuentas": [
            {
                "banco": "Banorte",
                "titular": "Batia Servicios SA de CV",
                "clabe": "072180012345678901",
                "numero_cuenta": "1234567890",
                "moneda": "MXN",
            },
            {
                "banco": "Mifel",
                "titular": "Batia Servicios SA de CV",
                "clabe": "042180098765432109",
                "numero_cuenta": "0098765432",
                "moneda": "MXN",
            },
        ],
    },
    "Grupo Norte": {
        "documentos": {
            "constancia_fiscal": "constancia_fiscal_grupo_norte.pdf",
            "acta_constitutiva": "acta_constitutiva_grupo_norte.pdf",
            "poder_representante": "poder_representante_grupo_norte.pdf",
            "identificacion_representante": "identificacion_representante_grupo_norte.pdf",
            "comprobante_domicilio_fiscal": "comprobante_domicilio_grupo_norte.pdf",
            "opinion_32d": "opinion_32d_grupo_norte.pdf",
            "estado_cuenta_bancario": "estado_cuenta_bancario_grupo_norte.pdf",
            "politica_autorizacion_pagos": "politica_autorizacion_pagos_grupo_norte.pdf",
        },
        "cuentas": [
            {
                "banco": "BBVA",
                "titular": "Grupo Norte Industrial SA de CV",
                "clabe": "012180112233445566",
                "numero_cuenta": "1122334455",
                "moneda": "MXN",
            }
        ],
    },
}

USUARIOS = [
    {"email": "salo@batia.local", "nombre": "Salo", "rol": "direccion", "password": "DirBatia#2026"},
    {"email": "mgonzalez@batia.local", "nombre": "M. Gonzalez", "rol": "tesoreria", "password": "TesoMgonz#2026"},
    {"email": "lhernandez@batia.local", "nombre": "L. Hernandez", "rol": "tesoreria", "password": "TesoLhern#2026"},
    {"email": "rfuentes@batia.local", "nombre": "R. Fuentes", "rol": "administracion", "password": "AdminRfuen#2026"},
    {"email": "cmorales@batia.local", "nombre": "C. Morales", "rol": "administracion", "password": "AdminCmora#2026"},
    {"email": "pramirez@batia.local", "nombre": "P. Ramirez", "rol": "contabilidad", "password": "ContaPram#2026"},
]

FOLIOS = [
    {"numero": "17172", "proveedor": "Limpiadores SA", "empresa": "Batia", "presupuesto": 150_000, "periodo": "2026-03"},
    {"numero": "17165", "proveedor": "Insumos Alfa", "empresa": "Batia", "presupuesto": 90_000, "periodo": "2026-03"},
    {"numero": "17160", "proveedor": "TechServ", "empresa": "Grupo Norte", "presupuesto": 185_000, "periodo": "2026-03"},
    {"numero": "17148", "proveedor": "Mant. Delta", "empresa": "Grupo Norte", "presupuesto": 0, "periodo": "2026-03"},
]

TRASPASOS = [
    {"folio": "17172", "folio_bancario": "182822", "monto": 148_500, "banco_origen": "Banorte", "fecha": "2026-03-14", "estado": "conciliado"},
    {"folio": "17165", "folio_bancario": "91822", "monto": 89_200, "banco_origen": "Banorte", "fecha": "2026-03-08", "estado": "conciliado"},
    {
        "folio": "17160",
        "folio_bancario": "28228",
        "monto": 210_000,
        "banco_origen": "BBVA",
        "fecha": "2026-03-18",
        "estado": "alerta",
        "excede_presup": True,
        "diferencia": 25_000,
    },
    {"folio": "17148", "folio_bancario": None, "monto": 320_000, "banco_origen": "Banorte", "fecha": "2026-03-14", "estado": "alerta"},
]

PROGRESO = {
    "17165": 1.00,
    "17172": 0.60,
    "17160": 0.35,
    "17148": 0.10,
}


with app.app_context():
    db.drop_all()
    db.create_all()

    by_name = {}
    for u in USUARIOS:
        db.session.add(
            Usuario(
                email=u["email"].lower(),
                nombre=u["nombre"],
                rol=u["rol"],
                password=u["password"],
                activo=True,
            )
        )

    db.session.flush()

    empresas = {}
    for e in EMPRESAS:
        empresa = Empresa(
            nombre=e["nombre"],
            rfc=e["rfc"],
            tipo_empresa=e.get("tipo_empresa", "servicios"),
            activo=True,
        )
        empresas[e["nombre"]] = empresa
        db.session.add(empresa)

    db.session.flush()

    vigencia_demo = date.today() + timedelta(days=365)
    aprobado_en_demo = datetime.utcnow()
    for empresa_nombre, empresa in empresas.items():
        onboarding_demo = EMPRESAS_ONBOARDING.get(empresa_nombre, {})
        empresa.reglas_negocio = {regla: True for regla in REGLAS_NEGOCIO_REQUERIDAS}
        empresa.onboarding_status = "aprobada"
        empresa.onboarding_aprobada_por = "seed"
        empresa.onboarding_aprobada_en = aprobado_en_demo

        for tipo in DOCS_REQUERIDOS_EMPRESA:
            filename = onboarding_demo.get("documentos", {}).get(tipo, f"{tipo}_{empresa.id}.pdf")
            ensure_demo_empresa_document_file(
                base_dir=app.config["BASE_DIR"],
                empresa_id=empresa.id,
                filename=filename,
                empresa=empresa.nombre,
                rfc=empresa.rfc,
                doc_tipo=tipo,
            )
            db.session.add(
                EmpresaDocumento(
                    empresa_id=empresa.id,
                    tipo=tipo,
                    nombre_archivo=filename,
                    url=f"/uploads/empresas/{empresa.id}/{filename}",
                    estado_validacion="valido",
                    vigente_hasta=vigencia_demo,
                    subido_por="seed",
                    validado_por="seed",
                    subido_en=aprobado_en_demo,
                    validado_en=aprobado_en_demo,
                )
            )

        for cuenta in onboarding_demo.get("cuentas", []):
            db.session.add(
                EmpresaCuentaBancaria(
                    empresa_id=empresa.id,
                    banco=cuenta["banco"],
                    titular=cuenta["titular"],
                    clabe=cuenta["clabe"],
                    numero_cuenta=cuenta.get("numero_cuenta"),
                    moneda=cuenta.get("moneda", "MXN"),
                    activa=True,
                    validada=True,
                    validada_por="seed",
                    validada_en=aprobado_en_demo,
                )
            )

        policy_set = PolicySet(empresa_id=empresa.id, nombre="Politica Operativa Demo")
        db.session.add(policy_set)
        db.session.flush()
        policy_version = PolicyVersion(
            policy_set_id=policy_set.id,
            version=1,
            estado="active",
            parametros=deepcopy(DEFAULT_POLICY),
            creado_por="seed",
            nota_cambio="Version demo publicada para habilitar el flujo completo",
            creado_en=aprobado_en_demo,
            publicado_en=aprobado_en_demo,
        )
        db.session.add(policy_version)
        db.session.flush()
        policy_set.activa_version_id = policy_version.id
        db.session.add(
            EmpresaCredencial(
                empresa_id=empresa.id,
                username=f"empresa_{empresa.id}_portal",
                password=f"demo-empresa-{empresa.id}",
                activo=True,
            )
        )

    for p in PROVEEDORES:
        proveedor = Proveedor(
            nombre=p["nombre"],
            rfc=p["rfc"],
            tipo=p["tipo"],
            nivel=p["nivel"],
            banco=p.get("banco"),
            cuenta=p.get("cuenta"),
            repse=bool(p["repse"]),
            tiene_fisico=bool(p["tiene_fisico"]),
            efos_ok=True,
        )
        by_name[p["nombre"]] = proveedor
        db.session.add(proveedor)

    db.session.flush()

    cred_pairs = set()
    by_num = {}
    for f in FOLIOS:
        proveedor = by_name[f["proveedor"]]
        empresa = empresas[f["empresa"]]
        cred_pairs.add((proveedor.id, empresa.id))
        folio = Folio(
            numero=f["numero"],
            proveedor_id=proveedor.id,
            empresa_id=empresa.id,
            presupuesto=float(f["presupuesto"]),
            periodo=f["periodo"],
            fecha_limite_entrega=date(
                int(f["periodo"].split("-")[0]),
                int(f["periodo"].split("-")[1]),
                monthrange(int(f["periodo"].split("-")[0]), int(f["periodo"].split("-")[1]))[1],
            ),
            estado="activo",
        )
        db.session.add(folio)
        db.session.flush()

        expediente = Expediente(folio_id=folio.id)
        db.session.add(expediente)
        db.session.flush()

        tipos = DOCS_BY_LEVEL[proveedor.nivel]
        docs = []
        for tipo in tipos:
            d = Documento(expediente_id=expediente.id, tipo=tipo, subido=False)
            db.session.add(d)
            docs.append(d)

        db.session.flush()

        to_upload = int(len(docs) * PROGRESO[f["numero"]])
        for d in islice(docs, to_upload):
            d.subido = True
            d.nombre_archivo = f"{d.tipo}.pdf"
            d.url = f"/uploads/{folio.numero}/{d.tipo}.pdf"
            d.subido_por = "seed"
            ensure_demo_document_file(
                base_dir=app.config["BASE_DIR"],
                folio_numero=folio.numero,
                filename=d.nombre_archivo,
                proveedor=proveedor.nombre,
                empresa=empresa.nombre,
                doc_tipo=d.tipo,
                nivel=proveedor.nivel,
                periodo=folio.periodo,
            )
            aplicar_validacion_documento(d, motor="seed")

        if f["numero"] == "17172":
            expediente.razon_negocio = "Servicio recurrente con beneficio operativo"
        if f["numero"] == "17165":
            expediente.manifiesto = True

        by_num[f["numero"]] = folio

    db.session.flush()

    for proveedor_id, empresa_id in sorted(cred_pairs):
        db.session.add(
            ProveedorCredencial(
                proveedor_id=proveedor_id,
                empresa_id=empresa_id,
                username=f"prov_{proveedor_id}_emp_{empresa_id}",
                password=f"demo-prov-{proveedor_id}-{empresa_id}",
                activo=True,
            )
        )

    for t in TRASPASOS:
        folio = by_num[t["folio"]]
        traspaso = Traspaso(
            folio_id=folio.id,
            folio_bancario=t.get("folio_bancario"),
            banco_origen=t["banco_origen"],
            monto=float(t["monto"]),
            fecha=t["fecha"],
            estado=t.get("estado", "pendiente"),
            excede_presup=bool(t.get("excede_presup", False)),
            diferencia=float(t.get("diferencia", 0.0)),
            registrado_por="seed",
        )
        db.session.add(traspaso)

    db.session.commit()

    for folio in by_num.values():
        calcular_completitud(folio.expediente.id)

    print("Seed cargado correctamente")
