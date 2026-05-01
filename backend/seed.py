from itertools import islice
from calendar import monthrange
from datetime import date

from app import create_app
from app.extensions import db
from app.models import Documento, Empresa, Expediente, Folio, Proveedor, Traspaso
from app.services.bloqueo import calcular_completitud
from app.services.catalogo import DOCS_BY_LEVEL

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
    {"nombre": "Batia", "rfc": "BAT010101AAA"},
    {"nombre": "Grupo Norte", "rfc": "GRN010101BBB"},
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
    empresas = {}
    for e in EMPRESAS:
        empresa = Empresa(nombre=e["nombre"], rfc=e["rfc"], activo=True)
        empresas[e["nombre"]] = empresa
        db.session.add(empresa)

    db.session.flush()

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

    by_num = {}
    for f in FOLIOS:
        proveedor = by_name[f["proveedor"]]
        empresa = empresas[f["empresa"]]
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

        if f["numero"] == "17172":
            expediente.razon_negocio = "Servicio recurrente con beneficio operativo"
        if f["numero"] == "17165":
            expediente.manifiesto = True

        by_num[f["numero"]] = folio

    db.session.flush()

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
