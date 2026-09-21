"""Keep retries within the video quality the user selected."""


def quality_preserving_selector(video):
    bounds = ""
    for key in ("width", "height"):
        value = int(video.get(key) or (video.get("raw") or {}).get(key) or 0)
        if value:
            bounds += f"[{key}>={value}]"
    fps = float(video.get("fps") or (video.get("raw") or {}).get("fps") or 0)
    if fps:
        bounds += f"[fps>={max(1, fps - 0.5):g}]"
    return f"bestvideo{bounds}+bestaudio/best{bounds}"


def validate_download_resolution(info, selected):
    expected = sorted(int(selected.get(key) or (selected.get("raw") or {}).get(key) or 0)
                      for key in ("width", "height"))
    if not any(expected):
        return
    streams = [s for s in (info or {}).get("streams", []) if s.get("codec_type") == "video"
               and not (s.get("disposition") or {}).get("attached_pic")]
    actual = max((sorted((int(s.get("width") or 0), int(s.get("height") or 0)))
                  for s in streams), default=[0, 0])
    if any(wanted and got < wanted for got, wanted in zip(actual, expected)):
        raise RuntimeError(
            f"El archivo recibido tiene {actual[0]}×{actual[1]}, inferior a la resolución "
            f"seleccionada ({expected[0]}×{expected[1]}). No se dará por completada la descarga. "
            "Vuelve a analizar el enlace para renovar los formatos disponibles."
        )
