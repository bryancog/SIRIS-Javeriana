const resultsList = document.getElementById("resultsList");
const resultsCount = document.getElementById("resultsCount");
const resultsHint = document.getElementById("resultsHint");
const areaStatus = document.getElementById("areaStatus");
const logoutButton = document.getElementById("logoutButton");

const MAX_AREA_KM2 = 1000;
const MAX_AREA_M2 = MAX_AREA_KM2 * 1000 * 1000;
const COLOMBIA_BOUNDS = [
  [-4.3, -82.0],
  [16.0, -66.5]
];


let mapInstance;
let editableLayers;

bootDashboard();

logoutButton.addEventListener("click", async () => {
  try {
    await fetch("/api/logout", { method: "POST" });
  } finally {
    window.location.href = "/index.html";
  }
});

async function bootDashboard() {
  const session = await requireSession();

  if (!session) {
    return;
  }

  initializeMap();
}

async function requireSession() {
  try {
    const response = await fetch("/api/session");
    const payload = await response.json();

    if (!payload.authenticated) {
      window.location.href = "/index.html";
      return null;
    }

    return payload;
  } catch (error) {
    window.location.href = "/index.html";
    return null;
  }
}

function initializeMap() {
  mapInstance = L.map("map", {
    zoomControl: false,
    maxBounds: COLOMBIA_BOUNDS,
    maxBoundsViscosity: 1.0,
    minZoom: 6
  }).setView([1.25, -77.25], 10);

  L.control.zoom({ position: "topright" }).addTo(mapInstance);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(mapInstance);

  loadStudyArea();

  editableLayers = new L.FeatureGroup();
  mapInstance.addLayer(editableLayers);

  const drawControl = new L.Control.Draw({
    position: "topright",
    draw: {
      polyline: false,
      rectangle: false,
      circle: false,
      circlemarker: false,
      marker: false,
      polygon: {
        allowIntersection: false,
        showArea: true,
        shapeOptions: {
          color: "#83d6b3",
          fillColor: "#83d6b3",
          fillOpacity: 0.18
        }
      }
    },
    edit: {
      featureGroup: editableLayers,
      edit: false,
      remove: true
    }
  });

  mapInstance.addControl(drawControl);

  mapInstance.on(L.Draw.Event.CREATED, (event) => {
    const polygonAreaM2 = calculatePolygonArea(event.layer);
    const polygonWkt = buildPolygonWkt(event.layer);

    console.log("Poligono WKT:", polygonWkt);

    if (polygonAreaM2 > MAX_AREA_M2) {
      clearResults(`El poligono supera el maximo permitido de ${MAX_AREA_KM2} km2.`);
      areaStatus.textContent = `Ultima seleccion: ${formatAreaKm2(polygonAreaM2)} km2 | Maximo: ${MAX_AREA_KM2} km2`;
      return;
    }

    editableLayers.clearLayers();
    editableLayers.addLayer(event.layer);
    exportSelectedArea(event.layer, polygonAreaM2);
  });

  mapInstance.on(L.Draw.Event.DELETED, async () => {
    await cancelActiveExport();
    clearResults();
  });
}

function renderMockResults(layer, polygonAreaM2) {
  const polygon = layer.getLatLngs()[0] || [];
  const seed = polygon.reduce((acc, point) => acc + Math.abs(point.lat * point.lng), 0);
  const total = Math.max(3, Math.min(7, Math.round(seed % 6) + 2));
  const mockIds = Array.from({ length: total }, (_, index) => buildSentinelId(seed, index + 1));

  resultsList.innerHTML = "";
  resultsHint.classList.remove("is-error");
  resultsHint.textContent = "Consulta simulada completada para el poligono seleccionado.";
  resultsCount.textContent = `${mockIds.length} escenas`;
  areaStatus.textContent = `Area seleccionada: ${formatAreaKm2(polygonAreaM2)} km2 | Maximo: ${MAX_AREA_KM2} km2`;

  mockIds.forEach((id, index) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <strong>${id}</strong>
      <span>Interseccion estimada ${(72 - index * 6).toFixed(0)}% | Nivel L1C</span>
    `;
    resultsList.appendChild(item);
  });
}

function clearResults(message) {
  resultsList.innerHTML = "";
  resultsCount.textContent = "0 escenas";
  resultsHint.textContent = message || "Usa la herramienta de poligono para generar resultados mock.";
  resultsHint.classList.toggle("is-error", Boolean(message));
  areaStatus.textContent = `Area maxima permitida: ${MAX_AREA_KM2} km2`;
}

function buildSentinelId(seed, suffix) {
  const orbit = String(Math.floor((seed * 17) % 143) + 1).padStart(3, "0");
  const tile = `T${String(Math.floor((seed * 9) % 60) + 10).padStart(2, "0")}N${String(Math.floor((seed * 13) % 99)).padStart(2, "0")}`;
  const baseDate = new Date(Date.UTC(2025, 5, 1 + ((suffix * 3) % 20), 15, 22, 10 + suffix));
  const stamp = baseDate.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "");
  return `S2A_OPER_PRD_MSIL1C_${stamp}_R${orbit}_${tile}_${suffix}`;
}

function calculatePolygonArea(layer) {
  const latLngs = layer.getLatLngs()[0] || [];
  return L.GeometryUtil.geodesicArea(latLngs);
}

function formatAreaKm2(areaM2) {
  return (areaM2 / 1000 / 1000).toFixed(2);
}

function buildPolygonWkt(layer) {
  const latLngs = layer.getLatLngs()[0] || [];
  const coordinates = latLngs.map((point) => `${point.lng.toFixed(6)} ${point.lat.toFixed(6)}`);

  if (coordinates.length > 0) {
    coordinates.push(coordinates[0]);
  }

  return `POLYGON ((${coordinates.join(", ")}))`;
}

async function exportSelectedArea(layer, polygonAreaM2) {
  const bounds = layer.getBounds();

  const polygon = layer.getLatLngs()[0] || [];
  const bbox = polygonToMockSrBoundingBox(polygon);

  const row0 = bbox.row0;
  const col0 = bbox.col0;
  const height = bbox.height;
  const width = bbox.width;

  resultsList.innerHTML = "";
  resultsHint.classList.remove("is-error");
  resultsHint.textContent = "Generando imagenes y video del area seleccionada...";
  resultsCount.textContent = "Procesando";
  areaStatus.textContent = `Area seleccionada: ${formatAreaKm2(polygonAreaM2)} km2`;

  try {
    const response = await fetch("/api/area/export", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ row0, col0, height, width })
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.message || "Error generando exportacion.");
    }

    resultsHint.textContent = "Exportacion generada correctamente.";
    resultsCount.textContent = "1 video";

    const item = document.createElement("li");
    item.innerHTML = `
      <strong>Area seleccionada</strong>
      <span>Video generado para el area solicitada</span>
      <video src="${payload.videoUrl}" controls style="width:100%; margin-top:10px; border-radius:12px;"></video>
      <a href="${payload.videoUrl}" target="_blank">Abrir video</a>
    `;
    resultsList.appendChild(item);
  } catch (error) {
    clearResults(error.message);
  }
}

async function loadStudyArea() {
  try {
    const response = await fetch("/api/study-area");
    const geojson = await response.json();

    const layer = L.geoJSON(geojson, {
      style: {
        color: "#d9a441",
        weight: 2,
        dashArray: "8 6",
        fillColor: "#d9a441",
        fillOpacity: 0.08
      }
    }).addTo(mapInstance);

    mapInstance.fitBounds(layer.getBounds(), {
      padding: [40, 40]
    });

  } catch (error) {
    console.error("Error cargando area de estudio", error);
  }
}

async function cancelActiveExport() {
  try {
    await fetch("/api/area/cancel", {
      method: "POST"
    });
  } catch (error) {
    console.error("No se pudo cancelar la exportacion activa", error);
  }
}

function polygonToMockSrBoundingBox(polygon) {
  // Bounding box del polígono en lat/lng
  const lats = polygon.map((p) => p.lat);
  const lngs = polygon.map((p) => p.lng);

  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);

  /*
    Conversión temporal aproximada lat/lng -> coordenadas SR.
    Esta fórmula se calibra con el área de estudio.
    Luego la reemplazamos por una transformación geoespacial real.
  */

  const STUDY_EXTENT = {
    minLat: 0.85,
    maxLat: 1.65,
    minLng: -78.55,
    maxLng: -76.55,

    // Dimensiones aproximadas del mosaico SR disponible
    minRow: 0,
    maxRow: 8192,
    minCol: 0,
    maxCol: 15872
  };

  function latToRow(lat) {
    const t = (STUDY_EXTENT.maxLat - lat) / (STUDY_EXTENT.maxLat - STUDY_EXTENT.minLat);
    return STUDY_EXTENT.minRow + t * (STUDY_EXTENT.maxRow - STUDY_EXTENT.minRow);
  }

  function lngToCol(lng) {
    const t = (lng - STUDY_EXTENT.minLng) / (STUDY_EXTENT.maxLng - STUDY_EXTENT.minLng);
    return STUDY_EXTENT.minCol + t * (STUDY_EXTENT.maxCol - STUDY_EXTENT.minCol);
  }

  const rowA = latToRow(maxLat);
  const rowB = latToRow(minLat);
  const colA = lngToCol(minLng);
  const colB = lngToCol(maxLng);

  let row0 = Math.floor(Math.min(rowA, rowB));
  let col0 = Math.floor(Math.min(colA, colB));
  let row1 = Math.ceil(Math.max(rowA, rowB));
  let col1 = Math.ceil(Math.max(colA, colB));

  // Limitar al mosaico
  row0 = Math.max(0, row0);
  col0 = Math.max(0, col0);
  row1 = Math.min(STUDY_EXTENT.maxRow, row1);
  col1 = Math.min(STUDY_EXTENT.maxCol, col1);

  // Tamaño mínimo para que el video no salga diminuto
  const minSize = 512;

  let height = Math.max(minSize, row1 - row0);
  let width = Math.max(minSize, col1 - col0);

  return {
    row0,
    col0,
    height,
    width
  };
}