"""Best-effort diagnostic output that never rejects Unicode media paths."""
import builtins
import sys


def diagnostic_print(*values, sep=" ", end="\n", file=None, flush=False):
    """Escape only the log text if a redirected Windows stream uses ANSI.

    Do not sanitize filenames or subprocess arguments: FFmpeg accepts the
    original Unicode paths. Windowed builds may have no stdout at all.
    """
    stream = file if file is not None else sys.stdout
    if stream is None:
        return
    try:
        builtins.print(*values, sep=sep, end=end, file=stream, flush=flush)
    except UnicodeEncodeError:
        text = (" " if sep is None else sep).join(str(value) for value in values)
        text += "\n" if end is None else end
        encoding = getattr(stream, "encoding", None) or "ascii"
        try:
            stream.write(text.encode(encoding, errors="backslashreplace").decode(encoding))
            if flush:
                stream.flush()
        except (OSError, ValueError, LookupError):
            pass  # A diagnostic sink must not abort media work.
    except (OSError, ValueError):
        pass
