import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import L from "leaflet";
import "leaflet-draw";
import { apiFetch, exportUrl } from "../api.js";

const MAX_AREA_KM2 = 1000;
const MAX_AREA_M2 = MAX_AREA_KM2 * 1000 * 1000;
const COLOMBIA_BOUNDS = [
  [-4.3, -82.0],
  [16.0, -66.5]
];

export default function Dashboard() {
  const navigate = useNavigate();
  const mapElementRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const editableLayersRef = useRef(null);
  const pollingRef = useRef(null);
  const dateFromRef = useRef("");
  const dateToRef = useRef("");

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [results, setResults] = useState([]);
  const [resultsCount, setResultsCount] = useState("0 escenas");
  const [resultsHint, setResultsHint] = useState("Usa la herramienta de polígono para generar resultados.");
  const [isHintError, setIsHintError] = useState(false);
  const [areaStatus, setAreaStatus] = useState(`Área máxima permitida: ${MAX_AREA_KM2} km²`);
  const [progress, setProgress] = useState({ visible: true, message: "Listo.", state: "done" });

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
      minZoom: 6
    }).setView([1.25, -77.25], 10);

    mapInstanceRef.current = map;
    L.control.zoom({ position: "topright" }).addTo(map);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "© OpenStreetMap contributors"
    }).addTo(map);

    loadStudyArea(map);

    const editableLayers = new L.FeatureGroup();
    editableLayersRef.current = editableLayers;
    map.addLayer(editableLayers);

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

    map.addControl(drawControl);

    map.on(L.Draw.Event.CREATED, (event) => {
      const polygonAreaM2 = calculatePolygonArea(event.layer);
      if (polygonAreaM2 > MAX_AREA_M2) {
        clearResults(`El polígono supera el máximo permitido de ${MAX_AREA_KM2} km².`);
        setAreaStatus(`Última selección: ${formatAreaKm2(polygonAreaM2)} km² | Máximo: ${MAX_AREA_KM2} km²`);
        return;
      }

      editableLayers.clearLayers();
      editableLayers.addLayer(event.layer);
      exportSelectedArea(event.layer, polygonAreaM2);
    });

    map.on(L.Draw.Event.DELETED, async () => {
      await cancelActiveExport();
      clearResults();
    });
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
          fillOpacity: 0.08
        }
      }).addTo(map);
      map.fitBounds(layer.getBounds(), { padding: [40, 40] });
    } catch (error) {
      console.error("Error cargando área de estudio", error);
    }
  }

  function setExportProgress(message, state = "running") {
    setProgress({ visible: true, message: message || "Procesando exportación...", state });
  }

  function startExportProgressPolling() {
    stopExportProgressPolling();
    setExportProgress("Generando video...", "running");
    pollingRef.current = window.setInterval(async () => {
      try {
        const status = await apiFetch("/api/area/geotiff-status", { method: "GET" });
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
    setResultsHint(message || "Usa la herramienta de polígono para generar resultados.");
    setIsHintError(Boolean(message));
    setAreaStatus(`Área máxima permitida: ${MAX_AREA_KM2} km²`);
  }

  function calculatePolygonArea(layer) {
    const latLngs = layer.getLatLngs()[0] || [];
    return L.GeometryUtil.geodesicArea(latLngs);
  }

  function formatAreaKm2(areaM2) {
    return (areaM2 / 1000 / 1000).toFixed(2);
  }

  async function exportSelectedArea(layer, polygonAreaM2) {
    const polygon = (layer.getLatLngs()[0] || []).map((point) => ({ lat: point.lat, lng: point.lng }));

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
        body: JSON.stringify({ polygon, dateFrom: selectedDateFrom, dateTo: selectedDateTo })
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
          geotiffZipUrl: payload.geotiffZipUrl
        }
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
      setExportProgress("Exportación cancelada.", "error");
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
          <button className="ghost-button" type="button" onClick={handleLogout}>Cerrar sesión</button>
          <p>Dibuja un polígono en el mapa para generar productos que intersectan tu zona de interés.</p>
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
            <label htmlFor="dateFrom">
              Fecha inicial
              <input
                id="dateFrom"
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  dateFromRef.current = e.target.value;
                  setDateFrom(e.target.value);
                }}
              />
            </label>
            <label htmlFor="dateTo">
              Fecha final
              <input
                id="dateTo"
                type="date"
                value={dateTo}
                onChange={(e) => {
                  dateToRef.current = e.target.value;
                  setDateTo(e.target.value);
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
            <span>{resultsCount}</span>
          </div>
          <p className={`results-hint ${isHintError ? "is-error" : ""}`}>{resultsHint}</p>
          <ul className="results-list">
            {results.map((item, index) => (
              <li key={`${item.title}-${index}`}>
                <strong>{item.title}</strong>
                <span>{item.description}</span>
                <div className="result-actions">
                  {item.videoUrl && <a href={exportUrl(item.videoUrl)} target="_blank" rel="noreferrer">Abrir video</a>}
                  {item.geotiffZipUrl && <a href={exportUrl(item.geotiffZipUrl)}>Descargar GeoTIFF + CSV</a>}
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
            <p>Traza un polígono y revisa la generación de productos satelitales.</p>
          </div>
        </div>
        <div ref={mapElementRef} id="map" aria-label="Mapa interactivo" />
      </section>
    </main>
  );
}
