# MULTYPO
### *Multilingual Keyboard-Aware Typo Generator for NLP Robustness*

[![PyPI version](https://img.shields.io/pypi/v/multypo.svg)](https://pypi.org/project/multypo/)
![Python >=3.8](https://img.shields.io/badge/python-%3E%3D3.8-blue)

---

## 🚀 Overview

**MULTYPO** provides realistic, keyboard-based typographical noise across **12+ languages**, enabling robust evaluation, stress testing, and synthetic data generation for NLP and LLM systems.

It was originally designed for multilingual robustness research, and is now packaged for public use.

### 🔥 Key Features

- **Multilingual support** (English, German, French, Russian, Greek, Arabic, Hindi, Bengali, Tamil, Armenian, Georgian, Hebrew)
- **Keyboard-aware typo modeling**  
  - `replace`: wrong nearby key  
  - `insert`: accidental double press  
  - `delete`: skipped key  
  - `transpose`: swapped left/right-hand keys  
- **Horizontal + vertical keyboard neighbors** with configurable weights
- **Configurable typo distributions**
- **Built-in excluding sets** (numbers, number words, etc.)
- **Register custom keyboards and ignoring sets**

---

## 📦 Installation

```bash
pip install multypo
```

## 📝 Quick Start

### Generate typos in English

```python
from multypo import generate_typos

text = "This is an example sentence. And here is another one."

noisy = generate_typos(
    text=text,
    language="english",
    typo_rate=0.25,
)

print(noisy)
```

Example output:

```
Thi is an ezample sentence. Amd here is anoter one.
```

### 🛠️ Advanced Usage: MultiTypoGenerator

```python
from multypo import MultiTypoGenerator

gen = MultiTypoGenerator(
    language="english",
    use_excluding_set=True,
    typo_distribution={"delete":0.2, "insert":0.2, "replace":0.4, "transpose":0.2},
    horizontal_vs_vertical=(2.0, 1.0),
)

typoed = gen.insert_typos_in_text(
    "This is a test sentence. Second sentence here.",
    typo_rate=0.3
)

print(typoed)
```

### 🎹 Custom Keyboard Layouts

```python
from multypo import register_keyboard_layout

custom_keyboard = [
    list("qwertyuiop"),
    list("asdfghjkl"),
    list("zxcvbnm"),
]

register_keyboard_layout(
    lang_code="en-custom",
    language="english-custom",
    keyboard_rows=custom_keyboard,
    left_keys=list("qwertasdfgzxcvb"),
    right_keys=list("yuiophjklbnm"),
    ignoring_set={"million", "billion", "42"},
)
```

Use like any other language:

```python
generate_typos("This is custom.", language="english-custom", typo_rate=0.3)
```

### 📏 Adjust Typo Type Probabilities

Set global defaults:

```python
from multypo import set_default_typo_distribution

set_default_typo_distribution({
    "delete": 0.1,
    "insert": 0.2,
    "replace": 0.5,
    "transpose": 0.2,
})

```

Or override per call:

```python
noisy = generate_typos(
    text="Example",
    language="english",
    typo_rate=0.3,
    typo_distribution={"delete":0.2, "insert":0.2, "replace":0.4, "transpose":0.2},
)
```

### 🌍 Supported Languages

```python

from multypo import get_supported_languages

print(get_supported_languages())

```

**Of course, you can always register new languages and their custom keyboard layouts!**


### 📜 License

MIT License.


### Citation

```
@misc{liu2025evaluating,
      title={Evaluating Robustness of Large Language Models Against Multilingual Typographical Errors}, 
      author={Yihong Liu and Raoyuan Zhao and Lena Altinger and Hinrich Schütze and Michael A. Hedderich},
      year={2025},
      eprint={2510.09536},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2510.09536}, 
}
```

