"""
Enrichment opsional lewat figma-console MCP (tool `figma_audit_design_system`).

Aktifkan: FIGMA_MCP_ENRICH=1 dan pasang dependensi `mcp` (+ Node/npx untuk server).

Lingkungan perlu FIGMA_ACCESS_TOKEN; token dari formulir audit juga dikirim ke subprocess.

Penting (Desktop Bridge): server `figma-console-mcp` baru mendaftarkan penuh tools setelah
plugin **Figma Desktop Bridge** terhubung ke WebSocket (9223–9232). Tanpa menunggu, call_tool
bisa gagal dengan "Tool ... not found". Atur FIGMA_MCP_BRIDGE_WAIT bila perlu.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import timedelta
from typing import Any

_MAX_TEXT = 24_000
_MCP_AUDIT_TOOL = "figma_audit_design_system"


def mcp_enrichment_enabled() -> bool:
    v = (os.environ.get("FIGMA_MCP_ENRICH") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _mcp_timeout_seconds() -> float:
    try:
        return max(15.0, float(os.environ.get("FIGMA_MCP_TIMEOUT", "120")))
    except ValueError:
        return 120.0


def _bridge_wait_seconds() -> float:
    """Tunggu plugin Bridge menghubungkan WS sebelum tool tersedia."""
    try:
        return max(5.0, float(os.environ.get("FIGMA_MCP_BRIDGE_WAIT", "60")))
    except ValueError:
        return 60.0


def _mcp_subprocess_env(token: str) -> dict[str, str]:
    """
    Gabung env parent + token. README figma-console: ENABLE_MCP_APPS=true untuk apps/bridge.
    """
    env: dict[str, str] = {k: str(v) if v is not None else "" for k, v in os.environ.items()}
    env["FIGMA_ACCESS_TOKEN"] = token
    if "ENABLE_MCP_APPS" not in os.environ:
        env["ENABLE_MCP_APPS"] = "true"
    return env


def _server_command() -> tuple[str, list[str]]:
    cmd = (os.environ.get("FIGMA_MCP_COMMAND") or "npx").strip()
    raw = (os.environ.get("FIGMA_MCP_ARGS") or "-y figma-console-mcp@latest").strip()
    parts = raw.split()
    return cmd, parts


def _blocks_to_text(content) -> str:
    parts: list[str] = []
    for block in content or []:
        if getattr(block, "type", None) == "text" and getattr(block, "text", None):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
            parts.append(str(block["text"]))
    return "\n\n".join(parts).strip()


async def _wait_for_tool_registered(session, tool_name: str, max_wait: float) -> None:
    """Poll list_tools sampai tool ada (setelah Desktop Bridge connect)."""
    deadline = time.monotonic() + max_wait
    last_n = 0
    while time.monotonic() < deadline:
        tools = await session.list_tools()
        last_n = len(tools.tools)
        if any(t.name == tool_name for t in tools.tools):
            return
        await asyncio.sleep(0.35)
    raise TimeoutError(
        f"Setelah {int(max_wait)}s tool `{tool_name}` belum tersedia (saat ini {last_n} tools). "
        "Buka Figma Desktop dengan file yang diaudit, lalu jalankan plugin: "
        "Plugins → Development → **Figma Desktop Bridge** sampai terhubung. "
        "Jika Cursor juga menjalankan figma-console-mcp, tutup satu instance atau samakan port (FIGMA_WS_PORT)."
    )


async def _call_figma_audit_async(figma_url: str, token: str) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    command, args = _server_command()
    env = _mcp_subprocess_env(token)
    sp = StdioServerParameters(command=command, args=args, env=env)
    call_timeout = _mcp_timeout_seconds()
    bridge_wait = _bridge_wait_seconds()
    td = timedelta(seconds=call_timeout)

    async with stdio_client(sp) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=min(45.0, bridge_wait + 30.0))
            await _wait_for_tool_registered(session, _MCP_AUDIT_TOOL, bridge_wait)
            result = await session.call_tool(
                _MCP_AUDIT_TOOL,
                {"fileUrl": figma_url},
                read_timeout_seconds=td,
            )

    out: dict[str, Any] = {
        "ok": not result.isError,
        "tool": _MCP_AUDIT_TOOL,
        "is_error": result.isError,
    }
    if result.structuredContent:
        out["structured"] = result.structuredContent
    text = _blocks_to_text(result.content)
    if text:
        out["text"] = text if len(text) <= _MAX_TEXT else (text[: _MAX_TEXT] + "\n… [truncated]")
    if result.isError and text:
        out["error"] = text[:2000]
    return out


def run_mcp_enrichment_sync(figma_url: str, token: str) -> dict[str, Any] | None:
    if not mcp_enrichment_enabled():
        return None
    try:
        return asyncio.run(_call_figma_audit_async(figma_url, token))
    except ModuleNotFoundError:
        return {
            "ok": False,
            "error": "Paket `mcp` belum terpasang. Contoh: pip install 'mcp>=1.2'",
            "tool": _MCP_AUDIT_TOOL,
        }
    except Exception as e:  # noqa: BLE001 — gabungkan semua ke payload agar audit REST tidak gagal
        return {
            "ok": False,
            "error": str(e),
            "tool": _MCP_AUDIT_TOOL,
        }


def summarize_for_doc_fragment(enrich: dict[str, Any] | None, max_chars: int = 3500) -> str | None:
    if not enrich or not enrich.get("ok"):
        return None
    if enrich.get("structured"):
        try:
            s = json.dumps(enrich["structured"], ensure_ascii=False, indent=2)
        except Exception:
            s = str(enrich["structured"])
        if len(s) > max_chars:
            s = s[:max_chars] + "\n…"
        return s
    t = enrich.get("text") or ""
    if not t:
        return None
    return t[:max_chars] + ("…" if len(t) > max_chars else "")
