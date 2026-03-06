"""
Extracción de fragmentos de texto (snippets) alrededor del término buscado
para mostrar contexto: N palabras antes y después con el match resaltado.
"""
import re


# Número de palabras de contexto antes y después del texto encontrado
DEFAULT_CONTEXT_WORDS = 10
# Máximo de snippets por archivo para no saturar la respuesta
DEFAULT_MAX_SNIPPETS = 5


def extract_snippets(full_text, query, context_words=DEFAULT_CONTEXT_WORDS, max_snippets=DEFAULT_MAX_SNIPPETS):
    """
    Obtiene fragmentos del texto con el término buscado y contexto.

    - full_text: texto completo extraído del archivo
    - query: término o frase buscada (se busca en minúsculas, sin distinguir mayúsculas)
    - context_words: palabras anteriores y posteriores al match (por defecto 10)
    - max_snippets: máximo de fragmentos por archivo (por defecto 5)

    Retorna lista de strings. Cada string tiene la forma:
      "... palabra1 palabra2 ... **texto encontrado** palabra1 ... palabra2 ..."
    El marcador ** se reemplazará por <strong> en el frontend.
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
