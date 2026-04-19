# Backend Spec — Plataforma de Aseguramiento Contable
> Documento para agente de programación. Leer completo antes de escribir una sola línea de código.

---

## Contexto

Existe un prototipo funcional en un solo archivo `index.html` que simula toda la plataforma de aseguramiento contable para la empresa **Batia**. El objetivo de este backend es reemplazar todos los datos hardcodeados del HTML con datos reales persistidos en **SQLite**, expuestos via una **API REST con FastAPI**.

El frontend seguirá siendo el mismo HTML en una primera fase — solo se reemplazarán los datos estáticos por llamadas `fetch()` a la API.

---

## Stack

| Capa | Tecnología |
|---|---|
| API | FastAPI (Python 3.11+) |
| Base de datos | SQLite (archivo `database.db`) |
| ORM | SQLAlchemy 2.0 |
| Migraciones | Alembic |
| Validación | Pydantic v2 |
| Servidor dev | Uvicorn |
| Tests | Pytest |

### Instalación base
```bash
pip install fastapi uvicorn sqlalchemy alembic pydantic pytest httpx
```

### Estructura de carpetas
```
backend/
├── main.py                  # Entry point FastAPI
├── database.py              # Conexión SQLite + session
├── models/                  # Modelos SQLAlchemy
│   ├── __init__.py
│   ├── proveedor.py
│   ├── expediente.py
│   ├── documento.py
│   ├── folio.py
│   ├── traspaso.py
│   └── audit_log.py
├── schemas/                 # Pydantic schemas
│   ├── __init__.py
│   ├── proveedor.py
│   ├── expediente.py
│   ├── documento.py
│   ├── folio.py
│   ├── traspaso.py
│   └── audit_log.py
├── routers/                 # Endpoints por módulo
│   ├── __init__.py
│   ├── proveedores.py
│   ├── expedientes.py
│   ├── documentos.py
│   ├── folios.py
│   ├── traspasos.py
│   ├── clasificador.py
│   ├── semaforo.py
│   └── audit_log.py
├── services/                # Lógica de negocio
│   ├── clasificador.py      # Motor de clasificación N1-N4
│   ├── bloqueo.py           # Lógica de bloqueo de pagos
│   └── semaforo.py          # Cálculo del semáforo fiscal
├── seed.py                  # Datos de prueba (Batia)
├── alembic.ini
├── alembic/
│   └── versions/
└── tests/
    ├── test_clasificador.py
    ├── test_expedientes.py
    └── test_traspasos.py
```

---

## Base de datos — Esquema SQLite

### Tabla `proveedores`
```sql
CREATE TABLE proveedores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    rfc         TEXT NOT NULL UNIQUE,
    tipo        TEXT NOT NULL,         -- 'outsourcing' | 'materiales' | 'servicios' | 'construccion'
    nivel       INTEGER NOT NULL,      -- 1 | 2 | 3 | 4
    banco       TEXT,
    cuenta      TEXT,
    clabe       TEXT,
    repse       INTEGER DEFAULT 0,     -- 0 | 1 (boolean)
    tiene_fisico INTEGER DEFAULT 0,    -- 0 | 1
    efos_ok     INTEGER DEFAULT 1,     -- 0 = en lista negra, 1 = limpio
    activo      INTEGER DEFAULT 1,
    creado_en   TEXT DEFAULT (datetime('now'))
);
```

### Tabla `folios`
```sql
CREATE TABLE folios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    numero          TEXT NOT NULL UNIQUE,   -- ej. '17172'
    proveedor_id    INTEGER NOT NULL REFERENCES proveedores(id),
    presupuesto     REAL NOT NULL,          -- monto autorizado en SINGA
    periodo         TEXT NOT NULL,          -- ej. '2026-03'
    estado          TEXT DEFAULT 'activo',  -- 'activo' | 'cerrado' | 'cancelado'
    creado_en       TEXT DEFAULT (datetime('now')),
    cerrado_en      TEXT
);
```

### Tabla `expedientes`
```sql
CREATE TABLE expedientes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    folio_id        INTEGER NOT NULL REFERENCES folios(id),
    completitud     REAL DEFAULT 0.0,       -- porcentaje 0.0 - 100.0
    pago_bloqueado  INTEGER DEFAULT 1,      -- 1 = bloqueado, 0 = liberado
    razon_negocio   TEXT,                   -- respuesta Art. 5-A CFF
    manifiesto      INTEGER DEFAULT 0,      -- materialidad firmada
    creado_en       TEXT DEFAULT (datetime('now')),
    actualizado_en  TEXT DEFAULT (datetime('now'))
);
```

### Tabla `documentos`
```sql
CREATE TABLE documentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    expediente_id   INTEGER NOT NULL REFERENCES expedientes(id),
    tipo            TEXT NOT NULL,    -- ver catálogo abajo
    nombre_archivo  TEXT,
    url             TEXT,             -- path local o URL S3
    subido          INTEGER DEFAULT 0,
    subido_en       TEXT,
    subido_por      TEXT
);
```

**Catálogo de tipos de documento por nivel:**

| tipo | niveles | descripción |
|---|---|---|
| `cfdi_xml` | 1,2,3,4 | Factura XML |
| `cfdi_pdf` | 1,2,3,4 | Factura PDF |
| `constancia_sat` | 1,2,3,4 | Constancia de situación fiscal |
| `nota_remision` | 1 | Nota de remisión firmada |
| `foto_entrega` | 1,2 | Foto del producto/entrega |
| `crp` | 1,2,3,4 | Complemento de recepción de pagos |
| `opinion_32d` | 2,3,4 | Opinión 32-D SAT positiva |
| `contrato_nom151` | 2,3,4 | Contrato con fecha cierta NOM-151 |
| `carta_porte` | 2 | Guía de embarque / carta porte |
| `certificado_calidad` | 2 | Certificado de calidad |
| `entrada_erp` | 2 | Registro entrada almacén |
| `repse` | 3,4 | Registro REPSE |
| `curriculum_empresa` | 3 | Currículum empresarial |
| `bitacora` | 3,4 | Bitácora de actividades |
| `minutas` | 3,4 | Minutas de trabajo |
| `correos_avance` | 3 | Hilos de correo con avances |
| `entregable_efirma` | 3,4 | Entregable final con e.firma |
| `manifiesto_materialidad` | 3,4 | Carta bajo protesta |
| `acta_constitutiva` | 4 | Acta constitutiva del proveedor |
| `poder_representante` | 4 | Poderes del representante legal |
| `declaracion_anual` | 4 | Declaración anual ejercicio anterior |
| `nomina_imss` | 4 | Nómina IMSS del personal |
| `seguro_rc` | 4 | Seguro responsabilidad civil |
| `cedula_activos` | 4 | Cédula de activos fijos |
| `cuestionario_5a` | 3,4 | Análisis razón de negocios Art. 5-A |

### Tabla `traspasos`
```sql
CREATE TABLE traspasos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    folio_id        INTEGER NOT NULL REFERENCES folios(id),
    folio_bancario  TEXT,
    banco_origen    TEXT NOT NULL,
    banco_destino   TEXT,
    cuenta_destino  TEXT,
    monto           REAL NOT NULL,
    fecha           TEXT NOT NULL,
    estado          TEXT DEFAULT 'pendiente',  -- 'pendiente' | 'conciliado' | 'alerta'
    excede_presup   INTEGER DEFAULT 0,
    diferencia      REAL DEFAULT 0.0,
    registrado_por  TEXT,
    creado_en       TEXT DEFAULT (datetime('now'))
);
```

### Tabla `audit_log`
```sql
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tabla       TEXT NOT NULL,       -- 'expedientes' | 'traspasos' | 'documentos' ...
    tabla_id    INTEGER NOT NULL,
    accion      TEXT NOT NULL,       -- 'crear' | 'actualizar' | 'bloquear' | 'liberar' | 'alerta_ia'
    detalle     TEXT,                -- JSON string con el contexto
    usuario     TEXT,
    creado_en   TEXT DEFAULT (datetime('now'))
);
```

---

## Motor de Clasificación N1–N4

Implementar en `services/clasificador.py`. Es la lógica central del sistema.

```python
def clasificar_proveedor(
    tipo: str,          # 'limpieza' | 'materia' | 'outsourcing' | 'consultoria' | 'construccion'
    monto: float,       # monto estimado de la operación
    repse: bool,        # ¿el personal opera en las instalaciones?
    tiene_fisico: bool  # ¿hay un bien físico que entra al almacén?
) -> dict:
    """
    Retorna:
    {
        "nivel": int,           # 1 | 2 | 3 | 4
        "label": str,           # "Transaccional" | "Operativo" | "Servicios Intangibles" | "Estratégico"
        "documentos": list[str] # lista de tipos de documentos requeridos
        "riesgo": str           # "bajo" | "medio" | "alto" | "critico"
    }
    """
```

**Reglas de clasificación (implementar exactamente así):**

```python
# Nivel 4 — Estratégico
if tipo == 'construccion' or monto > 500_000:
    nivel = 4

# Nivel 3 — Servicios Intangibles
elif tipo in ('consultoria', 'outsourcing') or (repse and not tiene_fisico):
    nivel = 3

# Nivel 2 — Operativo
elif tipo == 'materia' or tiene_fisico:
    nivel = 2

# Nivel 1 — Transaccional
else:
    nivel = 1
```

Los documentos requeridos se generan automáticamente según el catálogo de la sección anterior.

---

## Lógica de Bloqueo de Pagos

Implementar en `services/bloqueo.py`.

```python
def calcular_completitud(expediente_id: int, db: Session) -> float:
    """
    Cuenta documentos subidos / documentos totales requeridos.
    Actualiza expediente.completitud y expediente.pago_bloqueado en la DB.
    Registra en audit_log si el estado cambia.
    Retorna el porcentaje (0.0 - 100.0).
    """

def puede_pagar(expediente_id: int, db: Session) -> dict:
    """
    Retorna:
    {
        "puede_pagar": bool,
        "completitud": float,
        "documentos_faltantes": list[str]
    }
    Si completitud < 100.0 → puede_pagar = False, HTTP 403 en el endpoint de traspaso.
    """
```

---

## Semáforo Fiscal

Implementar en `services/semaforo.py`. Calcula el estado de cada indicador del módulo fiscal.

```python
def calcular_semaforo(db: Session) -> dict:
    """
    Retorna un dict con cada indicador y su estado:
    {
        "efos": {
            "estado": "verde" | "amarillo" | "rojo",
            "valor": "24/24 proveedores OK",
            "ley": "Art. 69-B CFF"
        },
        "cfdi_correcto": { ... },
        "nom151": { ... },
        "repse": { ... },
        "manifiesto": { ... },
        "razon_negocios": { ... }
    }
    """
```

**Reglas de color:**
- `verde`: cumplimiento >= 90%
- `amarillo`: cumplimiento entre 70% y 89%
- `rojo`: cumplimiento < 70% o hay casos críticos

---

## Endpoints de la API

### Proveedores
```
GET    /api/proveedores                  # Lista todos con nivel y estado EFOS
GET    /api/proveedores/{id}             # Detalle de un proveedor
POST   /api/proveedores                  # Crear proveedor (ejecuta clasificador automáticamente)
PATCH  /api/proveedores/{id}             # Actualizar datos
GET    /api/proveedores/{id}/expedientes # Todos los expedientes de un proveedor
```

### Clasificador
```
POST   /api/clasificar
# Body: { tipo, monto, repse, tiene_fisico }
# Response: { nivel, label, documentos, riesgo }
```

### Folios
```
GET    /api/folios                       # Lista con filtros: ?periodo= ?estado= ?proveedor_id=
GET    /api/folios/{id}                  # Detalle completo
POST   /api/folios                       # Crear folio (genera expediente y documentos automáticamente)
PATCH  /api/folios/{id}                  # Actualizar estado
```

### Expedientes
```
GET    /api/expedientes                  # Lista con filtros: ?nivel= ?bloqueado= ?proveedor_id=
GET    /api/expedientes/{id}             # Detalle + checklist de documentos + completitud
GET    /api/expedientes/{id}/completitud # Solo el % y documentos faltantes
```

### Documentos
```
GET    /api/documentos/{expediente_id}   # Checklist completo del expediente
POST   /api/documentos/{id}/subir        # Marcar documento como subido
# Body: { nombre_archivo, url, subido_por }
# Después de subir: recalcula completitud y desbloquea pago si llega a 100%
```

### Traspasos
```
GET    /api/traspasos                    # Lista con filtros: ?folio_id= ?estado=
GET    /api/traspasos/{id}               # Detalle
POST   /api/traspasos                    # Registrar traspaso
# IMPORTANTE: antes de crear, verifica puede_pagar().
# Si pago_bloqueado = 1 → retorna HTTP 403 con detalle de documentos faltantes.
# Si monto > folio.presupuesto → marca excede_presup=1, registra alerta en audit_log.
```

### Semáforo
```
GET    /api/semaforo                     # Estado completo del semáforo fiscal
GET    /api/semaforo/efos                # Solo validación EFOS (simula llamada al SAT)
```

### Dashboard
```
GET    /api/dashboard                    # KPIs globales para la pantalla principal
# Response:
# {
#   "folios_activos": int,
#   "materializados": int,
#   "pagos_bloqueados": int,
#   "alertas_ia": int,
#   "por_nivel": { "n1": int, "n2": int, "n3": int, "n4": int },
#   "semaforo": { ... }
# }
```

### Auditoría
```
GET    /api/audit_log                    # Log completo con filtros: ?tabla= ?accion= ?desde=
```

---

## Datos de prueba — seed.py

Crear un script `seed.py` que al ejecutarse con `python seed.py` llene la base de datos con los datos del prototipo HTML:

### Proveedores a crear:
```python
proveedores = [
    { "nombre": "Limpiadores SA", "rfc": "LSA010101AAA", "tipo": "outsourcing",   "nivel": 3, "banco": "Banorte", "cuenta": "4821", "repse": False, "tiene_fisico": False },
    { "nombre": "Insumos Alfa",   "rfc": "IAL010101BBB", "tipo": "materiales",    "nivel": 2, "banco": "BBVA",    "cuenta": "2210", "repse": False, "tiene_fisico": True  },
    { "nombre": "TechServ",       "rfc": "TSV010101CCC", "tipo": "consultoria",   "nivel": 3, "banco": "BBVA",    "cuenta": "8832", "repse": True,  "tiene_fisico": False },
    { "nombre": "Mant. Delta",    "rfc": "MDE010101DDD", "tipo": "construccion",  "nivel": 4, "banco": None,      "cuenta": None,   "repse": True,  "tiene_fisico": True  },
]
```

### Folios a crear:
```python
folios = [
    { "numero": "17172", "proveedor": "Limpiadores SA", "presupuesto": 150_000, "periodo": "2026-03" },
    { "numero": "17165", "proveedor": "Insumos Alfa",   "presupuesto":  90_000, "periodo": "2026-03" },
    { "numero": "17160", "proveedor": "TechServ",       "presupuesto": 185_000, "periodo": "2026-03" },
    { "numero": "17148", "proveedor": "Mant. Delta",    "presupuesto":       0, "periodo": "2026-03" },
]
```

### Estado de documentos (simular progreso):
- Folio 17165 (Insumos Alfa N2): **100% completo** → pago liberado
- Folio 17172 (Limpiadores SA N3): **60% completo** → pago bloqueado
- Folio 17160 (TechServ N3): **35% completo** → pago bloqueado + alerta excede presupuesto
- Folio 17148 (Mant. Delta N4): **10% completo** → pago bloqueado + sin presupuesto SINGA

### Traspasos a crear:
```python
traspasos = [
    { "folio": "17172", "folio_bancario": "182822", "monto": 148_500, "banco_origen": "Banorte", "fecha": "2026-03-14", "estado": "conciliado" },
    { "folio": "17165", "folio_bancario":  "91822", "monto":  89_200, "banco_origen": "Banorte", "fecha": "2026-03-08", "estado": "conciliado" },
    { "folio": "17160", "folio_bancario":  "28228", "monto": 210_000, "banco_origen": "BBVA",    "fecha": "2026-03-18", "estado": "alerta", "excede_presup": True, "diferencia": 25_000 },
    { "folio": "17148", "folio_bancario": None,      "monto": 320_000, "banco_origen": "Banorte", "fecha": "2026-03-14", "estado": "alerta" },
]
```

---

## Configuración CORS

El HTML se sirve desde `file://` o un servidor local diferente al de la API. Configurar CORS en `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # En producción restringir al dominio del frontend
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Tests mínimos requeridos

```python
# test_clasificador.py
def test_nivel_1_limpieza_monto_bajo()    # tipo=limpieza, monto=30000 → nivel 1
def test_nivel_2_materiales_fisico()      # tipo=materia, tiene_fisico=True → nivel 2
def test_nivel_3_consultoria()            # tipo=consultoria → nivel 3
def test_nivel_4_construccion()           # tipo=construccion → nivel 4
def test_nivel_4_monto_alto()             # monto=600000 → nivel 4 sin importar tipo

# test_expedientes.py
def test_completitud_cero_al_crear()      # expediente nuevo → completitud = 0
def test_completitud_actualiza()          # subir doc → recalcula correctamente
def test_pago_liberado_al_100()           # al llegar a 100% → pago_bloqueado = 0

# test_traspasos.py
def test_traspaso_bloqueado_sin_materialidad()  # → HTTP 403
def test_traspaso_ok_con_materialidad()         # → HTTP 201
def test_alerta_excede_presupuesto()            # monto > presupuesto → excede_presup = 1
```

---

## Comandos para arrancar

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install fastapi uvicorn sqlalchemy alembic pydantic pytest httpx

# 3. Inicializar base de datos
python -c "from database import Base, engine; Base.metadata.create_all(engine)"

# 4. Cargar datos de prueba
python seed.py

# 5. Levantar servidor
uvicorn main:app --reload --port 8000

# 6. Ver documentación interactiva
# http://localhost:8000/docs

# 7. Correr tests
pytest tests/ -v
```

---

## Notas finales para el agente

1. **No inventar lógica** — toda la lógica de negocio (niveles, documentos requeridos, bloqueo de pagos, semáforo) está descrita exactamente en este documento. Implementarla tal cual.

2. **Registrar todo en audit_log** — cualquier cambio de estado (bloqueo, liberación, alerta, subida de documento) debe quedar registrado con timestamp y usuario.

3. **El clasificador es el corazón del sistema** — cuando se crea un proveedor, el nivel se asigna automáticamente. Cuando se crea un folio, los documentos requeridos se generan automáticamente según el nivel.

4. **SQLite es suficiente para esta fase** — no usar PostgreSQL todavía. El archivo `database.db` debe crearse en la raíz del proyecto.

5. **La API debe ser consumible desde el HTML existente** — todos los endpoints retornan JSON. El frontend hará `fetch('http://localhost:8000/api/...')` para reemplazar los datos hardcodeados.