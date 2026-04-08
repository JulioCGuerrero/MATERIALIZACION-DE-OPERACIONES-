# CODIGO PRUEBA  
# Servicia (Piloto Batia)

Plataforma de aseguramiento contable construida con Flask (App Factory + Blueprints), con frontend server-rendered y flujo operativo integral para UI, Contabilidad, Tesoreria y Direccion.

## Estado actual del proyecto
Esta version ya incluye:
- Login web por roles (UI, Contabilidad, Tesoreria, Direccion)
- Centro unificado de Folios SINGA (alta + filtros + historial)
- Flujo operativo con reglas de bloqueo por pasos
- Cumplimiento SAT/EFOS por proveedor
- Traspasos SPEI con validaciones fiscales y de presupuesto
- CFDI por folio (XML/PDF y control de estatus)
- Conciliacion bancaria manual y por carga de PDF
- Alertas operativas (deposito sin folio, excedente, cuenta no autorizada, diferencia CFDI-banco)
- Carga masiva de presupuestos desde Excel
- Reporte mensual a Direccion (manual y autogenerado)
- Acuse de conformidad UI + Contabilidad
- Carga y descarga de evidencias

## Stack
- Backend: Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended
- Frontend: Jinja, CSS, JS
- Utilidades: openpyxl (Excel), pypdf (extraccion de PDF)
- Base de datos: SQLite por defecto (configurable por `DATABASE_URL`)

## Requisitos
- Python 3.11+ (probado en 3.13)

## Instalacion y ejecucion
1. Instalar dependencias:
```bash
python -m pip install -r requirements.txt
```

2. Configurar entorno:
```bash
cp .env.example .env
```

3. Ejecutar aplicacion:
```bash
python run.py
```

4. Abrir en navegador:
- `http://127.0.0.1:5000`

## Usuarios demo
Contrasena para todos: `servicia2026`

- `salo@batia.local` (direccion)
- `mgonzalez@batia.local` (tesoreria)
- `lhernandez@batia.local` (tesoreria)
- `rfuentes@batia.local` (ui)
- `cmorales@batia.local` (ui)
- `pramirez@batia.local` (contabilidad)

## Rutas principales
- `/dashboard`
- `/folios/`
- `/operacion/`
- `/operacion/cumplimiento`
- `/operacion/traspasos`
- `/operacion/cfdi`
- `/operacion/conciliacion`
- `/operacion/presupuestos`
- `/operacion/reportes`
- `/operacion/acuse`

## Estructura
- `app/__init__.py`: inicializacion de app y blueprints
- `app/models.py`: modelos de dominio y operacion
- `app/auth/`: autenticacion
- `app/folios/`: gestion de folios
- `app/operations/`: modulos operativos (SAT, CFDI, conciliacion, reportes, acuse)
- `app/templates/`: vistas HTML
- `app/static/`: CSS y JS
- `app/seed.py`: datos demo

## Nota
La conciliacion por PDF usa extraccion base de texto. Si quieres precision de nivel productivo en bancos reales, se recomienda parser por formato bancario y validadores adicionales.

## Deploy en Cloud Run (mismo proyecto que million-logo-hunt)
Proyecto detectado en tu entorno: `trusty-agility-439318-a8`.

### 1) Preparar variables
1. Copiar archivo:
```powershell
Copy-Item .\env.yaml.example .\env.yaml
```
2. Ajustar secretos/SA en `env.yaml` con valores reales del proyecto.
Si quieres reutilizar el mismo stack de `million-logo-hunt`, usa:
- `CLOUDSQL_CONNECTION_NAME: trusty-agility-439318-a8:us-central1:mlh-db`
- `DATABASE_URL_SECRET_NAME: mlh-database-url`
- `SECRET_KEY_SECRET_NAME: mlh-secret-key`

### 2) Login de gcloud (si hace falta)
```powershell
& "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" auth login
& "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" config set project trusty-agility-439318-a8
```

### 3) Desplegar
```powershell
.\deploy.ps1 -Service "servicia-contabilidad" -Region "us-central1"
```

### 4) Hacerlo publico (si aparece 403)
```powershell
& "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services add-iam-policy-binding servicia-contabilidad `
  --region us-central1 `
  --member="allUsers" `
  --role="roles/run.invoker"
```

### Servicios sugeridos en el mismo proyecto
- `million-logo-hunt` (ya existente)
- `million-logo-hunt-web` (ya existente)
- `servicia-contabilidad` (este repo)
