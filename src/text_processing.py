from __future__ import annotations

import re
import sys
from collections import Counter

import spacy
from nltk.util import ngrams


class WikipediaTextProcessor:
    def __init__(self, model_name: str = "en_core_sci_md") -> None:
        self.model_name = model_name
        try:
            self.nlp = spacy.load(model_name, disable=["parser"])
        except Exception as exc:
            print(f"Error al cargar el modelo de spaCy '{model_name}': {exc}")
            print("Instala el modelo antes de ejecutar el pipeline.")
            sys.exit(1)

    @staticmethod
    def is_low_information_verb(token) -> bool:
        return token.pos_ == "VERB" and token.lemma_ in {
            "be",
            "have",
            "do",
            "say",
            "go",
            "can",
            "get",
            "would",
            "make",
            "know",
            "will",
            "think",
            "take",
            "see",
            "come",
            "could",
            "want",
            "look",
            "use",
            "find",
            "give",
            "tell",
            "work",
            "call",
            "include",
        }

    def clean_text(self, text: str) -> tuple[list[str], list[str]]:
        text = text.lower()
        text = re.sub(r"[^a-zA-Z\s]", "", text)
        doc = self.nlp(text)

        words: list[str] = []
        entities: list[str] = []

        for token in doc:
            if token.is_stop or self.is_low_information_verb(token):
                continue
            if token.is_alpha and len(token) > 2:
                words.append(token.lemma_)

        for ent in doc.ents:
            entities.append(ent.text.lower())

        all_words = words + entities
        word_freq = Counter(all_words)
        most_common_words = [
            word
            for word, _ in word_freq.most_common(100)
            if " " not in word and word.isalpha()
        ]

        if len(most_common_words) < 2:
            return all_words, []

        bigrams = [" ".join(bigram) for bigram in ngrams(most_common_words, 2)]
        return all_words, bigrams
