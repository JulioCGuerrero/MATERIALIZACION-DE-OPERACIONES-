from collections import defaultdict
from datetime import datetime

from ..models import AuditLog


def _area_from_row(row: AuditLog) -> str:
    if row.tabla in ("traspasos",):
        return "Tesorería"
    if row.tabla in ("documentos", "expedientes"):
        return "Administración"
    if row.tabla in ("proveedores", "folios", "audit_log", "alertas", "empresas"):
        return "Contabilidad"
    return "General"


def _kpi_name(area: str) -> str:
    if area == "Tesorería":
        return "Traspasos registrados y conciliados"
    if area == "Administración":
        return "Expedientes y evidencia documental"
    if area == "Contabilidad":
        return "Gobierno fiscal (EFOS/semaforo/reportes)"
    return "Cumplimiento operativo"


def kpis_personal_data(periodo: str | None = None) -> dict:
    q = AuditLog.query
    if periodo:
        try:
            start = datetime.fromisoformat(f"{periodo}-01T00:00:00")
            if int(periodo.split("-")[1]) == 12:
                end = datetime.fromisoformat(f"{int(periodo.split('-')[0]) + 1}-01-01T00:00:00")
            else:
                end = datetime.fromisoformat(
                    f"{periodo.split('-')[0]}-{int(periodo.split('-')[1]) + 1:02d}-01T00:00:00"
                )
            q = q.filter(AuditLog.creado_en >= start, AuditLog.creado_en < end)
        except Exception:
            pass

    rows = q.order_by(AuditLog.creado_en.desc()).all()
    by_user = defaultdict(list)
    for r in rows:
        user = (r.usuario or "Sistema").strip()
        by_user[user].append(r)

    people = []
    sistema = None
    for user, evs in by_user.items():
        total = len(evs)
        bad = sum(1 for e in evs if ("bloquear" in e.accion) or ("alerta" in e.accion))
        good = sum(1 for e in evs if ("liberar" in e.accion) or ("crear" in e.accion))
        score = max(0, min(100, round(((good + 1) / (total + 1)) * 100 - (bad * 4))))
        area_counts = defaultdict(int)
        for e in evs:
            area_counts[_area_from_row(e)] += 1
        area = max(area_counts.items(), key=lambda x: x[1])[0] if area_counts else "General"
        trend = "↑" if score >= 85 else ("→" if score >= 70 else "↓")
        item = {
            "usuario": user,
            "area": area,
            "kpi": _kpi_name(area),
            "score": score,
            "trend": trend,
            "eventos": total,
        }
        if user.lower() == "sistema":
            sistema = item
        else:
            people.append(item)

    people.sort(key=lambda x: x["score"], reverse=True)
    avg = round(sum(p["score"] for p in people) / len(people), 1) if people else 0.0
    return {"periodo": periodo, "promedio": avg, "personas": people, "sistema": sistema}
