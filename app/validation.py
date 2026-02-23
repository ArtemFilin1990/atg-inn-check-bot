import re


def validate_inn(inn: str) -> bool:
    """Return True if inn is a valid 10- or 12-digit INN string."""
    if not re.fullmatch(r"\d{10}|\d{12}", inn):
        return False
    digits = [int(c) for c in inn]
    if len(digits) == 10:
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        check = sum(w * d for w, d in zip(weights, digits[:9])) % 11 % 10
        return digits[9] == check
    # 12-digit
    w11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    w12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    c11 = sum(w * d for w, d in zip(w11, digits[:10])) % 11 % 10
    c12 = sum(w * d for w, d in zip(w12, digits[:11])) % 11 % 10
    return digits[10] == c11 and digits[11] == c12
