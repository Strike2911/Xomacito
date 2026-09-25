# Xomacito en macOS

Se conserva el build de Windows. El nuevo build se ejecuta en macOS con Python
3.11 y genera una aplicacion para la arquitectura del interprete: arm64 o x86_64.
No es compilacion cruzada ni un bundle universal. Usa macOS 14 o posterior con
las versiones actuales de las dependencias; la version de macOS del equipo de
build puede elevar el minimo requerido por las bibliotecas de Homebrew.

## Checklist de instalacion

- [ ] Instalar las herramientas de linea de comandos de Xcode: `xcode-select --install`.
- [ ] Instalar Homebrew siguiendo https://brew.sh/ y ejecutar su instruccion `shellenv`.
- [ ] Instalar Python 3.11, Git y las herramientas nativas:

```bash
brew install python@3.11 git ffmpeg deno poppler ghostscript cairo create-dmg
brew install --cask inkscape
```

- [ ] Usar un Python y un Homebrew de la misma arquitectura. En Apple Silicon,
  preferir arm64 nativo, sin ejecutar la terminal mediante Rosetta.
- [ ] Para los motores NCNN descargados, validar la compatibilidad de la GPU y
  del paquete oficial con la Mac. Xomacito descarga los ZIP oficiales de macOS,
  conserva modelos y bibliotecas que contienen y habilita el ejecutable.
- [ ] En equipos de destino, instalar Inkscape si se necesitan sus conversiones.
  Inkscape permanece como aplicacion externa; no se copia dentro del DMG.

FFmpeg, FFprobe, Deno, Poppler, Ghostscript y Cairo se incluyen en el `.app`.
PyInstaller recolecta sus bibliotecas nativas como binarios Mach-O. Las pruebas
del build comprueban carga de Python/Qt, SVG a PDF, PDF a imagen y Ghostscript.
Los modelos de IA se descargan bajo demanda, igual que en Windows.

## Ejecutar desde el codigo

Desde la raiz del repositorio:

```bash
"$(brew --prefix python@3.11)/bin/python3.11" -m venv .tools/mac-venv
source .tools/mac-venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python main.py --self-test
python main.py
```

No hace falta copiar binarios a `bin/`. En macOS se detectan las herramientas
de Homebrew y se exponen en `~/Library/Application Support/Xomacito/bin`.
Los ajustes y modelos tambien viven en Application Support, fuera del `.app`.
Los diagnosticos de inicio se guardan en `~/Library/Logs/Xomacito-startup-error.log`.
En Mac, los botones de componentes comprueban la instalacion nativa; para
instalar o actualizar esas herramientas se usa Homebrew, no paquetes Windows.

## Icono

```bash
bash scripts/make_mac_icon.sh
```

Genera `Xomacito-icon.icns` a partir de `Xomacito-icon.ico` usando `sips` e
`iconutil`, herramientas incluidas en macOS. El `.ico` original se conserva.
El script genera todos los tamanos del iconset, incluidos los de Retina.

## Compilar

```bash
bash scripts/build_mac.sh
```

Resultados para la version actual:

- `dist/mac/Xomacito.app`
- `release/mac/Xomacito-1.2.8-arm64.dmg` o `Xomacito-1.2.8-x86_64.dmg`

El script obtiene la version de `main.py`, verifica el `.app`, comprueba su
firma local y valida el DMG. Si ya existe un DMG con el mismo nombre, se detiene
para no sobrescribirlo. Los temporales se limitan a directorios nuevos creados
por el script. El trabajo de PyInstaller vive en `.build/work/mac`.

Sin una identidad de Apple, la firma es ad hoc para pruebas locales. Para
distribucion publica sin avisos de Gatekeeper se necesita Developer ID y
notarizacion con Apple; esa publicacion no se realiza automaticamente. Se puede
pasar una identidad instalada mediante `XOMACITO_CODESIGN_IDENTITY` al build.

Las actualizaciones Mac seleccionan DMG con sufijo de arquitectura, comprueban
tamano, cabecera UDIF y SHA-256 de GitHub, y abren la imagen para que el usuario
arrastre Xomacito a Aplicaciones. No usan Inno Setup ni instalacion silenciosa.
Las releases deben contener el DMG con el nombre generado y su digest de GitHub.

## Cambios por archivo

| Archivo | Cambio limitado a compatibilidad |
| --- | --- |
| `main.py` | Recursos del bundle, datos persistentes, diagnosticos y arranque de multiprocessing en Mac. |
| `src/core/macos_runtime.py` | Deteccion de herramientas y bibliotecas Mac, rutas y comprobacion nativa. |
| `src/core/single_instance.py` | Activacion del bundle existente. El cerrojo POSIX ya funcionaba y no se modifica. |
| `src/core/notification_sound.py` | `afplay` en lugar de WinMM en Mac. |
| `src/core/setup.py` | Evita paquetes Windows en Mac; selecciona archivos NCNN macOS y aplica permisos. |
| `src/core/downloader.py` | Deno desde la ruta de Mac. |
| `src/core/ytdlp_runtime.py` | Descubre recursos del bundle y el directorio actualizable del usuario. |
| `src/core/video_upscaler.py` | Nombres nativos de FFmpeg, FFprobe y motores NCNN. |
| `src/core/image_converter.py` | Ghostscript y nombres nativos de motores NCNN. |
| `src/core/inkscape_service.py` | Detecta el ejecutable de Inkscape.app y rutas nativas. |
| `src/core/app_updater.py` | Seleccion, validacion y apertura de DMG en Mac. |
| `src/ui/download_controller.py` | Mostrar resultados en Finder. |
| `src/ui/image_controller.py` | Poppler y Upscayl nativos. |
| `src/ui/settings_controller.py` | Selector de Inkscape y estado de herramientas Mac. |
| `src/ui/settings_store.py` | Ajustes en Library/Application Support. |
| `requirements.txt` | Conserva dependencias Windows; variantes Intel de ONNX Runtime/rawpy y PyInstaller solo en Mac. |
| `.build/XomacitoMac.spec` | Nuevo bundle y dependencias nativas. |
| `scripts/build_mac.sh` | Nuevo build APP/DMG. |
| `scripts/make_mac_icon.sh` | Conversion ICO a ICNS. |
| `.gitattributes` | LF exclusivamente para los dos scripts nuevos. |
| `tests/test_macos_support.py` | Pruebas de seleccion de plataforma, descargas, digest y permisos. |
| `tests/test_core.py` | Agrega el nuevo spec Mac a la lista de archivos de build permitidos. |

No se modifican `scripts/build_release.ps1`, `.build/XomacitoInstaller.spec`,
`launcher.py` ni el icono original. `launcher.py` es el lanzador Windows; el
bundle Mac entra por `main.py`. Las APIs Win32 y el registro ya protegidos se
conservan. No se cambian filtros de formatos ni reglas de procesamiento.

ONNX Runtime 1.27.0 y rawpy 0.27.0 no publican wheels Intel para macOS/Python
3.11. Solo en Intel Mac se seleccionan ONNX Runtime 1.23.2 y rawpy 0.25.1,
que si los publican. La compatibilidad de modelos ONNX y archivos RAW concretos
debe verificarse en ambos tipos de Mac; Windows mantiene sus versiones.

## Validacion pendiente en Mac

En este checkout Windows se validaron 33 pruebas dirigidas con Python 3.12,
incluida una comparacion AST de las ramas Windows con HEAD, y la sintaxis Python
y Bash. La suite ampliada requiere dependencias de UI y binarios Windows que
no estan instalados aqui (PySide6, pillow-avif, yt-dlp, bin/ y dist/).
No se ha ejecutado el build ni la interfaz en macOS/Python 3.11; las pruebas
nativas del script deben pasar en la Mac antes de considerar validado el DMG.

- [ ] Abrir desde Finder, cerrar y volver a abrir; comprobar segunda instancia.
- [ ] Descargar audio/video, probar cookies del navegador y FFmpeg/FFprobe.
- [ ] Convertir SVG/PDF/EPS/RAW/AVIF y quitar fondo con un modelo ONNX real.
- [ ] Reescalar imagen/video con cada motor NCNN y comprobar permisos y GPU.
- [ ] Comprobar sonido, Finder, Inkscape, tema y persistencia de ajustes/modelos.
- [ ] Probar el DMG en otra Mac de la misma arquitectura sin el entorno Python.
- [ ] Validar actualizacion por DMG y reemplazo manual en Aplicaciones.

Referencias: https://pyinstaller.org/en/stable/spec-files.html,
https://pyinstaller.org/en/stable/feature-notes.html,
https://formulae.brew.sh/formula/create-dmg,
https://pypi.org/project/onnxruntime/1.23.2/#files,
https://pypi.org/project/rawpy/0.25.1/#files.
