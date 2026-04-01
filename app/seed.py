"""Carga de datos iniciales (seed) para entorno demo/desarrollo.

El seed es idempotente: si ya existen registros, no inserta duplicados.
"""

from datetime import date

from app.extensions import db
from app.models import (
    AuthorizedAccount,
    Folio,
    FolioDeliverableItem,
    FolioWorkflow,
    Provider,
    ProviderCompliance,
    Role,
    User,
)
from app.operations.services import ensure_deliverables, ensure_workflow

# Catalogo base de roles.
ROLES = ["direccion", "ui", "contabilidad", "tesoreria", "auditor"]

# Usuarios demo por area.
USERS = [
    ("Salo", "direccion", "salo@batia.local"),
    ("M. Gonzalez", "tesoreria", "mgonzalez@batia.local"),
    ("L. Hernandez", "tesoreria", "lhernandez@batia.local"),
    ("R. Fuentes", "ui", "rfuentes@batia.local"),
    ("C. Morales", "ui", "cmorales@batia.local"),
    ("P. Ramirez", "contabilidad", "pramirez@batia.local"),
]

# Proveedores de ejemplo.
PROVIDERS = [
    ("Limpiadores SA", "outsourcing"),
    ("Insumos Alfa", "materiales"),
    ("TechServ", "servicios"),
    ("Mant. Delta", "outsourcing"),
]


def seed_data():
    """Inicializa catalogos, usuarios, proveedores y muestras operativas."""
    # Crea tablas si aun no existen.
    db.create_all()

    if Role.query.count() == 0:
        for role_name in ROLES:
            db.session.add(Role(name=role_name))
        db.session.commit()

    if User.query.count() == 0:
        for full_name, role_name, email in USERS:
            role = Role.query.filter_by(name=role_name).first()
            user = User(full_name=full_name, email=email, role_id=role.id)
            user.set_password("servicia2026")
            db.session.add(user)
        db.session.commit()

    if Provider.query.count() == 0:
        for provider_name, provider_type in PROVIDERS:
            db.session.add(Provider(name=provider_name, provider_type=provider_type))
        db.session.commit()

    if AuthorizedAccount.query.count() == 0:
        limpia = Provider.query.filter_by(name="Limpiadores SA").first()
        alfa = Provider.query.filter_by(name="Insumos Alfa").first()
        tech = Provider.query.filter_by(name="TechServ").first()

        db.session.add_all(
            [
                AuthorizedAccount(
                    provider_id=limpia.id,
                    bank="Banorte",
                    clabe="072180004821123456",
                    rfc="LIM010101AAA",
                    authorized_by="Salo",
                ),
                AuthorizedAccount(
                    provider_id=alfa.id,
                    bank="BBVA",
                    clabe="012180002210123456",
                    rfc="IAL020202BBB",
                    authorized_by="Salo",
                ),
                AuthorizedAccount(
                    provider_id=tech.id,
                    bank="BBVA",
                    clabe="012180008832123456",
                    rfc="TEC030303CCC",
                    authorized_by="Salo",
                ),
            ]
        )
        db.session.commit()

    if Folio.query.count() == 0:
        limpia = Provider.query.filter_by(name="Limpiadores SA").first()
        alfa = Provider.query.filter_by(name="Insumos Alfa").first()
        tech = Provider.query.filter_by(name="TechServ").first()

        db.session.add_all(
            [
                Folio(
                    singa_number="#17172",
                    provider_id=limpia.id,
                    provider_type="outsourcing",
                    communication_responsible="R. Fuentes",
                    contract_amount=150000,
                    budget_amount=148500,
                    status="en_proceso",
                ),
                Folio(
                    singa_number="#17165",
                    provider_id=alfa.id,
                    provider_type="materiales",
                    communication_responsible="C. Morales",
                    contract_amount=90000,
                    budget_amount=89200,
                    status="cerrado",
                ),
                Folio(
                    singa_number="#17160",
                    provider_id=tech.id,
                    provider_type="servicios",
                    communication_responsible="P. Ramirez",
                    contract_amount=210000,
                    budget_amount=185000,
                    status="alerta",
                ),
            ]
        )
        db.session.commit()

    # Configuracion SAT por proveedor (demo).
    for provider in Provider.query.all():
        compliance = ProviderCompliance.query.filter_by(provider_id=provider.id).first()
        if not compliance:
            compliance = ProviderCompliance(
                provider_id=provider.id,
                sat_opinion_status="vigente" if provider.name != "Mant. Delta" else "no_cargada",
                sat_valid_until=date(2026, 12, 31) if provider.name != "Mant. Delta" else None,
                efos_flag=False,
                activity_match=provider.name != "Mant. Delta",
                rfc_matches_account=provider.name != "Mant. Delta",
                notes="Semilla inicial",
            )
            db.session.add(compliance)
    db.session.commit()

    # Asegura workflow + checklist para cada folio.
    for folio in Folio.query.order_by(Folio.id.asc()).all():
        workflow = ensure_workflow(folio)
        db.session.add(workflow)
        for deliverable in ensure_deliverables(folio):
            db.session.add(deliverable)
    db.session.commit()

    # Marca algunos entregables como cargados para que el demo luzca "vivo".
    if FolioDeliverableItem.query.count() > 0:
        first_folio = Folio.query.filter_by(singa_number="#17172").first()
        if first_folio:
            for item in FolioDeliverableItem.query.filter_by(folio_id=first_folio.id).limit(3).all():
                if not item.uploaded:
                    item.uploaded = True
                    db.session.add(item)
        db.session.commit()
