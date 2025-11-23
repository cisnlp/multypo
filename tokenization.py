# multypo/tokenization.py
"""
Sentence tokenization helpers for MULTYPO.

We wrap NLTK, stanza and regex-based tokenization into a single interface:
    tokenize_sentences(text, lang, stanza_pipeline=None, use_gpu=True)
"""

from __future__ import annotations
from typing import List, Optional

import re

# Optional imports – we only import when available
try:
    import nltk
    _HAS_NLTK = True
except ImportError:
    nltk = None
    _HAS_NLTK = False

try:
    import stanza
    _HAS_STANZA = True
except ImportError:
    stanza = None
    _HAS_STANZA = False

try:
    from pyarabic.araby import sentence_tokenize as arabic_sentence_tokenize
    _HAS_PYARABIC = True
except ImportError:
    arabic_sentence_tokenize = None
    _HAS_PYARABIC = False


# Languages handled by different backends
NLTK_LANGUAGES = {"german", "french", "russian", "english", "greek"}
STANZA_LANGUAGES = {"armenian", "georgian", "hebrew", "hindi", "tamil"}


def _ensure_nltk_punkt():
    """Lazy-download NLTK punkt if needed."""
    if not _HAS_NLTK:
        raise RuntimeError(
            "NLTK is not installed. Install it via `pip install nltk` to "
            "use NLTK-based sentence tokenization."
        )
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")


def _stanza_pipeline_for_lang(lang: str, use_gpu: bool = True):
    """Create a stanza tokenization pipeline for the given language."""
    if not _HAS_STANZA:
        raise RuntimeError(
            "stanza is not installed. Install it via `pip install stanza` "
            "and download models (stanza.download(lang)) to use stanza-based tokenization."
        )
    # NOTE: You can change processors / device here if needed
    return stanza.Pipeline(
        lang=lang,
        processors="tokenize",
        use_gpu=use_gpu,
        download_method=None,   # assumes models already downloaded
    )


def tokenize_sentences(
    text: str,
    lang: str,
    stanza_pipeline: Optional[object] = None,
    use_gpu: bool = True,
) -> List[str]:
    """
    Tokenize `text` into sentences for a given language name.

    Parameters
    ----------
    text : str
        Input text.
    lang : str
        Language name (e.g. "english", "german", "bengali", "arabic").
        This is consistent with the LANGUAGES dict in keyboards.py.
    stanza_pipeline : Optional[stanza.Pipeline]
        If given and lang is in STANZA_LANGUAGES, use this pipeline instead
        of creating a new one.
    use_gpu : bool
        Whether to use GPU when constructing a new stanza pipeline.

    Returns
    -------
    List[str]
        List of sentence strings.
    """
    lang = lang.lower()

    # 1) NLTK-backed languages
    if lang in NLTK_LANGUAGES:
        _ensure_nltk_punkt()
        # NLTK expects specific names; for your current set they match
        return nltk.sent_tokenize(text, language=lang)

    # 2) stanza-backed languages
    if lang in STANZA_LANGUAGES:
        if stanza_pipeline is None:
            stanza_pipeline = _stanza_pipeline_for_lang(lang=lang, use_gpu=use_gpu)
        doc = stanza_pipeline(text)
        return [s.text for s in doc.sentences]

    # 3) Bengali: regex split on the danda punctuation
    if lang == "bengali":
        sentences = re.findall(r".*?[।?!]", text)
        return [s.strip() for s in sentences if s.strip()]

    # 4) Arabic: pyarabic-based sentence tokenizer
    if lang == "arabic":
        if not _HAS_PYARABIC:
            raise RuntimeError(
                "pyarabic is not installed. Install it via `pip install pyarabic` "
                "to use Arabic sentence tokenization."
            )
        return arabic_sentence_tokenize(text)

    # 5) Fallback: naive split
    # You can make this smarter later (e.g., generic regex).
    return [text.strip()] if text.strip() else []
