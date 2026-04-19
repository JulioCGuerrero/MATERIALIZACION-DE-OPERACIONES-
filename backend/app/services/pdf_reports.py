from datetime import datetime
from io import BytesIO

from flask import current_app, render_template


class PdfEngineMissing(RuntimeError):
    pass


def _html_to_pdf_bytes(html: str) -> bytes:
    try:
        from weasyprint import HTML
        base_url = str(current_app.config.get("BASE_DIR", current_app.root_path))
        return HTML(string=html, base_url=base_url).write_pdf()
    except Exception:
        # Fallback sin dependencias nativas pesadas
        try:
            from xhtml2pdf import pisa
        except Exception as exc:  # pragma: no cover
            raise PdfEngineMissing(
                "No se pudo generar PDF. Instala: pip install weasyprint xhtml2pdf"
            ) from exc

        output = BytesIO()
        result = pisa.CreatePDF(src=html, dest=output)
        if result.err:
            raise PdfEngineMissing(
                f"No se pudo generar PDF con motores disponibles (weasyprint/xhtml2pdf). Código: {result.err}"
            )
        return output.getvalue()


def render_pdf(template_name: str, **context) -> bytes:
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        **context,
    }
    html = render_template(template_name, **payload)
    return _html_to_pdf_bytes(html)
