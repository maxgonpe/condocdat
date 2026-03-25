"""
Extracción de fragmentos de texto (snippets) alrededor del término buscado
para mostrar contexto: N palabras antes y después con el match resaltado.

- extract_snippets: frase con espacios = subcadena contigua; una sola palabra = límite de palabra.
- extract_snippets_multi_term: varios términos como palabras completas; ventana mínima que los contiene.
"""
import re
from itertools import product

from .text_search_match import list_term_spans, MAX_TERM_OCCURRENCES


DEFAULT_CONTEXT_WORDS = 10
DEFAULT_MAX_SNIPPETS = 5
# Evita explosión combinatoria al enlazar varias ocurrencias por término
MAX_OCCURRENCES_PER_TERM_FOR_COMBO = 14


def _snippet_around_span(full_text, pos, end, context_words):
    before_text = full_text[:pos]
    after_text = full_text[end:]
    words_before = re.findall(r"\S+", before_text)
    words_after = re.findall(r"\S+", after_text)
    before_10 = words_before[-context_words:] if len(words_before) > context_words else words_before
    after_10 = words_after[:context_words] if len(words_after) > context_words else words_after
    match_phrase = full_text[pos:end]
    prefix = "… " if len(words_before) > context_words else ""
    suffix = " …" if len(words_after) > context_words else ""
    return prefix + " ".join(before_10) + " **" + match_phrase + "** " + " ".join(after_10) + suffix


def extract_snippets(full_text, query, context_words=DEFAULT_CONTEXT_WORDS, max_snippets=DEFAULT_MAX_SNIPPETS):
    """
    Fragmentos con la frase o palabra buscada y contexto (N palabras antes/después).

    - Varios tokens separados por espacio: subcadena contigua (comportamiento anterior).
    - Una sola palabra: solo coincidencias con límite de palabra (evita matches dentro de tokens OCR).
    """
    if not full_text or not query:
        return []
    query = query.strip()
    if not query:
        return []
    if re.search(r"\s", query):
        text_lower = full_text.lower()
        query_lower = query.lower()
        if query_lower not in text_lower:
            return []
        snippets = []
        start = 0
        while len(snippets) < max_snippets:
            pos = text_lower.find(query_lower, start)
            if pos < 0:
                break
            end = pos + len(query)
            snippets.append(_snippet_around_span(full_text, pos, end, context_words))
            start = pos + 1
        return snippets

    spans = list_term_spans(full_text, query, max_occurrences=max_snippets)
    return [_snippet_around_span(full_text, pos, end, context_words) for pos, end in spans]


def _merge_overlapping_spans(spans):
    spans = sorted(spans)
    if not spans:
        return []
    out = [[spans[0][0], spans[0][1]]]
    for s, e in spans[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [tuple(x) for x in out]


def _highlight_word_bounded_terms(span_text, terms):
    mtc = len(terms) > 1
    spans = []
    for t in terms:
        spans.extend(
            list_term_spans(
                span_text,
                t,
                max_occurrences=MAX_TERM_OCCURRENCES,
                multi_term_context=mtc,
            )
        )
    merged = _merge_overlapping_spans(spans)
    out = span_text
    for s, e in reversed(merged):
        out = out[:s] + "**" + out[s:e] + "**" + out[e:]
    return out


def extract_snippets_multi_term(full_text, terms, context_words=DEFAULT_CONTEXT_WORDS, max_snippets=DEFAULT_MAX_SNIPPETS):
    """
    Varios términos: cada uno debe aparecer como palabra completa. Ventana mínima que contiene
    todos los términos (cualquier orden) y context_words palabras antes/después.
    """
    if not full_text or not terms:
        return []
    terms = [t.strip() for t in terms if t and t.strip()]
    if not terms:
        return []
    cap = min(MAX_OCCURRENCES_PER_TERM_FOR_COMBO, MAX_TERM_OCCURRENCES)
    occs = {
        t: list_term_spans(full_text, t, max_occurrences=cap, multi_term_context=True)
        for t in terms
    }
    if any(not occs[t] for t in terms):
        return []
    words = list(re.finditer(r"\S+", full_text))
    word_spans = [(m.start(), m.end(), m.group()) for m in words]
    if not word_spans:
        return []

    combos = product(*(occs[t] for t in terms))
    candidates = []
    for combo in combos:
        min_s = min(s for s, e in combo)
        max_e = max(e for s, e in combo)
        candidates.append((min_s, max_e))
    candidates = sorted(set(candidates), key=lambda x: (x[1] - x[0], x[0]))[:max_snippets]
    snippets = []
    for min_s, max_e in candidates:
        i_start = next((i for i, (ws, we, _) in enumerate(word_spans) if we > min_s), 0)
        i_end = next((i for i in range(len(word_spans) - 1, -1, -1) if word_spans[i][0] < max_e), len(word_spans) - 1)
        n_before = max(0, i_start - context_words)
        n_after = min(len(word_spans), i_end + 1 + context_words)
        before_str = " ".join(w for _, _, w in word_spans[n_before:i_start])
        after_str = " ".join(w for _, _, w in word_spans[i_end + 1:n_after])
        span_text = full_text[min_s:max_e]
        span_text = _highlight_word_bounded_terms(span_text, terms)
        prefix = "… " if n_before > 0 else ""
        suffix = " …" if n_after < len(word_spans) else ""
        snip = prefix + before_str + " " + span_text + " " + after_str + suffix
        snippets.append(snip.strip())
    return snippets[:max_snippets]
