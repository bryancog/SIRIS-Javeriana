const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

let activeAreaProcess = null;
let activeAreaOutName = null;

function runAreaExport({
  row0,
  col0,
  height,
  width,
  polygon,
  dateFrom,
  dateTo,
  outName,
  dataRoot,
  exportsRoot,
  webExportsRoot
}) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, "..", "scripts", "generar_area_desde_tiles.py");

    activeAreaOutName = outName;

   const args = [
      scriptPath,
      "--web-root", webExportsRoot,
      "--out-name", outName,
      "--fps", "8"
    ];

    if (dateFrom) {
      args.push("--date-from", String(dateFrom).replace(/-/g, ""));
    }

    if (dateTo) {
      args.push("--date-to", String(dateTo).replace(/-/g, ""));
    }

    if (polygon) {
      const exportPath = path.join(exportsRoot, outName);
      fs.mkdirSync(exportPath, { recursive: true });

      const polygonPath = path.join(exportPath, "polygon.json");
      fs.writeFileSync(polygonPath, JSON.stringify(polygon), "utf8");

      args.push("--polygon-file", polygonPath);
      args.push("--grid-georef", path.join(dataRoot, "grid_georef.json"));
    } else {
      args.push("--row0", String(Math.round(row0)));
      args.push("--col0", String(Math.round(col0)));
      args.push("--height", String(Math.round(height)));
      args.push("--width", String(Math.round(width)));
    }

    const child = spawn("python", args, {
      cwd: dataRoot
    });

    activeAreaProcess = child;

    let stderr = "";

    child.stdout.on("data", (data) => {
      console.log(data.toString());
    });

    child.stderr.on("data", (data) => {
      stderr += data.toString();
      console.error(data.toString());
    });

    child.on("close", (code, signal) => {
      if (activeAreaProcess === child) {
        activeAreaProcess = null;
      }

      if (activeAreaOutName === outName) {
        activeAreaOutName = null;
      }

      if (signal || code !== 0) {
        reject(
          new Error(
            signal
              ? "Exportacion cancelada."
              : stderr || `Proceso Python terminó con código ${code}`
          )
        );
        return;
      }

      resolve();
    });
  });
}

function runGeoTiffAreaExport({
  polygon,
  dateFrom,
  dateTo,
  outName,
  dataRoot,
  exportsRoot,
  npyRoots,
  maskRoot
}) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, "..", "scripts", "generar_area_geotiff_csv_desde_npy.py");

    const exportPath = path.join(exportsRoot, outName);
    fs.mkdirSync(exportPath, { recursive: true });

    const polygonPath = path.join(exportPath, "polygon.json");

    if (polygon) {
      fs.writeFileSync(polygonPath, JSON.stringify(polygon), "utf8");
    }

    const args = [
      scriptPath,
      "--npy-roots",
      ...npyRoots,
      "--mask-root", maskRoot,
      "--polygon-file", polygonPath,
      "--grid-georef", path.join(dataRoot, "grid_georef.json"),
      "--out-root", exportsRoot,
      "--out-name", outName
    ];

    const workers = process.env.SIRIS_GEOTIFF_WORKERS || "2";
    args.push("--workers", workers);

    if (dateFrom) {
      args.push("--date-from", String(dateFrom).replace(/-/g, ""));
    }

    if (dateTo) {
      args.push("--date-to", String(dateTo).replace(/-/g, ""));
    }

    const child = spawn("python", args, {
      cwd: dataRoot
    });

    let stderr = "";

    child.stdout.on("data", (data) => {
      console.log(data.toString());
    });

    child.stderr.on("data", (data) => {
      stderr += data.toString();
      console.error(data.toString());
    });

    child.on("close", (code, signal) => {
      if (signal || code !== 0) {
        reject(
          new Error(
            signal
              ? "Exportacion GeoTIFF cancelada."
              : stderr || `Proceso GeoTIFF terminó con código ${code}`
          )
        );
        return;
      }

      resolve();
    });
  });
}

function cancelActiveAreaExport(exportsRoot) {
  if (activeAreaProcess) {
    activeAreaProcess.kill("SIGTERM");
    activeAreaProcess = null;
  }

  if (activeAreaOutName) {
    const exportPath = path.join(exportsRoot, activeAreaOutName);
    fs.rm(exportPath, { recursive: true, force: true }, () => {});
    activeAreaOutName = null;
  }
}

module.exports = {
  runAreaExport,
  runGeoTiffAreaExport,
  cancelActiveAreaExport
};