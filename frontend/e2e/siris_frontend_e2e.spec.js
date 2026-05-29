import { test, expect } from "@playwright/test";

const baseURL = (process.env.SIRIS_E2E_BASE_URL || "http://127.0.0.1:3000").replace(/\/$/, "");

function uniqueUser() {
  const suffix = `${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  return {
    name: "Usuario E2E Playwright",
    username: `siris_e2e_${suffix}`,
    password: "Password123",
  };
}

async function takeEvidence(page, name) {
  await page.screenshot({
    path: `../tests_evidence/frontend_e2e/${name}.png`,
    fullPage: true,
  });
}

test.describe.configure({ mode: "serial" });

test.describe("SIRIS frontend E2E v0.4.1", () => {
  let user;

  test.beforeAll(() => {
    user = uniqueUser();
  });

  test("E2E-01 carga login y muestra controles principales", async ({ page }) => {
    await page.goto(`${baseURL}/login`, { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: /iniciar sesi/i })).toBeVisible();
    await expect(page.locator("#username")).toBeVisible();
    await expect(page.locator("#password")).toBeVisible();
    await expect(page.getByRole("button", { name: /ingresar/i })).toBeVisible();

    await takeEvidence(page, "EV_FRONTEND_E2E_01_LOGIN");
  });

  test("E2E-02 valida mensaje de login incorrecto", async ({ page }) => {
    await page.goto(`${baseURL}/login`, { waitUntil: "networkidle" });

    await page.locator("#username").fill(`usuario_inexistente_${Date.now()}`);
    await page.locator("#password").fill("PasswordIncorrecto123");
    await page.getByRole("button", { name: /ingresar/i }).click();

    await expect(page.locator(".form-message")).toContainText(/incorrect|no fue posible|error|credencial/i, {
      timeout: 8000,
    });

    await takeEvidence(page, "EV_FRONTEND_E2E_02_LOGIN_INVALIDO");
  });

  test("E2E-03 registra un usuario desde la interfaz", async ({ page }) => {
    await page.goto(`${baseURL}/register`, { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: /registro/i })).toBeVisible();

    await page.locator("#name").fill(user.name);
    await page.locator("#username").fill(user.username);
    await page.locator("#password").fill(user.password);
    await page.getByRole("button", { name: /crear cuenta/i }).click();

    await expect(page.locator(".form-message")).toContainText(/creado correctamente|redirigiendo/i, {
      timeout: 8000,
    });

    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    await takeEvidence(page, "EV_FRONTEND_E2E_03_REGISTRO");
  });

  test("E2E-04 inicia sesión y accede al dashboard", async ({ page }) => {
    await page.goto(`${baseURL}/login`, { waitUntil: "networkidle" });

    await page.locator("#username").fill(user.username);
    await page.locator("#password").fill(user.password);
    await page.getByRole("button", { name: /ingresar/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
    await expect(page.getByText(/Selector Geoespacial/i)).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#map")).toBeVisible();

    await takeEvidence(page, "EV_FRONTEND_E2E_04_DASHBOARD");
  });

  test("E2E-05 valida sesión autenticada desde frontend y API", async ({ page }) => {
    await page.goto(`${baseURL}/login`, { waitUntil: "networkidle" });

    await page.locator("#username").fill(user.username);
    await page.locator("#password").fill(user.password);
    await page.getByRole("button", { name: /ingresar/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });

    const response = await page.request.get(`${baseURL}/api/session`);
    expect(response.ok()).toBeTruthy();

    const payload = await response.json();
    expect(payload.authenticated).toBe(true);
    expect(payload.user.username).toBe(user.username);

    await takeEvidence(page, "EV_FRONTEND_E2E_05_SESION_AUTH");
  });

  test("E2E-06 valida mapa, filtro temporal y panel de resultados", async ({ page }) => {
    await page.goto(`${baseURL}/login`, { waitUntil: "networkidle" });

    await page.locator("#username").fill(user.username);
    await page.locator("#password").fill(user.password);
    await page.getByRole("button", { name: /ingresar/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });

    await expect(page.getByText(/Filtro temporal/i)).toBeVisible();
    await expect(page.getByText(/IDs detectados/i)).toBeVisible();
    await expect(page.locator("#map")).toBeVisible();
    await expect(page.locator(".leaflet-container")).toBeVisible({ timeout: 15000 });

    const dateInputs = page.locator('input[type="date"]');
    await expect(dateInputs).toHaveCount(2);

    await dateInputs.nth(0).fill("2016-01-01");
    await dateInputs.nth(1).fill("2016-02-01");

    await takeEvidence(page, "EV_FRONTEND_E2E_06_MAPA_FECHAS");
  });

  test("E2E-07 activa la herramienta visual de polígono sin ejecutar exportación", async ({ page }) => {
    await page.goto(`${baseURL}/login`, { waitUntil: "networkidle" });

    await page.locator("#username").fill(user.username);
    await page.locator("#password").fill(user.password);
    await page.getByRole("button", { name: /ingresar/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
    await expect(page.locator(".leaflet-container")).toBeVisible({ timeout: 15000 });

    const drawButton = page.locator(".siris-draw-polygon-button");
    await expect(drawButton).toBeVisible({ timeout: 15000 });
    await drawButton.click();

    // Se usa el selector específico del panel de resultados para evitar strict mode violation.
    await expect(page.locator(".results-hint")).toContainText(/Haz clic en el mapa/i, {
      timeout: 8000,
    });

    const map = page.locator("#map");
    const box = await map.boundingBox();

    if (!box) {
      throw new Error("No se pudo obtener el área del mapa.");
    }

    await page.mouse.click(box.x + box.width * 0.45, box.y + box.height * 0.45);

    await expect(page.locator(".status-card")).toContainText(/Dibujo activo:\s*1 punto/i, {
      timeout: 8000,
    });

    await takeEvidence(page, "EV_FRONTEND_E2E_07_DIBUJO_POLIGONO");

    const clearButton = page.locator(".siris-draw-clear-button");
    await clearButton.click();
  });

  test("E2E-08 cierra sesión desde la interfaz", async ({ page }) => {
    await page.goto(`${baseURL}/login`, { waitUntil: "networkidle" });

    await page.locator("#username").fill(user.username);
    await page.locator("#password").fill(user.password);
    await page.getByRole("button", { name: /ingresar/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });

    await page.getByRole("button", { name: /cerrar sesi/i }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    await takeEvidence(page, "EV_FRONTEND_E2E_08_LOGOUT");
  });
});
