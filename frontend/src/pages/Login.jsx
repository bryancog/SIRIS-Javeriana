import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api.js";
import AuthShell from "../components/AuthShell.jsx";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);

  useEffect(() => {
    let mounted = true;
    apiFetch("/api/session")
      .then((payload) => {
        if (mounted && payload.authenticated) navigate("/dashboard", { replace: true });
      })
      .catch(() => {
        if (mounted) {
          setMessage("Servidor no disponible. Inicia el backend para continuar.");
          setIsError(true);
        }
      });
    return () => { mounted = false; };
  }, [navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setIsLoading(true);
    setIsError(false);
    setMessage("Validando credenciales...");

    try {
      await apiFetch("/api/login", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password })
      });
      setMessage("Acceso correcto. Redirigiendo...");
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setIsError(true);
      setMessage(error.message || "No fue posible iniciar sesión.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <AuthShell
      kicker="Analítica geoespacial"
      title="Iniciar sesión"
      description="Prototipo web para consultar información satelital Sentinel-2 sobre el Pacífico colombiano, seleccionar áreas de interés y generar productos geoespaciales exportables."
      highlightTitle="Consulta geoespacial interactiva"
      highlightText="Selecciona polígonos sobre el mapa, define un rango de fechas y genera video, GeoTIFF y CSV para el área consultada."
      switchText="¿No tienes cuenta?"
      switchTo="/register"
      switchLabel="Crear cuenta"
    >
      <form className="login-form" onSubmit={handleSubmit}>
        <label htmlFor="username">Usuario</label>
        <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />

        <label htmlFor="password">Contraseña</label>
        <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />

        <p className={`form-message ${isError ? "is-error" : ""}`}>{message || "Autenticación conectada a la base de datos del sistema."}</p>
        <button type="submit" disabled={isLoading}>{isLoading ? "Ingresando..." : "Ingresar"}</button>
      </form>
    </AuthShell>
  );
}
