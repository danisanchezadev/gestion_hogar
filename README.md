# Gestión Hogar

Aplicación local para gestionar las finanzas de un hogar con base SQLite y acceso mediante login local.

## Estado del proyecto

### Hecho

- Backend base separado en entidades, repositorio SQLite y servicio de negocio.
- Base de datos local `finance_data.db`.
- Tabla `movimiento` creada y operativa.
- Tabla `usuario` creada y operativa.
- Login local con usuario inicial `admin` y contraseña `admin`.
- Migración básica del JSON legado a SQLite.
- Añadido el campo `descripcion` a la tabla `movimiento`.
- Creada la tabla `categoria_personalizada` para soportar categorías configurables.
- Semilla inicial de categorías por defecto para ingresos y gastos.
- Pantalla principal tras login con accesos a `Configuración de categorías`, `Vista del mes`, `Agregar movimiento` y `Evolución mensual`.
- Pantalla de configuración de categorías ampliada con descripción, grupo, naturaleza, estado, marca esencial y frecuencia.
- Edición completa de categorías y actualización de movimientos asociados cuando cambia nombre, tipo o naturaleza.
- Borrado inteligente: elimina categorías sin uso y archiva automáticamente las que ya tienen movimientos.
- Filtros ampliados por tipo, naturaleza, grupo, frecuencia, esencial y estado.
- Resumen enriquecido de categorías con activas, archivadas, tipos, naturalezas y esenciales.
- La pantalla de movimientos ya carga las categorías desde SQLite en lugar de usar una lista fija.
- Añadido `inversion` como tercer tipo de movimiento junto a `ingreso` y `gasto`.

### Por hacer

- Pantalla de movimientos con últimos 10 registros y filtros avanzados.
- Filtros por rango de fechas, tipo, categoría, subcategoría, cantidad y descripción.
- Pantalla de seguimiento mensual con regla 50/30/10/10.
- Gráficos de anillo con escala de color desde azul eléctrico hasta rojo oscuro.
- Pantalla de evolución mensual con gráficos de barras.
- Asociar movimientos al usuario autenticado si decidimos que cada usuario tenga sus propios datos.

## Requisitos

- Python 3.11 o superior
- PySide6
- SQLite incluido en Python

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

Ese arranque inicializa la base de datos local, crea el usuario local por defecto si no existe y abre la ventana de login.

## Acceso inicial

- Usuario: `admin`
- Contraseña: `admin`

## Estructura

- `main.py`: arranque y comprobación básica del backend.
- `gestion_hogar/backend/entities.py`: entidades de dominio.
- `gestion_hogar/backend/repository.py`: acceso SQLite a la tabla `movimiento`.
- `gestion_hogar/backend/service.py`: reglas de negocio, validaciones y autenticación.
- `gestion_hogar/storage.py`: bootstrap compartido de la base de datos.
- `gestion_hogar/ui/login_window.py`: ventana de acceso.
- `gestion_hogar/ui/home_window.py`: pantalla principal de navegación tras autenticación.
- `gestion_hogar/ui/main_window.py`: sección actual de movimientos.
- `gestion_hogar/ui/section_window.py`: ventana provisional para secciones aún no desarrolladas.

## Modelo de datos actual

### Tabla `usuario`

- `id`
- `username`
- `password_hash`

### Tabla `movimiento`

- `id`
- `cantidad`
- `tipo`
- `categoria`
- `subcategoria`
- `fecha`
- `descripcion`

### Tabla `categoria_personalizada`

- `id`
- `nombre`
- `descripcion`
- `tipo_movimiento`
- `subtipo` (`naturaleza` en la interfaz)
- `grupo`
- `esencial`
- `frecuencia`
- `activa`

## Notas de diseño

- `tipo` en `movimiento` distingue entre `ingreso` y `gasto`.
- `categoria` en `movimiento` representa `fijo` o `variable`.
- `subcategoria` es la clasificación concreta que el usuario verá y configurará.
- `descripcion` sirve para observaciones libres sobre el movimiento.
- La interfaz llama `naturaleza` a lo que internamente sigue persistido como `subtipo` para mantener compatibilidad con los datos ya existentes.
- Las categorías archivadas se conservan para el histórico y no se ofrecen por defecto al registrar nuevos movimientos.
