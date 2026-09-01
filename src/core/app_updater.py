"""Actualizaciones de Xomacito mediante el repositorio oficial de GitHub."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests
from packaging.version import InvalidVersion, Version


REPOSITORY = "Strike2911/Xomacito"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
REQUEST_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Xomacito-Updater",
    "X-GitHub-Api-Version": "2022-11-28",
}
MAX_INSTALLER_SIZE = 2 * 1024 * 1024 * 1024
INSTALLER_APP_ID = "{8B474FFD-6C60-4B82-889E-7DD12563E7E5}_is1"
IDEA_CONTRIBUTORS = [
    "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
    "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio", "Maog", "Zane", "Nuan",
]
PUBLIC_VERSION_BY_INTERNAL = {
    "4.0.17": "1.1",
    "4.0.16": "1.1",
    "4.0.15": "1.1",
    "4.0.14": "1.1",
}
PUBLIC_BUGFIX_NOTE = "- Arreglo de bugs de la versión 1.0."
RELEASE_NOTICES = {
    "4.0.17": {
        "eyebrow": "XOMACITO 1.1",
        "title": "Xomacito 1.1",
        "subtitle": "ARREGLO DE BUGS DE LA VERSIÓN 1.0",
        "message": "Una revisión enfocada en estabilidad y comodidad de edición.",
        "highlights": [
            "Arreglo de Bugs de la versión 1.0",
        ],
        "contributors": IDEA_CONTRIBUTORS,
        "closing": "Gracias a todos los aportadores de ideas de Xomacito 1.1.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.16": {
        "eyebrow": "XOMACITO 1.1",
        "title": "Xomacito 1.1",
        "subtitle": "ARREGLO DE BUGS DE LA VERSIÓN 1.0",
        "message": "Una revisión enfocada en estabilidad y comodidad de edición.",
        "highlights": [
            "Arreglo de Bugs de la versión 1.0",
        ],
        "contributors": IDEA_CONTRIBUTORS,
        "closing": "Gracias a todos los aportadores de ideas de Xomacito 1.1.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.15": {
        "eyebrow": "XOMACITO 1.1",
        "title": "Xomacito 1.1",
        "subtitle": "ARREGLO DE BUGS DE LA VERSIÓN 1.0",
        "message": "Una revisión enfocada en estabilidad y comodidad de edición.",
        "highlights": [
            "Arreglo de Bugs de la versión 1.0",
        ],
        "contributors": IDEA_CONTRIBUTORS,
        "closing": "Gracias a todos los aportadores de ideas de Xomacito 1.1.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.14": {
        "eyebrow": "XOMACITO 1.1",
        "title": "Xomacito 1.1",
        "subtitle": "ARREGLO DE BUGS DE LA VERSIÓN 1.0",
        "message": "Una revisión enfocada en estabilidad y comodidad de edición.",
        "highlights": [
            "Arreglo de Bugs de la versión 1.0",
        ],
        "contributors": IDEA_CONTRIBUTORS,
        "closing": "Gracias a todos los aportadores de ideas de Xomacito 1.1.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.13": {
        "eyebrow": "XOMACITO 1.0",
        "title": "Xomacito 1.0",
        "subtitle": "ARREGLO DE BUGS DE LA VERSIÓN 1.0",
        "message": "Una revisión enfocada en estabilidad y comodidad de edición.",
        "highlights": [
            "Arreglo de Bugs de la versión 1.0",
        ],
        "contributors": IDEA_CONTRIBUTORS,
        "closing": "Gracias a todos los aportadores de ideas de Xomacito 1.0.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.12": {
        "eyebrow": "XOMACITO 1.0",
        "title": "Xomacito 1.0",
        "subtitle": "ARREGLO DE BUGS DE LA VERSIÓN 1.0",
        "message": "Una revisión enfocada en estabilidad, colección y comodidad de edición.",
        "highlights": [
            "Arreglo de Bugs de la versión 1.0",
        ],
        "contributors": IDEA_CONTRIBUTORS,
        "closing": "Gracias a todos los aportadores de ideas de Xomacito 1.0.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.11": {
        "eyebrow": "XOMACITO 1.0",
        "title": "Xomacito 1.0",
        "subtitle": "ARRANQUE SEGURO Y TU PROGRESO CONSERVADO",
        "message": (
            "Esta revisión corrige el inicio de Xomacito en equipos afectados por una "
            "biblioteca incompatible incluida en la actualización anterior."
        ),
        "highlights": [
            "Qt vuelve a iniciar correctamente sin una DLL de ICU incompatible.",
            "Cada instalador valida QtCore y sus recursos antes de poder publicarse.",
            "Las tiradas, la colección y los modelos de IA conservan las correcciones de 4.0.10.",
            "PERRO ZANE permanece completamente contenido dentro de su marco circular.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio", "Strike", "Zane", "Nuan",
        ],
        "closing": "Gracias a quienes compartieron el diagnóstico de inicio de la 4.0.10.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.10": {
        "eyebrow": "XOMACITO 1.0",
        "title": "Xomacito 1.0",
        "subtitle": "TU COLECCION Y TUS MODELOS, SIEMPRE EN ORDEN",
        "message": (
            "Cada tirada se descuenta de forma definitiva y la nube conserva la colección "
            "correcta cuando inicias sesión desde otra computadora."
        ),
        "highlights": [
            "Las tiradas gastadas ya no reaparecen al sincronizar con una copia anterior.",
            "Una instalación nueva restaura gatos, duplicados, equipamiento y saldo de la cuenta.",
            "La fusión entre equipos utiliza una revisión del saldo para distinguir el progreso más reciente.",
            "PERRO ZANE queda completamente contenido dentro de su marco circular.",
            "Los modelos de IA descargados se conservan al actualizar Xomacito.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio", "Strike", "Zane", "Nuan",
        ],
        "closing": "Gracias a quienes detectaron el saldo infinito y probaron su colección en equipos nuevos.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.9": {
        "eyebrow": "XOMACITO 1.0",
        "title": "Xomacito 1.0",
        "subtitle": "TU CUENTA Y TU COLECCION VIAJAN CONTIGO",
        "message": (
            "Recuperar la contraseña vuelve a funcionar con el correo oficial de Supabase, "
            "y tu colección gatuna puede restaurarse al iniciar sesión en otro equipo."
        ),
        "highlights": [
            "El enlace de recuperación abre una página local segura para crear la nueva contraseña.",
            "La interfaz explica el enlace real y ya no solicita un código que el correo no envía.",
            "El token desaparece inmediatamente de la barra del navegador y nunca se guarda en el equipo.",
            "Gatos desbloqueados, repetidos y equipados se combinan de forma segura entre computadoras.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio", "Strike", "Zane", "Nuan",
        ],
        "closing": "Gracias a quienes reportaron la recuperación rota y probaron su colección en varios equipos.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.8": {
        "eyebrow": "XOMACITO 1.0",
        "title": "Xomacito 1.0",
        "subtitle": "RECORTES PRECISOS Y UNA BIBLIOTECA CONECTADA",
        "message": (
            "La forma de onda ahora se recupera incluso cuando el sitio rechaza su enlace "
            "temporal, y el recortador permite acercarse a cada silencio antes de exportar."
        ),
        "highlights": [
            "Forma de onda con recuperación automática mediante una copia temporal segura.",
            "Zoom de hasta 16×, navegación horizontal y enfoque directo del fragmento.",
            "Carpeta de salida clara para cada recorte y flujo compacto en Biblioteca.",
            "Xomacito Link 1.3 organiza el proyecto activo de Premiere y tolera carpetas sincronizadas.",
            "GATO STRIKE y el tema Platino reciben una presentación más elegante y distintiva.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio", "Strike", "Zane", "Nuan",
        ],
        "closing": "Gracias a quienes prueban cada herramienta y ayudan a que Xomacito 1.0 siga creciendo.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.7": {
        "eyebrow": "EDICION DEFINITIVA 1.0.7",
        "title": "Xomacito 1.0.7 Definitive Edition",
        "subtitle": "TU BIBLIOTECA Y CADA 6 ESTRELLAS TIENEN IDENTIDAD",
        "message": (
            "Xomacito Link ahora explica el flujo completo, organiza el material por tipo "
            "y espera a que cada descarga termine antes de importarla a Premiere."
        ),
        "highlights": [
            "Panel de Premiere compacto, legible y guiado para biblioteca, proyecto e importación automática.",
            "Los medios se organizan dentro de Xomacito Import por video, audio, imágenes y recortes.",
            "Cada gato de 6 estrellas recibe partículas, ritmo y silueta visual propios.",
            "Regalos especiales ligados de forma segura a la cuenta y reclamables una sola vez.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio", "Strike", "Zane", "Nuan",
        ],
        "closing": "Gracias a todos los contribuyentes que han convertido Xomacito en una herramienta para editores.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.6": {
        "eyebrow": "ACTUALIZACION LOCAL 1.0.6",
        "title": "Xomacito 1.0.6 Definitive Edition",
        "subtitle": "ZANE Y FRIDO LLEGAN A LA COLECCION",
        "message": (
            "La colección recibe dos nuevos compañeros y Xomacito Link puede mantener "
            "sincronizada la biblioteca con el proyecto activo de Premiere."
        ),
        "highlights": [
            "PERRO ZANE y Frido se incorporan como recompensas de 5 estrellas.",
            "El 26 de agosto de 2026 entrega una sola vez 10 rolleos y PERRO ZANE exclusivo.",
            "Xomacito Link crea el bin Xomacito Import y detecta medios nuevos sin duplicarlos.",
            "La biblioteca incluye un acceso directo para instalar y preparar el panel de Premiere.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio", "Strike", "Zane", "Nuan",
        ],
        "closing": "Esta compilación se instaló sólo en tu equipo; no se publicó en GitHub.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.5": {
        "eyebrow": "ACTUALIZACION LOCAL 1.0.5",
        "title": "Xomacito 1.0.5 Definitive Edition",
        "subtitle": "UNA BIBLIOTECA PENSADA PARA EDITORES",
        "message": (
            "Las herramientas conservan sus proporciones al cambiar la ventana y la "
            "biblioteca encuentra recursos por categoría, metadata y favoritos."
        ),
        "highlights": [
            "Diseño estable en ventanas panorámicas y cuadradas.",
            "Búsqueda, favoritos y categorías para SFX, música, video, imágenes y green screen.",
            "Acceso directo e inicio posterior a la instalación más compatibles con Windows.",
            "Sólo quedan visibles los perfiles estables de BiRefNet y Real-ESRGAN.",
        ],
        "contributors": ["Strike", "Mensva"],
        "closing": "Esta compilación se instaló sólo en tu equipo para validarla antes de publicarla.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.4": {
        "eyebrow": "EDICION DEFINITIVA 1.0.4",
        "title": "Xomacito 1.0.4 Definitive Edition",
        "subtitle": "UNA INTERFAZ QUE SE ADAPTA A TU PANTALLA",
        "message": (
            "Xomacito ahora conserva mejor sus proporciones en Full HD, 2K y 4K, "
            "mantiene ordenada la biblioteca y hace más suave cada descarga y revelación."
        ),
        "highlights": [
            "Escalado automático y conservador según resolución y DPI de Windows.",
            "Carpetas agrupadas, ocultables y restaurables sin borrar archivos del editor.",
            "Maullido de descarga reducido 10 dB para no interrumpir al editor.",
            "Revelación de GATO STRIKE optimizada y sin el mensaje incorrecto de BlackBull.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio",
        ],
        "closing": "Gracias por ayudarnos a hacer Xomacito más cómodo en cada espacio de edición.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.3": {
        "eyebrow": "EDICION DEFINITIVA 1.0.3",
        "title": "Xomacito 1.0.3 Definitive Edition",
        "subtitle": "MAS ESPACIO PARA EDITAR, MAS CONTROL EN TU COLA",
        "message": (
            "La biblioteca ahora trabaja como un explorador compacto, las playlists "
            "responden de verdad al elegir cantidad y la interfaz se adapta a pantallas 2K."
        ),
        "highlights": [
            "Escalado legible para pantallas 2K y 4K usadas al 100 %.",
            "Carpetas plegables, filas compactas y detalles técnicos ampliados.",
            "Selector de playlists sincronizado de 0 hasta el total real.",
            "GATO STRIKE, GATO ALE y RYKOZIO se unen a la colección; Pixelart ahora es GATO SPIKE.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako", "Ale", "Rykozio",
        ],
        "closing": "Gracias por seguir convirtiendo Xomacito en una herramienta hecha para editores.",
        "platinumCelebration": False,
        "smoothMotionPromotion": False,
    },
    "4.0.2": {
        "eyebrow": "EDICION DEFINITIVA 1.0.2",
        "title": "Xomacito 1.0.2 Definitive Edition",
        "subtitle": "TU COLA Y TUS GATOS EVOLUCIONAN",
        "message": (
            "La cola ahora responde con precisión, las cuentas recuperan su acceso con correo "
            "y los gatos repetidos convierten el platino en una colección que sigue creciendo."
        ),
        "highlights": [
            "Selector de cantidad rediseñado y arrastrable para playlists.",
            "Presets separados por audio o video, miniaturas y salida MP4 más clara.",
            "Correo de recuperación verificado y recompensa única de 15 tiradas.",
            "Auras de cinco niveles para gatos repetidos y sonidos más suaves.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako",
        ],
        "closing": "Gracias por convertir cada detalle extraño en una mejora para toda la comunidad.",
        "platinumCelebration": False,
        "smoothMotionPromotion": True,
    },
    "4.0.1": {
        "eyebrow": "EDICION DEFINITIVA 1.0.1",
        "title": "Xomacito 1.0.1 Definitive Edition",
        "subtitle": "LA VERSION DEFINITIVA V.1.0.1",
        "message": (
            "El Estudio de Imagen ahora presenta sus opciones por tarea para que puedas "
            "preparar recursos sin perderte entre ajustes tecnicos."
        ),
        "highlights": [
            "Opciones de resultado guiadas: tamano, lienzo, formato, mejora y video.",
            "El perfil inestable Modelo Generico x4 fue retirado.",
            "La mejora con IA conserva perfiles fiables con escala 2x recomendada.",
            "Los controles detallados siguen disponibles solo cuando los necesitas.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako",
        ],
        "closing": "Gracias por seguir puliendo la Definitive Edition junto a la comunidad.",
        "platinumCelebration": False,
        "smoothMotionPromotion": True,
    },
    "4.0.0": {
        "eyebrow": "EDICIÓN DEFINITIVA INSTALADA",
        "title": "Xomacito 1.0 Definitive Edition",
        "subtitle": "LA EDICIÓN DEFINITIVA DE XOMACITO",
        "message": (
            "Esta entrega consolida el descargador, la cola, el Estudio de Imagen, "
            "la colección gatuna y la comunidad en una versión preparada para seguir creciendo."
        ),
        "highlights": [
            "Actualización automática compatible con instalaciones anteriores de Xomacito.",
            "Descargas y conversión con formatos compatibles para editar y compartir.",
            "Colección, temas y personalización reunidos en la Definitive Edition.",
            "Scoreboard, rachas y progreso de la comunidad conservados en un solo flujo.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako",
        ],
        "closing": "Gracias por construir la Definitive Edition junto a la comunidad de Xomacito.",
        "platinumCelebration": True,
        "smoothMotionPromotion": True,
    },
    "3.6": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 3.6",
        "subtitle": "¡COLECCIÓN PLATINO UPDATE!!",
        "message": (
            "Xomacito cierra y abre de forma predecible, conserva el progreso de la "
            "comunidad y celebra completar la colección."
        ),
        "highlights": [
            "BLACK BULL queda centrado dentro de sus marcos y del anuncio de Smooth Motion.",
            "La X vuelve a cerrar Xomacito correctamente, incluso si el modo en segundo plano estaba activo.",
            "El scoreboard sincroniza el total exacto de gatos después de renovar la sesión de Supabase.",
            "El inicio ya no interrumpe con una ventana de acceso: el scoreboard se conecta sólo cuando tú lo decides.",
            "Completar la colección desbloquea una celebración y el tema exclusivo Platinum Duality.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako",
        ],
        "closing": "Gracias a la comunidad por ayudarnos a pulir esta versión.",
        "platinumCelebration": False,
        "smoothMotionPromotion": True,
    },
    "3.5": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 3.5",
        "subtitle": "¡THE PAPU UPDATE!!",
        "message": (
            "El acceso a la comunidad ahora llega en el momento correcto y Xomacito vuelve "
            "a primer plano correctamente cuando permanecía abierto en la bandeja."
        ),
        "highlights": [
            "El formulario de ID mantiene textos, campos y botones dentro de su tarjeta.",
            "La creación de ID aparece después del anuncio y la recompensa de BLACK BULL.",
            "Abrir Xomacito desde Inicio recupera la ventana que quedó en segundo plano.",
            "BLACK BULL conserva el sombrero y queda centrado dentro de su marco mítico.",
            "El flujo del scoreboard conserva su conexión segura mediante Supabase Auth.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako",
        ],
        "closing": "Gracias a la comunidad por seguir puliendo cada rincón de Xomacito.",
        "platinumCelebration": True,
        "smoothMotionPromotion": True,
    },
    "3.4": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 3.4",
        "subtitle": "¡RACHAS DE COMUNIDAD UPDATE!!",
        "message": (
            "La Liga de Xomacito estrena una vista más clara, celebratoria y humana: "
            "ahora puedes reconocer el progreso, la colección y la constancia de la comunidad."
        ),
        "highlights": [
            "Nuevo podio visual para descubrir a las leyendas de la comunidad.",
            "Rachas diarias con fueguito, mejor marca personal y actividad de hoy.",
            "Tu puesto, descargas y gatos aparecen juntos sin perderse en la tabla.",
            "Resumen de jugadores activos y progreso total de la comunidad.",
            "La actividad se calcula de forma segura sin publicar fechas exactas ni contraseñas.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako",
        ],
        "closing": "Gracias a toda la comunidad por mantener encendida la racha de Xomacito.",
        "platinumCelebration": True,
        "smoothMotionPromotion": True,
    },
    "3.3": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 3.3",
        "subtitle": "¡SMOOTH MOTION UPDATE!!",
        "message": (
            "La alianza creativa recibe un acabado visual más claro para que la recompensa "
            "de BLACK BULL se sienta mítica, legible y bien integrada en Xomacito."
        ),
        "highlights": [
            "La recompensa de BLACK BULL ahora aparece completa, centrada y legible en cualquier pestaña.",
            "El retrato de BLACK BULL ocupa mejor su marco mítico sin verse pequeño.",
            "La tarjeta de Smooth Motion utiliza el avatar circular preparado para Xomacito.",
            "Se conserva el desbloqueo automático de BLACK BULL 6★ al visitar Smooth Motion.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako",
        ],
        "closing": "Gracias a BlackBull y Smooth Motion por seguir impulsando esta alianza para creadores.",
        "platinumCelebration": True,
        "smoothMotionPromotion": True,
    },
    "3.2": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 3.2",
        "subtitle": "¡BLACK BULL EDITION!!!",
        "message": (
            "La colección mítica estrena una nueva leyenda, fondos con identidad propia "
            "y una alianza especial para creadores que trabajan en After Effects."
        ),
        "highlights": [
            "BLACK BULL llega al gacha como personaje mítico de 6★ con nombre, sonido y estilo propios.",
            "BLACK BULL, GATO MAGO, GATO PLAYERA y GATO ZARKING tienen fondos animados diferentes.",
            "Cada personaje de 6★ conserva una animación exclusiva al desbloquearlo y equiparlo.",
            "Desbloquear un personaje de 5★ o 6★ ahora confirma también un nuevo tema de Xomacito.",
            "Visita Smooth Motion desde el anuncio especial y BLACK BULL 6★ se añadirá a tu colección.",
            "Smooth Motion reúne curvas, texto, composición, FX, color, guías y exportación para After Effects.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d", "Gako",
        ],
        "closing": "Gracias a BlackBull y Smooth Motion por esta alianza especial para la comunidad creativa.",
        "platinumCelebration": True,
        "smoothMotionPromotion": True,
    },
    "3.1": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 3.1",
        "subtitle": "¡GAKO NOS COMENTÓ EN RECURSOS!!",
        "message": (
            "Una actualización centrada en conservar tu lugar, recordar tus preferencias "
            "y hacer que imágenes y videos difíciles se procesen con mayor seguridad."
        ),
        "highlights": [
            "La selección de playlists conserva la posición: ya no vuelve al primer elemento.",
            "La apariencia y la paleta elegidas permanecen después de reiniciar Xomacito.",
            "El reescalado de video reintenta con memoria segura en equipos AMD y de VRAM limitada.",
            "El convertidor incorpora JPEG como formato visible y compatible.",
            "Pinterest e Instagram admiten imágenes directas y publicaciones con varias imágenes.",
            "El descargador activa el modo Imágenes y guarda todos los elementos de un carrusel.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d",
        ],
        "closing": "Gracias a Gako por comentar en Recursos y regalarnos un momento histórico del proyecto.",
        "platinumCelebration": True,
    },
    "3.0": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 3.0",
        "subtitle": "¡LA GACHA MÍTICA UPDATE!!",
        "message": (
            "El gacha entra en su era mítica con tres gatos de seis estrellas, "
            "revelaciones más espectaculares y una progresión justa para las colas."
        ),
        "highlights": [
            "GATO PLAYERA y GATO ZARKING llegan como nuevos gatos míticos de 6★.",
            "GATO MAGO, GATO PLAYERA y GATO ZARKING tienen animaciones de equipamiento únicas.",
            "Cada rareza estrena una identidad sonora de revelación más clara y emocionante.",
            "Partículas, portales, confeti prismático y escáneres digitales enriquecen el desbloqueo.",
            "Una cola completa cuenta como una sola descarga para el progreso del gacha.",
            "La colección crece a 144 gatos, todos con nombres estandarizados en mayúsculas.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d",
        ],
        "closing": "Gracias a Playera y Zarking por convertirse oficialmente en leyendas míticas de Xomacito.",
        "platinumCelebration": True,
    },
    "2.9": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.9",
        "subtitle": "¡LA EDUARDITO UPDATE!!",
        "message": (
            "La cola ahora enseña lo que contiene cada playlist antes de descargar, "
            "organiza los destinos con etiquetas y deja las opciones técnicas en segundo plano."
        ),
        "highlights": [
            "Previsualización completa y seleccionable de canciones y videos dentro de cada playlist.",
            "Controles Todos y Ninguno para decidir rápidamente qué elementos procesar.",
            "Modo y calidad se guardan correctamente por cada playlist seleccionada.",
            "Etiquetas con color y carpeta disponibles también en la Cola.",
            "Interfaz simplificada con opciones avanzadas plegables y un destino visual más claro.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike",
            "BlackBull", "Eduardito3d",
        ],
        "closing": "Gracias a Eduardito3d por ayudar a convertir la cola en un flujo más claro y controlable.",
        "platinumCelebration": True,
    },
    "2.8": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.8",
        "subtitle": "¡LA MP3 DE VERDAD UPDATE!!",
        "message": (
            "La cola ahora analiza playlists grandes sin hacerte esperar por cada canción "
            "y entrega archivos de audio reales, compatibles y listos para reproducir."
        ),
        "highlights": [
            "Análisis progresivo de playlists incluso con el modo rápido compatible desactivado.",
            "Los formatos completos se consultan sólo cuando cada elemento va a descargarse.",
            "Solo Audio en playlists convierte siempre el stream WEBM de origen a MP3 real.",
            "Salida MP3 a 192 kbps mediante FFmpeg, compatible con reproductores y editores.",
            "La comprobación final sigue validando que cada archivo exista antes de marcar éxito.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike", "BlackBull",
        ],
        "closing": "Gracias por seguir cazando esos WEBM disfrazados de audio.",
        "platinumCelebration": True,
    },
    "2.7": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.7",
        "subtitle": "¡LA BLACKBULL PLAYLIST UPDATE!!",
        "message": (
            "Las playlists ahora se descargan con comprobación real de cada archivo, "
            "sin volver a declarar éxito cuando la carpeta quedó vacía."
        ),
        "highlights": [
            "Xomacito reconstruye enlaces incompletos de los elementos de una playlist.",
            "Cada descarga se valida en disco antes de contarla como completada.",
            "Los fallos parciales muestran cuántos archivos terminaron y cuántos fallaron.",
            "Una playlist vacía ya no aparece en verde: conserva el error para poder reintentar.",
            "La celebración con confeti confirma que Zarking se platinó Xomacito, ahora con SFX.",
        ],
        "contributors": [
            "Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike", "BlackBull",
        ],
        "closing": "Gracias a BlackBull por encontrar el fallo de playlists y ayudar a cerrarlo.",
        "platinumCelebration": True,
    },
    "2.6": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.6",
        "subtitle": "¡LA PLATINO GACHA UPDATE!!",
        "message": (
            "La colección gatuna crece, estrena una categoría mítica de seis estrellas "
            "y celebra a quienes ya completaron el Xomacito original."
        ),
        "highlights": [
            "37 gatos nuevos se unen al gacha: ahora hay 142 para coleccionar.",
            "Todos los nombres están estandarizados en mayúsculas.",
            "Nueva rareza mítica de 6★ con efectos visuales propios.",
            "GATO MAGO debuta como el primer 6★ con animaciones arcanas exclusivas.",
            "Rarezas revisadas para GATO DIOS, GATO DETECTIVE, GATO PIXELART y otros favoritos.",
        ],
        "contributors": ["Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking", "Spike"],
        "closing": "Gracias a Spike y a toda la comunidad por llevar el gacha mucho más lejos.",
        "platinumCelebration": True,
    },
    "2.5": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.5",
        "subtitle": "¡LA PAPU UPDATE!!",
        "message": (
            "La descarga de audio y el Estudio de Imagen ahora respetan exactamente "
            "lo que eliges: formato, portada, arrastre y carpeta de salida."
        ),
        "highlights": [
            "Los presets MP3 generan MP3 reales incluso al importar OGG u otros audios locales.",
            "Arrastra y suelta imágenes directamente en el Estudio de Imagen.",
            "El removedor de fondo guarda el resultado en la carpeta de salida seleccionada.",
            "Nueva opción contextual para incluir la miniatura como portada del audio.",
            "Elige en Configuración si el Explorador se abre al terminar una descarga.",
        ],
        "contributors": ["Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking"],
        "closing": "Gracias por seguir probando Xomacito y convertir cada detalle raro en una mejora.",
    },
    "2.4": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.4",
        "subtitle": "¡LA ZARKING UPDATE!",
        "message": (
            "El Estudio de Imagen estrena herramientas más claras y potentes, "
            "mientras las descargas ahora resisten correctamente títulos, idiomas "
            "y símbolos que antes podían chocar con la codificación de Windows."
        ),
        "highlights": [
            "Nuevo reescalado inteligente de imágenes con perfiles según el contenido.",
            "Reescalado de video 2× y 4× con salida MP4 y audio conservado.",
            "Removedor de fondos mejorado con modelos BiRefNet especializados.",
            "Estudio de Imagen reorganizado, compacto y más fácil de entender.",
            "Descargas protegidas contra errores Unicode de la consola de Windows.",
        ],
        "contributors": ["Jorge", "Xomas", "Megas", "Playera", "Mensva", "Zarking"],
        "closing": "Gracias a Zarking y a todos los colaboradores por probar, proponer y mejorar Xomacito.",
    },
    "2.3": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.3",
        "subtitle": "¡LA PREMIERE READY UPDATE!!",
        "message": (
            "La recodificación vuelve a funcionar de forma confiable y Xomacito "
            "prepara resultados MP4 más compatibles con Premiere. Encontrar el archivo "
            "terminado ahora también es inmediato."
        ),
        "highlights": [
            "Recodificación reparada para entradas MKV y salidas MP4.",
            "Audio AAC/M4A prioritario para evitar MKV cuando los streams lo permiten.",
            "Temporales y contenedores FFmpeg validados en todos los flujos.",
            "El botón Resultado abre la ubicación y selecciona el archivo.",
            "El Explorador se abre automáticamente al terminar una descarga.",
        ],
        "contributors": ["Jorge", "Xomas", "Megas", "Playera", "Mensva"],
        "closing": "Gracias por seguir aportando ideas y pruebas al proyecto.",
    },
    "2.2": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.2",
        "subtitle": "¡LA MIAU UPDATE!!",
        "message": (
            "Ahora cada descarga y cada revelación del gacha tienen una respuesta "
            "sonora clara, mientras el instalador explica su progreso desde el primer segundo."
        ),
        "highlights": [
            "Nuevo maullido al completar una descarga.",
            "Cinco efectos de revelación, uno para cada rareza del gacha.",
            "Sonidos asíncronos que no bloquean ni ralentizan la interfaz.",
            "Actualizador más claro y con menos espera al preparar la instalación.",
        ],
        "contributors": ["Jorge", "Xomas", "Megas", "Playera"],
        "closing": "Gracias por seguir aportando ideas al proyecto.",
    },
    "2.1": {
        "eyebrow": "ACTUALIZACIÓN INSTALADA",
        "title": "Xomacito 2.1",
        "subtitle": "LA XOMACITO KILLER UPDATE!!",
        "message": (
            "Xomacito dio el salto a una interfaz más rápida, limpia y fluida, "
            "manteniendo todas sus herramientas en un espacio más cómodo."
        ),
        "highlights": [
            "Nueva interfaz Qt Quick, más suave y responsiva.",
            "Pantalla principal compacta, incluso en 1280 × 720.",
            "Temas instantáneos y pegado automático de enlaces.",
            "Descargas, recodificación e imagen con el flujo completo.",
            "¡Nuevo sistema de GACHA! Desbloquea gatos y personaliza tu avatar.",
        ],
        "contributors": ["Jorge", "Xomas", "Megas", "Playera"],
        "closing": "Gracias por ser los principales contribuyentes de ideas del proyecto.",
    },
    "1.6.4": {
        "title": "Xomacito 1.6.4 — ¡Actualización instalada!",
        "message": (
            "Playera encontró un fallo en donde la recodificación no "
            "funcionaba correctamente :v\n\n"
            "Importante para videos MOV con transparencia:\n"
            "• ProRes 422 Proxy no admite canal alfa y elimina la transparencia.\n"
            "• Xomacito ahora selecciona ProRes 4444 Liviano (Transparencia), "
            "que conserva el alfa y reduce el peso.\n"
            "• La aplicación bloquea perfiles incompatibles para que el alfa no "
            "se pierda por accidente.\n\n"
            "ᗧ • • •  VIVA LA GRASA!!! :V"
        ),
    }
}


class AppUpdateError(RuntimeError):
    """Error recuperable durante la comprobación o descarga de una versión."""


def build_update_prompt(update_info: dict, current_version: str) -> str:
    """Construye una alerta pública sin exponer la revisión interna ni su hash."""
    public_version = str(update_info.get("public_version") or current_version or "1.1")
    return (
        f"Xomacito {public_version}\n\n"
        f"{PUBLIC_BUGFIX_NOTE}\n\n"
        "¿Quieres descargarla e instalarla ahora?\n\n"
        "Si eliges Sí, Xomacito verificará el instalador, se cerrará "
        "durante la actualización y volverá a abrirse al terminar."
    )


def _parsed_version(value: str) -> Version:
    normalized = str(value or "").strip()
    if normalized.lower().startswith("v"):
        normalized = normalized[1:]
    try:
        return Version(normalized)
    except InvalidVersion as error:
        raise AppUpdateError(f"Versión no válida: {value!r}") from error


def release_notice_for_version(current_version: str) -> dict | None:
    """Devuelve el aviso que debe mostrarse una vez al instalar una versión."""
    try:
        normalized = str(_parsed_version(current_version))
    except AppUpdateError:
        return None
    return RELEASE_NOTICES.get(normalized)


def has_existing_installation() -> bool:
    """Detecta una instalación administrada; una copia portable no cuenta como instalada."""
    override = str(os.environ.get("XOMACITO_EXISTING_INSTALL") or "").strip().casefold()
    if override in {"1", "true", "yes"}:
        return True
    if override in {"0", "false", "no"}:
        return False
    if os.name != "nt":
        return False
    try:
        import winreg

        key_path = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{INSTALLER_APP_ID}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            install_location, _kind = winreg.QueryValueEx(key, "InstallLocation")
        return (Path(str(install_location)) / "Xomacito.exe").is_file()
    except (ImportError, FileNotFoundError, OSError):
        pass
    default_executable = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Xomacito" / "Xomacito.exe"
    return default_executable.is_file()


def _select_installer_asset(assets: list[dict], prefer_light: bool = False) -> dict | None:
    uploaded = [asset for asset in assets if asset.get("state", "uploaded") == "uploaded"]
    installers = [
        asset for asset in uploaded
        if str(asset.get("name", "")).casefold().endswith(".exe")
        and "xomacito" in str(asset.get("name", "")).casefold()
    ]
    light = [asset for asset in installers if "light" in str(asset.get("name", "")).casefold()]
    full = [
        asset for asset in installers
        if "setup" in str(asset.get("name", "")).casefold()
        and "light" not in str(asset.get("name", "")).casefold()
    ]
    if prefer_light and light:
        return light[0]
    if full:
        return full[0]
    return None


def _official_installer_url(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    expected_prefix = f"/{REPOSITORY}/releases/download/".casefold()
    return (
        parsed.scheme.casefold() == "https"
        and parsed.hostname is not None
        and parsed.hostname.casefold() == "github.com"
        and parsed.path.casefold().startswith(expected_prefix)
        and parsed.path.casefold().endswith(".exe")
    )


def check_for_app_update(
    current_version: str,
    session=None,
    timeout: float = 12.0,
    prefer_light: bool | None = None,
) -> dict:
    """Devuelve información de la última versión estable sin provocar downgrades."""
    try:
        current = _parsed_version(current_version)
        client = session or requests
        response = client.get(LATEST_RELEASE_API, headers=REQUEST_HEADERS, timeout=timeout)
        response.raise_for_status()
        release = response.json()

        latest_text = str(release.get("tag_name", "")).strip()
        latest = _parsed_version(latest_text)
        normalized_latest = str(latest)
        update_available = latest > current
        result = {
            "update_available": update_available,
            "current_version": str(current),
            "latest_version": normalized_latest,
            "public_version": PUBLIC_VERSION_BY_INTERNAL.get(normalized_latest, ""),
            "release_url": release.get("html_url") or RELEASES_URL,
            "release_notes": PUBLIC_BUGFIX_NOTE,
        }

        if not update_available:
            return result

        use_light = has_existing_installation() if prefer_light is None else bool(prefer_light)
        asset = _select_installer_asset(list(release.get("assets") or []), prefer_light=use_light)
        if not asset:
            return {
                **result,
                "error": "La versión nueva no contiene el instalador oficial de Xomacito.",
            }

        installer_url = str(asset.get("browser_download_url") or "")
        if not _official_installer_url(installer_url):
            return {
                **result,
                "error": "GitHub devolvió una dirección de instalador no reconocida.",
            }

        installer_size = int(asset.get("size") or 0)
        if installer_size <= 0 or installer_size > MAX_INSTALLER_SIZE:
            return {
                **result,
                "error": "El tamaño publicado del instalador no es válido.",
            }

        installer_sha256 = _expected_sha256(str(asset.get("digest") or ""))
        if not installer_sha256:
            return {
                **result,
                "error": "La versión nueva no incluye una huella SHA-256 verificable.",
            }

        return {
            **result,
            "installer_url": installer_url,
            "installer_name": str(asset.get("name") or "Xomacito-Setup.exe"),
            "installer_size": installer_size,
            "installer_digest": f"sha256:{installer_sha256}",
            "installer_kind": "light" if "light" in str(asset.get("name") or "").casefold() else "full",
        }
    except Exception as error:
        if isinstance(error, AppUpdateError):
            message = str(error)
        else:
            message = f"No se pudo consultar la versión más reciente: {error}"
        return {
            "update_available": False,
            "current_version": str(current_version),
            "error": message,
        }


def _expected_sha256(digest: str) -> str | None:
    match = re.fullmatch(r"sha256:([0-9a-fA-F]{64})", str(digest or "").strip())
    return match.group(1).lower() if match else None


def download_installer(
    update_info: dict,
    destination: str | Path | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
    session=None,
) -> Path:
    """Descarga el setup completo y valida tamaño, formato PE y SHA-256."""
    installer_url = str(update_info.get("installer_url") or "")
    if not _official_installer_url(installer_url):
        raise AppUpdateError("La dirección del instalador no pertenece al repositorio oficial.")

    expected_size = int(update_info.get("installer_size") or 0)
    if expected_size <= 0 or expected_size > MAX_INSTALLER_SIZE:
        raise AppUpdateError("El tamaño esperado del instalador no es válido.")

    version_text = re.sub(r"[^0-9A-Za-z._-]+", "-", str(update_info.get("latest_version") or "new"))
    if destination is None:
        update_dir = Path(tempfile.gettempdir()) / "Xomacito" / "updates"
        # Cada intento recibe su propio nombre. Un setup anterior puede seguir
        # abierto unos segundos y Windows no permite reemplazarlo en ese estado.
        attempt_id = uuid.uuid4().hex[:12]
        destination_path = update_dir / f"Xomacito-{version_text}-Setup-{attempt_id}.exe"
    else:
        destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = destination_path.with_suffix(destination_path.suffix + ".part")
    partial_path.unlink(missing_ok=True)

    client = session or requests
    response = None
    downloaded = 0
    hasher = hashlib.sha256()
    try:
        response = client.get(
            installer_url,
            headers={"User-Agent": REQUEST_HEADERS["User-Agent"]},
            stream=True,
            timeout=(12, 90),
        )
        response.raise_for_status()
        with partial_path.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > expected_size or downloaded > MAX_INSTALLER_SIZE:
                    raise AppUpdateError("La descarga superó el tamaño publicado por GitHub.")
                output.write(chunk)
                hasher.update(chunk)
                if progress_callback:
                    progress_callback(downloaded, expected_size)

        if downloaded != expected_size:
            raise AppUpdateError(
                f"La descarga quedó incompleta ({downloaded} de {expected_size} bytes)."
            )
        with partial_path.open("rb") as downloaded_file:
            if downloaded_file.read(2) != b"MZ":
                raise AppUpdateError("El archivo descargado no es un instalador válido de Windows.")

        expected_digest = _expected_sha256(update_info.get("installer_digest", ""))
        if not expected_digest:
            raise AppUpdateError("No hay una huella SHA-256 válida para verificar el instalador.")
        if hasher.hexdigest().lower() != expected_digest:
            raise AppUpdateError("La verificación SHA-256 del instalador no coincide.")

        partial_path.replace(destination_path)
        return destination_path
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise
    finally:
        if response is not None and hasattr(response, "close"):
            response.close()


def silent_installer_command(installer_path: str | Path) -> list[str]:
    """Parámetros Inno Setup usados después de que el usuario acepta actualizar."""
    return [
        str(Path(installer_path)),
        "/SILENT",
        "/SP-",
        "/CLOSEAPPLICATIONS",
        "/NORESTART",
        "/XOMACITOUPDATE=1",
    ]


_DEFERRED_INSTALLER_SCRIPT = r"""param(
    [Parameter(Mandatory=$true)][int]$XomacitoProcessId,
    [Parameter(Mandatory=$true)][string]$InstallerPath
)

$ErrorActionPreference = 'Stop'

# Wait for the application to finish normally. If shutdown gets stuck, force
# only the exact process that requested this already-authorized update.
for ($attempt = 0; $attempt -lt 300; $attempt++) {
    if ($null -eq (Get-Process -Id $XomacitoProcessId -ErrorAction SilentlyContinue)) {
        break
    }
    Start-Sleep -Milliseconds 100
}

if ($null -ne (Get-Process -Id $XomacitoProcessId -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $XomacitoProcessId -Force -ErrorAction SilentlyContinue
    Wait-Process -Id $XomacitoProcessId -ErrorAction SilentlyContinue
}

if (-not (Test-Path -LiteralPath $InstallerPath -PathType Leaf)) {
    exit 2
}

$installerArguments = @(
    '/SILENT',
    '/SP-',
    '/CLOSEAPPLICATIONS',
    '/NORESTART',
    '/XOMACITOUPDATE=1'
)
$setup = Start-Process -FilePath $InstallerPath -ArgumentList $installerArguments `
    -WindowStyle Hidden -Wait -PassThru
$setupExitCode = $setup.ExitCode

if ($setupExitCode -eq 0) {
    Remove-Item -LiteralPath $InstallerPath -Force -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
exit $setupExitCode
"""


def deferred_installer_command(
    installer_path: str | Path,
    xomacito_process_id: int,
    launcher_path: str | Path | None = None,
) -> list[str]:
    """Crea un lanzador que espera el cierre real de Xomacito antes de instalar."""
    installer = Path(installer_path).resolve()
    if launcher_path is None:
        launcher = installer.parent / f"xomacito-update-{uuid.uuid4().hex[:12]}.ps1"
    else:
        launcher = Path(launcher_path).resolve()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(_DEFERRED_INSTALLER_SCRIPT, encoding="utf-8-sig")

    return [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        str(launcher),
        "-XomacitoProcessId",
        str(int(xomacito_process_id)),
        "-InstallerPath",
        str(installer),
    ]
