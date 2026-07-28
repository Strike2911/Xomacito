# Xomacito 2.8 — ¡LA MP3 DE VERDAD UPDATE!!

Esta actualización corrige dos problemas del flujo de playlists:

- El análisis completo ya no resuelve por adelantado todos los formatos de cientos
  de canciones. La lista aparece de forma progresiva y cada elemento obtiene sus
  formatos justo antes de descargarse.
- El modo **Solo Audio** convierte siempre los streams WEBM/Opus de una playlist
  a un archivo MP3 real de 192 kbps mediante FFmpeg.

## Validación

- Prueba automatizada del análisis progresivo con el modo rápido desactivado.
- Prueba automatizada del postprocesador MP3 de playlists.
- Análisis real de una playlist pública de 40 elementos en menos de dos segundos.
- Descarga real desde YouTube verificada como archivo `.mp3`.

## Instalador

- `Xomacito-2.8-Setup.exe`
