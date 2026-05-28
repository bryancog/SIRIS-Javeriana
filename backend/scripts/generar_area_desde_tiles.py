from pathlib import Path
import argparse
import re
import shutil
import subprocess
import json
import math
from pyproj import Transformer
from PIL import Image, ImageDraw, ImageFont

TILE_SIZE_RAW = 512
SCALE = 4
TILE_SIZE_SR = TILE_SIZE_RAW * SCALE
BAR_H = 110


def parse_tile(tile_name):
    m = re.match(r"tile_r(\d+)_c(\d+)$", tile_name)
    if not m:
        raise ValueError(f"Nombre de tile inválido: {tile_name}")
    return int(m.group(1)), int(m.group(2))


def tile_bounds_sr(tile_name):
    r_raw, c_raw = parse_tile(tile_name)
    r0 = r_raw * SCALE
    c0 = c_raw * SCALE
    return r0, c0, r0 + TILE_SIZE_SR, c0 + TILE_SIZE_SR


def intersects(a, b):
    ar0, ac0, ar1, ac1 = a
    br0, bc0, br1, bc1 = b
    return not (ar1 <= br0 or ar0 >= br1 or ac1 <= bc0 or ac0 >= bc1)


def get_frame_map(tile_dir):
    frames = sorted((tile_dir / "frames_jpg").glob("frame_*.jpg"))
    out = {}
    for f in frames:
        m = re.search(r"frame_(\d+)_(\d{8})\.jpg$", f.name)
        if m:
            out[m.group(2)] = f
    return out


ap = argparse.ArgumentParser()

ap.add_argument("--web-root", required=True)
ap.add_argument("--out-name", required=True)
ap.add_argument("--fps", type=int, default=8)

ap.add_argument("--row0", type=int, required=False)
ap.add_argument("--col0", type=int, required=False)
ap.add_argument("--height", type=int, required=False)
ap.add_argument("--width", type=int, required=False)

ap.add_argument("--polygon-file", required=False)
ap.add_argument("--grid-georef", required=False)

ap.add_argument("--copy-if-single-tile", action="store_true")

args = ap.parse_args()

web_root = Path(args.web_root)
out_root = Path("area_exports") / args.out_name
frames_out = out_root / "frames_jpg"
frames_out.mkdir(parents=True, exist_ok=True)

def polygon_to_sr_bbox(polygon_file, grid_georef):
    polygon = json.loads(Path(polygon_file).read_text(encoding="utf-8"))
    meta = json.loads(Path(grid_georef).read_text(encoding="utf-8"))

    crs = meta["crs"]
    a, b, c, d, e, f = meta["transform"]
    scale = int(meta.get("sr_scale", 4))

    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)

    rows = []
    cols = []

    for p in polygon:
        lng = float(p["lng"])
        lat = float(p["lat"])

        x, y = transformer.transform(lng, lat)

        # Para rasters norte-arriba: b=d=0 normalmente
        col = (x - c) / a
        row = (y - f) / e

        rows.append(row * scale)
        cols.append(col * scale)

    row0 = math.floor(min(rows))
    row1 = math.ceil(max(rows))
    col0 = math.floor(min(cols))
    col1 = math.ceil(max(cols))

    return row0, col0, row1 - row0, col1 - col0

if args.polygon_file:
    if not args.grid_georef:
        raise SystemExit("Falta --grid-georef")

    row0, col0, height, width = polygon_to_sr_bbox(args.polygon_file, args.grid_georef)

    args.row0 = row0
    args.col0 = col0
    args.height = height
    args.width = width

    print("BBox calculado desde poligono:", row0, col0, height, width)
else:
    if args.row0 is None or args.col0 is None or args.height is None or args.width is None:
        raise SystemExit("Debe enviar row0/col0/height/width o polygon-file")

area = (args.row0, args.col0, args.row0 + args.height, args.col0 + args.width)

tiles = []
for td in sorted(web_root.glob("tile_r*_c*")):
    if not td.is_dir():
        continue
    tile = td.name
    tb = tile_bounds_sr(tile)
    if intersects(area, tb):
        tiles.append((tile, td, tb))

print("Área SR:", area)
print("Tiles necesarios:", [t[0] for t in tiles])

if not tiles:
    raise SystemExit("El área no intersecta ningún tile disponible.")

# Caso simple: un solo tile y se quiere reutilizar todo el tile completo
if len(tiles) == 1 and args.copy_if_single_tile:
    tile, td, tb = tiles[0]
    ar0, ac0, ar1, ac1 = area
    tr0, tc0, tr1, tc1 = tb

    if ar0 == tr0 and ac0 == tc0 and ar1 == tr1 and ac1 == tc1:
        print("Área equivale al tile completo. Copiando video y frames existentes.")
        shutil.copytree(td / "frames_jpg", frames_out, dirs_exist_ok=True)
        mp4s = list(td.glob("*.mp4"))
        if mp4s:
            shutil.copy2(mp4s[0], out_root / mp4s[0].name)
        raise SystemExit(0)

# Mapear fechas disponibles por tile
tile_frame_maps = [(tile, td, tb, get_frame_map(td)) for tile, td, tb in tiles]

common_dates = sorted(set.intersection(*(set(m.keys()) for _, _, _, m in tile_frame_maps)))
print("Fechas comunes:", len(common_dates))

if not common_dates:
    raise SystemExit("No hay fechas comunes entre los tiles seleccionados.")

# Determinar bounding box de mosaico en coordenadas SR
mr0 = min(tb[0] for _, _, tb, _ in tile_frame_maps)
mc0 = min(tb[1] for _, _, tb, _ in tile_frame_maps)
mr1 = max(tb[2] for _, _, tb, _ in tile_frame_maps)
mc1 = max(tb[3] for _, _, tb, _ in tile_frame_maps)

mosaic_h = mr1 - mr0
mosaic_w = mc1 - mc0

crop_left = args.col0 - mc0
crop_top = args.row0 - mr0
crop_right = crop_left + args.width
crop_bottom = crop_top + args.height

def extract_tile_content(img):
    """
    Extrae solo la imagen útil del tile.
    Si el frame trae barra superior, la elimina.
    Si no trae barra, no recorta innecesariamente.
    """
    src_bar = max(0, img.height - TILE_SIZE_SR)

    content = img.crop((
        0,
        src_bar,
        min(img.width, TILE_SIZE_SR),
        min(img.height, src_bar + TILE_SIZE_SR)
    ))

    if content.size != (TILE_SIZE_SR, TILE_SIZE_SR):
        fixed = Image.new("RGB", (TILE_SIZE_SR, TILE_SIZE_SR), (0, 0, 0))
        fixed.paste(content, (0, 0))
        return fixed

    return content

def remove_source_label(img):
    """
    Elimina la etiqueta interna heredada del tile original.
    Ajusta coordenadas si la caja cambia de posición/tamaño.
    """
    # Caja aproximada del sello negro con fecha dentro del tile
    x0, y0, x1, y1 = 0, TILE_SIZE_SR - 95, 170, TILE_SIZE_SR - 35

    # Tomar una zona vecina a la derecha para cubrir la etiqueta
    replacement = img.crop((x1, y0, min(x1 + (x1 - x0), img.width), y1))

    if replacement.size[0] == 0 or replacement.size[1] == 0:
        return img

    replacement = replacement.resize((x1 - x0, y1 - y0))
    img.paste(replacement, (x0, y0))

    return img


for i, fecha in enumerate(common_dates):
    # Mosaico solo con imagen satelital, sin barra superior.
    mosaic = Image.new("RGB", (mosaic_w, mosaic_h), (0, 0, 0))

    for tile, td, tb, fmap in tile_frame_maps:
        img = Image.open(fmap[fecha]).convert("RGB")
        img_content = extract_tile_content(img)
        img_content = remove_source_label(img_content)

        tr0, tc0, tr1, tc1 = tb
        x = tc0 - mc0
        y = tr0 - mr0

        mosaic.paste(img_content, (x, y))

    cropped = mosaic.crop((crop_left, crop_top, crop_right, crop_bottom))

    # Crear salida final con barra superior propia.
    final = Image.new("RGB", (args.width, args.height + BAR_H), (0, 0, 0))
    final.paste(cropped, (0, BAR_H))

    label = f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:8]} | area {args.out_name}"

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
    except:
        font = None

    d2 = ImageDraw.Draw(final)
    d2.rectangle((0, 0, args.width, BAR_H), fill=(0, 0, 0))
    d2.text((40, 28), label, fill=(255, 255, 255), font=font)

    out = frames_out / f"frame_{i:04d}_{fecha}.jpg"
    final.save(out, quality=85, optimize=True)

    if i == 0 or (i + 1) % 50 == 0 or i == len(common_dates) - 1:
        print(f"{i+1}/{len(common_dates)} {out}", flush=True)

video = out_root / f"{args.out_name}.mp4"

frames_list = out_root / "frames.txt"

with open(frames_list, "w", encoding="utf-8") as f:
    for jpg in sorted(frames_out.glob("*.jpg")):
        safe_path = str(jpg.resolve()).replace("\\", "/")
        f.write(f"file '{safe_path}'\n")

cmd = [
    "ffmpeg", "-nostdin", "-y",
    "-r", str(args.fps),
    "-f", "concat",
    "-safe", "0",
    "-i", str(frames_list),
    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
    "-c:v", "libx264",
    "-crf", "20",
    "-preset", "medium",
    str(video),
]

print("Creando video...")
subprocess.run(cmd, check=True)

print("Video:", video)
print("Frames:", frames_out)

zip_base = out_root / f"{args.out_name}_frames"
zip_path = Path(str(zip_base) + ".zip")

if zip_path.exists():
    zip_path.unlink()

created_zip = shutil.make_archive(
    str(zip_base),
    "zip",
    root_dir=frames_out
)

print("ZIP imagenes:", created_zip)
