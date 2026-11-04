# Corrección local de Xomacito 1.4.7 — 4 de noviembre de 2026

Este parche corrige la interfaz del **instalador Windows 1.4.7**. No es un instalador nuevo ni una publicación automática. Comprueba el SHA-256 del ejecutable y de todos los archivos afectados antes de aplicar cambios; rechaza otras compilaciones.

## Cambios

- Una fila de navegación: **Cajas · Mis gatos · Temas**. Se eliminan los dos botones superiores GATOS/TEMAS.
- Cambiar de paleta conserva la imagen y su opacidad. La imagen recién seleccionada empieza al 50 %, mientras que cancelar el selector conserva los ajustes anteriores.
- Vista previa con la proporción de la ventana, arrastre, zoom, posición horizontal/vertical, rellenar, imagen completa y restablecer encuadre. Vista previa y fondo comparten el mismo renderizador y ajustes persistentes.
- Botón **Para Premiere** en Descargar. Selecciona el servicio existente de preparación compatible, desactiva los presets de conversión manual y conserva la resolución y los FPS elegidos.
- Recuperación del selector **Destino del video** en Modo rápido → **Destino / convertir** (muestra **Premiere ✓** cuando está seleccionado). La interfaz publicada en 1.4.7 lo había ocultado.

## Aplicar o restaurar

Cierra Xomacito. Desde PowerShell en esta carpeta:

```powershell
./Apply-Hotfix.ps1 -InstallationPath 'D:/Xomacito' -CheckOnly
./Apply-Hotfix.ps1 -InstallationPath 'D:/Xomacito'
```

Sustituye la ruta si tu instalación está en otra carpeta. Los originales se conservan en `hotfix-backup-2026-11-04`, dentro de la instalación. Para restaurarlos, con la aplicación cerrada:

```powershell
./Apply-Hotfix.ps1 -InstallationPath 'D:/Xomacito' -Restore
```

El script modifica exclusivamente los archivos QML del manifiesto. No cambia los datos de gatos, cuenta, biblioteca o descargas. No cambia automáticamente las preferencias de salida ni la opacidad de imágenes existentes. En la reparación local solicitada se eligió además **Premiere · alta calidad** para Descargar/Modo rápido y se recuperó al 50 % el fondo que estaba al 0 %, con copia previa de la configuración fuera de este paquete.

## Por qué no basta con instalar nightly

`av01` identifica AV1; `vp09` identifica VP9. MP4 es el contenedor y no convierte estos códecs en H.264. El canal [nightly de yt-dlp](https://github.com/yt-dlp/yt-dlp#update) incorpora correcciones recientes para descargar contenido; no sustituye la conversión multimedia de FFmpeg. El proyecto recomienda nightly para incidencias de extracción, pero no se necesita cambiar de motor para corregir este caso de importación.

La salida **Premiere · alta calidad** ya disponible en Xomacito usa FFmpeg: AV1/VP9 SDR de 8 bits → H.264 CRF 18; HDR/10 bits o transparencia → ProRes cuando corresponde. La conversión puede tardar y aumentar el tamaño; H.264 CRF 18 es compresión con pérdida de alta calidad. El original se conserva. [Formatos admitidos por Adobe](https://helpx.adobe.com/premiere/desktop/organize-media/import-files/supported-file-formats.html).

## Error de Unicode al registrar la conversión

Durante el diagnóstico se inició la aplicación con stdout redirigido a un archivo. El registro del comando FFprobe usó la codificación ANSI de Windows y falló al imprimir el selector de emoji U+FE0F presente en el nombre del video. El error `charmap` se produjo en el registro, antes de convertir; no indica un fallo del códec.

La instalación se volvió a iniciar normalmente, sin redirigir stdout. En el fuente se añadió `src/core/diagnostics.py` y se aplicó a los mensajes de `processor.py`: los caracteres no representables se escapan sólo en el registro; las rutas y argumentos reales conservan Unicode. También se tolera la ausencia o cierre del destino de diagnóstico. **Esta protección Python está en el parche de código y requiere una nueva compilación; el ZIP QML no modifica el ejecutable instalado.**

## Publicación y mantenimiento

La [release v4.0.47](https://github.com/Strike2911/Xomacito/releases/tag/v4.0.47) distribuye 1.4.7, pero su tag apunta a `d5426f7`, cuyo `main.py` todavía declara 1.4.6. No se encontró el fuente Python completo de la compilación instalada. Por eso esta carpeta contiene las versiones QML completas recuperadas de la instalación y corregidas, sin sustituir el EXE ni retroceder al código 1.4.6.

En el Python de 1.4.7, `ThemeController.setTheme()` llama a `restoreThemeDefaults()`, que borra `custom_wallpaper` y `custom_wallpaper_opacity`. `CustomThemePage.selectPalette()` conserva la imagen efectiva mediante los métodos públicos `setWallpaper()` y `setWallpaperOpacity()`. Eso crea una copia optimizada local de la imagen al cambiar de paleta. Cuando se recupere el fuente de esa versión, debe corregirse `setTheme()` para restablecer sólo los colores y establecer 0.5 al seleccionar una imagen nueva; entonces se podrá retirar el adaptador QML.

El encuadre se guarda mediante Qt Settings en la categoría `WallpaperLayout`, con la organización/aplicación existentes. Estos ajustes son globales, no forman parte de los presets de temas guardados.

**Antes de una release pública:** sincronizar el fuente completo 1.4.7 con GitHub, integrar estos cambios allí y reconstruir/verificar el instalador. Una actualización posterior puede reemplazar este parche. No se cambió ningún tag ni se publicó una actualización automática.

## Validación

- 83 pruebas aprobadas: preparación para Premiere, conservación del original, selección/calidad de video, flujo rápido, geometría/preferencias de Descargar y registro Unicode. Incluyen conversiones reales AV1 y VP9 con nombres que contienen U+FE0F, emoji y japonés bajo stdout CP1252 estricto; también recorte, remultiplexado y HDR con FFmpeg instalado.
- Instalador del parche probado en una copia aislada: verificar, aplicar, verificar otra vez, restaurar los originales byte por byte y rechazar archivos modificados. Los finales de línea de esta carpeta se fijan en LF para conservar las sumas del manifiesto al clonar en Windows.
- QML cargado sin errores. Prueba adicional contra el `ThemeController` real extraído del EXE 1.4.7: cambio de paleta conserva imagen/opacidad; nueva imagen al 50 %; cancelar no cambia ajustes; zoom/posición compartidos; geometría a 960, 1280 y 1600 px; sin advertencias QML. Requiere Python 3.12, PySide6, Pillow, PyInstaller y las dependencias del proyecto:

```powershell
python patches/1.4.7/verify_hotfix.py 'D:/Xomacito'
```

- Clip reportado convertido completamente: AV1 → H.264, 3840×2160, 60 fps, 1572 fotogramas, audio AAC estéreo y duración del contenedor de 26.261769 s conservados; 39,929,990 → 66,271,299 bytes. El original no se modificó. El video no forma parte de este paquete.
- La aplicación instalada reinició con el parche, con el fondo visible y la navegación compacta. El usuario detuvo el control de ventanas con Escape; la revisión posterior se hizo mediante pruebas aisladas.
- **Importación/reproducción dentro de Premiere no verificadas:** Premiere estaba abierto, pero su MCP Bridge no estaba conectado. La validación multimedia no equivale a una prueba del importador Adobe.
