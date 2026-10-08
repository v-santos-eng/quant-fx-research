"""Notificações (RF-22): Telegram via Bot API. Fallback é responsabilidade do chamador.

Lê token/chat_id de config/secrets.yaml (gitignored). Sem config -> no-op que retorna
'not_configured' — nunca crasha o pipeline por falta de credencial. O token JAMAIS
entra em código, log ou git.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

SECRETS = Path("config/secrets.yaml")


def _telegram_conf(secrets_path: Path = SECRETS) -> dict | None:
    if not secrets_path.exists():
        return None
    conf = yaml.safe_load(secrets_path.read_text(encoding="utf-8")) or {}
    tg = conf.get("telegram") or {}
    if not tg.get("token") or not tg.get("chat_id"):
        return None
    return tg


def telegram_send(text: str, *, secrets_path: Path = SECRETS, timeout: int = 15) -> str:
    """Envia `text`. Retorna 'sent' | 'not_configured' | 'error: ...' (nunca levanta)."""
    tg = _telegram_conf(secrets_path)
    if tg is None:
        return "not_configured"
    url = f"https://api.telegram.org/bot{tg['token']}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": tg["chat_id"], "text": text}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=timeout) as r:
            return "sent" if json.load(r).get("ok") else "error: telegram recusou"
    except OSError as e:
        return f"error: {e}"
