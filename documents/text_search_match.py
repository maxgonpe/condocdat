"""
Coincidencias de búsqueda como palabra completa (límite de palabra Unicode).

Evita falsos positivos de OCR donde subcadenas cortas aparecen dentro de tokens rotos
(p. ej. "fe" + "ha" en "Fe c ha", o "enter" como palabra suelta en "C enter").
"""
import re
from typing import Iterable, List, Optional, Tuple

# Límite de ocurrencias por término (snippets y producto de combinaciones)
MAX_TERM_OCCURRENCES = 40
# Términos tan cortos suelen ser fragmentos de palabras rotas por OCR en multi-palabra
_SHORT_TERM_LEN = 3
# Sufijos típicos de palabra partida por OCR tras un token de una letra ("C enter" ← Center)
_MIN_LEN_PREV_SINGLE_CHAR = 5


def _python_word_boundary_pattern(term: str) -> re.Pattern:
    escaped = re.escape(term.strip())
    return re.compile(r"(?<!\w)" + escaped + r"(?!\w)", re.IGNORECASE | re.UNICODE)


def _immediate_prev_token(haystack: str, start: int) -> Optional[str]:
    sub = haystack[:start].rstrip()
    if not sub:
        return None
    tokens = list(re.finditer(r"\S+", sub))
    if not tokens:
        return None
    return tokens[-1].group()


def _short_term_not_ocr_fragment(haystack: str, start: int, end: int, term: str) -> bool:
    """
    Para términos cortos (<= _SHORT_TERM_LEN): descarta coincidencias pegadas a
    cadenas típicas de OCR (token de 1 letra + otro corto), p. ej. "Fe c ha".
    """
    tl = len(term.strip())
    if tl > _SHORT_TERM_LEN:
        return True
    after = haystack[end:]
    m = re.match(r"\s*(\S+)", after)
    if m:
        nxt = m.group(1)
        if len(nxt) == 1 and nxt.isalpha():
            rest = after[m.end() :]
            m2 = re.match(r"\s*(\S+)", rest)
            if m2:
                n2 = m2.group(1)
                if n2.isalpha() and len(n2) <= 3:
                    return False
    before = haystack[:start]
    tokens = list(re.finditer(r"\S+", before))
    if len(tokens) >= 2:
        prev = tokens[-1].group()
        prev2 = tokens[-2].group()
        if len(prev) == 1 and prev.isalpha() and prev2.isalpha() and len(prev2) <= 3:
            return False
    return True


def _long_term_not_after_single_letter_token(haystack: str, start: int, term: str) -> bool:
    """Evita "C enter", "C ódigo", etc.: término largo pegado a un token de una sola letra."""
    tl = len(term.strip())
    if tl < _MIN_LEN_PREV_SINGLE_CHAR:
        return True
    prev = _immediate_prev_token(haystack, start)
    if prev is not None and len(prev) == 1 and prev.isalpha():
        return False
    return True


def iter_term_spans(
    haystack: str,
    term: str,
    *,
    max_occurrences: int = MAX_TERM_OCCURRENCES,
    multi_term_context: bool = False,
) -> Iterable[Tuple[int, int]]:
    if not haystack or not term or not term.strip():
        yield from ()
        return
    pat = _python_word_boundary_pattern(term)
    n = 0
    for m in pat.finditer(haystack):
        s, e = m.start(), m.end()
        if multi_term_context:
            if not _short_term_not_ocr_fragment(haystack, s, e, term):
                continue
            if not _long_term_not_after_single_letter_token(haystack, s, term):
                continue
        yield s, e
        n += 1
        if n >= max_occurrences:
            break


def list_term_spans(
    haystack: str,
    term: str,
    *,
    max_occurrences: int = MAX_TERM_OCCURRENCES,
    multi_term_context: bool = False,
) -> List[Tuple[int, int]]:
    return list(
        iter_term_spans(
            haystack,
            term,
            max_occurrences=max_occurrences,
            multi_term_context=multi_term_context,
        )
    )


def text_has_word_bounded_term(
    haystack: str,
    term: str,
    *,
    multi_term_context: bool = False,
) -> bool:
    return any(iter_term_spans(haystack, term, max_occurrences=1, multi_term_context=multi_term_context))


def text_matches_all_terms_as_words(haystack: str, terms: List[str]) -> bool:
    terms = [t.strip() for t in (terms or []) if t and t.strip()]
    if not haystack or not terms:
        return False
    if len(terms) == 1:
        return text_has_word_bounded_term(haystack, terms[0], multi_term_context=False)
    return all(text_has_word_bounded_term(haystack, t, multi_term_context=True) for t in terms)


def text_matches_single_query(haystack: str, query: str) -> bool:
    """Varias palabras: subcadena contigua (frase). Una palabra: límite de palabra."""
    if not haystack or not query:
        return False
    q = query.strip()
    if not q:
        return False
    if re.search(r"\s", q):
        return q.lower() in haystack.lower()
    return text_has_word_bounded_term(haystack, q)


def pg_word_anchored_regex(term: str) -> str:
    """Patrón para PostgreSQL ~* : inicio y fin de palabra POSIX (\\m / \\M)."""
    t = (term or "").strip()
    escaped = re.escape(t)
    return rf"\m{escaped}\M"
