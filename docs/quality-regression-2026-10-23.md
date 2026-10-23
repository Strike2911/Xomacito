# Corrección de calidad pendiente de distribución

Enlace reportado: https://www.youtube.com/watch?v=K8jWXGm57TU

La 1.4.4 forzaba `web_embedded` al analizar y descargar videos de YouTube. En la prueba del 23 de octubre, ese cliente solo ofreció el formato 18: 640×360 a 30 FPS. yt-dlp avisó que las demás URLs estaban ausentes por el modo SABR. No era una recodificación: el catálogo ya llegaba limitado antes de elegir la descarga. El cliente predeterminado ofreció 2560×1440 a 60 FPS y 1920×1080 a 60 FPS.

La corrección permite a yt-dlp usar sus clientes predeterminados; el cliente incrustado solo permanece como alternativa ante errores de acceso. Los reintentos de descarga mantienen los límites de resolución y FPS seleccionados.

También se corrigió Modo rápido:
- 1080×1920 se reconoce como 1080p, no 1920p. Antes, pedir 1080p podía elegir 360×640.
- Resolución y FPS tienen prioridad sobre la compatibilidad del códec.
- Una calidad numérica no disponible muestra un error antes de descargar una inferior; el usuario puede elegir otra calidad o Mejor disponible.
- Las preferencias nuevas usan Mejor disponible; las preferencias guardadas explícitamente se conservan.
- La comprobación del archivo descargado valida resolución y FPS antes de marcarlo como completado. No fuerza recodificación.

Se descargaron muestras reales de aproximadamente 10 segundos con el controlador de la aplicación, usando copia de streams:
- Mejor disponible: formato 623 + audio AAC, MP4 con VP9, 2560×1440, 60000/1001 FPS, 17.189.454 bytes.
- 1080p: formato 312 + audio AAC, MP4 con H.264, 1920×1080, aproximadamente 59,94 FPS, 7.346.914 bytes.

Las muestras comprueban el enlace y la conexión del equipo de prueba; no garantizan el catálogo que YouTube entregue a todas las cuentas o regiones. La corrección aún no tiene un instalador público, por el incidente de Defender descrito en `defender-1.4.3-review.md`.

Validación automatizada: 205 pruebas aprobadas de selección de calidad, controlador Qt, Modo rápido, ausencia de recodificación implícita, descargas de X, núcleo y compatibilidad del actualizador. Antes de la corrección se reprodujeron nueve fallos con los nuevos casos de regresión.
