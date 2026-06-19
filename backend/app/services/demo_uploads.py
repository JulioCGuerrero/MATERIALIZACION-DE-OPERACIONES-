from __future__ import annotations

from pathlib import Path

from .catalogo import DOC_LABELS, LEVEL_LABELS
from .storage import save_bytes


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_simple_pdf(lines: list[str]) -> bytes:
    content_parts = ["BT", "/F1 16 Tf", "50 770 Td"]
    first = True
    for line in lines:
        escaped = _escape_pdf_text(line)
        if first:
            content_parts.append(f"({escaped}) Tj")
            first = False
        else:
            content_parts.append("0 -22 Td")
            content_parts.append(f"({escaped}) Tj")
    content_parts.append("ET")
    content = "\n".join(content_parts).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>".encode("ascii") + b"\nstream\n" + content + b"\nendstream",
    ]

    chunks = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")

    xref_start = sum(len(chunk) for chunk in chunks)
    xref = [f"xref\n0 {len(objects) + 1}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")
    return b"".join(chunks + xref + [trailer])


def build_demo_document_pdf(*, proveedor: str, empresa: str, folio: str, doc_tipo: str, nivel: int, periodo: str) -> bytes:
    label = DOC_LABELS.get(doc_tipo, doc_tipo.replace("_", " ").title())
    lines = [
        "SINGA · Documento Demo",
        f"Documento: {label}",
        f"Folio: {folio}",
        f"Proveedor: {proveedor}",
        f"Empresa: {empresa}",
        f"Nivel: N{nivel} · {LEVEL_LABELS.get(nivel, 'Operativo')}",
        f"Periodo: {periodo}",
        "Este archivo es un placeholder para demostracion del portal.",
        "No corresponde a un comprobante fiscal o legal real.",
    ]
    return _build_simple_pdf(lines)


def ensure_demo_document_file(
    *,
    base_dir: Path,
    folio_numero: str,
    filename: str,
    proveedor: str,
    empresa: str,
    doc_tipo: str,
    nivel: int,
    periodo: str,
) -> Path:
    file_path = base_dir / "uploads" / str(folio_numero) / filename
    save_bytes(
        build_demo_document_pdf(
            proveedor=proveedor,
            empresa=empresa,
            folio=str(folio_numero),
            doc_tipo=doc_tipo,
            nivel=nivel,
            periodo=periodo,
        ),
        f"{folio_numero}/{filename}",
        "application/pdf",
        only_if_missing=True,
    )
    return file_path


def build_demo_empresa_document_pdf(
    *,
    empresa: str,
    rfc: str,
    doc_tipo: str,
    filename: str,
) -> bytes:
    label = DOC_LABELS.get(doc_tipo, doc_tipo.replace("_", " ").title())
    lines = [
        "SINGA · Documento Demo Empresa",
        f"Empresa: {empresa}",
        f"RFC: {rfc}",
        f"Documento: {label}",
        f"Archivo: {filename}",
        "Este archivo es un placeholder para demostracion de onboarding.",
        "No corresponde a un documento legal o bancario real.",
    ]
    return _build_simple_pdf(lines)


def ensure_demo_empresa_document_file(
    *,
    base_dir: Path,
    empresa_id: int,
    filename: str,
    empresa: str,
    rfc: str,
    doc_tipo: str,
) -> Path:
    file_path = base_dir / "uploads" / "empresas" / str(empresa_id) / filename
    save_bytes(
        build_demo_empresa_document_pdf(
            empresa=empresa,
            rfc=rfc,
            doc_tipo=doc_tipo,
            filename=filename,
        ),
        f"empresas/{empresa_id}/{filename}",
        "application/pdf",
        only_if_missing=True,
    )
    return file_path
