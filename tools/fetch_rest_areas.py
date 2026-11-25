"""Unduh rest area & SPBU nyata dari OpenStreetMap (Overpass API) ke data/rest_areas.csv.

Contoh:
    python tools/fetch_rest_areas.py                      # seluruh Lampung
    python tools/fetch_rest_areas.py --bbox -6.0 104.5 -5.0 105.9 --no-fuel
Butuh internet. Data OSM di Indonesia belum selengkap Google; cek hasilnya.
"""
import argparse
import csv
import json
import os
import urllib.parse
import urllib.request

URL = "https://overpass-api.de/api/interpreter"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"),
                    default=[-6.0, 103.6, -3.7, 106.0], help="selatan barat utara timur")
    ap.add_argument("--no-fuel", action="store_true", help="jangan sertakan SPBU")
    ap.add_argument("--out", default="data/rest_areas.csv")
    a = ap.parse_args()

    b = ",".join(str(x) for x in a.bbox)
    parts = [f'nwr["highway"="rest_area"]({b});', f'nwr["highway"="services"]({b});']
    if not a.no_fuel:
        parts.append(f'nwr["amenity"="fuel"]({b});')
    query = "[out:json][timeout:90];(" + "".join(parts) + ");out center tags;"

    req = urllib.request.Request(URL, data=urllib.parse.urlencode({"data": query}).encode(),
                                 headers={"User-Agent": "drowsiness-detector/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)

    rows, seen = [], set()
    for el in data.get("elements", []):
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        tags = el.get("tags", {})
        kind = "spbu" if tags.get("amenity") == "fuel" else "rest_area"
        name = tags.get("name") or ("SPBU" if kind == "spbu" else "Rest area")
        key = (name, round(lat, 4), round(lon, 4))
        if key in seen:
            continue
        seen.add(key)
        rows.append([name, f"{lat:.6f}", f"{lon:.6f}", kind])

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["name", "lat", "lon", "kind"])
        wr.writerows(rows)
    print(f"{len(rows)} tempat disimpan ke {a.out}")


if __name__ == "__main__":
    main()
