# Servicia 0.1 (Piloto Batia)

Plataforma de aseguramiento contable construida con Flask usando patrón **App Factory + Blueprints**, con frontend server-rendered accesible y elegante.

## Objetivo de esta entrega (F1)
- Setup inicial del proyecto
- Esquema de base de datos con constraints críticas
- Autenticación y roles
- Auditoría de acciones desde el inicio
- Datos piloto hardcodeados de Batia
- Todo servido en **un solo localhost**

## Stack de esta versión
- Backend/API: Flask + SQLAlchemy + JWT
- Frontend: Jinja + CSS + JS (sin build externo)
- BD: SQLite por defecto (configurable por `DATABASE_URL`)

## Ejecutar en un solo localhost
1. Crear entorno e instalar dependencias:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configurar variables:
   ```bash
   cp .env.example .env
   ```
3. Levantar:
   ```bash
   python run.py
   ```
   O en un solo paso:
   ```bash
   ./start.sh
   ```
4. Abrir:
   - `http://127.0.0.1:5000`

## Usuarios piloto
Contraseña inicial para todos: `servicia2026`

- `salo@batia.local` (`direccion`)
- `mgonzalez@batia.local` (`tesoreria`)
- `lhernandez@batia.local` (`tesoreria`)
- `rfuentes@batia.local` (`ui`)
- `cmorales@batia.local` (`ui`)
- `pramirez@batia.local` (`contabilidad`)

## Estructura
- `app/__init__.py`: app factory, registro de blueprints
- `app/models.py`: modelos base + constraints
- `app/auth/`: login web + emisión JWT
- `app/folios/`: listado y creación con bloqueo duro
- `app/main/`: landing y dashboard
- `app/seed.py`: datos piloto Batia

## Regla dura ya implementada
- No permite crear folio con proveedor sin cuenta autorizada (lista blanca)

## Siguiente fase sugerida (F2)
- Traspasos bancarios con bloqueos SAT y excedente
- Checklist dinámico por tipo de proveedor
- Flujo secuencial obligatorio sección C
- Conciliación IA con PDF + Claude
