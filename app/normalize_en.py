# AquaJupiterTTS
# Copyright (C) 2025  AzuDevCR (INL Creations)
# Licensed under GPLv3 (see LICENSE file for details).

# AquaJupiterTTS - English normalizer

from __future__ import annotations
import re
from typing import Callable, Optional

try:
    from num2words import num2words
    _HAS_NUM2WORDS = True
except Exception:
    _HAS_NUM2WORDS = False

Digits_EN = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}

def _num2words_en(n: int) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    
    return num2words(n, lang="en")

def _say_digits_en(s: str) -> str:
    return " ".join(Digits_EN.get(ch, ch) for ch in s)

def _parse_number_token(token: str) -> Optional[int]:
    t = token.replace(" ", "")
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.split(",")[0].replace(".", "")
        else:
            t = t.split(".")[0].replace(",", "")
    else:
        t = t.replace(",", "").split(".")[0]
    if t.isdigit():
        try:
            return int(t)
        except Exception:
            return None
    return None

def _year_to_words_en(y: int) -> str:
    # 1000–1999 → “nineteen eighty-four” (19 + 84)
    if 1000 <= y <= 1999:
        first = y // 100
        last = y % 100
        return f"{_num2words_en(first)} {_num2words_en(last)}"
    # 2000–2009 → “two thousand [x]”
    if 2000 <= y <= 2009:
        tail = y - 2000
        return "two thousand" if tail == 0 else f"two thousand {_num2words_en(tail)}"
    # 2010–2099 → “twenty [x]”
    if 2010 <= y <= 2099:
        return f"twenty {_num2words_en(y % 100)}"
    
    return _num2words_en(y)

def normalize_en_numbers(
    text: str,
    currency_default: str = "USD",
    digit_by_digit_threshold: int = 7,
    logger: Optional[Callable[[str], None]] = None,
) -> str:
    if not text:
        return text

    def log(msg: str) -> None:
        if logger:
            logger(msg)

    
    URL_RE = re.compile(r"(https?://\S+)", flags=re.IGNORECASE)
    EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
    TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d(:[0-5]\d)?\b")

    placeholders = []
    def _mask(pattern: re.Pattern, tag: str, s: str) -> str:
        def _rep(m):
            placeholders.append((f"__{tag}_{len(placeholders)}__", m.group(0)))
            return placeholders[-1][0]
        return pattern.sub(_rep, s)

    text = _mask(URL_RE, "URL", text)
    text = _mask(EMAIL_RE, "MAIL", text)
    text = _mask(TIME_RE, "TIME", text)

    text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)   # 3D  -> 3 D
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)   # D3  -> D 3


    
    def _pct_cb(m: re.Match) -> str:
        num = m.group("num")
        if "," in num or "." in num:
            ip, dp = re.split(r"[,.]", num, maxsplit=1)
            ipw = _num2words_en(int(ip)) if ip.isdigit() else ip
            
            if dp and (dp.startswith("0") or not dp.isdigit()):
                dpw = _say_digits_en(dp)
            else:
                try:
                    dpw = _num2words_en(int(dp))
                except Exception:
                    dpw = _say_digits_en(dp)
            return f"{ipw} point {dpw} percent"
        if num.isdigit():
            return f"{_num2words_en(int(num))} percent"
        return m.group(0)

    text = re.sub(r"(?P<num>\d+(?:[.,]\d+)?)\s*%", _pct_cb, text)

    def _money_cb(m: re.Match) -> str:
        sign = m.group("sign")
        amt = m.group("amt")
        ip = _parse_number_token(amt)
        if ip is None:
            return m.group(0)

        dec_m = re.search(r"[,.](\d{1,2})\b", amt)
        ipw = _num2words_en(ip)
        decw = ""
        if dec_m:
            dec = dec_m.group(1)
            try:
                decw = " and " + (_num2words_en(int(dec)) + " cents")
            except Exception:
                decw = " and " + _say_digits_en(dec) + " cents"

        currency = currency_default
        if sign in ("$", "US$", "USD"):
            currency = "dollars"
        elif sign in ("€", "EUR"):
            currency = "euros"
        elif sign in ("₡", "CRC"):
            currency = "colones"
        elif sign in ("£", "GBP"):
            currency = "pounds"

        return f"{ipw} {currency}{decw}"

    MONEY_RE = re.compile(r"(?P<sign>₡|CRC|\$|US\$|USD|€|EUR|£|GBP)\s*(?P<amt>\d[\d\.,]*)")
    text = MONEY_RE.sub(_money_cb, text)

    # 1000..2099
    def _year_cb(m: re.Match) -> str:
        y = int(m.group(0))
        return _year_to_words_en(y)
    text = re.sub(r"\b(1\d{3}|20\d{2})\b", _year_cb, text)

    def _dec_cb(m: re.Match) -> str:
        tok = m.group(0)
        ip_str, dp_str = re.split(r"[,.]", tok, maxsplit=1)
        if not ip_str.isdigit():
            return tok
        ipw = _num2words_en(int(ip_str))
        if dp_str.startswith("0") or len(dp_str) > 2 or not dp_str.isdigit():
            dpw = _say_digits_en(dp_str)
        else:
            try:
                dpw = _num2words_en(int(dp_str))
            except Exception:
                dpw = _say_digits_en(dp_str)
        return f"{ipw} point {dpw}"
    text = re.sub(r"\b\d+[.,]\d+\b", _dec_cb, text)

    def _long_cb(m: re.Match) -> str:
        return _say_digits_en(m.group(0))
    text = re.sub(r"\b\d{7,}\b", _long_cb, text)

    def _int_cb(m: re.Match) -> str:
        s = m.group(0)
        try:
            n = int(s)
            if len(s) >= digit_by_digit_threshold:
                return _say_digits_en(s)
            return _num2words_en(n)
        except Exception:
            return s
    text = re.sub(r"\b\d+\b", _int_cb, text)

    for key, val in reversed(placeholders):
        text = text.replace(key, val)

    return text

def normalize_text_en(text: str) -> str:
    text = re.sub(r'(?<=\w)\.(?=\w)', " dot ", text)     # a.b → a dot b
    text = re.sub(r'(\d+)\.(\d+)', r'\1 point \2', text) # 3.14 → 3 point 14 (fallback)
    text = re.sub(r'(\d+)\+', r'\1 plus', text)          # 5+ → 5 plus
    
    text = re.sub(r'\d{10,}', "[this incredible huge number]", text)

    text = normalize_en_numbers(text)

    return re.sub(r'\s+', ' ', text).strip()