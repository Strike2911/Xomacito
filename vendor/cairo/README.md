# Runtime nativo de Cairo

Estas DLL se conservan de forma explícita porque CairoSVG las carga mediante
`ctypes` y PyInstaller no puede detectarlas automáticamente. Son dependencias
de compilación y ejecución de las herramientas vectoriales de Xomacito.
