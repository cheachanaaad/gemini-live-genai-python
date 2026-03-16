import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from json_storage import JsonStorageTarget

logger = logging.getLogger(__name__)


LOCATION_ALIASES = {
    "냉장": "냉장",
    "냉장실": "냉장",
    "refrigerated": "냉장",
    "fridge": "냉장",
    "냉동": "냉동",
    "냉동실": "냉동",
    "frozen": "냉동",
    "freezer": "냉동",
    "상온": "상온",
    "실온": "상온",
    "팬트리": "상온",
    "pantry": "상온",
    "room": "상온",
}

RECIPE_CATALOG = [
    {
        "name": "계란 볶음밥",
        "ingredients": ["계란", "대파", "밥"],
        "description": "남은 재료를 볶아 빠르게 만들 수 있는 한 끼입니다.",
    },
    {
        "name": "김치찌개",
        "ingredients": ["김치", "두부", "대파"],
        "description": "냉장 재료를 정리하기 좋은 따뜻한 국물 요리입니다.",
    },
    {
        "name": "토마토 파스타",
        "ingredients": ["토마토", "양파", "마늘"],
        "description": "상온 재료와 냉장 재료를 함께 쓰기 좋은 기본 파스타입니다.",
    },
    {
        "name": "고등어 구이 정식",
        "ingredients": ["고등어", "레몬", "양파"],
        "description": "냉동 생선을 활용해 메인 메뉴를 만들 수 있습니다.",
    },
    {
        "name": "버섯 오믈렛",
        "ingredients": ["계란", "버섯", "치즈"],
        "description": "아침이나 브런치로 좋은 간단한 메뉴입니다.",
    },
]


def normalize_location(value):
    if not value:
        return "냉장"
    return LOCATION_ALIASES.get(str(value).strip().lower(), str(value).strip())


def normalize_name(value):
    return " ".join((value or "").strip().split())


class InventoryStore:
    def __init__(self, file_path):
        self.storage = JsonStorageTarget(file_path)
        self.items = []
        self._load()
        logger.info(
            "InventoryStore initialized path=%s items=%s",
            self.storage.describe(),
            len(self.items),
        )

    def _load(self):
        if not self.storage.exists():
            self.items = []
            logger.info("Inventory file not found path=%s", self.storage.describe())
            return

        try:
            self.items = json.loads(self.storage.read_text())
            logger.info(
                "Inventory loaded path=%s items=%s",
                self.storage.describe(),
                len(self.items),
            )
        except (json.JSONDecodeError, OSError):
            self.items = []
            logger.exception("Inventory load failed path=%s", self.storage.describe())

    def _save(self):
        self.storage.write_text(json.dumps(self.items, ensure_ascii=False, indent=2))
        logger.info(
            "Inventory saved path=%s items=%s",
            self.storage.describe(),
            len(self.items),
        )

    def _refresh(self):
        self._load()

    def list_items(self, location=None):
        self._refresh()
        normalized = normalize_location(location) if location else None
        items = self.items
        if normalized:
            items = [item for item in items if item["location"] == normalized]
        return sorted(items, key=lambda item: item["registered_at"], reverse=True)

    def summary(self):
        self._refresh()
        summary = {"total": len(self.items), "냉장": 0, "냉동": 0, "상온": 0}
        for item in self.items:
            summary[item["location"]] = summary.get(item["location"], 0) + 1
        return summary

    def register_item(
        self,
        name,
        location,
        expiry_date=None,
        quantity=None,
        memo=None,
        image=None,
        image_mime_type=None,
    ):
        self._refresh()
        item = {
            "id": str(uuid.uuid4()),
            "name": normalize_name(name),
            "location": normalize_location(location),
            "expiry_date": expiry_date or "",
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "quantity": quantity or "",
            "memo": memo or "",
            "image": image or "",
            "image_mime_type": image_mime_type or ("image/jpeg" if image else ""),
        }
        self.items.append(item)
        self._save()
        logger.info(
            "Inventory register_item id=%s name=%s location=%s total=%s",
            item["id"],
            item["name"],
            item["location"],
            len(self.items),
        )
        return item

    def find_item(self, name):
        self._refresh()
        normalized_name = normalize_name(name).lower()
        for item in self.items:
            if normalized_name in item["name"].lower():
                logger.info(
                    "Inventory find_item matched query=%s id=%s name=%s",
                    name,
                    item["id"],
                    item["name"],
                )
                return item
        logger.info("Inventory find_item no_match query=%s", name)
        return None

    def delete_item(self, name):
        self._refresh()
        normalized_name = normalize_name(name).lower()
        for index, item in enumerate(self.items):
            if normalized_name in item["name"].lower():
                removed = self.items.pop(index)
                self._save()
                logger.info(
                    "Inventory delete_item removed query=%s id=%s name=%s total=%s",
                    name,
                    removed["id"],
                    removed["name"],
                    len(self.items),
                )
                return removed
        logger.info("Inventory delete_item no_match query=%s", name)
        return None

    def get_expiring_items(self, within_days=3):
        self._refresh()
        now = datetime.now(timezone.utc).date()
        deadline = now + timedelta(days=within_days)
        result = []
        for item in self.items:
            expiry = item.get("expiry_date")
            if not expiry:
                continue
            try:
                expiry_date = datetime.fromisoformat(expiry).date()
            except ValueError:
                continue
            if now <= expiry_date <= deadline:
                enriched = dict(item)
                enriched["days_left"] = (expiry_date - now).days
                result.append(enriched)
        result = sorted(result, key=lambda item: item["days_left"])
        logger.info(
            "Inventory get_expiring_items within_days=%s matches=%s",
            within_days,
            len(result),
        )
        return result

    def get_recipe_recommendations(self, limit=3):
        self._refresh()
        names = {item["name"] for item in self.items}
        ranked = []
        for recipe in RECIPE_CATALOG:
            matched = [name for name in recipe["ingredients"] if name in names]
            score = len(matched)
            if score == 0:
                continue
            ranked.append(
                {
                    "name": recipe["name"],
                    "matched_ingredients": matched,
                    "missing_ingredients": [
                        name for name in recipe["ingredients"] if name not in names
                    ],
                    "description": recipe["description"],
                    "score": score,
                }
            )

        ranked.sort(key=lambda recipe: recipe["score"], reverse=True)
        if ranked:
            recommendations = ranked[:limit]
            logger.info(
                "Inventory get_recipe_recommendations limit=%s matches=%s",
                limit,
                len(recommendations),
            )
            return recommendations

        fallback_ingredients = sorted(list(names))[:4]
        if not fallback_ingredients:
            logger.info("Inventory get_recipe_recommendations no inventory data")
            return []

        recommendations = [
            {
                "name": "냉장고 털이 볶음",
                "matched_ingredients": fallback_ingredients,
                "missing_ingredients": [],
                "description": "남은 재료를 한 번에 볶아 만드는 자유형 레시피입니다.",
                "score": len(fallback_ingredients),
            }
        ]
        logger.info(
            "Inventory get_recipe_recommendations fallback limit=%s matches=%s",
            limit,
            len(recommendations),
        )
        return recommendations
