# Backend Materialización (Flask)

## Requisitos

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Inicializar base y seed

```bash
python backend/init_db.py
python backend/seed.py
```

## Levantar API

```bash
python backend/run.py
# API: http://localhost:8010/api/health
```

Puerto por defecto: `8010`.

Si necesitas usar otro puerto temporalmente:

```bash
PORT=8011 python backend/run.py
```

## Endpoints principales

- `GET /api/dashboard`
- `POST /api/clasificar`
- `GET /api/folios`
- `GET /api/expedientes/{id}`
- `GET /api/expedientes/{id}/completitud`
- `POST /api/proveedores`
- `GET /api/empresas`
- `POST /api/empresas`
- `GET /api/efos/consultar?rfc=...`
- `POST /api/efos/cargar`
- `POST /api/traspasos`
- `POST /api/folios/ciclo-mensual`
- `GET /api/alertas`
- `POST /api/alertas/generar`
- `PATCH /api/alertas/{id}/resolver`
- `GET /api/semaforo`
- `GET /api/audit_log`
- `GET /api/reportes/nivel`
- `GET /api/reportes/semaforo`
- `GET /api/reportes/trazabilidad`
- `POST /api/conciliacion/estado_cuenta`
- `GET /api/export/reportes/nivel.pdf`
- `GET /api/export/reportes/semaforo.pdf`
- `GET /api/export/reportes/trazabilidad.pdf`
- `GET /api/export/reportes/auditoria.pdf`
- `GET /api/export/paquete_sat.zip`

El frontend (`frontend.html`) ya está conectado a estos endpoints.

## Acceso por rol (nuevo)

El backend ahora valida acceso por rol usando encabezados:

- Interno: `X-Auth-Email` + `X-Auth-Role`
- Proveedor: `X-Proveedor-Username`

Roles internos operativos:

- `direccion`: consulta general (solo lectura) + gestión de políticas (`/api/empresas/{id}/policy/*`)
- `tesoreria`: traspasos y conciliación bancaria IA
- `administracion`: expedientes y carga documental
- `contabilidad`: operación completa (empresas/proveedores/folios/alertas/reportes/export)

## Flujo proveedor por empresa (nuevo)

1. Auto-registro público:

```bash
POST /api/proveedores/self-register
```

Payload base:

```json
{
  "nombre": "Proveedor XYZ",
  "rfc": "XYZ010101AAA",
  "tipo": "outsourcing",
  "monto": 120000,
  "repse": true,
  "tiene_fisico": false,
  "empresa_id": 1
}
```

2. El sistema crea/relaciona proveedor, genera folio/expediente y devuelve credenciales por empresa (`username`, `password`).
3. Login proveedor:

```bash
POST /api/auth/proveedor/login
```

4. Proveedor autenticado solo puede consultar/subir su propia información (misma empresa/proveedor).

## Subida real de documentos

`POST /api/documentos/{id}/subir` acepta:

- JSON: `{ nombre_archivo, url, subido_por }`
- `multipart/form-data` con campo `archivo` (guarda en `uploads/<expediente_id>/`)

## Tests rápidos

```bash
cd backend
pytest -q
```

## Exportación PDF (diseño empresarial)

La exportación usa plantillas HTML + CSS y motor `weasyprint` con fallback automático a `xhtml2pdf`.

Si al exportar aparece error de motor PDF:

```bash
pip install weasyprint xhtml2pdf
```
