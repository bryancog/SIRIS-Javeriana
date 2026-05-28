const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const {
  runAreaExport,
  cancelActiveAreaExport
} = require("./services/areaService");

const PORT = process.env.PORT || 3000;
const HOST = "127.0.0.1";
const SESSION_COOKIE = "siris_session";

const FRONTEND_ROOT = path.join(__dirname, "..", "frontend");
const DATA_ROOT = path.join(__dirname, "data");
const EXPORTS_ROOT = path.join(DATA_ROOT, "area_exports");
const WEB_EXPORTS_ROOT = path.join(DATA_ROOT, "web_exports");


const TEST_USER = {
  username: "demo",
  password: "demo123",
  name: "Usuario Demo"
};

const sessions = new Map();

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".mp4": "video/mp4",
  ".zip": "application/zip"
};

const server = http.createServer(async (req, res) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host}`);
  const cookies = parseCookies(req.headers.cookie || "");
  const session = getSession(cookies[SESSION_COOKIE]);

  if (req.method === "GET" && requestUrl.pathname === "/") {
    redirect(res, session ? "/dashboard.html" : "/index.html");
    return;
  }

  if (req.method === "GET" && requestUrl.pathname === "/api/session") {
    sendJson(res, 200, {
      authenticated: Boolean(session),
      user: session ? { username: session.username, name: session.name } : null
    });
    return;
  }

  if (req.method === "POST" && requestUrl.pathname === "/api/login") {
    const body = await readJsonBody(req);

    if (!body || body.username !== TEST_USER.username || body.password !== TEST_USER.password) {
      sendJson(res, 401, { message: "Usuario o contrasena incorrectos." });
      return;
    }

    const token = crypto.randomBytes(24).toString("hex");
    sessions.set(token, {
      username: TEST_USER.username,
      name: TEST_USER.name,
      createdAt: Date.now()
    });

    res.setHeader("Set-Cookie", `${SESSION_COOKIE}=${token}; HttpOnly; Path=/; SameSite=Lax`);
    sendJson(res, 200, {
      message: "Login correcto.",
      user: { username: TEST_USER.username, name: TEST_USER.name }
    });
    return;
  }

  if (req.method === "POST" && requestUrl.pathname === "/api/logout") {
    if (cookies[SESSION_COOKIE]) {
      sessions.delete(cookies[SESSION_COOKIE]);
    }

    res.setHeader("Set-Cookie", `${SESSION_COOKIE}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0`);
    sendJson(res, 200, { message: "Sesion cerrada." });
    return;
  }

  if (req.method === "GET" && requestUrl.pathname === "/dashboard.html" && !session) {
    redirect(res, "/index.html");
    return;
  }

  if (req.method === "GET" && requestUrl.pathname === "/index.html" && session) {
    redirect(res, "/dashboard.html");
    return;
  }

  if (req.method === "POST" && requestUrl.pathname === "/api/area/export") {
    if (!session) {
      sendJson(res, 401, { message: "Sesion no autenticada." });
      return;
    }

    const body = await readJsonBody(req);

    const hasPolygon = Array.isArray(body?.polygon) && body.polygon.length >= 3;
    const hasBox =
      Number.isFinite(body?.row0) &&
      Number.isFinite(body?.col0) &&
      Number.isFinite(body?.height) &&
      Number.isFinite(body?.width);

    if (!hasPolygon && !hasBox) {
      sendJson(res, 400, { message: "Parametros invalidos." });
      return;
    }

    const outName = `area_${Date.now()}`;

    try {
      await runAreaExport({
        row0: body.row0,
        col0: body.col0,
        height: body.height,
        width: body.width,
        polygon: body.polygon,
        outName,
        dataRoot: DATA_ROOT,
        exportsRoot: EXPORTS_ROOT,
        webExportsRoot: WEB_EXPORTS_ROOT
      });

      const exportDir = path.join(EXPORTS_ROOT, outName);
      const files = fs.readdirSync(exportDir);

      const videoFile = files.find((file) => file.toLowerCase().endsWith(".mp4"));
      const zipFile = files.find((file) => file.toLowerCase().endsWith(".zip"));

      if (!videoFile) {
        sendJson(res, 500, {
          message: "La exportacion terminó, pero no se encontró el video MP4."
        });
        return;
      }

      sendJson(res, 200, {
        message: "Exportacion generada.",
        outName,
        videoUrl: `/exports/${outName}/${videoFile}`,
        framesUrl: `/exports/${outName}/frames_jpg/`,
        imagesZipUrl: zipFile ? `/exports/${outName}/${zipFile}` : null
      });
    } catch (error) {
      sendJson(res, 500, { message: "Error generando exportacion.", error: error.message });
    }

    return;
  }

  if (req.method === "GET" && requestUrl.pathname === "/api/study-area") {
    const geojsonPath = path.join(DATA_ROOT, "study_area.geojson");

    fs.readFile(geojsonPath, "utf8", (error, content) => {
      if (error) {
        sendJson(res, 500, { message: "No se pudo leer el area de estudio." });
        return;
      }

      res.writeHead(200, {
       "Content-Type": "application/json"
      });

      res.end(content);
    });

    return;
  }

  if (req.method === "POST" && requestUrl.pathname === "/api/area/cancel") {
    if (!session) {
      sendJson(res, 401, { message: "Sesion no autenticada." });
      return;
    }

    cancelActiveAreaExport(EXPORTS_ROOT);

    sendJson(res, 200, { message: "Exportacion cancelada." });
    return;
  }

  if (req.method === "GET" && requestUrl.pathname.startsWith("/exports/")) {
    serveExportFile(requestUrl.pathname, res);
    return;
  }

  if (req.method !== "GET") {
    sendJson(res, 404, { message: "Ruta no encontrada." });
    return;
  }

  serveStaticFile(requestUrl.pathname, res);
});

server.listen(PORT, HOST, () => {
  console.log(`SIRIS server running at http://${HOST}:${PORT}`);
  console.log(`Credenciales de prueba -> usuario: ${TEST_USER.username} | contrasena: ${TEST_USER.password}`);
});

function serveExportFile(urlPath, res) {
  const relativePath = decodeURIComponent(urlPath.replace("/exports/", ""));
  const normalizedPath = path.normalize(relativePath).replace(/^(\.\.[/\\])+/, "");
  const filePath = path.join(EXPORTS_ROOT, normalizedPath);

  if (!filePath.startsWith(EXPORTS_ROOT)) {
    sendText(res, 403, "Acceso denegado.");
    return;
  }

  fs.readFile(filePath, (error, content) => {
    if (error) {
      sendText(res, 404, "Archivo no encontrado.");
      return;
    }

    const extension = path.extname(filePath).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME_TYPES[extension] || "application/octet-stream" });
    res.end(content);
  });
}

function serveStaticFile(urlPath, res) {
  const safePath = urlPath === "/" ? "/index.html" : urlPath;
  const normalizedPath = path.normalize(safePath).replace(/^(\.\.[/\\])+/, "");
  const filePath = path.join(FRONTEND_ROOT, normalizedPath);

  if (!filePath.startsWith(FRONTEND_ROOT)) {
    sendText(res, 403, "Acceso denegado.");
    return;
  }

  fs.readFile(filePath, (error, content) => {
    if (error) {
      sendText(res, 404, "Archivo no encontrado.");
      return;
    }

    const extension = path.extname(filePath).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME_TYPES[extension] || "application/octet-stream" });
    res.end(content);
  });
}

function parseCookies(cookieHeader) {
  return cookieHeader.split(";").reduce((accumulator, pair) => {
    const [rawKey, ...rawValue] = pair.trim().split("=");

    if (!rawKey) {
      return accumulator;
    }

    accumulator[rawKey] = decodeURIComponent(rawValue.join("="));
    return accumulator;
  }, {});
}

function getSession(token) {
  if (!token) {
    return null;
  }

  return sessions.get(token) || null;
}

function readJsonBody(req) {
  return new Promise((resolve) => {
    let rawData = "";

    req.on("data", (chunk) => {
      rawData += chunk;
    });

    req.on("end", () => {
      try {
        resolve(JSON.parse(rawData || "{}"));
      } catch (error) {
        resolve(null);
      }
    });
  });
}

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload));
}

function sendText(res, statusCode, text) {
  res.writeHead(statusCode, { "Content-Type": "text/plain; charset=utf-8" });
  res.end(text);
}

function redirect(res, location) {
  res.writeHead(302, { Location: location });
  res.end();
}
