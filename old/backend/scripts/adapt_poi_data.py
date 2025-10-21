import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def extract_tags_from_description(description: str, name: str) -> List[str]:
    """Extract relevant tags from description using keywords"""
    tags = []
    
    keywords_map = {
        "история": ["царь", "император", "век", "год", "памятник", "исторический"],
        "архитектура": ["здание", "башня", "постройка", "конструкция", "сооружение"],
        "памятник": ["памятник", "монумент", "скульптура", "статуя", "бюст"],
        "фотография": ["вид", "пейзаж", "панорама", "красиво"],
        "Волга": ["волга", "ока"],
        "культура": ["писатель", "поэт", "художник", "артист"],
        "инженерия": ["инженер", "технология", "уникальный"],
        "бесплатно": ["бесплатно", "свободный доступ"],
    }
    
    text = (description + " " + name).lower()
    
    for tag, keywords in keywords_map.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    
    if not tags:
        tags = ["достопримечательность", "памятник"]
    
    return list(set(tags))[:5]


def infer_social_mode(description: str, category: str) -> str:
    """Infer social mode from description"""
    desc_lower = description.lower()
    
    if "семья" in desc_lower or "дети" in desc_lower:
        return "family"
    elif "романтик" in desc_lower or "влюбленн" in desc_lower:
        return "friends"
    
    if category in ["monument", "viewpoint", "architecture"]:
        return "any"
    
    return "any"


def infer_intensity(category: str, avg_visit_minutes: int) -> str:
    """Infer intensity level from category and visit time"""
    if category in ["monument", "viewpoint"]:
        return "relaxed"
    elif category in ["museum"] and avg_visit_minutes > 60:
        return "medium"
    else:
        return "relaxed"


def adapt_poi(original: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt POI to our format"""
    adapted = {
        "id": original["id"],
        "name": original["name"],
        "lat": original["lat"],
        "lon": original["lon"],
        "category": original["category"],
        "description": original["description"],
        "rating": original.get("rating", 4.0),
        "avg_visit_minutes": original.get("avg_visit_minutes", 30),
    }
    
    if "address" in original:
        adapted["address"] = original["address"]
    
    if original.get("tags") and len(original["tags"]) > 0:
        adapted["tags"] = original["tags"]
    else:
        adapted["tags"] = extract_tags_from_description(
            original["description"], 
            original["name"]
        )
    
    adapted["social_mode"] = infer_social_mode(
        original["description"], 
        original["category"]
    )
    
    adapted["intensity_level"] = infer_intensity(
        original["category"],
        original.get("avg_visit_minutes", 30)
    )
    
    if "monument" in original["name"].lower() or original["category"] == "monument":
        adapted["photo_tip"] = "Снимайте с разных ракурсов, попробуйте найти интересный передний план"
    
    desc = original["description"].lower()
    if "набережн" in desc or "река" in desc or "волга" in desc or "ока" in desc:
        adapted["local_tip"] = "Лучше всего посещать на закате или рано утром для атмосферных фотографий"
    elif "памятник" in desc:
        adapted["local_tip"] = "Можно совместить с прогулкой по окрестностям"
    
    return adapted


def adapt_poi_dataset(input_path: Path, output_path: Path) -> None:
    """Adapt entire POI dataset"""
    print(f"📂 Reading: {input_path}")
    
    with open(input_path, "r", encoding="utf-8") as f:
        original_data = json.load(f)
    
    print(f"📊 Found {len(original_data)} POIs")
    
    adapted_data = []
    categories = {}
    
    for poi in original_data:
        adapted_poi = adapt_poi(poi)
        adapted_data.append(adapted_poi)
        
        cat = adapted_poi["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(adapted_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Adapted {len(adapted_data)} POIs")
    print(f"💾 Saved to: {output_path}")
    
    print(f"\n📊 Categories:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:15s}: {count}")
    
    with_tags = sum(1 for p in adapted_data if len(p.get("tags", [])) > 0)
    with_tips = sum(1 for p in adapted_data if p.get("local_tip"))
    with_photos = sum(1 for p in adapted_data if p.get("photo_tip"))
    
    print(f"\n📈 Quality metrics:")
    print(f"  With tags: {with_tags}/{len(adapted_data)} ({with_tags/len(adapted_data)*100:.1f}%)")
    print(f"  With local tips: {with_tips}/{len(adapted_data)} ({with_tips/len(adapted_data)*100:.1f}%)")
    print(f"  With photo tips: {with_photos}/{len(adapted_data)} ({with_photos/len(adapted_data)*100:.1f}%)")
    
    print(f"\n💡 Recommendations:")
    if with_tags < len(adapted_data):
        print(f"  ⚠️  {len(adapted_data) - with_tags} POIs need better tags")
    if with_tips < len(adapted_data) * 0.5:
        print(f"  ⚠️  Consider adding more local tips (only {with_tips/len(adapted_data)*100:.1f}%)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python adapt_poi_data.py <input.json> [output.json]")
        print("\nExample:")
        print("  python adapt_poi_data.py raw_pois.json data/poi_adapted.json")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = input_path.parent / f"{input_path.stem}_adapted.json"
    
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)
    
    adapt_poi_dataset(input_path, output_path)
    
    print("\n✅ Adaptation completed!")
    print(f"\nNext steps:")
    print(f"1. Review: {output_path}")
    print(f"2. Validate: python scripts/validate_pois.py {output_path}")
    print(f"3. Load: docker compose exec backend poetry run python scripts/load_pois.py")


if __name__ == "__main__":
    main()