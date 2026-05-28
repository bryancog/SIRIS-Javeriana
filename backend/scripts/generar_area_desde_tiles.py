from pathlib import Path
import argparse
import re
import shutil
import subprocess
from PIL import Image

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
ap.add_argument("--web-root", default="web_exports")
ap.add_argument("--row0", type=int, required=True, help="fila inicial en coordenadas SR globales")
ap.add_argument("--col0", type=int, required=True, help="columna inicial en coordenadas SR globales")
ap.add_argument("--height", type=int, required=True)
ap.add_argument("--width", type=int, required=True)
ap.add_argument("--out-name", default="area_export")
ap.add_argument("--fps", type=int, default=8)
ap.add_argument("--copy-if-single-tile", action="store_true")
args = ap.parse_args()

web_root = Path(args.web_root)
out_root = Path("area_exports") / args.out_name
frames_out = out_root / "frames_jpg"
frames_out.mkdir(parents=True, exist_ok=True)

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
crop_top = args.row0 - mr0 + BAR_H
crop_right = crop_left + args.width
crop_bottom = crop_top + args.height

for i, fecha in enumerate(common_dates):
    # El frame de tile tiene barra superior. El mosaico también debe contemplarla.
    mosaic = Image.new("RGB", (mosaic_w, mosaic_h + BAR_H), (0, 0, 0))

    for tile, td, tb, fmap in tile_frame_maps:
        img = Image.open(fmap[fecha]).convert("RGB")
        tr0, tc0, tr1, tc1 = tb
        x = tc0 - mc0
        y = tr0 - mr0
        mosaic.paste(img.crop((0, BAR_H, TILE_SIZE_SR, TILE_SIZE_SR + BAR_H)), (x, y + BAR_H))

    # copiar barra superior del primer tile, o crear una barra nueva simple
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(mosaic)
    draw.rectangle((0, 0, mosaic_w, BAR_H), fill=(0, 0, 0))
    label = f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:8]} | area {args.out_name}"
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
    except:
        font = None
    draw.text((40, 28), label, fill=(255, 255, 255), font=font)

    cropped = mosaic.crop((crop_left, crop_top - BAR_H, crop_right, crop_bottom))
    # agregar barra superior propia al recorte
    final = Image.new("RGB", (args.width, args.height + BAR_H), (0, 0, 0))
    final.paste(cropped, (0, BAR_H))
    d2 = ImageDraw.Draw(final)
    d2.text((40, 28), label, fill=(255, 255, 255), font=font)

    out = frames_out / f"frame_{i:04d}_{fecha}.jpg"
    final.save(out, quality=85, optimize=True)

    if i == 0 or (i + 1) % 50 == 0 or i == len(common_dates):
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
    "-vf", "format=yuv420p",
    "-c:v", "libx264",
    "-crf", "20",
    "-preset", "medium",
    str(video),
]

print("Creando video...")
subprocess.run(cmd, check=True)
print("Video:", video)
print("Frames:", frames_out)
