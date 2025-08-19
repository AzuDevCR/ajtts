from __future__ import annotations
import re
from typing import Callable, Optional

try:
    from num2words import num2words
    _HAS_NUM2WORDS = True
except Exception:
    _HAS_NUM2WORDS = False

Digits_ES = {
    "0": "cero", "1": "uno", "2": "dos", "3": "tres", "4": "cuatro",
    "5": "cinco", "6": "seis", "7": "siete", "8": "ocho", "9": "nueve",
}

def _num2words_es(n: int) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    return num2words(n, lang="es")

def _say_digits_es(s: str) -> str:
    return " ".join(Digits_ES.get(ch, ch) for ch in s)

def _parse_number_token(token: str) -> Optional[int]:
    t = token.replace(" ", "")
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.split(",")[0].replace(".", "")
        else:
            t = t.split(".")[0].replace(",", "")
    else:
        t = t.replace(".", "").split(",")[0]
    if t.isdigit():
        try:
            return int(t)
        except Exception:
            return None
    return None

def normalize_es_numbers(text: str,
                         currency_default: str="CRC",
                         digit_by_digit_threshold: int=7,
                         logger: Optional[Callable[[str], None]]=None) -> str:
    """
    Normalize numbers in Spanish text:
    - percentages: "45%" -> "cuarenta y cinco por ciento"
    - currency: ₡, $, € (integer + optional decimals as 'con ...')
    - years: 1000..2099 -> words
    - decimals: "3,5" -> "tres coma cinco"
    - integers up to threshold -> words; longer -> digit-by-digit
    Skips URLs/emails/times (hh:mm) and tokens with letters.
    """
    if not text:
        return text
    
    def log(msg: str) -> None:
        if logger: logger(msg)

    # Skip ULRs|emails|times
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

    #percentages
    def _pct_cb(m: re.Match) -> str:
        num = m.group("num")
        #decimals in percentage = "coma"
        if "," in num or "." in num:
            parts = re.split(r"[,.]", num, maxsplit=1)
            ip = parts[0]
            dp = parts[1] if len(parts) > 1 else ""
            ipw = _num2words_es(int(ip)) if ip.isdigit() else ip
            #decimal part read digits
            dpw = _say_digits_es(dp) if dp else ""
            mid = " coma " + dpw if dpw else ""
            return f"{ipw}{mid} por ciento"
        #integer
        if num.isdigit():
            return f"{_num2words_es(int(num))} por ciento"
        return m.group(0)
    
    text = re.sub(r"(?P<num>\d+(?:[.,]\d+)?)\s*%", _pct_cb, text)

    #Currency CRC, USD, EUR integer with optional decimals
    def _money_cb(m: re.Math) -> str:
        sign = m.group("sign")
        numt = m.group("amt")
        #normalize number token for integer part
        ip = _parse_number_token(numt)
        if ip is None:
            return m.group(0)
        #decimals
        dec_m = re.search(r"[,.](\d{1,2})\b", numt)
        ipw = _num2words_es(ip)
        decw = ""
        if dec_m:
            dec = dec_m.group(1)
            if dec.startswith("0"):
                decw = " con " + _say_digits_es(dec)
            else:
                try:
                    decw = " con " + _num2words_es(int(dec))
                except Exception:
                    decw = " con " + _say_digits_es(dec)

        currency = currency_default
        if sign in ("$", "US$", "USD"):
            currency = "dólares"
        elif sign in ("€", "EUR"):
            currency = "euros"
        elif sign in ("₡", "CRC"):
            currency = "colones"

        return f"{ipw} {currency}{decw}"
    
    MONEY_RE = re.compile(r"(?P<sign>₡|CRC|\$|US\$|USD|€|EUR)\s*(?P<amt>\d[\d\.,]*)")
    text = MONEY_RE.sub(_money_cb, text)

    #Years 1000..2099
    def _year_cb(m: re.Math) -> str:
        y = int(m.group(0))
        return _num2words_es(y)
    text = re.sub(r"\b(1\d{3}|20\d{2})\b", _year_cb, text)

    #Decimals in general
    def _dec_cb(m: re.Match) -> str:
        tok = m.group(0)
        ip_str, dp_str = re.split(r"[,.]", tok, maxsplit=1)
        if not ip_str.isdigit():
            return tok
        ipw = _num2words_es(int(ip_str))
        # decimal: if leading 0 or more than 2 digits, read digits; else num2words
        if dp_str.startswith("0") or len(dp_str) > 2 or not dp_str.isdigit():
            dpw = _say_digits_es(dp_str)
        else:
            try:
                dpw = _num2words_es(int(dp_str))
            except Exception:
                dpw = _say_digits_es(dp_str)
        sep = " coma " if "," in tok else " punto "
        return f"{ipw}{sep}{dpw}"
    text = re.sub(r"\b\d+[.,]\d+\b", _dec_cb, text)

    # Long integers 7+ -> digit by digit
    def _long_cb(m: re.Match) -> str:
        s = m.group(0)
        return _say_digits_es(s)
    text = re.sub(r"\b\d{7,}\b", _long_cb, text)

    #Integers up to threshold
    def _int_cb(m: re.Match) -> str:
        s = m.group(0)
        try:
            n = int(s)
            if len(s) >= digit_by_digit_threshold:
                return _say_digits_es(s)
            return _num2words_es(n)
        except Exception:
            return s
    text = re.sub(r"\b\d+\b", _int_cb, text)

    #Unmask placeholders
    for key, val in reversed(placeholders):
        text = text.replace(key, val)

    return text
