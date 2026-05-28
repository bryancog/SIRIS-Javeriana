const loginForm = document.getElementById("loginForm");
const loginMessage = document.getElementById("loginMessage");
const loginButton = document.getElementById("loginButton");

checkExistingSession();

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  setFormState(true, "Validando credenciales...");

  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ username, password })
    });

    const payload = await response.json();

    if (!response.ok) {
      setFormState(false, payload.message || "No fue posible iniciar sesion.");
      return;
    }

    setFormState(false, "Acceso correcto. Redirigiendo...");
    window.location.href = "/dashboard.html";
  } catch (error) {
    setFormState(false, "No fue posible conectar con el servidor.");
  }
});

async function checkExistingSession() {
  try {
    const response = await fetch("/api/session");
    const payload = await response.json();

    if (payload.authenticated) {
      window.location.href = "/dashboard.html";
    }
  } catch (error) {
    setFormState(false, "Servidor no disponible. Inicia el backend para continuar.");
  }
}

function setFormState(isLoading, message) {
  const normalizedMessage = String(message || "").toLowerCase();
  const isError = !isLoading && (
    normalizedMessage.includes("no fue posible") ||
    normalizedMessage.includes("incorrect")
  );

  loginButton.disabled = isLoading;
  loginButton.textContent = isLoading ? "Ingresando..." : "Ingresar";
  loginMessage.textContent = message;
  loginMessage.classList.toggle("is-error", isError);
}
