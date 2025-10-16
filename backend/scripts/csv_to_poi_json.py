import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def parse_tags(tags_str: str) -> List[str]:
    if not tags_str or tags_str.strip() == "":
        return []
    return [tag.strip() for tag in tags_str.split(",")]


def parse_float(value: str) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def parse_int(value: str) -> int:
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def parse_bool(value: str) -> bool:
    if isinstance(value, bool):
        return value
    return value.lower() in ("true", "yes", "1", "да")


def convert_csv_to_json(csv_path: Path, output_path: Path) -> None:
    print(f"Reading CSV: {csv_path}")
    
    pois: List[Dict[str, Any]] = []
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if not row.get("name") or not row.get("lat"):
                continue
            
            poi: Dict[str, Any] = {
                "id": parse_int(row.get("id", 0)),
                "name": row.get("name", "").strip(),
                "lat": parse_float(row.get("lat", 0)),
                "lon": parse_float(row.get("lon", 0)),
                "category": row.get("category", "").strip(),
                "tags": parse_tags(row.get("tags", "")),
                "description": row.get("description", "").strip(),
            }
            
            if row.get("name_en"):
                poi["name_en"] = row["name_en"].strip()
            
            if row.get("description_en"):
                poi["description_en"] = row["description_en"].strip()
            
            if row.get("photo_tip"):
                poi["photo_tip"] = row["photo_tip"].strip()
            
            if row.get("local_tip"):
                poi["local_tip"] = row["local_tip"].strip()
            
            if row.get("avg_visit_minutes"):
                poi["avg_visit_minutes"] = parse_int(row["avg_visit_minutes"])
            
            if row.get("open_time"):
                poi["open_time"] = row["open_time"].strip()
            
            if row.get("close_time"):
                poi["close_time"] = row["close_time"].strip()
            
            if row.get("social_mode"):
                poi["social_mode"] = row["social_mode"].strip()
            
            if row.get("intensity_level"):
                poi["intensity_level"] = row["intensity_level"].strip()
            
            if row.get("rating"):
                poi["rating"] = parse_float(row["rating"])
            
            if row.get("price_level"):
                poi["price_level"] = row["price_level"].strip()
            
            if row.get("indoor"):
                poi["indoor"] = parse_bool(row["indoor"])
            
            if row.get("accessibility"):
                poi["accessibility"] = row["accessibility"].strip()
            
            if row.get("website"):
                poi["website"] = row["website"].strip()
            
            if row.get("phone"):
                poi["phone"] = row["phone"].strip()
            
            pois.append(poi)
    
    print(f"Parsed {len(pois)} POIs")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pois, f, ensure_ascii=False, indent=2)
    
    print(f"Saved to: {output_path}")
    
    print("\nStatistics:")
    categories = {}
    for poi in pois:
        cat = poi.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    
    print("Categories:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:15s}: {count}")
    
    with_tips = sum(1 for p in pois if p.get("local_tip"))
    with_photos = sum(1 for p in pois if p.get("photo_tip"))
    print(f"\nWith local tips: {with_tips}/{len(pois)} ({with_tips/len(pois)*100:.1f}%)")
    print(f"With photo tips: {with_photos}/{len(pois)} ({with_photos/len(pois)*100:.1f}%)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python csv_to_poi_json.py <input.csv> [output.json]")
        print("\nExample:")
        print("  python csv_to_poi_json.py poi_data.csv data/poi_extended.json")
        print("\nCSV format:")
        print("  Required columns: id,name,lat,lon,category,tags,description")
        print("  Optional: photo_tip,local_tip,rating,social_mode,etc.")
        print("\nTags should be comma-separated: 'история,фотография,панорама'")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = csv_path.with_suffix(".json")
    
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)
    
    convert_csv_to_json(csv_path, output_path)
    
    print("\nConversion completed!")
    print(f"\nNext steps:")
    print(f"1. Validate: python scripts/validate_pois.py {output_path}")
    print(f"2. Load: docker compose exec backend poetry run python scripts/load_pois.py")


if __name__ == "__main__":
    main()