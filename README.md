# 🏋️ Gym Reserva — Multi-Usuario vía Google Form + Sheets

Servicio para que varios alumnos se anoten a través de un Google Form y el sistema
reserve automáticamente su clase todos los días a las 00:01 (hora Argentina),
usando GitHub Actions + Google Sheets como base de datos de usuarios.

---

## Cómo funciona

1. Los alumnos completan un **Google Form** con su email/contraseña de TurnosWeb y horario preferido
2. Las respuestas se guardan automáticamente en una **Google Sheet**
3. Todos los días a las **00:01 ART** (domingo a viernes), un workflow de **GitHub Actions**:
   - Lee la Sheet usando una **Service Account** de Google Cloud
   - Para cada fila/alumno: hace login en Gonnet Box, busca su clase del día siguiente **a la hora que cada uno eligió**, y la reserva
4. Al final muestra un resumen con el estado de cada alumno (✅ / ❌)

---

## Estructura del repo

```
spreadsheets-form-reserva-gym/
├── .github/
│   └── workflows/
│       └── reserva.yml
├── reservar.py
├── requirements.txt
└── README.md
```

---

## Setup completo (flujo que se siguió)

### 1. Crear el Google Form

1. **forms.google.com** → formulario nuevo
2. Preguntas (texto corto, salvo la última que es desplegable):
   - Nombre completo
   - Email de TurnosWeb
   - Contraseña de TurnosWeb
   - Hora de clase (ej: `8:00`, `09:00`, `17:00`, `19:00`)
3. Pestaña **Respuestas** → ícono de Sheets → **Crear hoja de cálculo**
4. Esa Sheet se va llenando sola con cada respuesta

> El script reconoce las columnas aunque tengan espacios extra o el texto varíe levemente (ej: "Hora de clase" en vez de "Hora de clase preferida") — hace matching flexible ignorando mayúsculas y espacios.

---

### 2. Google Cloud — proyecto, API y Service Account

1. **console.cloud.google.com** → crear proyecto (ej: `gym-reserva-multi`)
2. **APIs y servicios → Biblioteca** → buscar **Google Sheets API** → **Habilitar**
3. **APIs y servicios → Credenciales → Crear credenciales → Cuenta de servicio**
   - Nombre: `gym-reserva-sheets-reader`
4. Click en la cuenta creada → pestaña **Claves → Agregar clave → Crear clave nueva → JSON**
5. Se descarga un `.json` con las credenciales — **nunca subir este archivo al repo**

---

### 3. Compartir la Sheet con la Service Account

1. Abrí el `.json` descargado, copiá el valor de `client_email`
2. En la Google Sheet → **Compartir** → pegar ese email → rol **Lector**

---

### 4. Obtener el ID de la Sheet

El ID es la parte de la URL entre `/d/` y `/edit`:

```
https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit
```

---

### 5. Cargar los secrets en GitHub

En el repo → **Settings → Secrets and variables → Actions → New repository secret**

| Name | Valor |
|---|---|
| `GOOGLE_CREDENTIALS` | Contenido completo del archivo `.json` de la Service Account |
| `SHEET_ID` | El ID de la Sheet (paso 4) |

> Se usa el **ID** y no el nombre de la Sheet (`open_by_key`) para no depender de la API de Google Drive — con permisos solo de Sheets alcanza.

---

### 6. Workflow de GitHub Actions

`.github/workflows/reserva.yml` corre automáticamente:

```yaml
on:
  schedule:
    - cron: "1 3 * * 0-5"   # 00:01 ART (UTC-3), domingo a viernes
  workflow_dispatch:
```

- **Automático**: todos los días domingo a viernes a las 00:01 ART
- **Manual**: pestaña **Actions → Reserva Gym Diaria (Multi-Usuario via Sheets) → Run workflow**

---

## Variables y columnas reconocidas

### En `reservar.py`

| Constante | Descripción |
|---|---|
| `AGENDA` | ID del box en TurnosWeb (`0_227_0`, fijo para Gonnet Box) |
| `SHEET_ID` | Viene del secret, identifica la Google Sheet |
| `COL_NOMBRE`, `COL_EMAIL`, `COL_PASS`, `COL_HORA` | Nombres "ideales" de columna — el matching es flexible y también acepta variantes |

### Formato de la hora en el Form
Acepta `"8:00"`, `"08:00"` o `"080000"` — el script normaliza todo a formato `HHMMSS` internamente.

### Columnas — variantes aceptadas
| Dato | Nombres que reconoce |
|---|---|
| Nombre | "Nombre completo", "Nombre" |
| Email | "Email de TurnosWeb", "Email", "Correo" |
| Contraseña | "Contraseña de TurnosWeb", "Contraseña", "Password" |
| Hora | "Hora de clase preferida", "Hora de clase", "Hora" |

---

## Agregar, editar o quitar alumnos

No hace falta tocar código ni secrets — todo se gestiona desde la Sheet:
- **Agregar**: el alumno completa el Form (o se agrega una fila manual)
- **Quitar**: borrar su fila en la Sheet
- **Cambiar horario**: editar el valor de la columna de hora en la Sheet

El script lee la Sheet entera en cada ejecución, así que los cambios se aplican esa misma noche.

---

## Probar manualmente

1. **Actions → Reserva Gym Diaria (Multi-Usuario via Sheets) → Run workflow**
2. Click en el run → expandir el paso **"Ejecutar reserva"**

Log esperado con usuarios reales:
```
👥 2 usuarios cargados desde la Sheet

[Alumno Uno] --- Procesando usuario ---
[Alumno Uno] ✅ Login OK — Nombre Apellido
[Alumno Uno] 📋 7 clases encontradas para 20260626
[Alumno Uno] 🎯 Clase encontrada: Vie 26 08:00 — Crossfit / Functional (lugares: 14)
[Alumno Uno] ✅ Reserva confirmada: Vie 26 08:00 — Crossfit / Functional

[Alumno Dos] --- Procesando usuario ---
...

=== Resumen ===
✅ Alumno Uno
✅ Alumno Dos
```

Si una fila está incompleta (faltan datos), se omite con un aviso y no frena al resto.

---

## Relación con el otro repo (`gym-reserva`)

| Repo | Para quién | Horario de reserva |
|---|---|---|
| `gym-reserva` | Uso individual propio | Siempre 08:00, hardcodeado |
| `spreadsheets-form-reserva-gym` | Multi-usuario | Cada alumno define su propia hora en el Form |

Ambos corren con el mismo cron (00:01 ART), son independientes entre sí y no interfieren.

---

## Seguridad y consideraciones

- Las contraseñas de los alumnos quedan en texto plano en la Sheet — restringir el acceso solo a quien administra el servicio.
- Recomendarles a los alumnos no reutilizar contraseñas sensibles en esta cuenta del gym.
- Avisarle al gym/box sobre este servicio, para que no confunda logins automáticos masivos con actividad sospechosa.
- El `.json` de la Service Account vive únicamente como secret de GitHub, nunca en el código del repo.

---

## Consumo de GitHub Actions

Con ~15-20 usuarios, cada ejecución tarda unos 2-3 minutos. Corriendo todos los días, el consumo mensual estimado es de 60-90 minutos — muy por debajo del límite gratuito de 2.000 minutos/mes (~33 horas).
