import { Link } from "react-router-dom";

export default function AuthShell({
  kicker,
  title,
  description,
  highlightTitle,
  highlightText,
  children,
  switchText,
  switchTo,
  switchLabel
}) {
  return (
    <main className="login-screen">
      <section className="login-card" aria-label="SIRIS autenticación">
        <div className="login-hero-panel">
          <span className="brand-kicker">{kicker}</span>
          <h1>SIRIS</h1>
          <p className="login-hero-text">{description}</p>

          <div className="login-highlight-card">
            <strong>{highlightTitle}</strong>
            <span>{highlightText}</span>
          </div>

          <div className="login-metrics" aria-label="Productos disponibles">
            <div>
              <strong>Sentinel-2</strong>
              <span>Series temporales</span>
            </div>
            <div>
              <strong>GeoTIFF</strong>
              <span>Exportación espacial</span>
            </div>
            <div>
              <strong>CSV</strong>
              <span>Píxeles imputados</span>
            </div>
          </div>

          <div className="login-feature-list">
            <div><span className="feature-dot" /> Selección de polígonos sobre mapa interactivo.</div>
            <div><span className="feature-dot" /> Filtrado temporal por rango de fechas.</div>
            <div><span className="feature-dot" /> Generación de video, GeoTIFF y CSV descargable.</div>
          </div>
        </div>

        <div className="login-form-panel">
          <div className="login-form-header">
            <strong className="brand-kicker">Acceso al sistema</strong>
            <h2>{title}</h2>
          </div>
          {children}
          <div className="auth-switch">
            <span>{switchText}</span>
            <Link to={switchTo}>{switchLabel}</Link>
          </div>
          <div className="login-security-note">
            <strong>Acceso seguro</strong>
            <span>Las credenciales son validadas por el backend FastAPI mediante una base de datos SQLite.</span>
          </div>
        </div>
      </section>
    </main>
  );
}
