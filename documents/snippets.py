"""
Extracción de fragmentos de texto (snippets) alrededor del término buscado
para mostrar contexto: N palabras antes y después con el match resaltado.

- extract_snippets: frase exacta (una cadena), 10 palabras antes/después.
- extract_snippets_multi_term: varios términos en cualquier orden; encuentra la ventana
  mínima que contiene todos y devuelve 10 palabras antes y 10 después de esa ventana.
"""
import re
from itertools import product


DEFAULT_CONTEXT_WORDS = 10
DEFAULT_MAX_SNIPPETS = 5


def _word_boundaries(text, position):
    """Devuelve (start, end) del token (palabra) que contiene position."""
    if not text or position < 0 or position >= len(text):
        return 0, len(text or "")
    # Ir al inicio de la palabra
    start = position
    while start > 0 and text[start - 1].isalnum() or text[start - 1] in "'-_":
        start -= 1
    end = position
    while end < len(text) and (text[end].isalnum() or text[end] in "'-_"):
        end += 1
    return start, end


def extract_snippets(full_text, query, context_words=DEFAULT_CONTEXT_WORDS, max_snippets=DEFAULT_MAX_SNIPPETS):
    """
    Fragmentos con la frase exacta buscada y contexto (N palabras antes/después).

    - full_text: texto completo extraído del archivo
    - query: término o frase buscada (se busca en minúsculas)
    - context_words: palabras anteriores y posteriores al match (por defecto 10)
    - max_snippets: máximo de fragmentos por archivo (por defecto 5)

    Retorna lista de strings con **texto encontrado** para resaltar en el frontend.
    """
    if not full_text or not query:
        return []
    query = query.strip()
    if not query:
        return []
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
        before_text = full_text[:pos]
        after_text = full_text[end:]
        words_before = re.findall(r"\S+", before_text)
        words_after = re.findall(r"\S+", after_text)
        before_10 = words_before[-context_words:] if len(words_before) > context_words else words_before
        after_10 = words_after[:context_words] if len(words_after) > context_words else words_after
        match_phrase = full_text[pos:end]
        prefix = "… " if len(words_before) > context_words else ""
        suffix = " …" if len(words_after) > context_words else ""
        snip = prefix + " ".join(before_10) + " **" + match_phrase + "** " + " ".join(after_10) + suffix
        snippets.append(snip)
        start = pos + 1
    return snippets


def extract_snippets_multi_term(full_text, terms, context_words=DEFAULT_CONTEXT_WORDS, max_snippets=DEFAULT_MAX_SNIPPETS):
    """
    Fragmentos cuando la búsqueda tiene varios términos: encuentra la ventana mínima
    que contiene TODOS los términos (en cualquier orden) y devuelve context_words
    palabras antes y después. Los términos se marcan con ** en el snippet.

    - full_text: texto completo (content_extract o extracted_text)
    - terms: lista de cadenas (ej. ["ley", "trabajo"])
    - context_words: palabras de contexto antes/después (por defecto 10)
    - max_snippets: máximo de fragmentos (por defecto 5)
    """
    if not full_text or not terms:
        return []
    terms = [t.strip() for t in terms if t and t.strip()]
    if not terms:
        return []
    text_lower = full_text.lower()
    # Todas las ocurrencias (pos_start, pos_end) por término
    occs = {}
    for t in terms:
        tl = t.lower()
        occs[t] = []
        pos = 0
        while True:
            idx = text_lower.find(tl, pos)
            if idx < 0:
                break
            occs[t].append((idx, idx + len(t)))
            pos = idx + 1
    if any(not occs[t] for t in terms):
        return []
    words = list(re.finditer(r"\S+", full_text))
    word_spans = [(m.start(), m.end(), m.group()) for m in words]
    if not word_spans:
        return []

    # Candidatos: una ventana (min_s, max_e) por combinación de una ocurrencia de cada término
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
        span_lower = span_text.lower()
        for t in terms:
            tl = t.lower()
            idx = 0
            while True:
                p = span_lower.find(tl, idx)
                if p < 0:
                    break
                orig = span_text[p : p + len(t)]
                span_text = span_text[:p] + "**" + orig + "**" + span_text[p + len(t) :]
                span_lower = span_text.lower()
                idx = p + len(orig) + 4
        prefix = "… " if n_before > 0 else ""
        suffix = " …" if n_after < len(word_spans) else ""
        snip = prefix + before_str + " " + span_text + " " + after_str + suffix
        snippets.append(snip.strip())
    return snippets[:max_snippets]
