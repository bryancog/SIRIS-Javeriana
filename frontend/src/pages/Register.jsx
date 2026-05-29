import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api.js";
import AuthShell from "../components/AuthShell.jsx";

export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
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

    if (name.trim().length < 3) {
      setIsError(true);
      setMessage("El nombre debe tener al menos 3 caracteres.");
      return;
    }
    if (username.trim().length < 3) {
      setIsError(true);
      setMessage("El usuario debe tener al menos 3 caracteres.");
      return;
    }
    if (password.length < 6) {
      setIsError(true);
      setMessage("La contraseña debe tener al menos 6 caracteres.");
      return;
    }

    setIsLoading(true);
    setIsError(false);
    setMessage("Creando usuario...");

    try {
      await apiFetch("/api/register", {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), username: username.trim(), password })
      });
      setMessage("Usuario creado correctamente. Redirigiendo al login...");
      setTimeout(() => navigate("/login", { replace: true }), 800);
    } catch (error) {
      setIsError(true);
      setMessage(error.message || "No fue posible crear el usuario.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <AuthShell
      kicker="Nuevo acceso"
      title="Registro"
      description="Crea una cuenta para acceder al dashboard satelital, seleccionar áreas de interés y generar productos geoespaciales derivados de Sentinel-2."
      highlightTitle="Registro de usuarios"
      highlightText="Crea una cuenta para ingresar al dashboard, consultar áreas de interés y generar productos satelitales exportables."
      switchText="¿Ya tienes cuenta?"
      switchTo="/login"
      switchLabel="Iniciar sesión"
    >
      <form className="login-form" onSubmit={handleSubmit}>
        <label htmlFor="name">Nombre completo</label>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" required />

        <label htmlFor="username">Usuario</label>
        <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />

        <label htmlFor="password">Contraseña</label>
        <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required />

        <p className={`form-message ${isError ? "is-error" : ""}`}>{message || "Los datos serán validados por el backend del sistema."}</p>
        <button type="submit" disabled={isLoading}>{isLoading ? "Creando..." : "Crear cuenta"}</button>
      </form>
    </AuthShell>
  );
}
