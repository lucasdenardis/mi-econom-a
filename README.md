# Finanzas Personales V2

Esta versión fue adaptada al Excel real `Planificador_Financiero_Fusionado FINAL (1).xlsx`.

## Estructura detectada

- Hojas históricas: `Ingresos` y `Gastos`
- `Gastos`: header=3, 164 filas
- `Ingresos`: header=3, 15 filas
- También se revisó `Config`, que contiene la clasificación 50/30/20 y el catálogo original.

## Importación

La primera vez que la tabla `movimientos` está vacía, `app.py` importa automáticamente:

- Gastos → `Gasto Fijo` o `Gasto Variable` según la columna `Tipo`
- Ingresos → `Ingreso`
- Fechas → `YYYY-MM-DD`
- Montos → numéricos
- Categorías y medios de pago → conservados

No vuelve a importar mientras existan movimientos, evitando duplicados.

## Publicación

1. Crear proyecto Supabase gratuito.
2. Ejecutar `schema.sql`.
3. Crear repositorio GitHub y subir:
   - app.py
   - requirements.txt
   - schema.sql
   - `Planificador_Financiero_Fusionado FINAL (1).xlsx`
4. Crear una app en Streamlit Community Cloud apuntando al repositorio.
5. En Secrets:

SUPABASE_URL = "https://TU-PROYECTO.supabase.co"
SUPABASE_KEY = "TU_ANON_KEY"

## Importante

Esta versión usa una base Supabase compartida. Para una aplicación financiera privada publicada en internet, recomiendo como siguiente paso agregar autenticación y RLS por usuario.
