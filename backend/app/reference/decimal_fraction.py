"""Inch decimal <-> fraction conversion, computed directly (1/64ths).

Real asset, not a placeholder: this is exact arithmetic, so it needs no
lookup file. Stands in for Unilog_Master_UOM_Standards' Decimal_Fraction
sheet, which lists the same 63 values (1/64 .. 63/64) computed the same way.
"""

from fractions import Fraction

_DENOMINATOR = 64


def decimal_to_fraction(decimal_value: float) -> str:
    """0.5 -> '1/2', 50.25 -> '50-1/4', 24.0 -> '24'."""
    whole = int(decimal_value)
    remainder = round(decimal_value - whole, 6)
    if remainder == 0:
        return str(whole)

    frac = Fraction(round(remainder * _DENOMINATOR), _DENOMINATOR).limit_denominator(_DENOMINATOR)
    if frac.numerator == 0:
        return str(whole)
    if whole == 0:
        return f"{frac.numerator}/{frac.denominator}"
    return f"{whole}-{frac.numerator}/{frac.denominator}"


def fraction_to_decimal(fraction_str: str) -> float:
    """'1/2' -> 0.5, '50-1/4' -> 50.25."""
    fraction_str = fraction_str.strip()
    if "-" in fraction_str:
        whole_part, frac_part = fraction_str.split("-", 1)
        whole = int(whole_part)
    else:
        whole = 0
        frac_part = fraction_str

    if "/" in frac_part:
        num, denom = frac_part.split("/")
        return whole + int(num) / int(denom)
    return whole + float(frac_part)
