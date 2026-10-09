# Xomacito

Versión visible actual: **Xomacito 1.4.1**. Revisión interna de actualización: **4.0.41**.

Aplicación independiente para Windows y macOS que permite descargar, convertir y preparar contenido multimedia desde una interfaz moderna. Xomacito fue creado por **Strike** pero principalmente inspirado en Dowp hecho por Marck.

## Descargar para Windows

[![Descargar Xomacito](https://img.shields.io/badge/Descargar-Xomacito-2ea44f?style=for-the-badge&logo=windows)](https://github.com/Strike2911/Xomacito/releases/latest)

Si ya tienes Xomacito, instala [la actualización ligera 1.4.1](https://github.com/Strike2911/Xomacito/releases/download/v4.0.41/Xomacito-1.4.1-Update-Light.exe). Conserva los componentes, modelos y preferencias existentes. Para una instalación nueva, instala primero el [paquete completo 1.2.10](https://github.com/Strike2911/Xomacito/releases/download/v4.0.29/Xomacito-1.2.10-Setup.exe) y después la actualización 1.4.1. El paquete completo incluye FFmpeg y los componentes principales; los modelos de inteligencia artificial se descargan únicamente cuando se solicitan.

> Windows puede mostrar una advertencia de SmartScreen porque el instalador todavía no utiliza un certificado comercial de firma de código. Comprueba que el archivo provenga de este repositorio antes de ejecutarlo.

## Descargar para Mac — Mac Version DMG

[**Descargar DMG para Mac**](https://github.com/Strike2911/Xomacito/releases/download/v4.0.29/Xomacito-1.2.10-arm64.dmg) · [**Descargar actualización .exe para Windows**](https://github.com/Strike2911/Xomacito/releases/download/v4.0.29/Xomacito-1.2.10-Update-Light.exe)

**Xomacito 1.2.10 para Mac** incluye un instalador DMG completo para **Apple Silicon
(M1 o posterior) y macOS 26 o posterior**. No es compatible con Mac Intel.

La distribución conjunta ofrece el DMG completo de Mac, el instalador completo
`Xomacito-1.2.10-Setup.exe` y la actualización ligera
`Xomacito-1.2.10-Update-Light.exe` para Windows. El instalador completo permite
actualizar desde versiones antiguas que no reconocen paquetes ligeros.

El instalador de macOS es un DMG: ábrelo, arrastra **Xomacito** a **Applications**
y abre la aplicación desde Aplicaciones. El paquete incluye Python y las
herramientas multimedia; no necesitas instalar Homebrew para usarlo.
Los modelos de IA opcionales se descargan al solicitarlos.

El DMG tiene firma local y **no está notarizado por Apple**. Al descargarlo de
GitHub, macOS puede bloquear su primera apertura. Tras arrastrarlo a Aplicaciones,
intenta abrirlo y, si se bloquea, autoriza esa aplicación en **Ajustes del Sistema →
Privacidad y seguridad → Abrir igualmente**. No es necesario desactivar Gatekeeper.

### Trabajo realizado para macOS

- Empaquetado nativo de la interfaz Qt/QML, Python y herramientas multimedia.
- Corrección del conflicto de HarfBuzz entre las bibliotecas de imágenes y PDF.
- Comprobaciones de recursos que siguen activas en la aplicación optimizada.
- Detección del mínimo de macOS requerido por las bibliotecas incluidas.
- Validación del arranque, firma local, integridad del DMG y conversiones de video/PDF.
- Incluye las correcciones de YouTube y los cambios de personajes de Xomacito 1.2.10.

### Compilar en macOS

Para generar el instalador en un Mac con Homebrew:

```bash
brew install python@3.11 ffmpeg deno poppler ghostscript cairo harfbuzz create-dmg
bash scripts/build_mac.sh
```

El resultado se guarda en `release/mac/Xomacito-<versión>-<arquitectura>.dmg`.
La compilación es nativa para el equipo que la genera (`arm64` para Apple Silicon,
`x86_64` para Intel); no es un binario universal. Esta compilación se prueba
localmente en el Mac que la genera. El mínimo efectivo también depende de las
versiones de las herramientas nativas instaladas con Homebrew.
Sin un certificado Developer ID y notarización, el paquete tiene firma local
y macOS puede solicitar autorización al distribuirlo a otros equipos.
Los datos y modelos se guardan en `~/Library/Application Support/Xomacito`;
los errores de arranque, en `~/Library/Logs/Xomacito-startup-error.log`.

## Funciones principales

- Descarga individual y por lotes mediante yt-dlp.
- Previsualización seleccionable de canciones y videos dentro de cada playlist.
- Selector arrastrable de cantidad, miniaturas y formato de salida visible en la cola.
- Presets de conversión separados automáticamente entre audio y video.
- Etiquetas compartidas entre Descargar y Cola para organizar cada destino por color y carpeta.
- Video con audio, extracción de audio, miniaturas y subtítulos.
- Descarga de fotografías públicas de Instagram, incluidas publicaciones con `img_index`.
- Corte de fragmentos y recodificación mediante FFmpeg.
- Biblioteca Premiere compacta con arrastre de carpetas, metadatos de FFprobe, vista previa y recorte no destructivo.
- Panel UXP “Xomacito Link” con controles Spectrum, selección múltiple, lotes confirmados, importación de archivos terminados y envío de selecciones desde Premiere hacia la biblioteca.
- Conversión, optimización y procesamiento de imágenes.
- Reescalado inteligente de imágenes y videos con perfiles optimizados según el contenido.
- Removedor de fondos renovado con modelos BiRefNet para retratos, bordes finos y escenas complejas.
- Tema Strike como apariencia inicial, paletas con saturación más sobria, fondos adaptativos y colección gatuna equipable.
- Recorrido guiado breve y opcional, con ayuda contextual disponible en cada apartado desde el botón **Guía**.
- Cajas con ruleta, saldo virtual ($1.00 por cada 10 descargas válidas), regalo diario e inventario con venta de copias.
- 145 personajes con nombres estandarizados en mayúsculas y rarezas estables de 1 a 6 estrellas.
- Gatos míticos de 6 estrellas con animaciones exclusivas de desbloqueo y equipamiento.
- Auras mejorables de cinco niveles para los gatos repetidos, conservadas al vender copias.
- Cuenta comunitaria con correo de recuperación y recompensa única de 15 tiradas verificadas.
- Sonido de confirmación al finalizar una descarga.
- Instalación por usuario y desinstalador integrado en Windows.
- Instancia única: al abrir Xomacito otra vez se enfoca la ventana existente.
- Aviso de nuevas versiones al iniciar, con elección de actualizar o continuar.
- Actualización verificada: nunca reinstala si la versión actual ya es la más reciente.
- Inicio rápido con pestañas secundarias y motores pesados cargados bajo demanda.
- Renderizado visual optimizado para mantener la interfaz fluida al cambiar de tamaño.
- Las pestañas pesadas se construyen fuera de vista y aparecen completas, sin mezclar pantallas de carga con paneles parciales.

## Requisitos

- Windows: Windows 10 versión 1809 o posterior, o Windows 11.
- DMG de Mac: Apple Silicon (arm64) y macOS 26 o posterior.
- Procesador y sistema operativo de 64 bits.
- Conexión a Internet para las descargas y componentes opcionales.

## Código fuente

- `src`: lógica principal e interfaz.
- `assets`: identidad visual, iconos diarios y sonido de finalización.
- `installer`: definición del instalador y desinstalador Inno Setup.
- `scripts`: compilación, limpieza y benchmark.
- `tests`: pruebas de regresión.
- `vendor/cairo`: bibliotecas nativas requeridas por CairoSVG.
- `.build/XomacitoInstaller.spec`: definición del paquete PyInstaller.
- `premiere-panel`: panel UXP local para Adobe Premiere 25.6 o posterior.

Los runtimes de compilación, herramientas externas, modelos, builds y preferencias personales están excluidos del repositorio. Los binarios distribuidos a usuarios se publican únicamente en [GitHub Releases](https://github.com/Strike2911/Xomacito/releases).

El release se genera directamente desde `main.py` y la carpeta `src`, sin PyArmor ni otra etapa de ofuscación. `scripts/build_release.ps1` cancela la compilación si detecta envoltorios de PyArmor o si el spec deja de apuntar al código fuente legible.

La revisión interna 4.0.29 corresponde a Xomacito 1.2.10. La numeración 4.x se usa únicamente para comparar actualizaciones y no se muestra como versión pública.

Para volver a importar o ampliar la colección sin cambiar las rarezas ya asignadas:

```powershell
.\.venv\Scripts\python.exe .\scripts\import_cat_collection.py <carpeta-de-imágenes> .\assets\cat-collection
```

## Desarrollo

Consulta el [funcionamiento de Estudio, precios y migración de gatos](docs/estudio-y-economia-gatuna.md). En esta copia de desarrollo, `Probar-Xomacito.cmd` abre la aplicación desde el código actualizado.

Instala Python 3.11 y crea un entorno virtual:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para ejecutar las pruebas:

```powershell
.\.venv\Scripts\python.exe -m unittest -v tests.test_core
```

La creación del instalador requiere además PyInstaller, Inno Setup 6 o 7 y las herramientas externas esperadas bajo `bin`. El script usado para la versión oficial es:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

Consulta [docs/BENCHMARK.md](docs/BENCHMARK.md) para conocer las mediciones de arranque y las decisiones de distribución de Xomacito.

## Enlaces

- [YouTube de Strike](https://www.youtube.com/@ElStrikew)
- [Apoyar en Ko-fi](https://ko-fi.com/strikepoint)

## Modo rápido y biblioteca

**Modo rápido** ocupa su propia pestaña principal. La barra superior reúne enlaces, búsqueda en YouTube/SoundCloud, recortes, etiqueta, modo y calidad. Puedes seleccionar elementos de una playlist, bajar solo la miniatura, aplicar un preset de video y enviar el resultado a Premiere. La actividad ocupa el centro, el historial se abre a la derecha y el destino permanece abajo. Cada tarea conserva sus ajustes; cancelar o limpiar actividad no borra los archivos ni el historial. Los nombres repetidos generan una copia.

**Biblioteca** utiliza tres paneles ajustables: carpetas/colecciones, medios y previsualización/detalles. Admite lista y cuadrícula, búsqueda y filtros, orden, favoritos, colecciones persistentes, selección Ctrl/Shift y arrastre nativo de varios archivos. Indexar conserva la ubicación original. Los controles de reproducción incluyen volumen, repetición, búsqueda en el video, onda de audio y subclips independientes. El panel derecho permite enviar la selección a Premiere o insertar el medio seleccionado en el cabezal.

Las búsquedas de YouTube y SoundCloud muestran miniaturas, duración y autor en cuadrícula o lista. Pulsa **Ver** o haz doble clic para reproducir un resultado en el panel lateral mientras sigues explorando. Las casillas eligen qué descargar; abrir la vista previa no inicia una descarga ni cambia su calidad. Los resultados de búsqueda empiezan sin seleccionar, mientras que una playlist empieza seleccionada. Algunos sitios pueden requerir cookies o no ofrecer una vista previa reproducible: el panel permite reintentar o abrir el enlace original.

El reproductor compartido de búsqueda y Biblioteca permite ampliar la vista, acercar con la rueda y mover la imagen ampliada, cambiar velocidad, volumen y repetición. Atajos con el reproductor enfocado: **Espacio** reproduce/pausa, **←/→** avanza o retrocede cinco segundos, **M** silencia y **F** amplía. Al cerrar la vista previa o salir de la página se detiene la reproducción.

**Medios web** reúne Wikimedia, Openverse, Freesound, Pixabay y Pexels. Wikimedia y Openverse permiten consultas públicas; los demás requieren una clave API personal, conservada solo durante la sesión. Freesound ofrece explícitamente su previa MP3 y enlaza al original. Cada resultado muestra origen, autor y licencia; las descargas guardan un archivo de créditos junto al medio. Pixabay conserva las consultas en caché durante 24 horas. Los proveedores y sus formatos pueden limitar una descarga; el enlace al origen permanece disponible.

La organización toma como referencia [DowP](https://github.com/MarckDP/DowP), con implementación propia en Python/QML y los componentes visuales de Xomacito. La conexión con editores de esta implementación está centrada en Premiere.

Para instalar el panel y configurar el envío, consulta [Xomacito Link](premiere-panel/README.md).

## Estudio de imagen

El lienzo ocupa el centro y permite ampliar con la rueda, desplazar la imagen ampliada y comparar el original con el resultado. La barra lateral selecciona eliminación de fondo, reescalado o conversión; la lista y los ajustes quedan a la derecha. **Administrar** abre Configuración → Modelos. Los controles de GPU, suavizado, expansión de bordes, escala, tamaño de bloques, potencia y TTA se aplican al motor correspondiente.

La salida admite No Convertir, PNG, JPG/JPEG, WebP, AVIF, PDF, SVG, TIFF, ICO, ICNS y BMP. SVG contiene la imagen raster incrustada, sin vectorización. ICNS genera iconos cuadrados con relleno transparente para conservar la proporción. No Convertir conserva el formato de las imágenes raster compatibles; documentos y entradas que no pueden reexportarse se guardan como PNG con la extensión correcta. El destino y la política para archivos existentes permanecen junto al botón de procesamiento.
