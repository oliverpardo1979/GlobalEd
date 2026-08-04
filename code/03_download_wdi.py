"""Download World Development Indicators used to compare real wages."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "world_bank_wdi"

INDICATORS = {
    "FP.CPI.TOTL": "Consumer price index (2010 = 100)",
    "PA.NUS.PRVT.PP": (
        "PPP conversion factor, private consumption "
        "(LCU per international dollar)"
    ),
    "PA.NUS.PPP": (
        "PPP conversion factor, GDP (LCU per international dollar)"
    ),
}

START_YEAR = 1990
END_YEAR = 2025
PER_PAGE = 20_000


def fetch_page(indicator: str, page: int) -> list[object]:
    query = urlencode(
        {
            "format": "json",
            "date": f"{START_YEAR}:{END_YEAR}",
            "per_page": PER_PAGE,
            "page": page,
        }
    )
    url = (
        "https://api.worldbank.org/v2/country/all/indicator/"
        f"{indicator}?{query}"
    )
    request = Request(url, headers={"User-Agent": "GlobalEd/1.0"})
    with urlopen(request, timeout=120) as response:
        return json.load(response)


def download_indicator(indicator: str) -> tuple[pd.DataFrame, dict[str, object]]:
    first = fetch_page(indicator, page=1)
    if not isinstance(first, list) or len(first) != 2:
        raise RuntimeError(f"Unexpected World Bank response for {indicator}")

    metadata = first[0]
    records = list(first[1] or [])
    pages = int(metadata.get("pages", 1))
    for page in range(2, pages + 1):
        payload = fetch_page(indicator, page=page)
        records.extend(payload[1] or [])

    rows = []
    for record in records:
        country_code = record.get("countryiso3code")
        value = record.get("value")
        if not country_code or len(country_code) != 3 or value is None:
            continue
        rows.append(
            {
                "indicator": indicator,
                "country_code": country_code,
                "country": record.get("country", {}).get("value"),
                "year": int(record["date"]),
                "value": float(value),
                "unit": record.get("unit"),
                "obs_status": record.get("obs_status"),
                "decimal": record.get("decimal"),
            }
        )

    frame = pd.DataFrame(rows).sort_values(["country_code", "year"])
    summary = {
        "indicator": indicator,
        "label": INDICATORS[indicator],
        "rows": int(len(frame)),
        "countries": int(frame["country_code"].nunique()),
        "first_year": int(frame["year"].min()),
        "last_year": int(frame["year"].max()),
        "api_pages": pages,
    }
    return frame, summary


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for indicator in INDICATORS:
        frame, summary = download_indicator(indicator)
        filename = indicator.replace(".", "_") + ".csv"
        frame.to_csv(RAW_DIR / filename, index=False)
        summaries.append(summary)

    manifest = {
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "World Bank Indicators API v2",
        "year_range_requested": [START_YEAR, END_YEAR],
        "indicators": summaries,
    }
    with (RAW_DIR / "download_manifest.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
