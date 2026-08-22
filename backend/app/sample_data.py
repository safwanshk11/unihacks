import csv
from pathlib import Path

from app.models import RawProductIn

# The real 211-row lighting-fixture slice of Unilog's 1,000-row raw catalog
# (Unihack_ Sample Dataset - Input.csv), filtered to rows whose Part_Manuf is
# a recognized lighting manufacturer. See backend/README.md for how it was
# derived.
_CSV_PATH = Path(__file__).parent / "data" / "lighting_input.csv"


def load_sample_products() -> list[RawProductIn]:
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            RawProductIn(
                mfg_part_num=row["Mfg_Part_Num"],
                part_desc=row["Part_Desc"],
                e1_brand=row["E1_Brand"],
                unilog_brand=row["Unilog_Brand"],
                dib_brand=row["DIB_Brand"],
                part_manuf=row["Part_Manuf"],
            )
            for row in reader
        ]


SAMPLE_PRODUCTS: list[RawProductIn] = load_sample_products()
