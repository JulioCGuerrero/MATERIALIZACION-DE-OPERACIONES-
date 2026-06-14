from app import create_app
from app.models import Documento
from app.services.demo_uploads import ensure_demo_document_file

app = create_app()


with app.app_context():
    docs = Documento.query.filter_by(subido=True).all()
    generated = 0
    for doc in docs:
        expediente = doc.expediente
        if not expediente or not expediente.folio:
            continue
        folio = expediente.folio
        proveedor = folio.proveedor
        empresa = folio.empresa
        filename = doc.nombre_archivo or f"{doc.tipo}.pdf"
        ensure_demo_document_file(
            base_dir=app.config["BASE_DIR"],
            folio_numero=folio.numero,
            filename=filename,
            proveedor=proveedor.nombre if proveedor else "Proveedor demo",
            empresa=empresa.nombre if empresa else "Empresa demo",
            doc_tipo=doc.tipo,
            nivel=proveedor.nivel if proveedor else 1,
            periodo=folio.periodo,
        )
        generated += 1

    print(f"Placeholders generados o verificados: {generated}")
