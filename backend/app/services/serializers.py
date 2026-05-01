from .catalogo import DOC_LABELS


def doc_to_dict(doc):
    return {
        "id": doc.id,
        "tipo": doc.tipo,
        "label": DOC_LABELS.get(doc.tipo, doc.tipo),
        "subido": doc.subido,
        "nombre_archivo": doc.nombre_archivo,
        "url": doc.url,
        "subido_en": doc.subido_en.isoformat() if doc.subido_en else None,
        "subido_por": doc.subido_por,
    }


def expediente_to_dict(expediente):
    folio = expediente.folio
    proveedor = folio.proveedor
    empresa = folio.empresa
    return {
        "id": expediente.id,
        "folio_id": folio.id,
        "folio_numero": folio.numero,
        "proveedor_id": proveedor.id,
        "proveedor_nombre": proveedor.nombre,
        "empresa_id": empresa.id if empresa else None,
        "empresa_nombre": empresa.nombre if empresa else None,
        "nivel": proveedor.nivel,
        "completitud": expediente.completitud,
        "pago_bloqueado": expediente.pago_bloqueado,
        "razon_negocio": expediente.razon_negocio,
        "manifiesto": expediente.manifiesto,
        "presupuesto": folio.presupuesto,
        "estado_folio": folio.estado,
        "documentos": [doc_to_dict(d) for d in expediente.documentos],
    }
