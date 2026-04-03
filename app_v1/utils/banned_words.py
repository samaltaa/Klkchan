# app/utils/banned_words.py
from __future__ import annotations
import re, unicodedata, json
from pathlib import Path
from functools import lru_cache
from typing import Iterable

# Carpeta con los .txt de LDNOOBW por idioma (es.txt, en.txt, ...)
DATA_DIR = (Path(__file__).resolve().parents[1] / "data" / "ldnoobw").resolve()

# Mapa básico de leet -> letra
LEET_MAP = str.maketrans({
    "0":"o","1":"i","3":"e","4":"a","5":"s","7":"t","8":"b","9":"g",
    "$":"s","@":"a","+":"t"
})

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _normalize(s: str) -> str:
    s = (s or "").lower().translate(LEET_MAP)
    s = _strip_accents(s)
    # colapsa repeticiones exageradas: "puuuta" -> "puuta"
    s = re.sub(r"(.)\1{2,}", r"\1\1", s)
    # espacios múltiples -> 1
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _load_words_for_lang(code: str) -> set[str]:
    """
    Lee LDNOOBW para un idioma. Acepta 'es.txt' o 'es' (como en el repo).
    Ignora líneas vacías y comentarios.
    """
    candidates = [DATA_DIR / f"{code}.txt", DATA_DIR / code]
    words: set[str] = set()
    for p in candidates:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                words.add(_normalize(line))
            break
    return words

def _apply_overrides(words: set[str], lang_codes: tuple[str, ...]) -> set[str]:
    """
    overrides.json formato:
    {
      "add":    {"*": ["frase x"], "es": ["insulto"], "en": []},
      "remove": {"*": ["palabra erronea"], "es": [], "en": []}
    }
    """
    ov_path = DATA_DIR / "overrides.json"
    if not ov_path.exists():
        return words
    ov = json.loads(ov_path.read_text(encoding="utf-8"))
    add = set(_normalize(w) for w in ov.get("add", {}).get("*", []))
    rm  = set(_normalize(w) for w in ov.get("remove", {}).get("*", []))
    for c in lang_codes:
        add |= set(_normalize(w) for w in ov.get("add", {}).get(c, []))
        rm  |= set(_normalize(w) for w in ov.get("remove", {}).get(c, []))
    return (words | add) - rm

def _build_tokens(words: Iterable[str]) -> list[str]:
    tokens = []
    for w in sorted(set(words), key=len, reverse=True):
        t = re.escape(w)
        t = t.replace(r"\ ", r"\s+")  # permitir espacios variables en frases
        tokens.append(t)
    return tokens

@lru_cache(maxsize=64)
def _compiled_for_langs(lang_codes: tuple[str, ...]) -> re.Pattern:
    """
    Compila un único regex para un conjunto de idiomas.
    Usa lookarounds para “bordes de palabra” sin romper tildes/UTF-8.
    """
    words: set[str] = set()
    for c in lang_codes:
        words |= _load_words_for_lang(c)
    words = _apply_overrides(words, lang_codes)
    if not words:
        return re.compile(r"^(?!)")  # no matchea nunca
    tokens = _build_tokens(words)
    # (?i) case-insensitive; (?<!\w) y (?!\w) reducen falsos positivos (Scunthorpe-like)
    pattern = r"(?i)(?<!\w)(" + "|".join(tokens) + r")(?!\w)"
    return re.compile(pattern)

def has_banned_words(text: str, lang_hint: str | Iterable[str] = "es") -> bool:
    """
    API drop-in. 'lang_hint' puede ser 'es' ó ['es','en'].
    Normaliza el texto y busca coincidencias de palabra/frase.
    """
    if isinstance(lang_hint, str):
        codes = (lang_hint,)
    else:
        codes = tuple(lang_hint) if lang_hint else ("es","en")
    rx = _compiled_for_langs(codes)
    return bool(rx.search(_normalize(text or "")))
