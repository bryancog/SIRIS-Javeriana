# Checklist de cierre documental SIRIS v0.9

## Estructura
- [ ] `README.md` actualizado.
- [ ] `.gitignore` actualizado.
- [ ] Backend FastAPI presente.
- [ ] Frontend React/Vite presente.
- [ ] Scripts de prueba disponibles.
- [ ] Evidencias organizadas en `tests_evidence`.

## Instalación
- [ ] Entorno virtual Python disponible.
- [ ] `requirements.txt` documentado.
- [ ] `package.json` documentado.
- [ ] `frontend/dist` generado con `npm run build`.

## Despliegue
- [ ] Backend local responde en `127.0.0.1:3000`.
- [ ] Swagger `/docs` responde.
- [ ] `/api/session` responde.
- [ ] `/api/study-area` responde.
- [ ] El README explica Cloudflare Tunnel.

## Flujo asíncrono
- [ ] `/api/area/export` documentado con HTTP 202.
- [ ] `/api/area/geotiff-status` documentado.
- [ ] Cancelación documentada.
- [ ] Evidencias de exportación disponibles.

## Pruebas
- [ ] v0.1 Backend/API.
- [ ] v0.2 Cloudflare + exportación asíncrona.
- [ ] v0.3 Validación geoespacial.
- [ ] v0.4 Frontend/E2E.
- [ ] v0.5 Carga moderada.
- [ ] v0.6 UAT.
- [ ] v0.7 Seguridad ampliada.
- [ ] v0.8 Cancelación y recuperación.
- [ ] v0.9 Documentación/instalación.
