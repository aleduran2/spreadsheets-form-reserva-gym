# 🏋️ Gym Reserva — Multi-Usuario vía Google Form + Sheets

Servicio para que varios alumnos se anoten a través de un Google Form y el sistema
reserve automáticamente su clase todos los días a las 00:01 (hora Argentina),
usando GitHub Actions + Google Sheets como base de datos de usuarios.

---

## Cómo funciona

1. Los alumnos completan un **Google Form** con su email/contraseña de TurnosWeb y horario preferido
2. Las respuestas se guardan automáticamente en una **Google Sheet**
3. Todos los días a las 00:01 ART, un script en **GitHub Actions**:
   - Lee la Sheet
   - Para cada alumno: hace login en Gonnet Box, busca su clase del día siguiente y la reserva
4. Al final muestra un resumen con el estado de cada alumno

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

## Setup paso a paso

### 1. Crear el Google Form

1. Ir a **forms.google.com** → formulario nuevo
2. Agregar estas preguntas (los nombres deben coincidir exactamente con las columnas que lee el script):
   - **Nombre completo** (texto corto)
   - **Email de TurnosWeb** (texto corto)
   - **Contraseña de TurnosWeb** (texto corto)
   - **Hora de clase preferida** (desplegable, ej: `08:00`, `09:00`, `17:00`, `19:00`)
3. En el formulario, pestaña **Respuestas** → ícono verde de Sheets → **Crear hoja de cálculo**
4. Anotá el nombre exacto que le pusiste a esa Sheet — lo vas a necesitar más adelante (por defecto se llama algo como "Respuestas Reserva Gym (Respuestas)")

> ⚠️ Cada alumno te está dando su contraseña real del gym. Aclará en la descripción del formulario qué uso le das a esos datos.

---

### 2. Crear proyecto en Google Cloud

1. Ir a **console.cloud.google.com**
2. Arriba a la izquierda, click en el selector de proyecto → **Proyecto nuevo**
3. Nombre: `gym-reserva-multi` → **Crear**
4. Una vez creado, seleccionalo desde el mismo selector de proyecto

---

### 3. Habilitar la API de Google Sheets

1. Menú lateral (☰) → **APIs y servicios → Biblioteca**
2. Buscar **Google Sheets API** → **Habilitar**

---

### 4. Crear la Service Account

1. Menú lateral → **APIs y servicios → Credenciales**
2. **Crear credenciales → Cuenta de servicio**
3. Completar:
   - **Nombre de la cuenta de servicio**: `gym-reserva-sheets-reader`
   - **Descripción**: `Lee la Google Sheet de usuarios para el script de reserva del gym`
4. **Crear y continuar**
5. Paso de permisos → dejar vacío → **Continuar**
6. Paso de principales con acceso → dejar vacío → **Listo**

> El aviso de "configurar la pantalla de consentimiento de OAuth" se puede ignorar — no aplica a este caso, porque la service account no le pide permiso a otros usuarios, solo accede a la Sheet que vos le compartís directamente.

7. En la lista de cuentas de servicio, copiá el email generado (formato `nombre@gym-reserva-multi.iam.gserviceaccount.com`)

---

### 5. Generar la clave JSON

1. Click en la cuenta de servicio recién creada
2. Pestaña **Claves (Keys)** → **Agregar clave → Crear clave nueva**
3. Tipo: **JSON** → **Crear**
4. Se descarga un archivo `.json` — **guardalo en un lugar seguro, no lo subas nunca al repo**

---

### 6. Compartir la Google Sheet con la Service Account

1. Abrí la Google Sheet de respuestas del Form
2. Botón **Compartir**
3. Pegá el email de la service account (el que copiaste en el paso 4)
4. Rol: **Lector**
5. **Enviar** (puede tirar un aviso de que es una cuenta externa — es esperado, confirmá)

---

### 7. Crear el repositorio en GitHub

1. **+ → New repository**
2. Nombre: `spreadsheets-form-reserva-gym`
3. Visibility: ✅ **Private**
4. ✅ **Add a README file**
5. **Create repository**

---

### 8. Crear los archivos del repo

#### `reservar.py`
**Add file → Create new file** → nombre `reservar.py` → pegar el contenido del script (incluido en este proyecto) → **Commit changes**

#### `requirements.txt`
**Add file → Create new file** → nombre `requirements.txt` → contenido:
```
requests==2.32.3
pytz==2024.1
gspread==6.1.2
google-auth==2.29.0
```
**Commit changes**

#### `.github/workflows/reserva.yml`
**Add file → Create new file** → nombre exacto `.github/workflows/reserva.yml` → pegar el contenido del workflow → **Commit changes**

---

### 9. Cargar los secrets en GitHub

En el repo → **Settings → Secrets and variables → Actions → New repository secret**

| Name | Valor |
|---|---|
| `GOOGLE_CREDENTIALS` | Todo el contenido del archivo `.json` descargado en el paso 5 |
| `SHEET_NAME` | El nombre exacto de la Google Sheet (paso 1.4) |

---

### 10. Probar manualmente

1. Pestaña **Actions** → **Reserva Gym Diaria (Multi-Usuario via Sheets)** → **Run workflow**
2. Click en el run para ver el log

Log esperado:
```
👥 4 usuarios cargados desde la Sheet

[Alumno Uno] --- Procesando usuario ---
[Alumno Uno] ✅ Login OK — Nombre Apellido
[Alumno Uno] 📋 7 clases encontradas para 20260527
[Alumno Uno] 🎯 Clase encontrada: Mié 27 08:00 — Crossfit / Functional (lugares: 14)
[Alumno Uno] ✅ Reserva confirmada: Mié 27 08:00 — Crossfit / Functional

=== Resumen ===
✅ Alumno Uno
✅ Alumno Dos
```

---

## Variables y columnas configurables

### En `reservar.py`

| Constante | Descripción |
|---|---|
| `SHEET_NAME` | Nombre de la Sheet (se puede pasar por variable de entorno) |
| `COL_NOMBRE`, `COL_EMAIL`, `COL_PASS`, `COL_HORA` | Deben coincidir EXACTO con los títulos de columna que generó el Form |
| `AGENDA` | ID del box en TurnosWeb (`0_227_0`, fijo para Gonnet Box) |

### Formato de la hora en el Form
El script acepta tanto `"08:00"` como `"080000"` en la columna de hora — los convierte automáticamente.

---

## Agregar o quitar alumnos

No hace falta tocar código ni secrets. Simplemente:
- **Agregar**: el alumno completa el Form de nuevo (o vos agregás una fila manual en la Sheet)
- **Quitar**: borrar su fila en la Sheet
- **Cambiar horario**: editar el valor de la columna "Hora de clase preferida" en la Sheet

El script lee la Sheet entera en cada ejecución, así que los cambios se aplican automáticamente esa misma noche.

---

## Horario del cron

| Cron | Días que corre | Reserva el día |
|---|---|---|
| `1 3 * * 0-5` | Domingo a viernes ✅ | Lunes a sábado |
| `1 3 * * 1-5` | Lunes a viernes | Martes a sábado |

---

## Seguridad y consideraciones

- Las contraseñas de los alumnos quedan guardadas en texto plano en la Google Sheet. Restringí el acceso a la Sheet solo a vos.
- Recomendá a los alumnos no reutilizar contraseñas sensibles para esta cuenta del gym.
- Avisale al gym/box que estás ofreciendo este servicio antes de automatizar logins masivos, para evitar que el proveedor de TurnosWeb lo confunda con actividad sospechosa.
- El archivo JSON de la service account nunca debe subirse al repo — solo vive como secret de GitHub.

---

## Consumo de GitHub Actions

Con ~15-20 usuarios, cada ejecución tarda unos 2-3 minutos. Corriendo todos los días, el consumo mensual es de aproximadamente 60-90 minutos — muy por debajo del límite gratuito de 2.000 minutos/mes.
