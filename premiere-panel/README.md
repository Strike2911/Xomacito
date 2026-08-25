# Xomacito Link para Adobe Premiere

Panel UXP nativo 1.3.0 para Premiere 25.6 o posterior. Vincula una carpeta elegida por el usuario, recuerda el permiso mediante un token persistente, tolera subcarpetas temporales de OneDrive, importa archivos al proyecto y puede insertarlos en el cabezal de reproducción de la secuencia activa.

Durante desarrollo se carga `manifest.json` con UXP Developer Tool 2.2 o posterior. Para distribución se empaqueta como `.ccx` desde esa herramienta; el host de producción declarado es únicamente `premierepro`.
