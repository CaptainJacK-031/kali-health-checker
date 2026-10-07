import datetime as dt
import json
import os
import shutil
import subprocess
from typing import Any


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_cmd(cmd: list[str], timeout: int = 8) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except FileNotFoundError:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"Command not found: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"Command timed out: {' '.join(cmd)}"}
    except Exception as e:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(e)}


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def json_loads(text: str, default: Any) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return default


def human_bytes(n: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n or 0)
    for u in units:
        if x < 1024 or u == units[-1]:
            return f"{x:.1f} {u}"
        x /= 1024
    return f"{x:.1f} TB"
