from __future__ import annotations

import base64
import hashlib
import marshal
import secrets
import shutil
from pathlib import Path

from Cryptodome.Cipher import AES


ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / ".build" / "public-hardened"
PROTECTED_ROOT = BUILD_ROOT / "protected"
RUNTIME_INPUT = BUILD_ROOT / "runtime-input"


def _safe_reset(path: Path) -> None:
    resolved_root = (ROOT / ".build").resolve()
    resolved = path.resolve()
    if resolved_root not in resolved.parents:
        raise RuntimeError(f"Ruta de compilación no segura: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def _encrypted_stub(source: Path, key: bytes) -> str:
    relative = source.relative_to(ROOT).as_posix()
    code = compile(source.read_text(encoding="utf-8-sig"), f"xomacito://{relative}", "exec", optimize=2)
    payload = marshal.dumps(code)
    nonce = secrets.token_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    encrypted, tag = cipher.encrypt_and_digest(payload)
    encoded = base64.b85encode(nonce + tag + encrypted).decode("ascii")
    return (
        "from xomacito_runtime import execute as __xomacito_execute\n"
        f"__xomacito_execute(globals(), b'{encoded}')\n"
        "del __xomacito_execute\n"
    )


def _runtime_source(key: bytes) -> str:
    mask = secrets.token_bytes(len(key))
    masked = bytes(left ^ right for left, right in zip(key, mask))
    mask_text = base64.b85encode(mask).decode("ascii")
    masked_text = base64.b85encode(masked).decode("ascii")
    fingerprint = hashlib.sha256(key).hexdigest()[:16]
    return f'''from __future__ import annotations
import base64
import marshal
from Cryptodome.Cipher import AES

_A = base64.b85decode(b"{mask_text}")
_B = base64.b85decode(b"{masked_text}")
_FINGERPRINT = "{fingerprint}"

def execute(namespace, encoded):
    key = bytes(a ^ b for a, b in zip(_A, _B))
    if __import__("hashlib").sha256(key).hexdigest()[:16] != _FINGERPRINT:
        raise RuntimeError("La protección de Xomacito no pudo validarse.")
    raw = base64.b85decode(encoded)
    cipher = AES.new(key, AES.MODE_GCM, nonce=raw[:12])
    code = marshal.loads(cipher.decrypt_and_verify(raw[28:], raw[12:28]))
    exec(code, namespace, namespace)
'''


def main() -> None:
    _safe_reset(BUILD_ROOT)
    PROTECTED_ROOT.mkdir(parents=True, exist_ok=True)
    RUNTIME_INPUT.mkdir(parents=True, exist_ok=True)
    key = secrets.token_bytes(32)

    sources = [ROOT / "main.py"] + sorted((ROOT / "src").rglob("*.py"))
    for source in sources:
        destination = PROTECTED_ROOT / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(_encrypted_stub(source, key), encoding="utf-8", newline="\n")

    (RUNTIME_INPUT / "xomacito_runtime.py").write_text(
        _runtime_source(key), encoding="utf-8", newline="\n"
    )
    print(f"Fuente protegida: {len(sources)} módulos")


if __name__ == "__main__":
    main()
