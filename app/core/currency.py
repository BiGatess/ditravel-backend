from decimal import Decimal, InvalidOperation
from typing import Any


def normalize_vnd_price(value: Any) -> Decimal | None:
    if value is None:
        return None

    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return value

    if Decimal("0") < amount < Decimal("1000"):
        return amount * Decimal("1000")
    return amount
