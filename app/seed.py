from datetime import date

from app.extensions import db
from app.models import AuthorizedAccount, Folio, Provider, Role, User


ROLES = ["direccion", "ui", "contabilidad", "tesoreria", "auditor"]

USERS = [
    ("Salo", "direccion", "salo@batia.local"),
    ("M. Gonzalez", "tesoreria", "mgonzalez@batia.local"),
    ("L. Hernandez", "tesoreria", "lhernandez@batia.local"),
    ("R. Fuentes", "ui", "rfuentes@batia.local"),
    ("C. Morales", "ui", "cmorales@batia.local"),
    ("P. Ramirez", "contabilidad", "pramirez@batia.local"),
]


PROVIDERS = [
    ("Limpiadores SA", "outsourcing"),
    ("Insumos Alfa", "materiales"),
    ("TechServ", "servicios"),
    ("Mant. Delta", "outsourcing"),
]


def seed_data():
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
                    contract_amount=148500,
                    budget_amount=150000,
                    status="en_proceso",
                ),
                Folio(
                    singa_number="#17165",
                    provider_id=alfa.id,
                    provider_type="materiales",
                    communication_responsible="C. Morales",
                    contract_amount=89200,
                    budget_amount=90000,
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

    # Mant. Delta intentionally has no authorized account
    mant = Provider.query.filter_by(name="Mant. Delta").first()
    if mant and not Folio.query.filter_by(singa_number="#17148").first():
        db.session.add(
            Folio(
                singa_number="#17148",
                provider_id=mant.id,
                provider_type="outsourcing",
                communication_responsible="R. Fuentes",
                contract_amount=320000,
                budget_amount=1,
                status="critico",
            )
        )
        db.session.commit()
