from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, TypedDict

from open_webui.internal.db import get_db
from open_webui.models.flight_pricing import Airport


class CityEntry(TypedDict):
    name: str
    chinese: str
    code: str
    display: str


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CITY_CODES_PATH = PROJECT_ROOT / "src" / "lib" / "utils" / "cityCodes.ts"

CITY_LIST_PATTERN = re.compile(
    r"\{\s*name:\s*'(?P<name>[^']+)',\s*chinese:\s*'(?P<chinese>[^']+)',\s*code:\s*'(?P<code>[^']+)',\s*display:\s*'(?P<display>[^']+)'\s*\}"
)

IATA_AIRPORT_NAMES = {
    "HKG": "Hong Kong International Airport",
    "ICN": "Incheon International Airport",
    "PUS": "Gimhae International Airport",
    "CJU": "Jeju International Airport",
    "NRT": "Narita International Airport",
    "KIX": "Kansai International Airport",
    "NGO": "Chubu Centrair International Airport",
    "FUK": "Fukuoka Airport",
    "CTS": "New Chitose Airport",
    "OKA": "Naha Airport",
    "TPE": "Taiwan Taoyuan International Airport",
    "KHH": "Kaohsiung International Airport",
    "RMQ": "Taichung International Airport",
    "PVG": "Shanghai Pudong International Airport",
    "PEK": "Beijing Capital International Airport",
    "CAN": "Guangzhou Baiyun International Airport",
    "SZX": "Shenzhen Bao'an International Airport",
    "CTU": "Chengdu Shuangliu International Airport",
    "XMN": "Xiamen Gaoqi International Airport",
    "HGH": "Hangzhou Xiaoshan International Airport",
    "NKG": "Nanjing Lukou International Airport",
    "TAO": "Qingdao Jiaodong International Airport",
    "KMG": "Kunming Changshui International Airport",
    "WUH": "Wuhan Tianhe International Airport",
    "XIY": "Xi'an Xianyang International Airport",
    "SIN": "Singapore Changi Airport",
    "BKK": "Suvarnabhumi Airport",
    "HKT": "Phuket International Airport",
    "CNX": "Chiang Mai International Airport",
    "UTP": "U-Tapao International Airport",
    "KBV": "Krabi International Airport",
    "KUL": "Kuala Lumpur International Airport",
    "PEN": "Penang International Airport",
    "BKI": "Kota Kinabalu International Airport",
    "LGK": "Langkawi International Airport",
    "MNL": "Ninoy Aquino International Airport",
    "CEB": "Mactan-Cebu International Airport",
    "MPH": "Godofredo P. Ramos Airport",
    "SGN": "Tan Son Nhat International Airport",
    "HAN": "Noi Bai International Airport",
    "DAD": "Da Nang International Airport",
    "CXR": "Cam Ranh International Airport",
    "CGK": "Soekarno-Hatta International Airport",
    "DPS": "Ngurah Rai International Airport",
    "PNH": "Phnom Penh International Airport",
    "REP": "Siem Reap International Airport",
    "DXB": "Dubai International Airport",
    "AUH": "Abu Dhabi International Airport",
    "DOH": "Hamad International Airport",
    "SYD": "Sydney Kingsford Smith Airport",
    "MEL": "Melbourne Airport",
    "BNE": "Brisbane Airport",
    "PER": "Perth Airport",
    "AKL": "Auckland Airport",
    "CHC": "Christchurch Airport",
    "LHR": "London Heathrow Airport",
    "PAR": "Paris Charles de Gaulle Airport",
    "FRA": "Frankfurt Airport",
    "MUC": "Munich Airport",
    "AMS": "Amsterdam Airport Schiphol",
    "FCO": "Leonardo da Vinci–Fiumicino Airport",
    "MAD": "Adolfo Suárez Madrid–Barajas Airport",
    "BCN": "Barcelona–El Prat Airport",
    "VIE": "Vienna International Airport",
    "ZRH": "Zurich Airport",
    "CPH": "Copenhagen Airport",
    "ARN": "Stockholm Arlanda Airport",
    "OSL": "Oslo Gardermoen Airport",
    "HEL": "Helsinki-Vantaa Airport",
    "IST": "Istanbul Airport",
    "JFK": "John F. Kennedy International Airport",
    "LAX": "Los Angeles International Airport",
    "SFO": "San Francisco International Airport",
    "YVR": "Vancouver International Airport",
    "YYZ": "Toronto Pearson International Airport",
    "ORD": "O'Hare International Airport",
    "SEA": "Seattle-Tacoma International Airport",
    "DEL": "Indira Gandhi International Airport",
    "BOM": "Chhatrapati Shivaji Maharaj International Airport",
    "BLR": "Kempegowda International Airport",
    "CMB": "Bandaranaike International Airport",
    "MLE": "Velana International Airport",
    "CAI": "Cairo International Airport",
    "JNB": "O. R. Tambo International Airport",
    "CPT": "Cape Town International Airport",
}


def parse_city_codes() -> List[CityEntry]:
    if not CITY_CODES_PATH.exists():
        raise FileNotFoundError(f"City codes file not found at {CITY_CODES_PATH}")

    contents = CITY_CODES_PATH.read_text(encoding="utf-8")
    matches = list(CITY_LIST_PATTERN.finditer(contents))
    return [CityEntry(match.groupdict()) for match in matches]


def resolve_airport_name(iata: str, default_city: str) -> str:
    return IATA_AIRPORT_NAMES.get(iata, f"{default_city} Airport")


def upsert_airports(entries: List[CityEntry]) -> None:
    inserted = 0
    updated = 0
    now = datetime.utcnow()

    with get_db() as db:
        for entry in entries:
            airport_name = resolve_airport_name(entry["code"], entry["name"])
            existing = (
                db.query(Airport).filter(Airport.iata == entry["code"]).first()
            )

            if existing:
                existing.airport_name = airport_name
                existing.place_name = entry["chinese"]
                existing.display_name = entry["display"]
                existing.updated_at = now
                updated += 1
            else:
                airport = Airport(
                    iata=entry["code"],
                    airport_name=airport_name,
                    place_name=entry["chinese"],
                    display_name=entry["display"],
                    created_at=now,
                    updated_at=now,
                )
                db.add(airport)
                inserted += 1

        db.commit()

    print(f"Airports inserted: {inserted}")
    print(f"Airports updated: {updated}")


def main() -> None:
    entries = parse_city_codes()
    if not entries:
        print("No city entries detected in cityCodes.ts")
        return

    upsert_airports(entries)


if __name__ == "__main__":
    main()

