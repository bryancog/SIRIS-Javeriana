# SIRIS - Prueba de aceptación de usuario UAT v0.6

## 1. Información general

| Campo | Valor |
|---|---|
| Proyecto | SIRIS-Javeriana |
| Versión de prueba | UAT v0.6 |
| Fecha de ejecución |  |
| Evaluador |  |
| Rol del evaluador | Usuario final / evaluador funcional |
| Ambiente | Local compilado / Cloudflare Tunnel / Dominio propio |
| URL evaluada |  |
| Rama evaluada | main |
| Navegador | Chrome / Edge / Firefox |
| Equipo usado |  |
| Observaciones generales |  |

---

## 2. Objetivo de la prueba

Validar desde la perspectiva de usuario final que el sistema SIRIS permite completar el flujo principal de uso: acceso al sistema, autenticación, selección de fechas, interacción con el mapa, dibujo de polígono, inicio de exportación asíncrona, seguimiento del estado, visualización del video generado, descarga del ZIP GeoTIFF/CSV y cierre de sesión.

---

## 3. Precondiciones

| ID | Precondición | Cumple | Observaciones |
|---|---|---|---|
| PRE-01 | El backend FastAPI está activo. | Sí / No |  |
| PRE-02 | El frontend React compilado se sirve desde FastAPI. | Sí / No |  |
| PRE-03 | Las variables de entorno de datos están configuradas. | Sí / No |  |
| PRE-04 | La URL pública o local carga correctamente. | Sí / No |  |
| PRE-05 | Existen datos satelitales disponibles para el rango temporal elegido. | Sí / No |  |

---

## 4. Datos sugeridos para la prueba

| Campo | Valor sugerido |
|---|---|
| Fecha inicial | 2016-01-01 |
| Fecha final | 2016-02-01 |
| Zona | Pasto / Pacífico colombiano |
| Polígono | Pequeño, dentro del área visible de estudio |
| Usuario | Crear un usuario nuevo durante la prueba |

---

## 5. Casos de aceptación

| ID | Caso de aceptación | Pasos resumidos | Resultado esperado | Estado | Observaciones |
|---|---|---|---|---|---|
| UAT-01 | Acceso a la aplicación | Abrir la URL evaluada. | La página de inicio/login carga correctamente. | Aprobado / Fallido |  |
| UAT-02 | Registro de usuario | Ir a Crear cuenta, diligenciar datos y registrar. | El sistema crea el usuario y redirige al login. | Aprobado / Fallido |  |
| UAT-03 | Inicio de sesión | Ingresar usuario y contraseña válidos. | El sistema permite acceder al dashboard. | Aprobado / Fallido |  |
| UAT-04 | Visualización del dashboard | Revisar mapa, panel lateral, filtro temporal y controles. | La interfaz se visualiza completa y comprensible. | Aprobado / Fallido |  |
| UAT-05 | Selección de fechas | Ingresar fecha inicial y fecha final. | El sistema conserva las fechas seleccionadas. | Aprobado / Fallido |  |
| UAT-06 | Dibujo de polígono | Activar la herramienta de polígono y marcar vértices. | El mapa permite crear el polígono de interés. | Aprobado / Fallido |  |
| UAT-07 | Inicio de exportación | Cerrar el polígono. | El sistema inicia la exportación asíncrona. | Aprobado / Fallido |  |
| UAT-08 | Seguimiento de estado | Observar mensajes del panel de exportación. | El sistema informa avance: video, GeoTIFF, validación/finalización. | Aprobado / Fallido |  |
| UAT-09 | Visualización de resultado | Esperar finalización. | El sistema muestra el video generado. | Aprobado / Fallido |  |
| UAT-10 | Descarga de ZIP | Usar el enlace de descarga GeoTIFF + CSV. | El ZIP se descarga correctamente. | Aprobado / Fallido |  |
| UAT-11 | Validación básica de usabilidad | Evaluar claridad de mensajes, botones y flujo. | El flujo es comprensible para un usuario final. | Aprobado / Fallido |  |
| UAT-12 | Cierre de sesión | Hacer clic en Cerrar sesión. | El sistema cierra la sesión y regresa al login. | Aprobado / Fallido |  |

---

## 6. Evidencias requeridas

Guardar las capturas en:

```txt
D:\SIRIS\tests_evidence\uat\
```

Nombres sugeridos:

```txt
EV_UAT_01_LOGIN.png
EV_UAT_02_REGISTRO.png
EV_UAT_03_DASHBOARD.png
EV_UAT_04_FECHAS_POLIGONO.png
EV_UAT_05_EXPORTACION_EN_PROCESO.png
EV_UAT_06_EXPORTACION_FINALIZADA.png
EV_UAT_07_VIDEO_RESULTADO.png
EV_UAT_08_ZIP_DESCARGADO.png
EV_UAT_09_LOGOUT.png
```

---

## 7. Resultado global

| Criterio | Resultado |
|---|---|
| Casos ejecutados |  |
| Casos aprobados |  |
| Casos fallidos |  |
| Resultado global | Aprobado / Aprobado con observaciones / Fallido |
| Observaciones relevantes |  |

---

## 8. Observaciones del evaluador

Escribir aquí comentarios sobre facilidad de uso, claridad de instrucciones, tiempos de espera, visibilidad de botones, mensajes de error o mejora de la experiencia.

```txt

```

---

## 9. Conclusión de aceptación

Marcar una opción:

- [ ] El sistema es aceptado para el alcance académico del prototipo.
- [ ] El sistema es aceptado con observaciones menores.
- [ ] El sistema requiere ajustes antes de aceptación.

Firma / nombre del evaluador:

```txt

```
