import json
import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


RECIPE_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "summary": {"type": "STRING"},
        "preference_reflection": {"type": "STRING"},
        "servings": {"type": "INTEGER"},
        "cook_time_minutes": {"type": "INTEGER"},
        "difficulty": {"type": "STRING"},
        "inventory_ingredients": {"type": "ARRAY", "items": {"type": "STRING"}},
        "missing_ingredients": {"type": "ARRAY", "items": {"type": "STRING"}},
        "ingredients": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "amount": {"type": "STRING"},
                    "from_inventory": {"type": "BOOLEAN"},
                },
                "required": ["name", "amount", "from_inventory"],
            },
        },
        "steps": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "instruction": {"type": "STRING"},
                },
                "required": ["title", "instruction"],
            },
        },
        "tips": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": [
        "title",
        "summary",
        "preference_reflection",
        "servings",
        "cook_time_minutes",
        "difficulty",
        "inventory_ingredients",
        "missing_ingredients",
        "ingredients",
        "steps",
        "tips",
    ],
}

RECOMMENDATION_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "preference_summary": {"type": "STRING"},
        "recommendations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "matched_ingredients": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "missing_ingredients": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "why_it_fits": {"type": "STRING"},
                },
                "required": [
                    "name",
                    "description",
                    "matched_ingredients",
                    "missing_ingredients",
                    "why_it_fits",
                ],
            },
        },
    },
    "required": ["preference_summary", "recommendations"],
}


class RecipeGenerator:
    def __init__(self, api_key, model="gemini-flash-lite-latest"):
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else None

    def _build_inventory_text(self, inventory_items):
        lines = []
        for item in inventory_items[:20]:
            parts = [item.get("name", "")]
            if item.get("location"):
                parts.append(f"위치:{item['location']}")
            if item.get("quantity"):
                parts.append(f"수량:{item['quantity']}")
            if item.get("expiry_date"):
                parts.append(f"유통기한:{item['expiry_date']}")
            lines.append(" | ".join(part for part in parts if part))
        return "\n".join(lines)

    def _generate_json(self, prompt, schema, temperature=0.4):
        if not self.client:
            raise RuntimeError("GEMINI_API_KEY is required for recipe generation.")

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                temperature=temperature,
            ),
        )
        return json.loads((response.text or "").strip())

    def recommend_recipes(self, inventory_items, preference, limit=3):
        if not inventory_items:
            raise RuntimeError("Inventory is empty.")

        inventory_text = self._build_inventory_text(inventory_items)
        prompt = f"""
너는 냉장고 재고 기반 메뉴 추천가다.
응답은 반드시 JSON만 반환한다.

[사용자가 먹고 싶은 스타일]
{preference}

[현재 재고]
{inventory_text}

작업:
- 현재 재고를 최대한 활용할 수 있는 메뉴 {limit}개를 추천한다.
- 추천 결과는 한국어로 쓴다.
- matched_ingredients에는 현재 재고에서 바로 쓸 수 있는 것만 넣는다.
- missing_ingredients에는 있으면 더 좋은 재료만 넣고, 꼭 필요 없으면 빈 배열도 가능하다.
- why_it_fits에는 왜 사용자의 취향과 맞는지 한 문장으로 쓴다.
- description은 완성 요리 느낌이 드는 짧은 소개로 쓴다.
""".strip()

        logger.info(
            "RecipeGenerator recommend request model=%s preference=%s inventory_count=%s limit=%s",
            self.model,
            preference,
            len(inventory_items),
            limit,
        )
        payload = self._generate_json(
            prompt=prompt,
            schema=RECOMMENDATION_RESPONSE_SCHEMA,
            temperature=0.5,
        )
        recommendations = payload.get("recommendations", [])[: max(1, limit)]
        logger.info(
            "RecipeGenerator recommend response count=%s top=%s",
            len(recommendations),
            recommendations[0]["name"] if recommendations else None,
        )
        return {
            "preference_summary": payload.get("preference_summary", preference),
            "recommendations": recommendations,
        }

    def generate_recipe(
        self,
        inventory_items,
        preference,
        servings=None,
        avoid_ingredients=None,
        recipe_name=None,
    ):
        if not inventory_items:
            raise RuntimeError("Inventory is empty.")

        inventory_text = self._build_inventory_text(inventory_items)
        avoid_text = ", ".join(avoid_ingredients or []) or "없음"
        serving_text = str(servings) if servings else "자율 판단"
        recipe_focus_text = recipe_name or "모델이 가장 적합한 요리"

        prompt = f"""
너는 냉장고 재고 기반 개인 요리 플래너다.
사용자가 먹고 싶은 스타일과 현재 재고를 바탕으로 바로 따라할 수 있는 실전 레시피를 작성해라.
응답은 반드시 JSON만 반환한다.

[사용자 선호]
{preference}

[선택된 메뉴]
{recipe_focus_text}

[희망 인분]
{serving_text}

[피하고 싶은 재료]
{avoid_text}

[현재 재고]
{inventory_text}

규칙:
- 재고에 있는 재료를 최대한 우선 사용한다.
- 없는 재료는 missing_ingredients에만 넣는다.
- steps는 4~7개로 짧고 실제 조리 순서대로 쓴다.
- summary는 한 문장으로 쓴다.
- preference_reflection에는 사용자의 취향을 어떻게 반영했는지 설명한다.
- difficulty는 쉬움, 보통, 어려움 중 하나로 쓴다.
- ingredients의 amount는 한국어 자연어로 쓴다.
- 선택된 메뉴가 있다면 그 요리에 맞춰 레시피를 구체화한다.
""".strip()

        logger.info(
            "RecipeGenerator recipe request model=%s preference=%s recipe_name=%s inventory_count=%s",
            self.model,
            preference,
            recipe_name,
            len(inventory_items),
        )
        recipe = self._generate_json(
            prompt=prompt,
            schema=RECIPE_RESPONSE_SCHEMA,
            temperature=0.4,
        )
        recipe["source_inventory_count"] = len(inventory_items)
        recipe["requested_preference"] = preference
        if recipe_name:
            recipe["recommended_recipe_name"] = recipe_name
        if avoid_ingredients:
            recipe["avoid_ingredients"] = avoid_ingredients

        logger.info(
            "RecipeGenerator recipe response title=%s ingredients=%s steps=%s",
            recipe.get("title"),
            len(recipe.get("ingredients", [])),
            len(recipe.get("steps", [])),
        )
        return recipe
