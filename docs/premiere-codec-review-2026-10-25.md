# Revisión de calidad e importación en Premiere — 25 de octubre de 2026

Estado: corrección local sobre la fuente de 1.4.5. No publicada ni instalada como nueva versión.

## Fallo reproducido

Enlace reportado: https://www.youtube.com/shorts/tVag5WaWdGM

El archivo «Your Minecraft Dog Deserves This Cozy Dog House» se descargaba como MP4 con video VP9 y audio AAC. MP4 identifica el contenedor; no garantiza que Premiere admita el códec. El mensaje `vp09` del usuario corresponde a VP9. Cambiar la extensión o remultiplexar no convierte ese video en H.264.

La corrección de calidad de 1.4.5 conservaba los formatos de alta resolución, pero el puente a Premiere enviaba sus rutas sin comprobar los códecs. Además, la cola conservaba selectores antiguos que priorizaban MP4 o el primer formato marcado compatible, aunque ofreciera menor resolución.

## Cambios

- Servicio común `premiere_media` para inspeccionar pistas reales, elegir la conversión y validar el resultado. Lo usan Descargar, Modo rápido, recortes y preparación desde Biblioteca.
- Elección explícita **Original · sin convertir** / **Premiere · alta calidad**. Seleccionar Premiere desactiva los presets de conversión manual para evitar conversiones dobles. Un preset manual sigue pudiendo alterar calidad; la interfaz lo indica.
- VP9/AV1 SDR de 8 bits se preparan en H.264 CRF 18, sin reducir dimensiones ni FPS. HDR/10 bits, transparencia y tamaños impares usan ProRes; ocupan más espacio. Los archivos de más de 10 bits que necesiten conversión automática se rechazan con explicación.
- Los archivos compatibles pasan sin recodificación. Cuando basta con cambiar contenedor o audio, se copia la pista de video. Las pistas de audio se conservan o convierten manteniendo sus canales.
- Original conservado, temporales fuera del alcance de autoimportación y publicación de la copia sólo después de verificar resolución, FPS, duración, fotogramas disponibles, color, proporción de píxel y pistas de audio. Error o cancelación elimina únicamente los temporales del trabajo.
- Preparación serial y cancelable, codificador limitado a cuatro hilos como máximo y prioridad inferior a normal en Windows. Esto limita la carga, pero una conversión 4K sigue consumiendo CPU y tarda; no se implementó aceleración GPU para este perfil.
- El envío manual comprueba códecs y pide crear una copia si hace falta. Autoimportar no autoriza conversiones: omite los incompatibles e indica cómo prepararlos. Se vuelve a comprobar la identidad del proyecto antes de enviar el resultado.
- Xomacito Link 1.6.1 incorpora avisos del manifiesto de Biblioteca y explica los rechazos de importación. Paquete CCX reconstruido localmente.
- La selección nativa compatible sólo recibe preferencia con las mismas dimensiones y una cadencia equivalente. La cola ordena primero por dimensiones/FPS, sin priorizar un MP4 inferior. Las calidades explícitas de playlists contemplan videos verticales y horizontales y no incluyen una alternativa libre de menor resolución.
- Corrección del progreso inicial de FFmpeg: 1 % ya no se muestra como 100 %. Los resultados de varios fragmentos se notifican individualmente.

## Caso real comprobado

| Propiedad | Descarga original | Copia preparada |
| --- | --- | --- |
| Video | VP9 | H.264 |
| Resolución | 2160 × 3840 | 2160 × 3840 |
| FPS | ≈60 | 60 |
| Fotogramas | 4097 | 4097 |
| Duración del contenedor | 68,405986 s | 68,405986 s |
| Audio | AAC, 2 canales | AAC, 2 canales |
| Tamaño | 226.476.209 bytes | 353.568.823 bytes |

Artefactos locales no versionados: `.artifacts/premiere-short/result.json`, `reported-short.mp4`, `reported-short_Premiere.mp4` y `ssim-aligned.log`.

SSIM en los primeros 180 fotogramas alineados por índice: **0,993395**. Es una comprobación parcial de similitud, no una garantía de conversión sin pérdida ni una medición de todo el video. La copia H.264 utiliza compresión con pérdida de alta calidad.

## Validación y límites

- `python -m pytest -q --disable-warnings --tb=short`: **500 passed, 2 skipped, 6 subtests passed**. Incluye conversiones reales VP9, AV1, HDR, recortes y remultiplexado H.264; controles de cancelación, audio, calidad, preferencias y diseño QML.
- `node --check premiere-panel/index.js` y `node tests/test_premiere_bridge.cjs`: aprobados. Comprueba también deduplicación del manifiesto y rechazo informativo de archivos incompatibles conocidos.
- `python scripts/build_premiere_panel.py`: CCX 1.6.1 generado y ZIP validado.
- Interfaz de Modo rápido comprobada a 960, 1280 y 1600 píxeles de ancho.
- Se intentó abrir Premiere 2026 para probar la importación. Mostró un aviso de recuperación de un cierre anterior. **La importación y reproducción en Premiere real todavía no están verificadas.** Los tests del puente usan dobles de la API Adobe.
- La revisión cubrió selección, descarga, reintentos, cola, preparación, biblioteca y puente/panel. No equivale a certificar todos los módulos, plataformas, perfiles de códec o versiones de Premiere del proyecto.

Referencias: [Adobe: VP9](https://www.adobe.com/creativecloud/file-types/video/codec/vp9.html), [formatos admitidos por Premiere](https://helpx.adobe.com/hk_en/premiere/desktop/organize-media/import-files/supported-file-formats.html).
