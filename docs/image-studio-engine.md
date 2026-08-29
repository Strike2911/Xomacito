# Motor del Estudio de Imagen

Este documento registra las decisiones técnicas del rediseño. El objetivo no es
mostrar muchos nombres de modelos, sino elegir una receta local explicable y dar
al usuario una muestra antes de procesar todo el lote.

## Problemas encontrados en el motor anterior

- Solicitaba `DmlExecutionProvider` aun cuando la distribución instalaba
  `onnxruntime` de CPU. Eso hacía que «Aceleración GPU» no describiera el motor
  que realmente se estaba usando.
- La opción automática siempre escogía el mismo modelo; no analizaba el archivo.
- El postproceso ONNX normalizaba cada máscara por su mínimo y máximo. Una
  predicción incierta podía convertirse artificialmente en fondo negro y sujeto
  blanco, deteriorando transparencias y pelo.
- El reescalado de video guarda todos los fotogramas como PNG antes de comenzar.
  En videos largos esto consume mucho disco y el progreso anterior era una
  estimación basada sólo en segundos transcurridos.
- No había vista previa del resultado, estimación de resolución/memoria ni una
  explicación de por qué se había elegido un modelo.

## Arquitectura nueva

1. El análisis se realiza en un thumbnail local de hasta 512 px. No se sube el
   archivo. Mide dimensiones, detalle, contraste, saturación, compresión y, si
   OpenCV está disponible, presencia probable de rostro.
2. La receta automática elige una familia distinta para fotografía, retrato o
   ilustración. La interfaz muestra la decisión y permite reemplazarla.
3. ONNX Runtime enumera sus proveedores reales. En Windows se instala la variante
   DirectML y se usa CPU como respaldo. DirectML se configura en ejecución
   secuencial y sin patrones de memoria, como exige su documentación oficial.
4. Los perfiles Rápido, Equilibrado y Máxima calidad cambian parámetros reales:
   concurrencia NCNN, TTA y calidad/preset del codificador final.
5. «Preparar vista previa» procesa una copia reducida. El comparador arrastrable
   permite revisar el borde o el detalle antes de lanzar el lote completo.
6. El video calcula fotogramas esperados, usa PNG temporal de compresión rápida,
   informa progreso real y comprueba el espacio libre antes de comenzar.

## Modelos curados

| Caso | Modelo | Motivo |
|---|---|---|
| Fondo, uso general rápido | BiRefNet Lite | Modelo oficial pequeño; menor tiempo y memoria. |
| Fondo, máxima precisión | BiRefNet General | Mejor capacidad, pero el ONNX pesa cerca de 928 MB. |
| Retratos | BiRefNet Portrait | Ajuste específico para personas y cabello. |
| Contornos complejos | BiRefNet DIS | Prioriza detalle fino y objetos difíciles. |
| Foto real | Real-ESRGAN x4plus | Restauración ciega práctica para degradaciones reales. |
| Ilustración | Real-ESRGAN x4plus Anime | Conserva líneas y colores planos. |
| Lotes rápidos/comprimidos | Real-ESRGAN General x4v3 | Modelo pequeño; consume menos tiempo y memoria. |
| Video animado | AnimeVideo v3 | Modelo oficial optimizado para animación por fotogramas. |

BiRefNet y Real-ESRGAN usan licencias permisivas en sus repositorios oficiales.
BRIA RMBG 2.0 no se ofrece en la interfaz porque sus pesos autoalojados tienen
restricciones de uso comercial. No se debe distribuir como si fuera un modelo
libre de Xomacito.

## Limitaciones honestas

- La selección automática es una recomendación heurística, no reconocimiento
  semántico infalible. Por eso la decisión siempre queda visible y editable.
- Los ONNX oficiales de BiRefNet son más lentos que su implementación PyTorch;
  el propio proyecto reporta esa diferencia. La vista previa reducida evita pagar
  el costo completo para descubrir un ajuste incorrecto.
- El reescalado actual de video es por fotogramas. Conserva audio y mejora detalle,
  pero no puede reconstruir movimiento entre cuadros. BasicVSR++ usa propagación y
  alineamiento temporal y produce transiciones más consistentes, pero su
  implementación oficial requiere PyTorch/MMCV y pesos grandes. Incluirla hoy
  multiplicaría el instalador y dejaría fuera a muchos equipos. La interfaz no
  afirma que existe coherencia temporal cuando no existe.
- TTA en «Máxima calidad» puede multiplicar varias veces el tiempo. No siempre da
  una mejora visible; se mantiene como una decisión explícita del usuario.
- Los modelos x4 usados a salida 2x generan primero su resultado nativo y luego lo
  reducen cuando el ejecutable no ofrece una escala x2 nativa. Es más lento que un
  modelo x2, pero evita mantener variantes inestables.

## Fuentes primarias

- BiRefNet, implementación y modelos oficiales: https://github.com/ZhengPeng7/BiRefNet
- Artículo BiRefNet: https://arxiv.org/abs/2401.03407
- Real-ESRGAN, implementación oficial: https://github.com/xinntao/Real-ESRGAN
- Artículo Real-ESRGAN: https://arxiv.org/abs/2107.10833
- Real-ESRGAN NCNN/Vulkan: https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan
- BasicVSR++ (CVPR 2022): https://github.com/ckkelvinchan/BasicVSR_PlusPlus
- ONNX Runtime DirectML: https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html
- Proveedores de ONNX Runtime: https://onnxruntime.ai/docs/execution-providers/
- Progreso programático de FFmpeg: https://ffmpeg.org/ffmpeg.html

## Protocolo de calidad recomendado

Antes de declarar un modelo «mejor» se debe medir con el mismo conjunto de
archivos y hardware:

- Fondo: MAE, weighted F-measure y error de contorno; para alpha matting, SAD,
  MSE, gradiente y conectividad. Separar retratos, productos y objetos finos.
- Imagen: PSNR/SSIM cuando exista referencia, LPIPS para similitud perceptual y
  una revisión a 100 % de halos, textura inventada, texto y rostros.
- Video: métricas por fotograma más error temporal compensado por movimiento;
  revisar parpadeo, audio/sincronía, VFR y cambios de escena.
- Rendimiento: primer uso (incluye carga), usos consecutivos, pico de RAM/VRAM,
  espacio temporal y tiempo por megapíxel o fotograma.

