const registerForm = document.getElementById("registerForm");
const registerMessage = document.getElementById("registerMessage");
const registerButton = document.getElementById("registerButton");

checkExistingSession();

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const name = document.getElementById("name").value.trim();
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  if (name.length < 3) {
    setRegisterState(false, "El nombre debe tener al menos 3 caracteres.");
    return;
  }

  if (username.length < 3) {
    setRegisterState(false, "El usuario debe tener al menos 3 caracteres.");
    return;
  }

  if (password.length < 6) {
    setRegisterState(false, "La contraseña debe tener al menos 6 caracteres.");
    return;
  }

  setRegisterState(true, "Creando usuario...");

  try {
    const response = await fetch("/api/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        name,
        username,
        password
      })
    });

    const payload = await response.json();

    if (!response.ok) {
      setRegisterState(false, payload.message || "No fue posible crear el usuario.");
      return;
    }

    setRegisterState(false, "Usuario creado correctamente. Redirigiendo al login...");

    setTimeout(() => {
      window.location.href = "/index.html";
    }, 1000);

  } catch (error) {
    setRegisterState(false, "No fue posible conectar con el servidor.");
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
    setRegisterState(false, "Servidor no disponible. Inicia el backend para continuar.");
  }
}

function setRegisterState(isLoading, message) {
  const normalizedMessage = String(message || "").toLowerCase();

  const isError = !isLoading && (
    normalizedMessage.includes("no fue posible") ||
    normalizedMessage.includes("debe") ||
    normalizedMessage.includes("ya existe") ||
    normalizedMessage.includes("servidor")
  );

  registerButton.disabled = isLoading;
  registerButton.textContent = isLoading ? "Creando..." : "Crear cuenta";
  registerMessage.textContent = message;
  registerMessage.classList.toggle("is-error", isError);
}