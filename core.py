# multypo/core.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable, Iterable
import random
import math

from .keyboards import LANGUAGES, KEYBOARDS, LEFT_RIGHTS, IGNORES
from .tokenization import tokenize_sentences as _tokenize_sentences


TypoFunc = Callable[[str, "MultiTypoGenerator"], Tuple[str, Optional[Tuple[int, ...]]]]


DEFAULT_TYPO_DISTRIBUTION: Dict[str, float] = {
    "delete": 0.28,
    "insert": 0.15,
    "replace": 0.28,
    "transpose": 0.28,
}

@dataclass
class MultiTypoGenerator:
    language: str                         # e.g. "english" or "english-custom"
    use_excluding_set: bool = True
    typo_distribution: Dict[str, float] = field(default_factory=lambda: DEFAULT_TYPO_DISTRIBUTION.copy())
    horizontal_vs_vertical: Tuple[float, float] = (9.0, 1.0)

    lang_code: str = field(init=False)
    keyboard: List[List[str]] = field(init=False)
    left_right: Dict[str, List[str]] = field(init=False)
    ignore_set: set = field(init=False)

    def __post_init__(self):
        if self.language not in LANGUAGES:
            raise ValueError(
                f"Unsupported language: {self.language}. "
                f"Available: {list(LANGUAGES.keys())}"
            )

        self.lang_code = LANGUAGES[self.language]

        if self.lang_code not in KEYBOARDS:
            raise ValueError(f"No keyboard layout defined for lang_code={self.lang_code}")

        self.keyboard = KEYBOARDS[self.lang_code]
        self.left_right = LEFT_RIGHTS.get(self.lang_code, {"left": [], "right": []})
        self.ignore_set = IGNORES.get(self.lang_code, set())

        self._normalize_distribution()

    def _normalize_distribution(self):
        total = sum(self.typo_distribution.values())
        if total <= 0:
            raise ValueError("typo_distribution must have positive total mass.")
        for k in self.typo_distribution:
            self.typo_distribution[k] /= total
    
    def _get_neighbours_with_orientation(self, char: str) -> List[str]:
        """
        Return neighbours of `char` from keyboard.
        Horizontal neighbours are repeated more often than vertical ones
        according to `horizontal_vs_vertical` (h_weight, v_weight).
        """
        h_weight, v_weight = self.horizontal_vs_vertical

        # find position(s) of char on keyboard
        positions = []
        for r_idx, row in enumerate(self.keyboard):
            for c_idx, k in enumerate(row):
                if k == char:
                    positions.append((r_idx, c_idx))

        if not positions:
            return []

        candidates: List[str] = []
        for r_idx, c_idx in positions:
            # horizontal neighbors in same row
            if c_idx > 0:
                left = self.keyboard[r_idx][c_idx - 1]
                if left:
                    candidates.extend([left] * max(1, int(round(h_weight))))
            if c_idx < len(self.keyboard[r_idx]) - 1:
                right = self.keyboard[r_idx][c_idx + 1]
                if right:
                    candidates.extend([right] * max(1, int(round(h_weight))))

            # vertical neighbors (same column index, row up/down)
            if r_idx > 0 and c_idx < len(self.keyboard[r_idx - 1]):
                up = self.keyboard[r_idx - 1][c_idx]
                if up:
                    candidates.extend([up] * max(1, int(round(v_weight))))
            if r_idx < len(self.keyboard) - 1 and c_idx < len(self.keyboard[r_idx + 1]):
                down = self.keyboard[r_idx + 1][c_idx]
                if down:
                    candidates.extend([down] * max(1, int(round(v_weight))))

        return candidates
    
    @staticmethod
    def _round_it(number: float, position: int = 0) -> float:
        factor = 10 ** position
        return int(number * factor + 0.5) / factor

    def _get_weights_of_idx(self, word: str) -> List[float]:
        n = len(word)
        if n == 1:
            return [0.0]
        elif n == 2:
            return [0.0, 1.0]

        weights = [0.0]
        for i in range(0, n - 1):
            weight = 0.1 + (0.2 - 0.1) * (i / (n - 2))
            weights.append(weight)

        weights = [self._round_it(p / sum(weights), 2) for p in weights]
        return weights

    def _belongs_to_hand(self, char: str) -> Optional[str]:
        if char in self.left_right["left"]:
            return "left"
        if char in self.left_right["right"]:
            return "right"
        return None
    
    def _replace(self, word: str) -> Tuple[str, Optional[Tuple[int, ...]]]:
        word_list = list(word)
        weights = self._get_weights_of_idx(word)
        idx, char = random.choices(list(enumerate(word_list)), weights=weights, k=1)[0]

        neighbours = self._get_neighbours_with_orientation(char.lower())
        if neighbours:
            replacement = random.choice(neighbours)
            if char.isupper():
                replacement = replacement.upper()

            # keep your original same-letter logic
            for i in range(idx - 1, -1, -1):
                if word_list[idx] != word_list[i]:
                    if (idx - i) == 2:
                        word_list[i + 1] = replacement
                        word_list[idx] = replacement
                        return "".join(word_list), (idx,)
                    break

            if idx != len(word_list) - 1 and word_list[idx] == word_list[idx + 1]:
                word_list[idx + 1] = replacement

            word_list[idx] = replacement

        return "".join(word_list), (idx,)

    def _delete(self, word: str) -> Tuple[str, Optional[Tuple[int, ...]]]:
        word_list = list(word)
        weights = self._get_weights_of_idx(word)
        idx, _ = random.choices(list(enumerate(word_list)), weights=weights, k=1)[0]
        del word_list[idx]
        return "".join(word_list), (idx,)

    def _insert(self, word: str) -> Tuple[str, Optional[Tuple[int, ...]]]:
        word_list = list(word)
        weights = self._get_weights_of_idx(word)
        idx, char = random.choices(list(enumerate(word_list)), weights=weights, k=1)[0]

        neighbours = self._get_neighbours_with_orientation(char.lower())
        if neighbours:
            inserted = random.choice(neighbours)
            if char.isupper():
                inserted = inserted.upper()
            word_list.insert(idx + 1, inserted)

        return "".join(word_list), (idx + 1,)

    def _transpose(self, word: str) -> Tuple[str, Optional[Tuple[int, ...]]]:
        # your original transpose logic, using belongs_to_hand
        word_list = list(word[1:])
        if len(word) <= 1:
            return word, None

        transposable: List[Tuple[int, int]] = []

        for i in range(len(word_list) - 1):
            first_hand = self._belongs_to_hand(word_list[i].lower())
            second_hand = self._belongs_to_hand(word_list[i + 1].lower())
            if (first_hand and second_hand and first_hand != second_hand) or word_list[i + 1] == " ":
                transposable.append((i, i + 1))

        if not transposable:
            return word, None

        weights = self._get_weights_of_idx(transposable)
        if sum(weights) == 0:
            return word, None

        first, second = random.choices(transposable, weights=weights, k=1)[0]
        word_list[first], word_list[second] = word_list[second], word_list[first]

        return word[0] + "".join(word_list), (first, second)
    
    def _is_valid_operation(self, word_history, idxs, typo_function: TypoFunc):
        if len(word_history) == 1:
            return True

        for prev_operation, prev_idx in word_history[1:]:
            if prev_operation is self._replace:
                if typo_function is self._insert and (prev_idx[0] + 1 == idxs[0]):
                    return False
                if (prev_idx == idxs) or any(i in idxs for i in prev_idx):
                    return False

            if prev_operation is self._delete:
                if typo_function is self._transpose and (prev_idx[0] == idxs[1]):
                    return False

            if prev_operation is self._insert:
                if (typo_function in {self._replace, self._delete}) and (
                    (prev_idx == idxs) or (prev_idx[0] - 1 == idxs[0])
                ):
                    return False
                elif (typo_function is self._insert) and (
                    (prev_idx == idxs) or (prev_idx[0] + 1 == idxs[0])
                ):
                    return False
                elif (typo_function is self._transpose) and (
                    (prev_idx == idxs) or any(i in idxs for i in prev_idx)
                ):
                    return False

            if prev_operation is self._transpose:
                if (typo_function in {self._transpose, self._insert, self._delete}) and (
                    (prev_idx == idxs) or any(i in idxs for i in prev_idx)
                ):
                    return False

        return True

    def tokenize_sentences(
        self,
        text: str,
        stanza_pipeline: Optional[object] = None,
        use_gpu: bool = True,
    ) -> List[str]:
        """
        Wrapper around multypo.tokenization.tokenize_sentences that uses
        this generator's language.
        """
        return _tokenize_sentences(
            text=text,
            lang=self.language,
            stanza_pipeline=stanza_pipeline,
            use_gpu=use_gpu,
        )
    
    def insert_typos(
        self,
        text: str,
        typo_rate: float,
        max_tries: int = 1000,
    ) -> str:
        """
        Insert typos into `text`. typo_rate is fraction of words to corrupt.
        """
        words = [[word] for word in text.split(" ")]
        typos_target = self._round_it(typo_rate * len(words))

        if typos_target < 0.5:
            return text

        # word weights ~ sqrt(len(word))
        weights = [math.sqrt(len(word[0])) for word in words]
        if sum(weights) == 0:
            return text
        weights = [self._round_it(w / sum(weights), 2) for w in weights]

        typoed = 0
        tries = 0
        new_word = ""
        ignore = True
        is_valid = False

        typo_funcs = {
            "delete": self._delete,
            "insert": self._insert,
            "replace": self._replace,
            "transpose": self._transpose,
        }

        typo_names = list(self.typo_distribution.keys())
        typo_weights = [self.typo_distribution[name] for name in typo_names]

        while typoed < typos_target and tries <= max_tries:
            # sample word that is not in IGNORE set (if enabled)
            while ignore and tries <= max_tries:
                tries += 1
                word_idx, word_info = random.choices(
                    list(enumerate(words)), weights=weights, k=1
                )[0]
                word = word_info[0]

                if len(word) <= 1:
                    ignore = True
                elif self.use_excluding_set and any(
                    str(i) in word.lower() for i in self.ignore_set
                ):
                    ignore = True
                else:
                    ignore = False

            if tries > max_tries:
                break

            # apply typo
            while ((new_word == word) or not is_valid) and tries <= max_tries:
                tries += 1
                typo_name = random.choices(typo_names, weights=typo_weights, k=1)[0]
                typo_function = typo_funcs[typo_name]

                # transpose special case, same as your original
                if (typo_function is self._transpose
                    and word_idx != len(words) - 1
                    and " " not in word):
                    word = word + " "

                new_word, idxs = typo_function(word)
                if new_word != word:
                    is_valid = self._is_valid_operation(words[word_idx], idxs, typo_function)

            if tries > max_tries:
                break

            # update history
            weights[word_idx] *= 0.5
            words[word_idx][0] = new_word
            words[word_idx].append((typo_function, idxs))

            typoed += 1
            ignore = True
            is_valid = False
            new_word = ""

        final_words = [w[0] for w in words]
        result = ""
        for w in final_words:
            if " " in w:
                result += w
            else:
                result += (w + " ")
        return result.strip()
    
    def insert_typos_in_text(
        self,
        text: str,
        typo_rate: float,
        max_tries: int = 1000,
        sentence_tokenize: bool = True,
        stanza_pipeline: Optional[object] = None,
        use_gpu: bool = True,
    ) -> str:
        """
        Insert typos into a potentially multi-sentence text.

        If `sentence_tokenize` is True (default), we first split the text
        into sentences using language-specific rules, apply `insert_typos`
        to each sentence independently, and then join them with spaces.

        This mirrors your previous pattern:
            sentences = tokenize_sentences(...)
            " ".join(insert_typos(sentence) for sentence in sentences)
        """
        if not sentence_tokenize:
            # treat the whole text as a single "sentence"
            return self.insert_typos(text=text, typo_rate=typo_rate, max_tries=max_tries)

        sentences = self.tokenize_sentences(
            text,
            stanza_pipeline=stanza_pipeline,
            use_gpu=use_gpu,
        )
        if not sentences:
            return text

        typoed_sentences = [
            self.insert_typos(s, typo_rate=typo_rate, max_tries=max_tries)
            for s in sentences
        ]
        return " ".join(typoed_sentences)


# multypo/core.py (continued)

# Global-ish mutable defaults for simple functional API
_GLOBAL_TYPO_DISTRIBUTION = DEFAULT_TYPO_DISTRIBUTION.copy()
_GLOBAL_KEYBOARDS = KEYBOARDS  # alias; users can add new


def get_supported_languages():
    """
    Return a list of supported languages (name + code).

    Includes both built-in and user-registered languages.
    """
    return [{"name": name, "code": code} for name, code in LANGUAGES.items()]


def register_keyboard_layout(
    lang_code: str,
    language: str,
    keyboard_rows: List[List[str]],
    left_keys: Optional[List[str]] = None,
    right_keys: Optional[List[str]] = None,
    ignoring_set: Optional[Iterable[str]] = None,
):
    """
    Register or override a keyboard layout + language mapping.

    Parameters
    ----------
    lang_code : str
        Short language code (e.g. "en", "de", "en-custom").
    language : str
        Human-readable language name used in `generate_typos(language=...)`
        and `MultiTypoGenerator(language=...)`. For new languages, this
        MUST NOT clash with any existing key in LANGUAGES.
        Example: "english-custom".
    keyboard_rows : List[List[str]]
        Keyboard layout as list of rows; each row is a list of string keys.
    left_keys, right_keys : Optional[List[str]]
        Optional sets of keys for left/right-hand assignment.
        If omitted, transpose behaviour that relies on hands may be limited.
    ignoring_set : Optional[Iterable[str]]
        Optional set/list of strings that should be excluded from typo
        insertion (e.g. number words, numeric tokens, special markers).
    """

    # 1) Register / validate language name → lang_code mapping
    if language in LANGUAGES and LANGUAGES[language] != lang_code:
        # You asked for "should not be the same as any existing pre-supported language name"
        # so we error out if it already exists.
        raise ValueError(
            f"Language name '{language}' is already registered with "
            f"lang_code='{LANGUAGES[language]}'. Please choose a different "
            f"language name for custom layouts (e.g. 'english-custom')."
        )

    LANGUAGES[language] = lang_code

    # 2) Keyboard layout
    _GLOBAL_KEYBOARDS[lang_code] = keyboard_rows
    KEYBOARDS[lang_code] = keyboard_rows  # keep base dict in sync

    # 3) Left/right-hand mapping
    if left_keys is not None and right_keys is not None:
        LEFT_RIGHTS[lang_code] = {"left": left_keys, "right": right_keys}
    else:
        # ensure there is at least a default entry
        LEFT_RIGHTS.setdefault(lang_code, {"left": [], "right": []})

    # 4) Ignoring set
    if ignoring_set is not None:
        IGNORES[lang_code] = set(ignoring_set)
    else:
        IGNORES.setdefault(lang_code, set())


def set_default_typo_distribution(distribution: Dict[str, float]):
    """
    Update the global default typo distribution used by generate_typos().
    Keys must be subset of {'delete', 'insert', 'replace', 'transpose'}.
    """
    allowed = {"delete", "insert", "replace", "transpose"}
    if not set(distribution.keys()).issubset(allowed):
        raise ValueError(f"Allowed keys are {allowed}, got {set(distribution.keys())}")

    total = sum(distribution.values())
    if total <= 0:
        raise ValueError("Distribution must have positive total mass.")

    for k in distribution:
        distribution[k] /= total
    _GLOBAL_TYPO_DISTRIBUTION.clear()
    _GLOBAL_TYPO_DISTRIBUTION.update(distribution)


def generate_typos(
    text: str,
    language: str,
    typo_rate: float,
    use_excluding_set: bool = True,
    typo_distribution: Optional[Dict[str, float]] = None,
    horizontal_vs_vertical: Tuple[float, float] = (9.0, 1.0),
    max_tries: int = 1000,
    sentence_tokenize: bool = True,
    stanza_pipeline: Optional[object] = None,
    use_gpu: bool = True,
) -> str:
    """
    Convenience wrapper for MultiTypoGenerator.insert_typos_in_text().

    By default, we sentence-tokenize the input text, apply typos per sentence,
    and join them back together with spaces.
    """
    dist = typo_distribution or _GLOBAL_TYPO_DISTRIBUTION
    gen = MultiTypoGenerator(
        language=language,
        use_excluding_set=use_excluding_set,
        typo_distribution=dist.copy(),
        horizontal_vs_vertical=horizontal_vs_vertical,
    )

    return gen.insert_typos_in_text(
        text=text,
        typo_rate=typo_rate,
        max_tries=max_tries,
        sentence_tokenize=sentence_tokenize,
        stanza_pipeline=stanza_pipeline,
        use_gpu=use_gpu,
    )


