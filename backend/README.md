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

`backend/seed.py` reinicia la base demo completa:

- borra la base actual
- vuelve a crear tablas
- vuelve a sembrar empresas, proveedores, folios, expedientes y credenciales demo
- vuelve a generar documentos placeholder en `uploads/`

Si capturas datos manualmente en la app y luego corres `seed.py`, esos cambios se pierden y el sistema regresa al escenario demo estándar.

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
- Empresa cliente: `X-Empresa-Username`

Roles internos operativos:

- `direccion`: consulta general (solo lectura) + gestión de políticas (`/api/empresas/{id}/policy/*`)
- `tesoreria`: traspasos y conciliación bancaria IA
- `administracion`: expedientes y carga documental
- `contabilidad`: operación completa (empresas/proveedores/folios/alertas/reportes/export)

### Actividades específicas por rol

#### `direccion`

- consulta dashboards, expedientes, semáforo, alertas, trazabilidad, cierre y reportes
- consulta el portal de empresa cliente y el portal proveedor en modo lectura
- puede revisar y gestionar políticas por empresa
- puede exportar reportes y paquete SAT

No debe:

- registrar empresas nuevas
- registrar proveedores nuevos
- subir documentos de onboarding
- modificar cuentas bancarias
- registrar traspasos

#### `tesoreria`

- consulta información operativa y bancaria en modo lectura
- registra traspasos bancarios
- ejecuta conciliación bancaria IA subiendo estado de cuenta
- resuelve alertas
- consulta auditoría IA
- exporta reportes y paquete SAT

No debe:

- registrar empresas nuevas
- registrar proveedores nuevos
- publicar políticas
- modificar onboarding documental de empresas
- modificar cuentas bancarias de empresas

#### `administracion`

- registra empresas cliente nuevas
- actualiza datos base de empresas
- sube, reemplaza y valida documentos de onboarding de empresa
- sube y reemplaza estado de cuenta bancario de empresa
- registra y edita cuentas bancarias de empresa
- guarda reglas de negocio
- envía a revisión y aprueba onboarding
- registra proveedores manualmente
- consulta cualquier portal de empresa cliente desde la vista administrativa

Es el rol maestro de altas y mantenimiento operativo.

#### `contabilidad`

- consulta operación completa
- consulta auditoría IA
- consulta reportes, cierre mensual y exportaciones
- puede gestionar empresas ya existentes solo para temas bancarios
- puede subir, reemplazar y validar únicamente el `estado_cuenta_bancario`
- puede registrar y editar cuentas bancarias de empresas ya existentes

No debe:

- crear empresas nuevas
- cambiar datos base de empresa
- subir documentos generales de onboarding
- modificar reglas de negocio
- aprobar onboarding
- registrar proveedores nuevos
- publicar políticas

## Datos demo sembrados

### Usuarios internos demo

Ingreso manual por usuario y contraseña. Cada cuenta tiene password propia:

- `salo@batia.local` · `direccion` · `DirBatia#2026`
- `mgonzalez@batia.local` · `tesoreria` · `TesoMgonz#2026`
- `lhernandez@batia.local` · `tesoreria` · `TesoLhern#2026`
- `rfuentes@batia.local` · `administracion` · `AdminRfuen#2026`
- `cmorales@batia.local` · `administracion` · `AdminCmora#2026`
- `pramirez@batia.local` · `contabilidad` · `ContaPram#2026`

### Empresas cliente demo

Se siembran dos empresas activas:

- `Batia` · RFC `BAT010101AAA`
- `Grupo Norte` · RFC `GRN010101BBB`

Ambas quedan listas para demo con:

- onboarding aprobado
- política activa publicada
- documentos obligatorios cargados y validados
- cuentas bancarias activas/validadas

### Credenciales demo de empresa cliente

El seed genera credenciales determinísticas para el portal empresa cliente:

```text
username: empresa_{empresa_id}_portal
password: demo-empresa-{empresa_id}
```

Credenciales demo actuales:

- `empresa_1_portal` / `demo-empresa-1` → `Batia`
- `empresa_2_portal` / `demo-empresa-2` → `Grupo Norte`

Cuando administración registra una empresa nueva desde la app, el backend también genera automáticamente su `username` y `password` para este portal.

### Proveedores demo registrados

Se siembran estos proveedores base:

- `Limpiadores SA`
- `Insumos Alfa`
- `TechServ`
- `Mant. Delta`

Además se generan sus folios, expedientes y documentos demo para portal proveedor.

### Credenciales demo de proveedor

El seed genera credenciales determinísticas por relación proveedor-empresa:

```text
username: prov_{proveedor_id}_emp_{empresa_id}
password: demo-prov-{proveedor_id}-{empresa_id}
```

Credenciales sembradas en la demo base:

- `prov_1_emp_1` / `demo-prov-1-1` → `Limpiadores SA` en `Batia`
- `prov_2_emp_1` / `demo-prov-2-1` → `Insumos Alfa` en `Batia`
- `prov_3_emp_2` / `demo-prov-3-2` → `TechServ` en `Grupo Norte`
- `prov_4_emp_2` / `demo-prov-4-2` → `Mant. Delta` en `Grupo Norte`

### Documentos demo

El seed deja archivos placeholder para demostración en:

- `uploads/<folio>/...` para documentos de expediente/proveedor
- `uploads/empresas/<empresa_id>/...` para onboarding de empresa cliente

Estos archivos:

- sirven para abrir documentos durante la demo sin `404`
- no son documentos fiscales, legales o bancarios reales
- existen solo como material de presentación

## Flujo proveedor por empresa (nuevo)

Prerequisito obligatorio para alta de proveedores:

- La empresa debe tener `onboarding` aprobado (`/api/empresas/{id}/onboarding/aprobar`).
- La empresa debe tener política activa publicada.

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

## Onboarding de empresa cliente (nuevo)

1. Alta base empresa:

```bash
POST /api/empresas
```

2. Subir y validar documentos requeridos:

```bash
GET /api/empresas/catalogo/onboarding
POST /api/empresas/{id}/documentos
PATCH /api/empresas/{id}/documentos/{doc_id}/validar
```

3. Registrar y validar cuentas bancarias:

```bash
POST /api/empresas/{id}/cuentas-bancarias
PATCH /api/empresas/{id}/cuentas-bancarias/{cuenta_id}
```

4. Configurar reglas de negocio:

```bash
PATCH /api/empresas/{id}/reglas-negocio
```

5. Revisar semáforo/checklist y aprobar onboarding:

```bash
GET /api/empresas/{id}/onboarding/status
POST /api/empresas/{id}/onboarding/enviar-revision
POST /api/empresas/{id}/onboarding/aprobar
```

## Portal empresa cliente (nuevo)

1. Administración registra la empresa cliente.
2. El backend crea credenciales del portal empresa y las devuelve en la respuesta.
3. Login empresa cliente:

```bash
POST /api/auth/empresa/login
```

4. La empresa autenticada consulta únicamente su propio resumen:

```bash
GET /api/portal-empresa/resumen
```

Este portal queda acotado a:

- datos de su empresa
- estatus de onboarding y política
- documentos de su empresa
- cuentas bancarias de su empresa
- proveedores y expedientes ligados a esa empresa

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

## Esquema PostgreSQL para nube

Nombre propuesto del esquema PostgreSQL:

```text
materializacion_operaciones
```

Archivo SQL listo para replicar la estructura actual:

- [backend/sql/materializacion_operaciones_postgres_schema.sql](/home/diego/Escritorio/materializacion_operaciones/backend/sql/materializacion_operaciones_postgres_schema.sql)

Uso sugerido en PostgreSQL:

```bash
psql "$DATABASE_URL" -f backend/sql/materializacion_operaciones_postgres_schema.sql
```

Ese script:

- crea el esquema `materializacion_operaciones`
- crea todas las tablas que usa hoy la app
- agrega llaves primarias, foráneas, `unique constraints` e índices base
- deja el `search_path` apuntando al esquema para que sea fácil ubicarlo
