# SIRIS-Javeriana

SIRIS is a research-oriented geospatial platform for Sentinel-2 satellite image restoration, temporal gap filling, super-resolution and visualization over the Colombian Pacific region.

The project combines cloud detection, temporal imputation, spatial super-resolution, user authentication and a web dashboard that allows users to select an area of interest, define a date range and generate exportable satellite products.

The current version includes a React + Vite frontend, a FastAPI backend, SQLite-based authentication, asynchronous geospatial export processing and Cloudflare Tunnel deployment support.

---

## Main Features

- Sentinel-2 time series visualization.
- Interactive web map using Leaflet.
- Polygon-based area selection.
- Date range filtering.
- Video generation for the selected area.
- GeoTIFF export for the selected polygon.
- CSV export with imputed pixel information.
- ZIP download containing GeoTIFF and CSV outputs.
- Asynchronous export workflow for long-running satellite processing.
- Export status polling through `/api/area/geotiff-status`.
- FastAPI backend with automatic API documentation.
- SQLite-based user authentication and registration.
- React + Vite frontend.
- File-based geospatial processing architecture for large satellite outputs.
- Local development with Vite dev server and FastAPI API proxy.
- Production/local compiled mode where FastAPI serves the React build from `frontend/dist`.
- Cloudflare Tunnel deployment support through a single FastAPI service on port `3000`.

---

## Current Architecture

The project is organized into two main components: a FastAPI backend and a React frontend built with Vite.

```txt
SIRIS/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ db.py
│  │  ├─ schemas.py
│  │  ├─ routes/
│  │  │  ├─ auth.py
│  │  │  ├─ area.py
│  │  │  └─ exports.py
│  │  └─ services/
│  │     └─ area_service.py
│  │
│  ├─ scripts/
│  │  ├─ generar_area_desde_tiles.py
│  │  └─ generar_area_geotiff_csv_desde_npy.py
│  │
│  ├─ data/
│  │  ├─ grid_georef.json
│  │  ├─ study_area.geojson
│  │  ├─ web_exports/
│  │  └─ area_exports/
│  │
│  ├─ tests/
│  │  ├─ conftest.py
│  │  ├─ test_auth_api.py
│  │  └─ test_study_area_and_security_api.py
│  │
│  ├─ pytest.ini
│  ├─ venv/
│  └─ requirements.txt
│
├─ frontend/
│  ├─ index.html
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ vite.config.js
│  ├─ public/
│  └─ src/
│     ├─ main.jsx
│     ├─ api.js
│     ├─ styles.css
│     ├─ components/
│     │  └─ AuthShell.jsx
│     └─ pages/
│        ├─ Login.jsx
│        ├─ Register.jsx
│        └─ Dashboard.jsx
│
├─ scripts_tests/
│  ├─ run_backend_api_tests.ps1
│  └─ apply_async_export_patch.ps1
│
├─ tests_evidence/
│  ├─ backend_api/
│  └─ cloudflare/
│
├─ docs/
│  └─ plan_pruebas_snippets/
│
├─ .gitignore
└─ README.md
```

The active frontend is located in `frontend/`.

If a legacy HTML frontend was kept during migration, it can be removed once the React + Vite frontend has been validated and committed.

---

## Technology Stack

### Backend

- Python 3.11
- FastAPI
- Uvicorn
- SQLite
- NumPy
- Rasterio
- PyProj
- Pillow
- Subprocess-based execution for geospatial scripts
- Background thread execution for asynchronous exports

### Frontend

- React
- Vite
- JavaScript / JSX
- CSS
- React Router DOM
- Leaflet

### Testing

- pytest
- FastAPI TestClient
- Temporary SQLite database for API tests
- Test evidence logs under `tests_evidence/`

### Geospatial Processing

- Sentinel-2 image products.
- Super-resolved NumPy arrays.
- Imputation masks.
- GeoTIFF generation.
- CSV generation for imputed pixels.
- ZIP packaging for export.

### Deployment

- React build served by FastAPI from `frontend/dist`.
- Cloudflare Tunnel exposing the backend service on port `3000`.

---

## React and Vite Clarification

This project uses both React and Vite.

React is the frontend library used to build the interface components and application pages, such as login, registration and dashboard.

Vite is the frontend development server and build tool. It runs the React app during development and generates the production build inside:

```txt
frontend/dist/
```

In development, Vite runs the frontend on port `5173` and proxies API requests to the FastAPI backend on port `3000`.

In compiled/deployment mode, Vite is not running. FastAPI serves the compiled React application from `frontend/dist`.

---

## Processing Workflow

The web application follows this workflow:

1. The user creates an account or logs in with existing credentials.
2. The backend validates credentials using a SQLite database.
3. The authenticated user accesses the React dashboard.
4. The user selects a date range.
5. The user draws a polygon on the Leaflet map.
6. The frontend sends the polygon and date range to the FastAPI backend.
7. The backend immediately starts an asynchronous export job.
8. The backend responds with HTTP `202 Accepted`, including `outName` and `statusUrl`.
9. The frontend polls `/api/area/geotiff-status`.
10. The backend generates a video from preprocessed image tiles.
11. The backend generates GeoTIFF outputs from super-resolved NumPy arrays.
12. The backend generates a CSV with imputed pixel information.
13. The backend compresses GeoTIFF and CSV outputs into a ZIP file.
14. When processing finishes, `/api/area/geotiff-status` returns `stage: "done"` with `videoUrl` and `geotiffZipUrl`.
15. The frontend displays the video and provides a download link for the ZIP file.

---

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/bryancog/SIRIS-Javeriana.git
cd SIRIS-Javeriana
```

### 2. Select the working branch

The current functional version can be used from:

```bash
git checkout main
```

If working from a migration branch:

```bash
git checkout migracion-react-vite
```

---

## Backend Setup

### 1. Enter the backend folder

```bash
cd backend
```

### 2. Create a Python virtual environment

Python 3.11 is recommended.

```bash
py -3.11 -m venv venv
```

### 3. Activate the virtual environment in PowerShell

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

If activation is not required, the backend can also be run directly with:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3000
```

### 4. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Verify installation

```bash
python -c "import fastapi, uvicorn, numpy, rasterio, pyproj, PIL; print('OK')"
```

---

## Frontend Setup

The frontend is located in:

```txt
frontend/
```

### 1. Enter the frontend folder

```powershell
cd D:\SIRIS\frontend
```

### 2. Install dependencies

```powershell
npm.cmd install
```

### 3. Run the frontend development server

```powershell
npm.cmd run dev
```

The frontend will usually be available at:

```txt
http://localhost:5173/
```

If port `5173` is already in use, Vite may start on another port, such as:

```txt
http://localhost:5174/
```

---

## Required Data Folders

Large satellite products and generated outputs are not stored in GitHub.

The following folders must exist locally:

```txt
backend/data/web_exports/
backend/data/area_exports/
D:/SIRIS_DATA/tesis_saits_v2_scl_mask/outputs_sr_x4_lanczos/
D:/SIRIS_DATA/tesis_saits_v2_scl_mask/outputs_sr_x4_lanczos_faltantes_web/
D:/SIRIS_DATA/tesis_saits_v2_scl_mask/outputs_imputation_masks/
```

---

## Data Folder Description

### `backend/data/web_exports/`

Contains preprocessed JPG frames used to generate video previews.

### `backend/data/area_exports/`

Stores generated outputs for each user export. This folder is generated automatically and should not be committed to GitHub.

### `outputs_sr_x4_lanczos/`

Contains super-resolved Sentinel-2 NumPy arrays.

### `outputs_sr_x4_lanczos_faltantes_web/`

Contains additional super-resolved Sentinel-2 NumPy arrays used for missing web outputs.

### `outputs_imputation_masks/`

Contains binary masks identifying pixels affected by temporal imputation.

---

## Environment Variables

Before running the backend, configure the data paths:

```powershell
$env:SIRIS_NPY_ROOTS="D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos;D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos_faltantes_web"

$env:SIRIS_MASK_ROOT="D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_imputation_masks"

$env:SIRIS_GEOTIFF_WORKERS="2"
```

`SIRIS_GEOTIFF_WORKERS` controls the number of workers used by the GeoTIFF/CSV generation script.

---

## Run the Application in Development Mode

Development mode uses two terminals.

### Terminal 1: FastAPI backend

```powershell
cd D:\SIRIS\backend

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

$env:SIRIS_NPY_ROOTS="D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos;D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos_faltantes_web"
$env:SIRIS_MASK_ROOT="D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_imputation_masks"
$env:SIRIS_GEOTIFF_WORKERS="2"

.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3000
```

Backend URL:

```txt
http://127.0.0.1:3000
```

API documentation:

```txt
http://127.0.0.1:3000/docs
```

### Terminal 2: React + Vite frontend

```powershell
cd D:\SIRIS\frontend
npm.cmd run dev
```

Frontend URL:

```txt
http://localhost:5173/
```

In development, access the system from the Vite URL.

---

## Run the Application in Compiled Mode

For local production-style testing, first build the React frontend:

```powershell
cd D:\SIRIS\frontend
npm.cmd run build
```

This generates:

```txt
frontend/dist/
```

Then run the FastAPI backend:

```powershell
cd D:\SIRIS\backend

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

$env:SIRIS_NPY_ROOTS="D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos;D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos_faltantes_web"
$env:SIRIS_MASK_ROOT="D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_imputation_masks"
$env:SIRIS_GEOTIFF_WORKERS="2"

.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3000
```

Open the application from:

```txt
http://127.0.0.1:3000/
```

In this mode, FastAPI serves the compiled React application from `frontend/dist`.

This is the recommended mode for Cloudflare Tunnel deployment.

---

## Authentication and User Registration

The system includes user registration and login using a local SQLite database.

React frontend routes:

```txt
/login
/register
/dashboard
```

During development, these routes are accessed through the Vite server:

```txt
http://localhost:5173/login
http://localhost:5173/register
http://localhost:5173/dashboard
```

In compiled mode, they are accessed through FastAPI:

```txt
http://127.0.0.1:3000/login
http://127.0.0.1:3000/register
http://127.0.0.1:3000/dashboard
```

Passwords are not stored in plain text. The backend stores a salted password hash and validates credentials through the FastAPI authentication route.

A demo user may be automatically created during development:

```txt
Username: demo
Password: demo123
```

The SQLite database is created locally at:

```txt
backend/data/siris.db
```

This database is local and should not be committed to GitHub.

---

## API Documentation

FastAPI automatically generates interactive API documentation.

### Swagger UI

```txt
http://127.0.0.1:3000/docs
```

### ReDoc

```txt
http://127.0.0.1:3000/redoc
```

These pages allow inspection and testing of the backend endpoints.

---

## Main API Endpoints

```txt
GET  /
GET  /login
GET  /register
GET  /dashboard

GET  /api/session
POST /api/register
POST /api/login
POST /api/logout

GET  /api/study-area

POST /api/area/export
POST /api/area/cancel
GET  /api/area/geotiff-status

GET  /exports/{file_path}
```

The frontend routes are handled by React. The API routes are handled by FastAPI.

---

## Register Endpoint

The registration endpoint is:

```txt
POST /api/register
```

Expected JSON body:

```json
{
  "name": "User Name",
  "username": "username",
  "password": "password123"
}
```

Example response:

```json
{
  "message": "Usuario registrado correctamente.",
  "user": {
    "username": "username",
    "name": "User Name"
  }
}
```

Validation rules:

- Username must have at least 3 characters.
- Name must have at least 3 characters.
- Password must have at least 6 characters.
- Username must be unique.

---

## Login Endpoint

The login endpoint is:

```txt
POST /api/login
```

Expected JSON body:

```json
{
  "username": "username",
  "password": "password123"
}
```

Example response:

```json
{
  "message": "Login correcto.",
  "user": {
    "username": "username",
    "name": "User Name"
  }
}
```

After successful login, the backend creates an HTTP-only session cookie named:

```txt
siris_session
```

---

## Asynchronous Export Endpoint

The main export endpoint is:

```txt
POST /api/area/export
```

Expected JSON body:

```json
{
  "polygon": [
    {
      "lat": 1.23,
      "lng": -77.12
    },
    {
      "lat": 1.24,
      "lng": -77.10
    },
    {
      "lat": 1.22,
      "lng": -77.09
    }
  ],
  "dateFrom": "2020-01-01",
  "dateTo": "2021-01-01"
}
```

The polygon can contain three or more vertices.

The endpoint starts the export process in the background and returns immediately.

Expected response:

```json
{
  "message": "Exportación iniciada.",
  "outName": "area_1780031031689",
  "statusUrl": "/api/area/geotiff-status"
}
```

Expected HTTP status:

```txt
202 Accepted
```

The final URLs are not returned by this endpoint. They are returned later by `/api/area/geotiff-status` when processing finishes.

---

## Export Status Endpoint

The frontend queries the export status using:

```txt
GET /api/area/geotiff-status
```

Example response while running:

```json
{
  "running": true,
  "stage": "geotiff",
  "message": "Generando GeoTIFF...",
  "outName": "area_1780031031689",
  "videoUrl": null,
  "geotiffZipUrl": null,
  "error": null
}
```

Example response when finished:

```json
{
  "running": false,
  "stage": "done",
  "message": "Exportación finalizada.",
  "outName": "area_1780031031689",
  "videoUrl": "/exports/area_1780031031689/area_1780031031689.mp4",
  "geotiffZipUrl": "/exports/area_1780031031689/area_1780031031689_geotiff_csv.zip",
  "error": null
}
```

Possible stages include:

```txt
idle
queued
video
geotiff
zip
done
error
cancelled
```

Possible messages include:

```txt
Sin exportación activa.
Exportación iniciada. Preparando procesamiento...
Generando video...
Generando GeoTIFF...
Validando archivos generados...
Exportación finalizada.
Error generando exportación.
Exportación cancelada.
```

---

## Cancel Export Endpoint

An active export can be cancelled with:

```txt
POST /api/area/cancel
```

Expected response:

```json
{
  "message": "Exportación cancelada."
}
```

---

## Generated Outputs

Each export creates a folder inside:

```txt
backend/data/area_exports/
```

Example:

```txt
backend/data/area_exports/area_1780031031689/
```

The folder may contain:

```txt
polygon.json
frames_jpg/
area_1780031031689.mp4
geotiff/
pixeles_imputados.csv
README_GEOTIFF_IMPUTACION.txt
area_1780031031689_geotiff_csv.zip
```

---

## Cloudflare Tunnel Deployment

The recommended deployment path for this version is:

```txt
React build + FastAPI backend + Cloudflare Tunnel
```

This means that the frontend is compiled once using Vite and then served by FastAPI. Cloudflare Tunnel points only to the backend service on port `3000`.

### 1. Build the frontend

```powershell
cd D:\SIRIS\frontend
npm.cmd run build
```

### 2. Run the FastAPI backend

```powershell
cd D:\SIRIS\backend

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

$env:SIRIS_NPY_ROOTS="D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos;D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos_faltantes_web"
$env:SIRIS_MASK_ROOT="D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_imputation_masks"
$env:SIRIS_GEOTIFF_WORKERS="2"

.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3000
```

### 3. Expose the backend through a temporary Cloudflare Tunnel

```powershell
cloudflared tunnel --url http://localhost:3000
```

The command returns a public URL similar to:

```txt
https://example-random-name.trycloudflare.com
```

Use that URL to access the system publicly.

### 4. Optional named tunnel with domain

For a more stable setup, configure a named Cloudflare Tunnel and route a hostname such as:

```txt
siris.yourdomain.com
```

to:

```txt
http://localhost:3000
```

---

## Cloudflare Deployment Notes

The asynchronous export workflow was introduced to support Cloudflare Tunnel deployment.

Long-running exports can take several minutes when the date range is wide or the selected polygon requires processing many scenes. Keeping the original HTTP request open until all files are generated can cause a public tunnel or browser connection to close before the backend finishes processing.

The current version avoids that issue by:

1. Returning immediately from `/api/area/export`.
2. Running the export in the background.
3. Polling `/api/area/geotiff-status`.
4. Returning `videoUrl` and `geotiffZipUrl` only when the export is complete.

For deployment evidence, recommended screenshots are:

```txt
EV_CLOUDFLARE_01_TUNNEL_RUNNING.png
EV_CLOUDFLARE_02_LOGIN_PUBLICO.png
EV_CLOUDFLARE_03_DASHBOARD_PUBLICO.png
EV_CLOUDFLARE_04_EXPORT_ASINCRONA_INICIADA.png
EV_CLOUDFLARE_05_EXPORT_FINALIZADA_VIDEO_ZIP.png
```

Recommended folder:

```txt
tests_evidence/cloudflare/
```

---

## Automated Tests

The first automated testing package validates Backend/API and basic security behavior.

### Run Backend/API tests

From the project root:

```powershell
cd D:\SIRIS
powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_backend_api_tests.ps1
```

The script runs `pytest` using a temporary SQLite database. It does not modify the functional database at:

```txt
backend/data/siris.db
```

### Current automated test coverage

```txt
API-01 Register user successfully
API-02 Reject duplicated username
API-03 Reject invalid registration fields
API-04 Login successfully and create authenticated session
API-05 Reject invalid password
API-06 Session without authentication
API-07 Logout
API-08 Study area returns valid GeoJSON

SEC-01 Reject area export without session
SEC-02 Reject export status query without session
SEC-03 Reject export cancellation without session
SEC-04 Return 404 for missing exported file
SEC-05 Reject or safely handle invalid export path
```

### Evidence

Test logs are generated under:

```txt
tests_evidence/backend_api/
```

Example:

```txt
backend_api_tests_20260529_115322.log
```

---

## Git and Large Files

The repository should not include generated or heavy geospatial files.

The following files and folders should remain ignored:

```gitignore
backend/data/web_exports/
backend/data/area_exports/
backend/data/*.db
backend/data/*.sqlite
backend/data/*.sqlite3
*.npy
*.tif
*.tiff
*.zip
*.mp4
*.jpg
*.jpeg
*.png
__pycache__/
venv/
node_modules/
frontend/dist/
tests_evidence/
backups/
.env
```

---

## Development Notes

This version migrated the frontend from static HTML/CSS/JavaScript to React with Vite while preserving the FastAPI backend and the existing Python geospatial processing scripts.

It also introduced asynchronous geospatial export processing to improve compatibility with public deployment through Cloudflare Tunnel.

The migration improves:

- Component-based frontend structure.
- React Router navigation.
- Vite development server with fast reload.
- Cleaner separation between frontend pages and API calls.
- Improved maintainability for future UI changes.
- Compatibility with a compiled frontend served by FastAPI.
- Easier path for Cloudflare Tunnel deployment.
- Long-running exports without keeping the original HTTP request open.
- More robust user feedback through export status polling.

The previous FastAPI migration also added:

- Backend structure.
- API documentation.
- Python-native integration with geospatial scripts.
- SQLite-based user persistence.
- User registration and login.
- Password hashing with individual salt.
- HTTP-only cookie-based session handling.
- Maintainability for research and thesis documentation.
- Future deployment options.

---

## Current Branch

The current functional version is being consolidated in:

```txt
main
```

The previous React + Vite migration branch was:

```txt
migracion-react-vite
```

The previous FastAPI-only migration branch was:

```txt
migracionFastAPI
```

---

## Project Purpose

SIRIS is designed as an academic and research tool to support analysis of Sentinel-2 satellite imagery in cloudy regions. The system helps generate visual and geospatial outputs from processed Sentinel-2 products, supporting environmental monitoring and remote sensing workflows.
