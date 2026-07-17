# Benchmark de distribución de Xomacito 1.5.0

Medición realizada el 15 de julio de 2026 en el mismo equipo Windows, con tres
arranques por variante. El tiempo termina cuando aparece la ventana principal
`Xomacito`; después se suma la memoria de los procesos asociados.

| Métrica | Portable anterior | Instalación optimizada | Cambio |
| --- | ---: | ---: | ---: |
| Arranque promedio | 28,95 s | 8,80 s | -69,6 % |
| Procesos | 2 | 1 | -50,0 % |
| Memoria de trabajo | 151,3 MB | 137,7 MB | -9,0 % |

La mejora proviene de ejecutar directamente un build PyInstaller `one-folder`.
Se eliminan del camino de inicio el launcher secundario, el corrector de título
y la extracción temporal completa del ejecutable `one-file`.

## Comparación de distribución

Comparación orientativa con los instaladores Windows publicados más recientes
consultados el mismo día. No es un benchmark de velocidad entre equipos: los
conjuntos de funciones y dependencias no son idénticos.

| Aplicación | Tecnología o enfoque publicado | Instalador Windows |
| --- | --- | ---: |
| Xomacito 1.5.0 | Python/PyInstaller, FFmpeg, herramientas de PDF e imagen | 307,8 MB |
| Parabolic 2026.5.0 | .NET 10/WinUI, descargas concurrentes | 223,9 MB |
| Open Video Downloader 2.5.6 | Electron/Node, cola de hasta 32 videos | 80,1 MB |

Fuentes primarias: [Parabolic](https://github.com/NickvisionApps/Parabolic),
[Open Video Downloader](https://github.com/StefanLobbenmeier/youtube-dl-gui),
[modo one-folder de PyInstaller](https://pyinstaller.org/en/stable/operating-mode.html)
y [funciones de Inno Setup](https://jrsoftware.org/isinfo.php).

## Decisiones de empaquetado

- Se conservan FFmpeg/FFprobe, Deno, Ghostscript, Poppler y yt-dlp.
- Los modelos de IA, que ocupan aproximadamente 1,17 GB, quedan bajo demanda.
- La instalación es por usuario y no exige permisos de administrador.
- El desinstalador conserva las preferencias personales en `%APPDATA%\Xomacito`.
