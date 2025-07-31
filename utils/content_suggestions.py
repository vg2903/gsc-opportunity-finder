# utils/content_suggestions.py

def generate_h2s(query, openai_key=None, gemini_key=None):
    """
    Dummy placeholder to generate H2s for a given query.
    In production, this should call OpenAI or Gemini APIs.
    """
    if openai_key:
        return f"OpenAI H2 suggestions for: {query}"
    elif gemini_key:
        return f"Gemini H2 suggestions for: {query}"
    else:
        return "No API key provided"
