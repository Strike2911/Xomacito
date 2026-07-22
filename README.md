# Xomacito

Versión actual: **Xomacito 2.0**.

Aplicación independiente para Windows que permite descargar, convertir y preparar contenido multimedia desde una interfaz moderna. Xomacito fue creado por **Strike**.

## Descargar para Windows

[![Descargar Xomacito](https://img.shields.io/badge/Descargar-Xomacito-2ea44f?style=for-the-badge&logo=windows)](https://github.com/Strike2911/Xomacito/releases/latest)

Descarga el único instalador `Xomacito-<versión>-Setup.exe` desde la versión más reciente, ejecútalo y sigue el asistente. El instalador incluye FFmpeg y los componentes necesarios para usar las funciones principales; los modelos de inteligencia artificial se descargan únicamente cuando se solicitan.

> Windows puede mostrar una advertencia de SmartScreen porque el instalador todavía no utiliza un certificado comercial de firma de código. Comprueba que el archivo provenga de este repositorio antes de ejecutarlo.

## Funciones principales

- Descarga individual y por lotes mediante yt-dlp.
- Video con audio, extracción de audio, miniaturas y subtítulos.
- Descarga de fotografías públicas de Instagram, incluidas publicaciones con `img_index`.
- Corte de fragmentos y recodificación mediante FFmpeg.
- Conversión, optimización y procesamiento de imágenes.
- Temas claros y oscuros, fondos adaptativos y gatito diario.
- Sonido de confirmación al finalizar una descarga.
- Instalación por usuario y desinstalador integrado en Windows.
- Instancia única: al abrir Xomacito otra vez se enfoca la ventana existente.
- Aviso de nuevas versiones al iniciar, con elección de actualizar o continuar.
- Actualización verificada: nunca reinstala si la versión actual ya es la más reciente.
- Inicio rápido con pestañas secundarias y motores pesados cargados bajo demanda.
- Renderizado visual optimizado para mantener la interfaz fluida al cambiar de tamaño.
- Las pestañas pesadas se construyen fuera de vista y aparecen completas, sin mezclar pantallas de carga con paneles parciales.

## Requisitos

- Windows 10 versión 1809 o posterior, o Windows 11.
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

Los runtimes de compilación, herramientas externas, modelos, builds y preferencias personales están excluidos del repositorio. Los binarios distribuidos a usuarios se publican únicamente en [GitHub Releases](https://github.com/Strike2911/Xomacito/releases).

## Desarrollo

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
