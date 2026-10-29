#!/usr/bin/env python3
"""Client MCP minimal pour les tests et la démonstration (stdio, JSON par ligne)."""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
SERVER = PROJECT / "src"
PYTHON = os.environ.get("TI_PYTHON", sys.executable)


class MCPClient:
    def __init__(self, token: str, env_extra: dict[str, str] | None = None,
                 command: list[str] | None = None, timeout: float = 10.0):
        env = dict(os.environ)
        env["TI_MCP_TOKEN"] = token
        env["PYTHONPATH"] = str(SERVER) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        env.setdefault("PYTHONUNBUFFERED", "1")
        if env_extra:
            env.update(env_extra)
        self.timeout = timeout
        self.command = command or [PYTHON, "-m", "ti_server"]
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(PROJECT),
            env=env,
            text=True,
            bufsize=1,
        )
        self._id = 0

    def _send(self, payload: dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _read_line(self) -> str:
        assert self.proc.stdout is not None
        ready, _, _ = select.select([self.proc.stdout], [], [], self.timeout)
        if not ready:
            raise TimeoutError("le serveur n'a pas répondu dans le délai imparti")
        line = self.proc.stdout.readline()
        if not line:
            stderr = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(f"serveur terminé sans réponse: {stderr[-800:]}")
        return line

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)
        line = self._read_line()
        message = json.loads(line)
        if "error" in message:
            return {"ok": False, "error": message["error"], "raw": message}
        return {"ok": True, "result": message.get("result", {}), "raw": message}

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    def initialize(self) -> dict[str, Any]:
        result = self.request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "tekup-lab-client", "version": "1.0"},
        })
        self.notify("notifications/initialized")
        return result

    def list_tools(self) -> dict[str, Any]:
        return self.request("tools/list", {})

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=3)
        except Exception:
            self.proc.kill()

    def __enter__(self) -> "MCPClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def summarize_tool_result(response: dict[str, Any]) -> dict[str, Any]:
    if not response.get("ok"):
        return {"transport_ok": False, "error": response.get("error")}
    result = response.get("result", {})
    return {
        "transport_ok": True,
        "isError": result.get("isError", False),
        "structured": result.get("structuredContent"),
        "text": (result.get("content") or [{}])[0].get("text", ""),
    }
