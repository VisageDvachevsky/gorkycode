import json
import sys
from pathlib import Path
from typing import Dict, List, Any


REQUIRED_FIELDS = {
    "id": int,
    "name": str,
    "lat": (int, float),
    "lon": (int, float),
    "category": str,
    "tags": list,
    "description": str,
}

OPTIONAL_FIELDS = {
    "name_en": str,
    "description_en": str,
    "photo_tip": str,
    "local_tip": str,
    "avg_visit_minutes": int,
    "open_time": str,
    "close_time": str,
    "social_mode": str,
    "intensity_level": str,
    "rating": (int, float),
    "price_level": str,
    "indoor": bool,
    "accessibility": str,
}

VALID_CATEGORIES = {
    "museum", "cafe", "viewpoint", "park", "streetart", 
    "architecture", "bar", "streetfood", "shopping", "entertainment",
    "monument", "memorial", "religious_site", "decorative_art", 
    "mosaic", "art_object", "sculpture"
}

VALID_SOCIAL_MODES = {"solo", "friends", "family", "any"}
VALID_INTENSITY_LEVELS = {"relaxed", "medium", "intense"}
VALID_PRICE_LEVELS = {"free", "cheap", "medium", "expensive"}


class POIValidator:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {
            "total": 0,
            "valid": 0,
            "categories": {},
            "with_tips": 0,
            "with_photos": 0,
            "avg_description_length": 0,
        }
    
    def validate_file(self, filepath: Path) -> bool:
        print(f"🔍 Validating: {filepath}\n")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            return False
        except FileNotFoundError:
            self.errors.append(f"File not found: {filepath}")
            return False
        
        if not isinstance(data, list):
            self.errors.append("Root element must be an array")
            return False
        
        self.stats["total"] = len(data)
        
        for idx, poi in enumerate(data):
            self._validate_poi(poi, idx)
        
        self._print_results()
        return len(self.errors) == 0
    
    def _validate_poi(self, poi: Dict, idx: int) -> None:
        if not isinstance(poi, dict):
            self.errors.append(f"POI #{idx}: Must be an object")
            return
        
        for field, field_type in REQUIRED_FIELDS.items():
            if field not in poi:
                self.errors.append(f"POI #{idx}: Missing required field '{field}'")
                continue
            
            if not isinstance(poi[field], field_type):
                self.errors.append(
                    f"POI #{idx}: Field '{field}' must be {field_type.__name__}"
                )
        
        poi_id = poi.get("id", f"unknown_{idx}")
        
        if "category" in poi and poi["category"] not in VALID_CATEGORIES:
            self.errors.append(
                f"POI #{poi_id}: Invalid category '{poi['category']}'. "
                f"Must be one of: {', '.join(VALID_CATEGORIES)}"
            )
        
        if "lat" in poi:
            lat = poi["lat"]
            if not (56.29 <= lat <= 56.36):
                self.warnings.append(
                    f"POI #{poi_id}: Latitude {lat} outside Nizhny Novgorod bounds (56.29-56.36)"
                )
        
        if "lon" in poi:
            lon = poi["lon"]
            if not (43.85 <= lon <= 44.10):
                self.warnings.append(
                    f"POI #{poi_id}: Longitude {lon} outside Nizhny Novgorod bounds (43.85-44.10)"
                )
        
        if "tags" in poi:
            if len(poi["tags"]) < 3:
                self.warnings.append(f"POI #{poi_id}: Less than 3 tags (recommended: 3-5)")
        
        if "description" in poi:
            desc_len = len(poi["description"])
            if desc_len < 50:
                self.warnings.append(
                    f"POI #{poi_id}: Description too short ({desc_len} chars, recommended: 100+)"
                )
            self.stats["avg_description_length"] += desc_len
        
        if "social_mode" in poi and poi["social_mode"] not in VALID_SOCIAL_MODES:
            self.warnings.append(
                f"POI #{poi_id}: Invalid social_mode '{poi['social_mode']}'"
            )
        
        if "intensity_level" in poi and poi["intensity_level"] not in VALID_INTENSITY_LEVELS:
            self.warnings.append(
                f"POI #{poi_id}: Invalid intensity_level '{poi['intensity_level']}'"
            )
        
        if "rating" in poi:
            rating = poi["rating"]
            if not (0.0 <= rating <= 5.0):
                self.warnings.append(f"POI #{poi_id}: Rating {rating} outside 0-5 range")
        
        category = poi.get("category", "unknown")
        self.stats["categories"][category] = self.stats["categories"].get(category, 0) + 1
        
        if "photo_tip" in poi and poi["photo_tip"]:
            self.stats["with_photos"] += 1
        
        if "local_tip" in poi and poi["local_tip"]:
            self.stats["with_tips"] += 1
        
        self.stats["valid"] += 1
    
    def _print_results(self) -> None:
        print("=" * 60)
        print("📊 VALIDATION RESULTS\n")
        
        print(f"Total POIs: {self.stats['total']}")
        print(f"Valid POIs: {self.stats['valid']}")
        
        if self.stats['total'] > 0:
            print(f"\nCategories distribution:")
            for cat, count in sorted(self.stats['categories'].items(), key=lambda x: -x[1]):
                pct = (count / self.stats['total']) * 100
                print(f"  {cat:15s}: {count:3d} ({pct:5.1f}%)")
        
        print(f"\nQuality metrics:")
        print(f"  POIs with photo tips: {self.stats['with_photos']} "
              f"({self.stats['with_photos']/max(self.stats['total'], 1)*100:.1f}%)")
        print(f"  POIs with local tips: {self.stats['with_tips']} "
              f"({self.stats['with_tips']/max(self.stats['total'], 1)*100:.1f}%)")
        
        if self.stats['total'] > 0:
            avg_desc = self.stats['avg_description_length'] / self.stats['total']
            print(f"  Avg description length: {avg_desc:.0f} chars")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors[:10]:
                print(f"  • {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:10]:
                print(f"  • {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")
        
        print("\n" + "=" * 60)
        
        if len(self.errors) == 0:
            print("✅ Validation passed!")
            if len(self.warnings) > 0:
                print(f"⚠️  But there are {len(self.warnings)} warnings to review")
        else:
            print("❌ Validation failed! Fix errors and try again.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_pois.py <path_to_poi_json>")
        print("\nExample:")
        print("  python validate_pois.py data/poi_extended.json")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    validator = POIValidator()
    success = validator.validate_file(filepath)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()