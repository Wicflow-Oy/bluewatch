"""Registry IDs and VAT numbers: checksums, normal forms, and finding them in page text.

Supported registries: Finland (PRH business ID), Norway (Brreg org number), Estonia (RIK registry
code). Swedish and Danish numbers are recognised only so a page's VAT number can be reported; there
is no keyless SE or DK registry to resolve them against.

Page tokens use one format everywhere: "FI:2855258-7" for a registry ID, "VAT:FI28552587" for a VAT
number.
"""

from __future__ import annotations

import re

_FI_WEIGHTS = (7, 9, 10, 5, 8, 4, 2)
_NO_WEIGHTS = (3, 2, 7, 6, 5, 4, 3, 2)
_EE_WEIGHTS = ((1, 2, 3, 4, 5, 6, 7), (3, 4, 5, 6, 7, 8, 9))

# Pages write IDs with any dash; only the ASCII hyphen is canonical.
_DASHES = dict.fromkeys([*range(0x2010, 0x2016), 0x2212], "-")


def _digits(s: str) -> str:
    return re.sub(r"[\s.\-]", "", s)


def _weighted(digits: str, weights: tuple[int, ...]) -> int:
    return sum(int(d) * w for d, w in zip(digits, weights, strict=True))


def _fi_canonical(s: str) -> str | None:
    """'1234567-8', '12345678', 'FI12345678' or the old six-digit form → '1234567-8' (unchecked)."""
    s = s.strip().upper().translate(_DASHES).removeprefix("FI").strip()
    m = re.fullmatch(r"(\d{6,7})-?(\d)", s.replace(" ", ""))
    return f"{m.group(1).zfill(7)}-{m.group(2)}" if m else None


def valid_fi_business_id(s: str) -> bool:
    """Finnish business ID (Y-tunnus): mod 11 with weights 7,9,10,5,8,4,2; remainder 1 is never issued."""
    canon = _fi_canonical(s or "")
    if canon is None:
        return False
    remainder = _weighted(canon[:7], _FI_WEIGHTS) % 11
    if remainder == 1:
        return False
    return (0 if remainder == 0 else 11 - remainder) == int(canon[8])


def valid_no_orgnr(s: str) -> bool:
    """Norwegian organisation number: 9 digits, mod 11 with weights 3,2,7,6,5,4,3,2; check 10 is never issued."""
    d = _digits(s or "")
    if not re.fullmatch(r"\d{9}", d):
        return False
    check = 11 - _weighted(d[:8], _NO_WEIGHTS) % 11
    if check == 10:
        return False
    return (0 if check == 11 else check) == int(d[8])


def valid_ee_registry_code(s: str) -> bool:
    """Estonian registry code: 8 digits; check digit as for the personal code (weights 1..7, then 3..9)."""
    d = _digits(s or "")
    if not re.fullmatch(r"\d{8}", d):
        return False
    for weights in _EE_WEIGHTS:
        remainder = _weighted(d[:7], weights) % 11
        if remainder < 10:
            return remainder == int(d[7])
    return int(d[7]) == 0


def _valid_se_orgnr(d: str) -> bool:
    """Swedish organisation number: 10 digits, Luhn."""
    if not re.fullmatch(r"\d{10}", d):
        return False
    total = 0
    for i, ch in enumerate(d):
        n = int(ch) * (2 if i % 2 == 0 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def normalise_id(country: str, s: str) -> str | None:
    """The canonical registry ID, or None when the format or checksum is wrong."""
    country = (country or "").upper()
    if not s:
        return None
    if country == "FI":
        canon = _fi_canonical(s)
        return canon if canon and valid_fi_business_id(canon) else None
    d = _digits(s.upper().removeprefix(country).removesuffix("MVA"))
    if country == "NO":
        return d if valid_no_orgnr(d) else None
    if country == "EE":
        return d if valid_ee_registry_code(d) else None
    if country == "SE":
        return d if _valid_se_orgnr(d) else None
    if country == "DK":
        return d if re.fullmatch(r"[1-9]\d{7}", d) else None
    return None


def normalise_vat(s: str) -> str | None:
    """Canonical VAT number (FI12345678, NO123456789MVA, EE101234567, SE556677889901, DK12345678) or None."""
    compact = re.sub(r"[\s.\-]", "", (s or "").upper())
    m = re.fullmatch(r"(FI|NO|EE|SE|DK)(\d+)(MVA)?", compact)
    if not m:
        return None
    cc, digits, mva = m.groups()
    if cc == "FI" and len(digits) == 8 and valid_fi_business_id(digits):
        return f"FI{digits}"
    if cc == "NO" and valid_no_orgnr(digits):
        return f"NO{digits}MVA"
    if cc == "EE" and re.fullmatch(r"10\d{7}", digits) and not mva:
        return f"EE{digits}"
    if cc == "SE" and len(digits) == 12 and digits.endswith("01") and _valid_se_orgnr(digits[:10]):
        return f"SE{digits}"
    if cc == "DK" and re.fullmatch(r"[1-9]\d{7}", digits) and not mva:
        return f"DK{digits}"
    return None


def vat_to_registry_id(vat: str) -> tuple[str, str] | None:
    """(country, registry ID) the VAT number encodes. Estonian VAT numbers are separate numbers: None."""
    nvat = normalise_vat(vat)
    if nvat is None:
        return None
    cc, body = nvat[:2], nvat[2:]
    if cc == "FI":
        return "FI", f"{body[:7]}-{body[7]}"
    if cc == "NO":
        return "NO", body.removesuffix("MVA")
    if cc == "SE":
        return "SE", body[:10]
    if cc == "DK":
        return "DK", body
    return None


def parse_token(token: str) -> tuple[str, str] | None:
    """'FI:2855258-7' → ('FI', '2855258-7'); 'VAT:FI28552587' → the registry ID it encodes; a bare ID → None."""
    prefix, _, value = (token or "").partition(":")
    if prefix == "VAT":
        return vat_to_registry_id(value)
    if value and normalise_id(prefix, value) is not None:
        return prefix, normalise_id(prefix, value)
    return None


# Labels that make a bare number on a page an identifier. Norwegian, Estonian and Swedish numbers
# need one: without it, nine- and eight-digit numbers on a page are usually phone or order numbers.
_LABEL = r"(?:org\.?\s*nr\.?|org\.?\s*no\.?|organisasjonsnummer|organisationsnummer|org(?:anisation)?\s+number)"
_NO_RE = re.compile(_LABEL + r"\s*[:.]?\s*((?:\d[ .]?){8}\d)(?!\d)", re.I)
_NO_VAT_RE = re.compile(r"\bNO\s?((?:\d[ .]?){8}\d)\s?MVA\b", re.I)
_EE_RE = re.compile(
    r"(?:registrikood|reg\.?\s*kood|registry\s+code|reg(?:istration)?\.?\s+(?:code|no\.?|nr\.?))\s*[:.]?\s*(\d{8})\b",
    re.I,
)
_EE_VAT_RE = re.compile(r"\bEE\s?(10\d{7})\b")
_SE_RE = re.compile(_LABEL + r"\s*[:.]?\s*(\d{6})-?(\d{4})\b", re.I)
_SE_VAT_RE = re.compile(r"\bSE\s?(\d{10}01)\b")
_DK_RE = re.compile(r"\b(?:CVR(?:[\s.\-]*nr\.?)?|DK)\s*[:.]?\s*([1-9]\d{7})\b", re.I)
_FI_RE = re.compile(r"(?<![\d\-/.])(\d{7})-(\d)(?![\d\-/])")
_FI_VAT_RE = re.compile(r"\bFI\s?(\d{8})\b")
# More bare FI-format numbers than this on one page are product or reference codes, not IDs.
_MAX_BARE_FI = 5


def find_ids(text: str) -> list[str]:
    """Registry IDs and VAT numbers on a page, checksum-valid only, in page order, as tokens."""
    text = (text or "").translate(_DASHES)
    found: list[str] = []

    def add(token: str) -> None:
        if token not in found:
            found.append(token)

    for m in _FI_VAT_RE.finditer(text):
        if (vat := normalise_vat("FI" + m.group(1))) is not None:
            add(f"VAT:{vat}")
            add(f"FI:{vat_to_registry_id(vat)[1]}")
    bare_fi = {f"{m.group(1)}-{m.group(2)}" for m in _FI_RE.finditer(text)}
    bare_fi = {x for x in bare_fi if valid_fi_business_id(x)}
    if len(bare_fi) <= _MAX_BARE_FI:
        for m in _FI_RE.finditer(text):
            if f"{m.group(1)}-{m.group(2)}" in bare_fi:
                add(f"FI:{m.group(1)}-{m.group(2)}")
    for m in _NO_VAT_RE.finditer(text):
        if (vat := normalise_vat("NO" + m.group(1) + "MVA")) is not None:
            add(f"VAT:{vat}")
            add(f"NO:{vat_to_registry_id(vat)[1]}")
    for m in _NO_RE.finditer(text):
        if (nid := normalise_id("NO", m.group(1))) is not None:
            add(f"NO:{nid}")
    for m in _SE_RE.finditer(text):
        if (nid := normalise_id("SE", m.group(1) + m.group(2))) is not None:
            add(f"SE:{nid}")
    for m in _SE_VAT_RE.finditer(text):
        if (vat := normalise_vat("SE" + m.group(1))) is not None:
            add(f"VAT:{vat}")
            add(f"SE:{vat_to_registry_id(vat)[1]}")
    for m in _EE_RE.finditer(text):
        if (nid := normalise_id("EE", m.group(1))) is not None:
            add(f"EE:{nid}")
    for m in _EE_VAT_RE.finditer(text):
        add(f"VAT:EE{m.group(1)}")
    for m in _DK_RE.finditer(text):
        add(f"DK:{m.group(1)}")
        if m.group(0).upper().startswith("DK"):
            add(f"VAT:DK{m.group(1)}")
    return found
