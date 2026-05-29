# SIRIS-Javeriana

SIRIS is a research-oriented geospatial platform for Sentinel-2 satellite image restoration, temporal gap filling, super-resolution and visualization over the Colombian Pacific region.

The project combines cloud detection, temporal imputation, spatial super-resolution, user authentication and a web dashboard that allows users to select an area of interest, define a date range and generate exportable satellite products.

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
- FastAPI backend with automatic API documentation.
- SQLite-based user authentication and registration.
- React + Vite frontend.
- File-based geospatial processing architecture for large satellite outputs.
- Local development with Vite dev server and FastAPI API proxy.
- Production/local compiled mode where FastAPI serves the React build from `frontend/dist`.

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
├─ .gitignore
└─ README.md
```

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

### Frontend

- React
- Vite
- JavaScript / JSX
- CSS
- React Router DOM
- Leaflet
- Leaflet Draw

### Geospatial Processing

- Sentinel-2 image products.
- Super-resolved NumPy arrays.
- Imputation masks.
- GeoTIFF generation.
- CSV generation for imputed pixels.
- ZIP packaging for export.

---

## React and Vite Clarification

This project uses both React and Vite.

React is the frontend library used to build the interface components and application pages, such as login, registration and dashboard.

Vite is the frontend development server and build tool. It runs the React app during development and generates the production build inside:

```txt
frontend/dist/
```

In development, Vite runs the frontend on port `5173` and proxies API requests to the FastAPI backend on port `3000`.

---

## Processing Workflow

The web application follows this workflow:

1. The user creates an account or logs in with existing credentials.
2. The backend validates credentials using a SQLite database.
3. The authenticated user accesses the React dashboard.
4. The user selects a date range.
5. The user draws a polygon on the Leaflet map.
6. The frontend sends the polygon and date range to the FastAPI backend.
7. The backend generates a video from preprocessed image tiles.
8. The backend generates GeoTIFF outputs from super-resolved NumPy arrays.
9. The backend generates a CSV with imputed pixel information.
10. The backend compresses GeoTIFF and CSV outputs into a ZIP file.
11. The frontend displays the video and provides a download link for the ZIP file.

---

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/bryancog/SIRIS-Javeriana.git
cd SIRIS-Javeriana
```

### 2. Select the React + Vite migration branch

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
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3000 --reload
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

---

## Run the Application in Development Mode

Development mode uses two terminals.

### Terminal 1: FastAPI backend

```powershell
cd D:\SIRIS\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3000 --reload
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

In development, access the system from the Vite URL, not directly from the backend URL.

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
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3000 --reload
```

Open the application from:

```txt
http://127.0.0.1:3000/
```

In this mode, FastAPI serves the compiled React application from `frontend/dist`.

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

## Export Endpoint

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

Example response:

```json
{
  "message": "Exportacion generada.",
  "outName": "area_1780031031689",
  "videoUrl": "/exports/area_1780031031689/area_1780031031689.mp4",
  "geotiffZipUrl": "/exports/area_1780031031689/area_1780031031689_geotiff_csv.zip"
}
```

---

## Export Status

The frontend can query the export status using:

```txt
GET /api/area/geotiff-status
```

Example response:

```json
{
  "running": true,
  "stage": "geotiff",
  "message": "Generando GeoTIFF...",
  "outName": "area_1780031031689"
}
```

Possible messages include:

```txt
Generando video...
Generando GeoTIFF...
Comprimiendo ZIP...
Exportación finalizada.
Error generando exportación.
Exportación cancelada.
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
.env
```

---

## Cloudflare Deployment Notes

The recommended deployment path for this version is:

```txt
React build + FastAPI backend + Cloudflare Tunnel
```

Recommended flow:

1. Build the frontend:

```powershell
cd D:\SIRIS\frontend
npm.cmd run build
```

2. Run the FastAPI backend:

```powershell
cd D:\SIRIS\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3000
```

3. Expose the backend through Cloudflare Tunnel:

```powershell
cloudflared tunnel --url http://localhost:3000
```

For production, configure a named Cloudflare Tunnel and route a hostname such as:

```txt
siris.yourdomain.com
```

to:

```txt
http://localhost:3000
```

---

## Development Notes

This version migrated the frontend from static HTML/CSS/JavaScript to React with Vite while preserving the FastAPI backend and the existing Python geospatial processing scripts.

The migration improves:

- Component-based frontend structure.
- React Router navigation.
- Vite development server with fast reload.
- Cleaner separation between frontend pages and API calls.
- Improved maintainability for future UI changes.
- Compatibility with a compiled frontend served by FastAPI.
- Easier path for Cloudflare Tunnel deployment.

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

The React + Vite frontend migration is being developed in:

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
