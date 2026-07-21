"""Shared token resolution for cognee-search.sh and cognee_mcp_server.py."""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional


def _jwt_exp_unix(token: str) -> Optional[int]:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        pad = "=" * (4 - len(payload) % 4)
        raw = base64.urlsafe_b64decode(payload + pad)
        data = json.loads(raw.decode("utf-8"))
        exp = data.get("exp")
        return int(exp) if exp is not None else None
    except Exception:
        return None


def resolve_bearer_token(config_path: str) -> str:
    """
    Priority: COGNEE_API_TOKEN env > config api_token > auth login + cache.
    Returns Bearer JWT string, or "" if no credentials configured.
    Raises RuntimeError on login failure when auth is required.
    """
    config_path = os.path.abspath(config_path)
    skill_dir = os.path.dirname(os.path.dirname(config_path))
    cache_path = os.path.join(skill_dir, ".cognee_token_cache.json")

    env_tok = os.environ.get("COGNEE_API_TOKEN", "").strip()
    if env_tok:
        return env_tok

    try:
        cfg: dict[str, Any] = json.load(open(config_path, encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"config: {e}") from e

    api_url = (cfg.get("api_url") or "").rstrip("/")
    direct = (cfg.get("api_token") or "").strip()
    if direct:
        return direct

    auth = cfg.get("auth") or {}
    user = (auth.get("username") or "").strip()
    pw = auth.get("password")
    if pw is not None and not isinstance(pw, str):
        pw = str(pw)
    pw = (pw or "").strip()

    if not user or not pw:
        return ""

    now = time.time()
    if os.path.isfile(cache_path):
        try:
            cache = json.load(open(cache_path, encoding="utf-8"))
            tok = (cache.get("access_token") or "").strip()
            if tok:
                exp_j = _jwt_exp_unix(tok)
                file_exp = cache.get("exp_unix")
                effective = exp_j if exp_j is not None else file_exp
                if effective is not None and now < float(effective) - 120:
                    return tok
        except Exception:
            pass

    data = urllib.parse.urlencode({"username": user, "password": pw}).encode("utf-8")
    req = urllib.request.Request(
        f"{api_url}/api/v1/auth/login",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"login failed HTTP {e.code}: {err}") from e
    except Exception as e:
        raise RuntimeError(f"login failed: {e}") from e

    token = body.get("access_token")
    if not token:
        raise RuntimeError("login response missing access_token")

    exp_unix = _jwt_exp_unix(token)
    if exp_unix is None:
        exp_unix = int(now) + 23 * 3600

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(
                {"access_token": token, "exp_unix": exp_unix},
                f,
                ensure_ascii=False,
                indent=0,
            )
    except OSError:
        pass

    return token
