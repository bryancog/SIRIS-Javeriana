import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import L from "leaflet";
import { apiFetch, exportUrl } from "../api.js";

const MAX_AREA_KM2 = 1000;
const MAX_AREA_M2 = MAX_AREA_KM2 * 1000 * 1000;

const COLOMBIA_BOUNDS = [
  [-4.3, -82.0],
  [16.0, -66.5],
];

const polygonStyle = {
  color: "#83d6b3",
  fillColor: "#83d6b3",
  fillOpacity: 0.18,
  weight: 3,
};

const draftLineStyle = {
  color: "#83d6b3",
  weight: 3,
  dashArray: "6 6",
};

export default function Dashboard() {
  const navigate = useNavigate();

  const mapElementRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const editableLayersRef = useRef(null);
  const pollingRef = useRef(null);
  const drawButtonRef = useRef(null);

  const dateFromRef = useRef("");
  const dateToRef = useRef("");

  const drawingRef = useRef({
    active: false,
    points: [],
    vertexLayers: [],
    draftLine: null,
  });

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [results, setResults] = useState([]);
  const [resultsCount, setResultsCount] = useState("0 escenas");
  const [resultsHint, setResultsHint] = useState(
    "Usa la herramienta de polígono para generar resultados."
  );
  const [isHintError, setIsHintError] = useState(false);
  const [areaStatus, setAreaStatus] = useState(
    `Área máxima permitida: ${MAX_AREA_KM2} km²`
  );
  const [progress, setProgress] = useState({
    visible: true,
    message: "Sin exportación activa.",
    state: "done",
  });

  useEffect(() => {
    let mounted = true;

    apiFetch("/api/session")
      .then((payload) => {
        if (!mounted) return;

        if (!payload.authenticated) {
          navigate("/login", { replace: true });
          return;
        }

        initializeMap();
      })
      .catch(() => navigate("/login", { replace: true }));

    return () => {
      mounted = false;
      stopExportProgressPolling();

      if (mapInstanceRef.current) {
        mapInstanceRef.current.off("click", handleMapClick);
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  function initializeMap() {
    if (mapInstanceRef.current || !mapElementRef.current) return;

    const map = L.map(mapElementRef.current, {
      zoomControl: false,
      maxBounds: COLOMBIA_BOUNDS,
      maxBoundsViscosity: 1.0,
      minZoom: 6,
    }).setView([1.25, -77.25], 10);

    mapInstanceRef.current = map;

    L.control.zoom({ position: "topright" }).addTo(map);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "© OpenStreetMap contributors",
    }).addTo(map);

    loadStudyArea(map);

    const editableLayers = new L.FeatureGroup();
    editableLayersRef.current = editableLayers;
    map.addLayer(editableLayers);

    addSirisDrawToolbar(map);
  }

  function addSirisDrawToolbar(map) {
    const SirisDrawControl = L.Control.extend({
      options: { position: "topright" },

      onAdd() {
        const container = L.DomUtil.create(
          "div",
          "leaflet-bar leaflet-control siris-custom-draw-toolbar"
        );

        const drawLink = L.DomUtil.create("a", "siris-draw-polygon-button", container);
        drawLink.href = "#";
        drawLink.title = "Dibujar polígono";
        drawLink.setAttribute("aria-label", "Dibujar polígono");
        drawLink.innerHTML = "⬟";
        drawButtonRef.current = drawLink;

        const clearLink = L.DomUtil.create("a", "siris-draw-clear-button", container);
        clearLink.href = "#";
        clearLink.title = "Eliminar selección";
        clearLink.setAttribute("aria-label", "Eliminar selección");
        clearLink.innerHTML = "🗑";

        L.DomEvent.disableClickPropagation(container);
        L.DomEvent.disableScrollPropagation(container);

        L.DomEvent.on(drawLink, "click", (event) => {
          L.DomEvent.preventDefault(event);
          startCustomPolygonDrawing();
        });

        L.DomEvent.on(clearLink, "click", async (event) => {
          L.DomEvent.preventDefault(event);
          await clearSelectionAndCancelExport();
        });

        return container;
      },
    });

    map.addControl(new SirisDrawControl());
  }

  async function loadStudyArea(map) {
    try {
      const geojson = await apiFetch("/api/study-area");

      const layer = L.geoJSON(geojson, {
        style: {
          color: "#d9a441",
          weight: 2,
          dashArray: "8 6",
          fillColor: "#d9a441",
          fillOpacity: 0.08,
        },
      }).addTo(map);

      map.fitBounds(layer.getBounds(), { padding: [40, 40] });
    } catch (error) {
      console.error("Error cargando área de estudio", error);
    }
  }

  function startCustomPolygonDrawing() {
    const map = mapInstanceRef.current;
    if (!map) return;

    clearDraftDrawing();
    editableLayersRef.current?.clearLayers();

    drawingRef.current.active = true;
    drawingRef.current.points = [];

    map.getContainer().classList.add("is-drawing-polygon");
    drawButtonRef.current?.classList.add("is-active");
    map.doubleClickZoom.disable();
    map.on("click", handleMapClick);

    setIsHintError(false);
    setResultsHint(
      "Haz clic en el mapa para agregar vértices. Para cerrar, vuelve a hacer clic sobre el primer punto."
    );
    setResultsCount("Dibujando");
    setAreaStatus("Dibujo activo: 0 puntos.");
    setExportProgress("Dibujo activo.", "done");
  }

  function handleMapClick(event) {
    addPolygonVertex(event.latlng);
  }

  function addPolygonVertex(latlng) {
    const map = mapInstanceRef.current;
    const drawing = drawingRef.current;

    if (!map || !drawing.active) return;

    const point = L.latLng(latlng.lat, latlng.lng);
    drawing.points.push(point);

    const marker = L.circleMarker(point, {
      radius: drawing.points.length === 1 ? 7 : 5,
      color: "#0b3d34",
      fillColor: "#83d6b3",
      fillOpacity: 0.96,
      weight: 2,
      pane: "markerPane",
    }).addTo(map);

    if (drawing.points.length === 1) {
      marker.bindTooltip("Clic aquí para cerrar", {
        permanent: false,
        direction: "top",
        opacity: 0.9,
      });

      marker.on("click", (markerEvent) => {
        if (markerEvent.originalEvent) {
          L.DomEvent.stop(markerEvent.originalEvent);
        }

        finishCustomPolygonDrawing();
      });
    }

    drawing.vertexLayers.push(marker);

    if (!drawing.draftLine) {
      drawing.draftLine = L.polyline(drawing.points, draftLineStyle).addTo(map);
    } else {
      drawing.draftLine.setLatLngs(drawing.points);
    }

    if (drawing.points.length < 3) {
      setAreaStatus(
        `Dibujo activo: ${drawing.points.length} punto(s). Mínimo 3 puntos.`
      );
      return;
    }

    const polygonAreaM2 = calculatePolygonAreaFromLatLngs(drawing.points);
    setAreaStatus(
      `Dibujo activo: ${drawing.points.length} puntos | Área aproximada: ${formatAreaKm2(
        polygonAreaM2
      )} km²`
    );
  }

  function finishCustomPolygonDrawing() {
    const map = mapInstanceRef.current;
    const editableLayers = editableLayersRef.current;
    const drawing = drawingRef.current;

    if (!map || !editableLayers || !drawing.active) return;

    if (drawing.points.length < 3) {
      setIsHintError(true);
      setResultsHint("El polígono debe tener mínimo 3 puntos.");
      setExportProgress("El polígono debe tener mínimo 3 puntos.", "error");
      return;
    }

    const points = [...drawing.points];
    const polygonAreaM2 = calculatePolygonAreaFromLatLngs(points);

    if (polygonAreaM2 > MAX_AREA_M2) {
      setIsHintError(true);
      setResultsHint(`El polígono supera el máximo permitido de ${MAX_AREA_KM2} km².`);
      setAreaStatus(
        `Última selección: ${formatAreaKm2(
          polygonAreaM2
        )} km² | Máximo: ${MAX_AREA_KM2} km²`
      );
      setExportProgress("Área excedida. Dibuja un polígono más pequeño.", "error");
      return;
    }

    stopCustomPolygonDrawing();

    const polygonLayer = L.polygon(points, polygonStyle);
    editableLayers.clearLayers();
    editableLayers.addLayer(polygonLayer);

    console.log("Polígono WKT:", buildPolygonWktFromLatLngs(points));

    setAreaStatus(
      `Área seleccionada: ${formatAreaKm2(polygonAreaM2)} km² | ${points.length} puntos`
    );

    exportSelectedArea(polygonLayer, polygonAreaM2);
  }

  function stopCustomPolygonDrawing() {
    const map = mapInstanceRef.current;

    if (map) {
      map.off("click", handleMapClick);
      map.getContainer().classList.remove("is-drawing-polygon");
      map.doubleClickZoom.enable();
    }

    drawButtonRef.current?.classList.remove("is-active");
    drawingRef.current.active = false;
    clearDraftDrawing();
  }

  function clearDraftDrawing() {
    const map = mapInstanceRef.current;
    const drawing = drawingRef.current;

    if (!map) return;

    drawing.vertexLayers.forEach((layer) => map.removeLayer(layer));
    drawing.vertexLayers = [];

    if (drawing.draftLine) {
      map.removeLayer(drawing.draftLine);
      drawing.draftLine = null;
    }

    drawing.points = [];
  }

  async function clearSelectionAndCancelExport() {
    stopCustomPolygonDrawing();
    editableLayersRef.current?.clearLayers();

    await cancelActiveExport();

    clearResults();
    setExportProgress("Selección limpiada.", "done");
  }

  function setExportProgress(message, state = "running") {
    setProgress({
      visible: true,
      message: message || "Procesando exportación...",
      state,
    });
  }

  function startExportProgressPolling() {
    stopExportProgressPolling();
    setExportProgress("Generando video...", "running");

    pollingRef.current = window.setInterval(async () => {
      try {
        const status = await apiFetch("/api/area/geotiff-status", {
          method: "GET",
        });

        if (!status.message) return;

        if (status.stage === "done") {
          setExportProgress(status.message, "done");
          stopExportProgressPolling();
          return;
        }

        if (status.stage === "error" || status.stage === "cancelled") {
          setExportProgress(status.message, "error");
          stopExportProgressPolling();
          return;
        }

        setExportProgress(status.message, "running");
      } catch (error) {
        console.warn("No se pudo consultar el progreso:", error);
      }
    }, 1500);
  }

  function stopExportProgressPolling() {
    if (pollingRef.current) {
      window.clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }

  function clearResults(message) {
    setResults([]);
    setResultsCount("0 escenas");
    setResultsHint(
      message || "Usa la herramienta de polígono para generar resultados."
    );
    setIsHintError(Boolean(message));
    setAreaStatus(`Área máxima permitida: ${MAX_AREA_KM2} km²`);
  }

  function calculatePolygonAreaFromLatLngs(latLngs) {
    if (!latLngs || latLngs.length < 3) return 0;

    const earthRadius = 6378137;
    let area = 0;

    for (let i = 0, j = latLngs.length - 1; i < latLngs.length; j = i++) {
      const p1 = latLngs[j];
      const p2 = latLngs[i];

      area +=
        toRadians(p2.lng - p1.lng) *
        (2 + Math.sin(toRadians(p1.lat)) + Math.sin(toRadians(p2.lat)));
    }

    return Math.abs((area * earthRadius * earthRadius) / 2);
  }

  function toRadians(value) {
    return (value * Math.PI) / 180;
  }

  function formatAreaKm2(areaM2) {
    return (areaM2 / 1000 / 1000).toFixed(2);
  }

  function buildPolygonWktFromLatLngs(latLngs) {
    const coordinates = latLngs.map(
      (point) => `${point.lng.toFixed(6)} ${point.lat.toFixed(6)}`
    );

    if (coordinates.length > 0) {
      coordinates.push(coordinates[0]);
    }

    return `POLYGON ((${coordinates.join(", ")}))`;
  }

  async function exportSelectedArea(layer, polygonAreaM2) {
    const polygon = (layer.getLatLngs()[0] || []).map((point) => ({
      lat: point.lat,
      lng: point.lng,
    }));

    const selectedDateFrom = dateFromRef.current;
    const selectedDateTo = dateToRef.current;

    if (!selectedDateFrom || !selectedDateTo) {
      clearResults("Selecciona fecha inicial y fecha final antes de exportar.");
      setExportProgress("Selecciona fecha inicial y fecha final antes de exportar.", "error");
      return;
    }

    if (selectedDateFrom > selectedDateTo) {
      clearResults("La fecha inicial no puede ser posterior a la fecha final.");
      setExportProgress("La fecha inicial no puede ser posterior a la fecha final.", "error");
      return;
    }

    setResults([]);
    setIsHintError(false);
    setResultsHint("Generando imágenes y video del área seleccionada...");
    setResultsCount("Procesando");
    setAreaStatus(`Área seleccionada: ${formatAreaKm2(polygonAreaM2)} km²`);

    startExportProgressPolling();

    try {
      const payload = await apiFetch("/api/area/export", {
        method: "POST",
        body: JSON.stringify({
          polygon,
          dateFrom: selectedDateFrom,
          dateTo: selectedDateTo,
        }),
      });

      stopExportProgressPolling();
      setExportProgress("Exportación finalizada.", "done");
      setResultsHint("Exportación generada correctamente.");
      setResultsCount("1 video");

      setResults([
        {
          title: "Área seleccionada",
          description: "Video, GeoTIFF y CSV generados para el área solicitada.",
          videoUrl: payload.videoUrl,
          geotiffZipUrl: payload.geotiffZipUrl,
        },
      ]);
    } catch (error) {
      stopExportProgressPolling();
      setExportProgress("Error generando exportación.", "error");
      clearResults(error.message);
    }
  }

  async function cancelActiveExport() {
    try {
      await apiFetch("/api/area/cancel", { method: "POST" });
      stopExportProgressPolling();
    } catch (error) {
      console.error("No se pudo cancelar la exportación activa", error);
    }
  }

  async function handleLogout() {
    try {
      await apiFetch("/api/logout", { method: "POST" });
    } finally {
      navigate("/login", { replace: true });
    }
  }

  return (
    <main className="dashboard">
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="brand-kicker">Sesión activa</span>
          <h2>Resultados Sentinel-2</h2>
          <button className="ghost-button" type="button" onClick={handleLogout}>
            Cerrar sesión
          </button>
          <p>
            Dibuja un polígono en el mapa para generar productos que intersectan
            tu zona de interés.
          </p>
        </div>

        <div className="status-card">
          <span className="status-label">Región enfocada</span>
          <strong>Pacífico Colombiano</strong>
          <small>Centro inicial: 1.25, -77.25</small>
          <small>{areaStatus}</small>
        </div>

        <div className="date-export-box">
          <div className="date-export-header">
            <strong>Filtro temporal</strong>
            <small>Selecciona las fechas que quieres exportar.</small>
          </div>

          <div className="date-fields">
            <label>
              Fecha inicial
              <input
                type="date"
                value={dateFrom}
                onChange={(event) => {
                  dateFromRef.current = event.target.value;
                  setDateFrom(event.target.value);
                }}
              />
            </label>

            <label>
              Fecha final
              <input
                type="date"
                value={dateTo}
                onChange={(event) => {
                  dateToRef.current = event.target.value;
                  setDateTo(event.target.value);
                }}
              />
            </label>
          </div>
        </div>

        {progress.visible && (
          <div className={`export-progress-box is-${progress.state}`}>
            <div className="export-progress-title">Estado de la exportación</div>
            <div className="export-progress-message">{progress.message}</div>
          </div>
        )}

        <div className="results-panel">
          <div className="results-heading">
            <h3>IDs detectados</h3>
            <strong>{resultsCount}</strong>
          </div>

          <p className={`results-hint ${isHintError ? "is-error" : ""}`}>
            {resultsHint}
          </p>

          <ul className="results-list">
            {results.map((item, index) => (
              <li key={`${item.title}-${index}`}>
                <strong>{item.title}</strong>
                <span>{item.description}</span>

                {item.videoUrl && (
                  <video
                    src={exportUrl(item.videoUrl)}
                    controls
                    style={{
                      width: "100%",
                      marginTop: "10px",
                      borderRadius: "12px",
                    }}
                  />
                )}

                <div className="result-actions">
                  {item.videoUrl && (
                    <a
                      href={exportUrl(item.videoUrl)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Abrir video
                    </a>
                  )}

                  {item.geotiffZipUrl && (
                    <a href={exportUrl(item.geotiffZipUrl)}>
                      Descargar GeoTIFF + CSV
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <section className="map-section">
        <div className="map-toolbar">
          <div>
            <span className="brand-kicker">Workspace</span>
            <h2>Selector Geoespacial</h2>
            <p>
              Traza un polígono y revisa la generación de productos satelitales.
            </p>
          </div>
        </div>

        <div id="map" ref={mapElementRef}></div>
      </section>
    </main>
  );
}
