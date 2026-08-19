"""Límite propio de uso diario de la API de Gemini (Google AI Studio), para
no depender únicamente del cupo gratuito de Google -que ya ha cambiado sin
aviso- y para poder mostrarle al docente cuánto le queda antes de un 429.

Persiste el conteo del día en un archivo JSON simple (no hay concurrencia
real: esto lo corre el docente manualmente desde un script)."""
import json
import os
import threading
from datetime import date

_LOCK = threading.Lock()
_QUOTA_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".gemini_quota.json"))


class QuotaExceededError(Exception):
    pass


def _today() -> str:
    return date.today().isoformat()


def _load() -> dict:
    if not os.path.exists(_QUOTA_PATH):
        return {}
    with open(_QUOTA_PATH) as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(_QUOTA_PATH, "w") as f:
        json.dump(data, f)


def get_usage_today() -> dict:
    return _load().get(_today(), {"calls": 0, "tokens": 0})


def check_and_reserve() -> None:
    """Levanta QuotaExceededError si ya se superó el cupo diario de tokens (los
    tokens de una llamada solo se conocen después de la respuesta, así que el
    límite de tokens se aplica "al primer exceso": la llamada que cruza el
    umbral se deja pasar, pero la siguiente ya no). El cupo de NÚMERO de
    llamados ya no aplica -la cuenta pasó a pago por uso, ya no depende del
    cupo gratuito de Google-; el conteo de llamadas se sigue guardando solo
    para mostrarle al docente cuánto se ha usado."""
    max_tokens = int(os.environ.get("GEMINI_MAX_TOKENS_PER_DAY", "200000"))
    with _LOCK:
        data = _load()
        today = _today()
        usage = data.get(today, {"calls": 0, "tokens": 0})
        if usage["tokens"] >= max_tokens:
            raise QuotaExceededError(f"cupo diario de tokens agotado ({usage['tokens']}/{max_tokens})")
        usage["calls"] += 1
        data[today] = usage
        _save(data)


def record_tokens(n_tokens: int) -> None:
    with _LOCK:
        data = _load()
        today = _today()
        usage = data.get(today, {"calls": 0, "tokens": 0})
        usage["tokens"] += n_tokens
        data[today] = usage
        _save(data)
