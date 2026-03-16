import asyncio
import base64
import json
import logging
import os
import re
import time
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.genai import types

from gemini_live import GeminiLive
from image_segmentation import ItemImageSegmenter
from inventory_store import InventoryStore, normalize_location
from recipe_generator import RecipeGenerator
from workspace_store import WorkspaceStore

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")
INVENTORY_PATH = os.getenv("INVENTORY_PATH", str(DATA_DIR / "inventory.json"))
WORKSPACE_STATE_PATH = os.getenv(
    "WORKSPACE_STATE_PATH", str(DATA_DIR / "workspace_state.json")
)

inventory_store = InventoryStore(INVENTORY_PATH)
workspace_store = WorkspaceStore(WORKSPACE_STATE_PATH)
logger.info(
    "FreshCheck server boot model=%s inventory_path=%s workspace_path=%s log_level=%s",
    MODEL,
    INVENTORY_PATH,
    WORKSPACE_STATE_PATH,
    LOG_LEVEL,
)

item_segmenter = ItemImageSegmenter(
    api_key=GEMINI_API_KEY,
    model=os.getenv("VISION_MODEL", "gemini-2.5-flash"),
)
recipe_generator = RecipeGenerator(
    api_key=GEMINI_API_KEY,
    model=os.getenv("RECIPE_MODEL", "gemini-flash-lite-latest"),
)

MUTATING_TOOLS = {
    "register_item",
    "register_items",
    "complete_pending_registration",
    "delete_item",
    "delete_items",
}
MAX_MUTATION_ITEMS_PER_TURN = int(
    os.getenv(
        "MAX_MUTATION_ITEMS_PER_TURN",
        os.getenv("MAX_MUTATION_TOOL_CALLS_PER_TURN", "12"),
    )
)
AUDIO_QUEUE_MAXSIZE = max(1, int(os.getenv("AUDIO_QUEUE_MAXSIZE", "6")))
VIDEO_QUEUE_MAXSIZE = max(1, int(os.getenv("VIDEO_QUEUE_MAXSIZE", "1")))
TEXT_QUEUE_MAXSIZE = max(1, int(os.getenv("TEXT_QUEUE_MAXSIZE", "8")))
SEGMENTATION_TIMEOUT_SECONDS = float(os.getenv("SEGMENTATION_TIMEOUT_SECONDS", "5"))
HEARTBEAT_TIMEOUT_SECONDS = float(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "12"))

SUPPORTED_RESPONSE_LANGUAGES = {
    "ko": "Korean",
    "kr": "Korean",
    "korean": "Korean",
    "한국어": "Korean",
    "en": "English",
    "english": "English",
    "영어": "English",
    "ja": "Japanese",
    "jp": "Japanese",
    "japanese": "Japanese",
    "일본어": "Japanese",
}

FRESHCHECK_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="register_item",
            description="새 식재료를 재고에 등록한다. 사용자가 무엇인지 알려주거나 정정했을 때 사용한다.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "식재료 이름"},
                    "location": {
                        "type": "string",
                        "enum": ["냉장", "냉동", "상온"],
                        "description": "보관 위치",
                    },
                    "expiry_date": {
                        "type": "string",
                        "description": "YYYY-MM-DD 형식의 유통기한 또는 소비기한",
                    },
                    "quantity": {"type": "string", "description": "수량 또는 분량"},
                    "memo": {"type": "string", "description": "추가 메모"},
                },
                "required": ["name", "location"],
            },
        ),
        types.FunctionDeclaration(
            name="register_items",
            description="Register multiple visible grocery items in one request. Use this when the user says to register everything or several items at once.",
            parameters={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "Items to register sequentially.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "location": {
                                    "type": "string",
                                    "enum": ["?됱옣", "?됰룞", "?곸삩"],
                                },
                                "expiry_date": {"type": "string"},
                                "quantity": {"type": "string"},
                                "memo": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                    "default_location": {
                        "type": "string",
                        "enum": ["?됱옣", "?됰룞", "?곸삩"],
                        "description": "Fallback location for items that do not specify one.",
                    },
                },
                "required": ["items"],
            },
        ),
        types.FunctionDeclaration(
            name="find_item",
            description="재고에서 특정 식재료를 찾아 위치를 확인한다.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "찾을 식재료 이름"}
                },
                "required": ["name"],
            },
        ),
        types.FunctionDeclaration(
            name="delete_item",
            description="재고에서 특정 식재료를 삭제한다.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "삭제할 식재료 이름"}
                },
                "required": ["name"],
            },
        ),
        types.FunctionDeclaration(
            name="delete_items",
            description="재고에서 여러 식재료를 한 번에 삭제한다.",
            parameters={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "삭제할 식재료 이름 목록",
                        "items": {"type": "string"},
                    }
                },
                "required": ["items"],
            },
        ),
        types.FunctionDeclaration(
            name="list_items",
            description="현재 재고를 전체 또는 위치별로 조회한다.",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "enum": ["냉장", "냉동", "상온"],
                        "description": "특정 위치만 조회할 때 사용",
                    }
                },
            },
        ),
        types.FunctionDeclaration(
            name="get_expiring_items",
            description="유통기한이 임박한 식재료를 조회한다.",
            parameters={
                "type": "object",
                "properties": {
                    "within_days": {
                        "type": "integer",
                        "description": "며칠 이내로 임박한 항목을 볼지 지정",
                    }
                },
            },
        ),
        types.FunctionDeclaration(
            name="get_recipe_recommendations",
            description="현재 재고를 기반으로 만들 수 있는 메뉴를 추천한다.",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "추천 개수",
                    }
                },
            },
        ),
        types.FunctionDeclaration(
            name="generate_recipe_plan",
            description="현재 재고와 사용자가 원하는 메뉴 스타일을 바탕으로 상세 레시피 JSON을 생성한다.",
            parameters={
                "type": "object",
                "properties": {
                    "preference": {
                        "type": "string",
                        "description": "사용자가 먹고 싶은 메뉴, 분위기, 스타일",
                    },
                    "servings": {
                        "type": "integer",
                        "description": "원하는 인분 수",
                    },
                    "avoid_ingredients": {
                        "type": "array",
                        "description": "사용하고 싶지 않은 재료 목록",
                        "items": {"type": "string"},
                    },
                },
                "required": ["preference"],
            },
        ),
        types.FunctionDeclaration(
            name="complete_pending_registration",
            description="유통기한을 물어본 뒤 대기 중인 식재료 등록을 완료한다.",
            parameters={
                "type": "object",
                "properties": {
                    "expiry_date": {
                        "type": "string",
                        "description": "YYYY-MM-DD 형식으로 정규화된 유통기한",
                    }
                },
                "required": ["expiry_date"],
            },
        ),
    ]
)

SYSTEM_PROMPT = """
너는 FreshCheck라는 한국어 식재료 관리 에이전트다.
사용자는 카메라로 냉장고나 식재료를 비추고, 음성 또는 텍스트로 명령한다.

목표:
- 보이는 식재료와 발화를 함께 해석한다.
- 재고 등록, 조회, 삭제, 유통기한 확인, 레시피 추천을 정확하게 처리한다.
- 짧고 자연스럽고 신뢰감 있게 말한다.

응답 규칙:
- 항상 한국어로 대답한다.
- 일반 응답은 1~2문장으로 짧게 말한다.
- 재고 관련 작업은 감으로 답하지 말고 반드시 적절한 tool을 먼저 호출한다.
- 사용자의 의도가 재고 등록/조회/삭제/목록/유통기한/레시피 중 하나면 바로 tool을 선택한다.
- 식재료 이름이나 위치가 부족하면 tool을 부르지 말고 한 번만 짧게 되묻는다.
- 같은 정보를 반복하지 말고, tool 결과를 바탕으로만 확정 표현을 쓴다.

의도별 행동:
- "이거 사과야", "이거 우유야 냉장에 넣어줘", "이건 고등어인데 냉동실에 둘 거야" -> register_item
- "사과 어디 있어?", "우유 찾아줘" -> find_item
- "사과 빼줘", "우유 먹었으니 삭제해줘" -> delete_item
- "사과, 우유, 계란 한꺼번에 삭제해줘", "보이는 영양제 전부 빼줘" -> delete_items
- "냉동에 뭐 있어?", "전체 재고 보여줘" -> list_items
- "곧 상하는 거 알려줘", "유통기한 임박한 거 보여줘" -> get_expiring_items
- "이 재료로 뭐 해먹어?", "지금 재고로 메뉴 추천해줘" -> get_recipe_recommendations
- "매콤한 국물 먹고 싶어, 레시피 짜줘", "지금 재료로 파스타 레시피 만들어줘" -> generate_recipe_plan
- "가지고 있는 재료로 만들 수 있는 거 알려줘", "뭐 해먹을지 추천해줘", "레시피 알려줘"처럼 막연한 요청은 바로 추천하지 말고 음식 종류를 먼저 묻는다.

카메라 해석 규칙:
- 사용자가 "이거", "방금 비춘 거", "보이는 거"라고 말하면 최근 카메라 프레임을 참고한다.
- 식재료가 확실하지 않으면 추측해서 등록하지 말고 확인 질문을 한다.

tool 호출 후 응답 규칙:
- register_item 후: 이름과 위치를 함께 확인한다.
- find_item 후: 위치를 먼저 말하고, 유통기한이 있으면 덧붙인다.
- delete_item 후: 삭제 여부를 명확히 말한다.
- get_expiring_items 후: 임박한 항목이 없으면 없다고 짧게 말한다.
- get_recipe_recommendations 후: 1~2개만 먼저 말하고 더 볼지 물을 수 있다.
- generate_recipe_plan 후: 완성된 레시피를 짧게 소개하고 사용자가 바로 볼 수 있게 안내한다.

중요:
- 현재 재고 요약과 최근 카메라 상태가 사용자 메시지와 함께 전달된다.
- 전달된 컨텍스트를 참고하되, 재고 결과를 확정할 때는 항상 tool 결과를 기준으로 말한다.
"""

SYSTEM_PROMPT += """

Additional rules:
- Always answer in the language from preferred_response_language in the session context.
- If preferred_response_language is missing, default to Korean.
- If the user asks to register everything visible or multiple items at once, prefer register_items instead of repeating register_item.
- When using register_items, extract a clean list first and send all visible items in one tool call.
- If the user asks to delete multiple items at once, prefer delete_items instead of repeating delete_item.
- For mutating tools, do not call register_item or delete_item repeatedly in the same turn once one mutation has already succeeded.
- Before calling register_item or register_items, always confirm expiry_date if it is missing.
- If expiry_date is unknown, ask the user for it first instead of registering immediately.
- If the user asks for a recipe but does not say what kind of dish they want, do not call generate_recipe_plan yet.
- In that case, briefly mention a few ingredients from inventory and ask what they feel like eating.
- If the user asks for recommendations without a cuisine, style, or dish name, do not call get_recipe_recommendations yet.
- Ask a short follow-up like "어떤 종류 음식 원하세요? 한식, 중식, 양식, 매콤한 거, 국물 요리 중에서 말씀해 주세요."
- If there are pending items waiting for expiry_date and the user replies with a date, call complete_pending_registration.
- Do not claim registration is complete after an expiry-date follow-up unless complete_pending_registration actually succeeded.
"""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


def inventory_payload(location=None):
    return {
        "items": inventory_store.list_items(location=location),
        "summary": inventory_store.summary(),
    }


def normalize_response_language(value):
    normalized = str(value or "").strip().lower()
    return SUPPORTED_RESPONSE_LANGUAGES.get(normalized, "Korean")


def build_inventory_context():
    items = inventory_store.list_items()
    if not items:
        return "현재 등록된 재고 없음"

    lines = []
    for item in items[:12]:
        parts = [item["name"], f"위치:{item['location']}"]
        if item.get("expiry_date"):
            parts.append(f"유통기한:{item['expiry_date']}")
        if item.get("quantity"):
            parts.append(f"수량:{item['quantity']}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def compose_turn_text(
    user_text,
    latest_frame_b64,
    pending_registration_items=None,
    preferred_response_language="Korean",
):
    frame_status = "있음" if latest_frame_b64 else "없음"
    summary = inventory_store.summary()
    pending_registration_items = pending_registration_items or []
    if pending_registration_items:
        pending_lines = [
            f"{item['name']} | 위치:{item['location']}"
            for item in pending_registration_items[:12]
        ]
        pending_context = "\n".join(pending_lines)
    else:
        pending_context = "없음"
    return (
        "[FreshCheck session context]\n"
        f"- latest_camera_frame: {frame_status}\n"
        f"- preferred_response_language: {preferred_response_language}\n"
        f"- inventory_summary: total={summary['total']}, 냉장={summary['냉장']}, 냉동={summary['냉동']}, 상온={summary['상온']}\n"
        f"- inventory_snapshot:\n{build_inventory_context()}\n"
        f"- pending_registration_items:\n{pending_context}\n"
        "[User request]\n"
        f"{user_text}"
    )


def compact_inventory_item(item):
    if not isinstance(item, dict):
        return item

    compact = {
        "id": item.get("id"),
        "name": item.get("name"),
        "location": item.get("location"),
    }

    for field in ["expiry_date", "quantity", "memo", "days_left"]:
        if item.get(field):
            compact[field] = item.get(field)

    return compact


def build_model_tool_result(result):
    if not isinstance(result, dict):
        return result

    compact = {
        "ok": result.get("ok"),
        "message": result.get("message"),
        "spoken_response": result.get("spoken_response"),
        "summary": result.get("summary"),
    }
    if result.get("needs_expiry") is not None:
        compact["needs_expiry"] = result.get("needs_expiry")
    if isinstance(result.get("missing_expiry_for"), list):
        compact["missing_expiry_for"] = result.get("missing_expiry_for")[:12]
    if result.get("needs_recipe_preference") is not None:
        compact["needs_recipe_preference"] = result.get("needs_recipe_preference")

    if result.get("item"):
        compact["item"] = compact_inventory_item(result["item"])
    if result.get("deleted_item"):
        compact["deleted_item"] = compact_inventory_item(result["deleted_item"])
    if isinstance(result.get("deleted_items"), list):
        compact["deleted_items"] = [
            compact_inventory_item(item) for item in result["deleted_items"][:8]
        ]
    if result.get("location"):
        compact["location"] = result.get("location")
    if result.get("default_location_used"):
        compact["default_location_used"] = result.get("default_location_used")
    if isinstance(result.get("items"), list):
        compact["items"] = [compact_inventory_item(item) for item in result["items"][:8]]
    if isinstance(result.get("registered_items"), list):
        compact["registered_items"] = [
            compact_inventory_item(item) for item in result["registered_items"][:8]
        ]
    if isinstance(result.get("skipped_items"), list):
        compact["skipped_items"] = result["skipped_items"][:8]
    if isinstance(result.get("expiring_items"), list):
        compact["expiring_items"] = [
            compact_inventory_item(item) for item in result["expiring_items"][:8]
        ]
    if isinstance(result.get("recipes"), list):
        compact["recipes"] = result["recipes"][:3]
    if isinstance(result.get("recipe_plan"), dict):
        recipe_plan = result["recipe_plan"]
        compact["recipe_plan"] = {
            "title": recipe_plan.get("title"),
            "summary": recipe_plan.get("summary"),
            "preference_reflection": recipe_plan.get("preference_reflection"),
            "servings": recipe_plan.get("servings"),
            "cook_time_minutes": recipe_plan.get("cook_time_minutes"),
            "difficulty": recipe_plan.get("difficulty"),
            "inventory_ingredients": recipe_plan.get("inventory_ingredients", [])[:8],
            "missing_ingredients": recipe_plan.get("missing_ingredients", [])[:8],
            "ingredients": recipe_plan.get("ingredients", [])[:12],
            "steps": recipe_plan.get("steps", [])[:8],
            "tips": recipe_plan.get("tips", [])[:6],
        }

    return compact


def infer_default_location_from_text(user_text):
    normalized = (user_text or "").lower()
    hints = {
        "?됱옣": "?됱옣",
        "냉장": "?됱옣",
        "fridge": "?됱옣",
        "refrigerator": "?됱옣",
        "?됰룞": "?됰룞",
        "냉동": "?됰룞",
        "freezer": "?됰룞",
        "?곸삩": "?곸삩",
        "상온": "?곸삩",
        "pantry": "?곸삩",
        "room temperature": "?곸삩",
    }
    for key, value in hints.items():
        if key in normalized:
            return value
    return None


@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/inventory")
async def get_inventory(location: str | None = None):
    normalized_location = normalize_location(location) if location else None
    logger.info("HTTP GET /api/inventory location=%s", normalized_location)
    return inventory_payload(location=normalized_location)


@app.get("/api/workspace-state")
async def get_workspace_state():
    state = workspace_store.get_state()
    logger.info(
        "HTTP GET /api/workspace-state recipes=%s activeWorkspace=%s",
        len(state.get("recipes", [])),
        state.get("activeWorkspace"),
    )
    return {"ok": True, "state": state}


@app.post("/api/workspace-state")
async def save_workspace_state(payload: dict = Body(...)):
    state = workspace_store.save_state(payload)
    logger.info(
        "HTTP POST /api/workspace-state recipes=%s currentRecipe=%s activeWorkspace=%s",
        len(state.get("recipes", [])),
        bool(state.get("currentRecipe")),
        state.get("activeWorkspace"),
    )
    return {"ok": True, "state": state}


@app.post("/api/recipe-detail")
async def get_recipe_detail(payload: dict = Body(...)):
    recipe_name = (payload.get("recipe_name") or "").strip()
    preference = (payload.get("preference") or recipe_name).strip()
    servings = payload.get("servings")
    avoid_ingredients = payload.get("avoid_ingredients") or None
    inventory_items = inventory_store.list_items()

    logger.info(
        "HTTP POST /api/recipe-detail recipe_name=%s preference=%s inventory_count=%s",
        recipe_name,
        preference,
        len(inventory_items),
    )

    if not inventory_items:
        return {
            "ok": False,
            "error": "inventory_empty",
            "message": "아직 등록된 재고가 없어서 레시피를 만들 수 없어요.",
        }

    if not recipe_name:
        return {
            "ok": False,
            "error": "missing_recipe_name",
            "message": "상세 레시피를 만들 메뉴 이름이 필요해요.",
        }

    recipe_plan = recipe_generator.generate_recipe(
        inventory_items=inventory_items,
        preference=preference,
        servings=servings,
        avoid_ingredients=avoid_ingredients,
        recipe_name=recipe_name,
    )
    return {"ok": True, "recipe_plan": recipe_plan}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection_id = uuid4().hex[:8]
    client = websocket.client
    client_label = f"{client.host}:{client.port}" if client else "unknown"
    await websocket.accept()
    logger.info("[%s] WebSocket accepted client=%s", connection_id, client_label)

    audio_input_queue = asyncio.Queue(maxsize=AUDIO_QUEUE_MAXSIZE)
    video_input_queue = asyncio.Queue(maxsize=VIDEO_QUEUE_MAXSIZE)
    text_input_queue = asyncio.Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    session_state = {
        "latest_frame_b64": "",
        "turn_id": 0,
        "mutation_items_this_turn": 0,
        "last_user_text": "",
        "last_default_location": None,
        "pending_registration_items": [],
        "selected_language": "Korean",
        "audio_chunks_received": 0,
        "audio_chunks_dropped": 0,
        "video_frames_received": 0,
        "video_frames_dropped": 0,
        "last_client_heartbeat": time.monotonic(),
        "suppress_gemini_until_turn_complete": False,
    }
    disconnected = asyncio.Event()

    async def safe_send_json(payload):
        if disconnected.is_set():
            logger.debug(
                "[%s] Skip send_json disconnected payload_type=%s",
                connection_id,
                payload.get("type") if isinstance(payload, dict) else type(payload).__name__,
            )
            return False
        try:
            await websocket.send_json(payload)
            logger.info(
                "[%s] Sent JSON payload type=%s",
                connection_id,
                payload.get("type") if isinstance(payload, dict) else type(payload).__name__,
            )
            return True
        except (WebSocketDisconnect, RuntimeError) as exc:
            logger.info("[%s] WebSocket JSON send failed: %s", connection_id, exc)
            disconnected.set()
            return False

    async def safe_send_bytes(data):
        if disconnected.is_set():
            logger.debug("[%s] Skip send_bytes disconnected bytes=%s", connection_id, len(data))
            return False
        try:
            await websocket.send_bytes(data)
            logger.debug("[%s] Sent audio bytes=%s", connection_id, len(data))
            return True
        except (WebSocketDisconnect, RuntimeError) as exc:
            logger.info("[%s] WebSocket bytes send failed: %s", connection_id, exc)
            disconnected.set()
            return False

    initial_inventory = {"type": "inventory_state", **inventory_payload()}
    logger.info(
        "[%s] Sending initial inventory_state total=%s",
        connection_id,
        initial_inventory["summary"]["total"],
    )
    await safe_send_json(initial_inventory)

    async def audio_output_callback(data):
        logger.debug("[%s] audio_output_callback bytes=%s", connection_id, len(data))
        await safe_send_bytes(data)

    async def audio_interrupt_callback():
        logger.info("[%s] audio interrupt callback invoked", connection_id)

    def enqueue_latest(queue, item, drop_counter_key):
        dropped = 0
        while queue.full():
            try:
                queue.get_nowait()
                dropped += 1
            except asyncio.QueueEmpty:
                break
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            return dropped, False
        if dropped:
            session_state[drop_counter_key] += dropped
        return dropped, True

    def enqueue_latest(queue, item, drop_counter_key):
        dropped = 0
        while queue.full():
            try:
                queue.get_nowait()
                dropped += 1
            except asyncio.QueueEmpty:
                break
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            return dropped, False
        if dropped:
            session_state[drop_counter_key] += dropped
        return dropped, True

    def log_tool_start(tool_name, **kwargs):
        logger.info("[%s] Tool start name=%s args=%s", connection_id, tool_name, kwargs)

    def log_tool_end(tool_name, result):
        logger.info(
            "[%s] Tool end name=%s ok=%s total=%s",
            connection_id,
            tool_name,
            result.get("ok") if isinstance(result, dict) else None,
            result.get("summary", {}).get("total") if isinstance(result, dict) else None,
        )

    def begin_user_turn(source_label, user_text):
        session_state["turn_id"] += 1
        session_state["mutation_items_this_turn"] = 0
        session_state["last_user_text"] = user_text
        session_state["last_default_location"] = infer_default_location_from_text(user_text)
        logger.info(
            "[%s] User turn started turn_id=%s source=%s text=%s inferred_location=%s",
            connection_id,
            session_state["turn_id"],
            source_label,
            user_text,
            session_state["last_default_location"],
        )

    def build_mutation_guard_result(tool_name, requested_items):
        current_items = session_state["mutation_items_this_turn"]
        result = {
            "ok": False,
            "guarded": True,
            "message": (
                f"이번 요청에서는 재고 항목을 최대 {MAX_MUTATION_ITEMS_PER_TURN}개까지만 "
                f"변경할 수 있어요. 지금까지 {current_items}개를 처리했고, "
                f"이번 작업은 {requested_items}개라서 다음 요청으로 나눠 주세요."
            ),
            "spoken_response": (
                f"이번 요청에서는 재고를 최대 {MAX_MUTATION_ITEMS_PER_TURN}개까지만 바꿀게요. "
                "나머지는 이어서 말해 주시면 계속 처리할게요."
            ),
            "requested_items": requested_items,
            **inventory_payload(),
        }
        result["model_response"] = {
            "ok": False,
            "guarded": True,
            "message": result["message"],
            "spoken_response": result["spoken_response"],
            "requested_items": requested_items,
            "summary": result.get("summary"),
        }
        logger.warning(
            "[%s] Mutation guard blocked tool=%s turn_id=%s current_items=%s requested_items=%s limit=%s",
            connection_id,
            tool_name,
            session_state["turn_id"],
            current_items,
            requested_items,
            MAX_MUTATION_ITEMS_PER_TURN,
        )
        return result

    def build_missing_expiry_result(names):
        item_names = [name for name in names if name]
        target_text = ", ".join(item_names) if item_names else "해당 식재료"
        question = f"{target_text}의 유통기한을 알려주세요. YYYY-MM-DD 형식으로 말해주시면 등록할게요."
        return {
            "ok": False,
            "needs_expiry": True,
            "missing_expiry_for": item_names,
            "message": question,
            "spoken_response": question,
            **inventory_payload(),
        }

    def normalize_expiry_date(raw_value):
        value = " ".join((raw_value or "").split()).strip()
        if not value:
            return ""

        direct_match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", value)
        if direct_match:
            year, month, day = direct_match.groups()
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

        korean_match = re.search(r"(\d{2,4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", value)
        if korean_match:
            year, month, day = korean_match.groups()
            year = int(year)
            if year < 100:
                year += 2000
            return f"{year:04d}-{int(month):02d}-{int(day):02d}"

        dotted_match = re.search(r"(\d{2,4})[./](\d{1,2})[./](\d{1,2})", value)
        if dotted_match:
            year, month, day = dotted_match.groups()
            year = int(year)
            if year < 100:
                year += 2000
            return f"{year:04d}-{int(month):02d}-{int(day):02d}"

        return value

    def capture_pending_registration_items(entries, default_location=None):
        latest_frame_b64 = session_state.get("latest_frame_b64", "")
        cleaned_entries = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = " ".join((entry.get("name") or "").split()).strip()
            if not name:
                continue
            cleaned_entries.append(
                {
                    "name": name,
                    "location": entry.get("location")
                    or default_location
                    or session_state.get("last_default_location"),
                    "quantity": entry.get("quantity"),
                    "memo": entry.get("memo"),
                }
            )

        pending_items = []
        for entry in cleaned_entries:
            pending_items.append(
                {
                    **entry,
                    "image": latest_frame_b64,
                    "image_mime_type": "image/jpeg" if latest_frame_b64 else "",
                }
            )

        session_state["pending_registration_items"] = pending_items
        logger.info(
            "[%s] Pending registration captured count=%s with_images=%s",
            connection_id,
            len(pending_items),
            sum(1 for item in pending_items if item.get("image")),
        )

    def complete_pending_registration(expiry_date):
        normalized_expiry_date = normalize_expiry_date(expiry_date)
        pending_items = session_state.get("pending_registration_items", [])
        if not pending_items:
            return {
                "ok": False,
                "message": "현재 유통기한 입력을 기다리는 등록 항목이 없어요.",
                "spoken_response": "현재 유통기한 입력을 기다리는 등록 항목이 없어요.",
                **inventory_payload(),
            }

        registered_items = []
        for entry in pending_items:
            item = inventory_store.register_item(
                name=entry["name"],
                location=entry.get("location") or "냉장",
                expiry_date=normalized_expiry_date,
                quantity=entry.get("quantity"),
                memo=entry.get("memo"),
                image=entry.get("image"),
                image_mime_type=entry.get("image_mime_type"),
            )
            registered_items.append(item)

        session_state["pending_registration_items"] = []
        names_preview = ", ".join(item["name"] for item in registered_items[:6])
        message = (
            f"{names_preview}의 유통기한을 {normalized_expiry_date}로 기록하고 "
            f"{len(registered_items)}개 항목 등록을 완료했어요."
        )
        return {
            "ok": True,
            "registered_items": registered_items,
            "message": message,
            "spoken_response": message,
            **inventory_payload(),
        }

    def build_recipe_preference_question():
        names = [item["name"] for item in inventory_store.list_items()[:6]]
        preview = ", ".join(names) if names else "현재 재고"
        question = (
            f"지금 {preview} 같은 재료가 있어요. 어떤 종류 음식 원하세요? "
            "예를 들면 한식, 중식, 양식, 일식, 매콤한 거, 따뜻한 국물, 가벼운 아침처럼 말해 주세요."
        )
        return {
            "ok": False,
            "needs_recipe_preference": True,
            "message": question,
            "spoken_response": question,
            **inventory_payload(),
        }

    def is_generic_recipe_preference(preference):
        normalized = " ".join((preference or "").split()).strip().lower()
        if not normalized:
            return True
        specific_style_terms = [
            "한식",
            "중식",
            "양식",
            "일식",
            "분식",
            "매콤",
            "담백",
            "고소",
            "따뜻한 국물",
            "국물",
            "가벼운 아침",
            "아침",
            "브런치",
            "야식",
            "안주",
            "면",
            "밥",
            "파스타",
            "리조또",
            "찌개",
            "국",
            "탕",
            "전골",
            "볶음",
            "조림",
            "구이",
            "찜",
            "덮밥",
            "볶음밥",
            "오믈렛",
            "샐러드",
            "스프",
            "카레",
            "토스트",
            "김치찌개",
            "계란찜",
            "recipe",
            "pasta",
            "soup",
        ]
        if any(term in normalized for term in specific_style_terms):
            return False

        generic_terms = [
            "레시피",
            "추천",
            "추천해",
            "추천해 줘",
            "추천해줘",
            "추천 좀",
            "추천 부탁",
            "아무거나",
            "맛있는 거",
            "해먹고 싶은데",
            "만들 수 있는 거",
            "만들수있는거",
            "뭘 먹지",
            "뭐 먹지",
            "뭐 해먹지",
            "가지고 있는 재료",
            "재료로만",
            "recipe",
            "something",
            "anything",
        ]
        return any(term in normalized for term in generic_terms)

    def estimate_mutation_items(tool_name, tool_kwargs):
        if tool_name == "register_items":
            items = tool_kwargs.get("items") or []
            return max(1, len(items))
        if tool_name == "delete_items":
            items = tool_kwargs.get("items") or []
            return max(1, len(items))
        if tool_name == "complete_pending_registration":
            pending_items = session_state.get("pending_registration_items", [])
            return max(1, len(pending_items))
        return 1

    def register_item(name, location, expiry_date=None, quantity=None, memo=None):
        if not expiry_date:
            capture_pending_registration_items(
                [
                    {
                        "name": name,
                        "location": location,
                        "quantity": quantity,
                        "memo": memo,
                    }
                ]
            )
            return build_missing_expiry_result([name])
        item = inventory_store.register_item(
            name=name,
            location=location,
            expiry_date=normalize_expiry_date(expiry_date),
            quantity=quantity,
            memo=memo,
            image=session_state["latest_frame_b64"],
            image_mime_type="image/jpeg" if session_state["latest_frame_b64"] else "",
        )
        session_state["pending_registration_items"] = []
        return {
            "ok": True,
            "message": f"{item['name']}을(를) {item['location']}에 등록했어요.",
            "spoken_response": f"{item['name']}을(를) {item['location']}에 넣어둘게요.",
            "item": item,
            **inventory_payload(),
        }

    async def register_items(items, default_location=None):
        effective_default_location = (
            default_location
            or session_state.get("last_default_location")
            or infer_default_location_from_text(session_state.get("last_user_text", ""))
        )
        logger.info(
            "[%s] register_items effective_default_location=%s requested_count=%s",
            connection_id,
            effective_default_location,
            len(items or []),
        )
        missing_expiry_names = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            name = (entry.get("name") or "").strip()
            if name and not entry.get("expiry_date"):
                missing_expiry_names.append(name)
        if missing_expiry_names:
            capture_pending_registration_items(
                items,
                default_location=effective_default_location,
            )
            logger.info(
                "[%s] register_items blocked missing_expiry=%s",
                connection_id,
                missing_expiry_names,
            )
            return build_missing_expiry_result(missing_expiry_names)

        requested_items = [entry.get("name", "") for entry in items if isinstance(entry, dict)]
        segmented_images = {}
        if session_state["latest_frame_b64"] and requested_items:
            try:
                segmented_images = await asyncio.wait_for(
                    item_segmenter.segment_items(
                        session_state["latest_frame_b64"],
                        requested_items,
                    ),
                    timeout=SEGMENTATION_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "[%s] register_items segmentation timed out after %ss requested=%s",
                    connection_id,
                    SEGMENTATION_TIMEOUT_SECONDS,
                    len(requested_items),
                )
            except Exception:
                logger.exception("[%s] register_items segmentation failed", connection_id)

        registered_items = []
        skipped_items = []

        for entry in items:
            if not isinstance(entry, dict):
                continue

            name = (entry.get("name") or "").strip()
            if not name:
                skipped_items.append({"reason": "missing_name"})
                continue

            location = entry.get("location") or effective_default_location
            if not location:
                skipped_items.append({"name": name, "reason": "missing_location"})
                continue

            segmented = segmented_images.get(" ".join(name.split()).lower(), {})
            item = inventory_store.register_item(
                name=name,
                location=location,
                expiry_date=normalize_expiry_date(entry.get("expiry_date")),
                quantity=entry.get("quantity"),
                memo=entry.get("memo"),
                image=segmented.get("image") or session_state["latest_frame_b64"],
                image_mime_type=segmented.get("mime_type")
                or ("image/jpeg" if session_state["latest_frame_b64"] else ""),
            )
            registered_items.append(item)

        message = f"{len(registered_items)}개 항목을 순서대로 등록했어요."
        if skipped_items:
            message += f" {len(skipped_items)}개는 정보가 부족해서 건너뛰었어요."
        if registered_items:
            session_state["pending_registration_items"] = []

        return {
            "ok": bool(registered_items),
            "message": message,
            "spoken_response": message,
            "registered_items": registered_items,
            "skipped_items": skipped_items,
            "default_location_used": effective_default_location,
            **inventory_payload(),
        }

    def find_item(name):
        item = inventory_store.find_item(name)
        if item:
            detail = f"{item['name']}은(는) {item['location']}에 있어요."
            if item.get("expiry_date"):
                detail += f" 유통기한은 {item['expiry_date']}입니다."
            return {
                "ok": True,
                "item": item,
                "message": detail,
                "spoken_response": detail,
                **inventory_payload(),
            }

        return {
            "ok": False,
            "item": None,
            "message": f"{name}은(는) 아직 재고에서 찾지 못했어요.",
            "spoken_response": f"{name}은(는) 아직 등록된 재고에서 찾지 못했어요.",
            **inventory_payload(),
        }

    def delete_item(name):
        item = inventory_store.delete_item(name)
        if item:
            return {
                "ok": True,
                "deleted_item": item,
                "message": f"{item['name']}을(를) 재고에서 삭제했어요.",
                "spoken_response": f"{item['name']} 삭제 완료했어요.",
                **inventory_payload(),
            }

        return {
            "ok": False,
            "deleted_item": None,
            "message": f"{name}은(는) 삭제할 항목을 찾지 못했어요.",
            "spoken_response": f"{name}은(는) 아직 등록되지 않았어요.",
            **inventory_payload(),
        }

    def delete_items(items):
        deleted_items = []
        skipped_items = []

        for entry in items or []:
            name = " ".join(str(entry or "").split()).strip()
            if not name:
                skipped_items.append({"reason": "missing_name"})
                continue

            item = inventory_store.delete_item(name)
            if item:
                deleted_items.append(item)
            else:
                skipped_items.append({"name": name, "reason": "not_found"})

        message = f"{len(deleted_items)}개 항목을 삭제했어요."
        if skipped_items:
            message += f" {len(skipped_items)}개는 찾지 못해서 건너뛰었어요."

        if deleted_items:
            preview = ", ".join(item["name"] for item in deleted_items[:4])
            spoken_response = f"{preview} 삭제를 완료했어요."
            if len(deleted_items) > 4:
                spoken_response = f"{preview} 등 {len(deleted_items)}개 항목 삭제를 완료했어요."
        elif skipped_items:
            preview = ", ".join(
                item["name"] for item in skipped_items[:3] if item.get("name")
            )
            spoken_response = (
                f"{preview} 항목을 찾지 못했어요."
                if preview
                else "삭제할 항목을 찾지 못했어요."
            )
        else:
            spoken_response = "삭제할 항목이 없었어요."

        return {
            "ok": bool(deleted_items),
            "deleted_items": deleted_items,
            "skipped_items": skipped_items,
            "message": message,
            "spoken_response": spoken_response,
            **inventory_payload(),
        }

    def list_items(location=None):
        normalized_location = normalize_location(location) if location else None
        data = inventory_payload(location=normalized_location)
        location_label = normalized_location or "전체"
        item_names = [item["name"] for item in data["items"][:6]]
        preview = ", ".join(item_names) if item_names else "등록된 재료가 없어요"
        return {
            "ok": True,
            "location": location_label,
            "message": f"{location_label} 재고를 정리해 보여드릴게요.",
            "spoken_response": f"{location_label} 재고는 {preview}입니다.",
            **data,
        }

    def get_expiring_items(within_days=3):
        days = within_days or 3
        expiring_items = inventory_store.get_expiring_items(within_days=days)
        if expiring_items:
            preview = ", ".join(
                f"{item['name']} D-{item['days_left']}" for item in expiring_items[:4]
            )
        else:
            preview = f"{days}일 이내에 임박한 재료가 없어요."

        return {
            "ok": True,
            "expiring_items": expiring_items,
            "message": "유통기한이 가까운 재료를 확인했어요.",
            "spoken_response": preview,
            **inventory_payload(),
        }

    def get_recipe_recommendations(limit=3):
        inventory_items = inventory_store.list_items()
        if not inventory_items:
            return {
                "ok": False,
                "message": "아직 등록된 재고가 없어서 메뉴 추천이 어려워요. 먼저 재료를 등록해 주세요.",
                "spoken_response": "아직 재고가 없어서 메뉴 추천이 어려워요. 먼저 재료를 등록해 주세요.",
                **inventory_payload(),
            }

        preference = session_state.get("last_user_text", "").strip()
        if is_generic_recipe_preference(preference):
            return build_recipe_preference_question()

        recommendation_payload = recipe_generator.recommend_recipes(
            inventory_items=inventory_items,
            preference=preference,
            limit=limit or 3,
        )
        recipes = recommendation_payload.get("recommendations", [])
        top_recipe_name = recipes[0]["name"] if recipes else None
        recipe_plan = None
        if top_recipe_name:
            recipe_plan = recipe_generator.generate_recipe(
                inventory_items=inventory_items,
                preference=preference,
                recipe_name=top_recipe_name,
            )

        if recipes:
            preview = ", ".join(recipe["name"] for recipe in recipes[:2])
            spoken_response = (
                f"{recommendation_payload.get('preference_summary', preference)} 기준으로 "
                f"{preview} 같은 메뉴를 추천할게요. 대표 레시피도 같이 열어둘게요."
            )
        else:
            spoken_response = "지금 재고로 어울리는 메뉴를 찾지 못했어요."

        return {
            "ok": bool(recipes),
            "recipes": recipes,
            "recipe_plan": recipe_plan,
            "recipe_preference": preference,
            "recipe_preference_summary": recommendation_payload.get(
                "preference_summary", preference
            ),
            "message": "현재 재고와 원하는 스타일을 바탕으로 메뉴를 추천했어요.",
            "spoken_response": spoken_response,
            **inventory_payload(),
        }

    def generate_recipe_plan(preference, servings=None, avoid_ingredients=None):
        inventory_items = inventory_store.list_items()
        if not inventory_items:
            return {
                "ok": False,
                "message": "아직 등록된 재고가 없어서 레시피를 만들 수 없어요. 먼저 재료를 등록해 주세요.",
                "spoken_response": "아직 재고가 없어서 레시피를 만들 수 없어요. 먼저 재료를 등록해 주세요.",
                **inventory_payload(),
            }
        if is_generic_recipe_preference(preference):
            return build_recipe_preference_question()

        recipe_plan = recipe_generator.generate_recipe(
            inventory_items=inventory_items,
            preference=preference,
            servings=servings,
            avoid_ingredients=avoid_ingredients,
        )
        title = recipe_plan.get("title") or "추천 레시피"
        summary = recipe_plan.get("summary") or ""
        spoken_response = f"{title} 레시피를 준비했어요. 화면에서 바로 확인해 보세요."
        return {
            "ok": True,
            "recipe_plan": recipe_plan,
            "recipe_preference": preference,
            "message": f"{title} 레시피를 만들었어요. {summary}".strip(),
            "spoken_response": spoken_response,
            **inventory_payload(),
        }

    def run_logged_tool(tool_name, tool_func, log_kwargs=None, **tool_kwargs):
        logger.info(
            "[%s] Tool start name=%s args=%s",
            connection_id,
            tool_name,
            log_kwargs or tool_kwargs,
        )
        requested_items = estimate_mutation_items(tool_name, tool_kwargs)
        if (
            tool_name in MUTATING_TOOLS
            and session_state.get("mutation_items_this_turn", 0) + requested_items
            > MAX_MUTATION_ITEMS_PER_TURN
        ):
            result = build_mutation_guard_result(tool_name, requested_items)
            log_tool_end(tool_name, result)
            return result

        result = tool_func(**tool_kwargs)
        if tool_name in MUTATING_TOOLS and isinstance(result, dict) and result.get("ok"):
            session_state["mutation_items_this_turn"] += requested_items
            logger.info(
                "[%s] Mutation tool committed tool=%s turn_id=%s total_items=%s added_items=%s limit=%s",
                connection_id,
                tool_name,
                session_state["turn_id"],
                session_state["mutation_items_this_turn"],
                requested_items,
                MAX_MUTATION_ITEMS_PER_TURN,
            )
        if isinstance(result, dict):
            result["model_response"] = build_model_tool_result(result)
            logger.info(
                "[%s] Tool payload sizes name=%s browser_bytes=%s model_bytes=%s",
                connection_id,
                tool_name,
                len(json.dumps(result, ensure_ascii=False).encode("utf-8")),
                len(json.dumps(result["model_response"], ensure_ascii=False).encode("utf-8")),
            )
        logger.info(
            "[%s] Tool end name=%s ok=%s total=%s",
            connection_id,
            tool_name,
            result.get("ok") if isinstance(result, dict) else None,
            result.get("summary", {}).get("total") if isinstance(result, dict) else None,
        )
        return result

    def register_item_logged(name, location, expiry_date=None, quantity=None, memo=None):
        return run_logged_tool(
            "register_item",
            register_item,
            log_kwargs={
                "name": name,
                "location": location,
                "expiry_date": expiry_date,
                "quantity": quantity,
                "memo": memo,
                "has_image": bool(session_state["latest_frame_b64"]),
            },
            name=name,
            location=location,
            expiry_date=expiry_date,
            quantity=quantity,
            memo=memo,
        )

    async def register_items_logged(items, default_location=None):
        log_payload = {"count": len(items or []), "default_location": default_location}
        logger.info("[%s] Tool start name=register_items args=%s", connection_id, log_payload)
        requested_items = estimate_mutation_items(
            "register_items",
            {"items": items, "default_location": default_location},
        )
        if (
            session_state.get("mutation_items_this_turn", 0) + requested_items
            > MAX_MUTATION_ITEMS_PER_TURN
        ):
            result = build_mutation_guard_result("register_items", requested_items)
            log_tool_end("register_items", result)
            return result

        result = await register_items(items=items, default_location=default_location)
        if result.get("ok"):
            session_state["mutation_items_this_turn"] += requested_items
            logger.info(
                "[%s] Mutation tool committed tool=register_items turn_id=%s total_items=%s added_items=%s limit=%s",
                connection_id,
                session_state["turn_id"],
                session_state["mutation_items_this_turn"],
                requested_items,
                MAX_MUTATION_ITEMS_PER_TURN,
            )
        result["model_response"] = build_model_tool_result(result)
        logger.info(
            "[%s] Tool payload sizes name=register_items browser_bytes=%s model_bytes=%s",
            connection_id,
            len(json.dumps(result, ensure_ascii=False).encode("utf-8")),
            len(json.dumps(result["model_response"], ensure_ascii=False).encode("utf-8")),
        )
        log_tool_end("register_items", result)
        return result

    def find_item_logged(name):
        return run_logged_tool("find_item", find_item, name=name)

    def delete_item_logged(name):
        return run_logged_tool("delete_item", delete_item, name=name)

    def delete_items_logged(items):
        return run_logged_tool(
            "delete_items",
            delete_items,
            log_kwargs={"count": len(items or []), "items": items},
            items=items,
        )

    def list_items_logged(location=None):
        return run_logged_tool("list_items", list_items, location=location)

    def get_expiring_items_logged(within_days=3):
        return run_logged_tool(
            "get_expiring_items",
            get_expiring_items,
            within_days=within_days,
        )

    def get_recipe_recommendations_logged(limit=3):
        return run_logged_tool(
            "get_recipe_recommendations",
            get_recipe_recommendations,
            limit=limit,
        )

    def generate_recipe_plan_logged(preference, servings=None, avoid_ingredients=None):
        return run_logged_tool(
            "generate_recipe_plan",
            generate_recipe_plan,
            preference=preference,
            servings=servings,
            avoid_ingredients=avoid_ingredients,
        )

    def complete_pending_registration_logged(expiry_date):
        return run_logged_tool(
            "complete_pending_registration",
            complete_pending_registration,
            expiry_date=expiry_date,
        )

    gemini_client = GeminiLive(
        api_key=GEMINI_API_KEY,
        model=MODEL,
        input_sample_rate=16000,
        tools=[FRESHCHECK_TOOL],
        tool_mapping={
            "register_item": register_item_logged,
            "register_items": register_items_logged,
            "find_item": find_item_logged,
            "delete_item": delete_item_logged,
            "delete_items": delete_items_logged,
            "list_items": list_items_logged,
            "get_expiring_items": get_expiring_items_logged,
            "get_recipe_recommendations": get_recipe_recommendations_logged,
            "generate_recipe_plan": generate_recipe_plan_logged,
            "complete_pending_registration": complete_pending_registration_logged,
        },
        system_instruction=SYSTEM_PROMPT,
    )

    async def maybe_complete_pending_registration_from_text(user_text):
        if not session_state.get("pending_registration_items"):
            return False

        if not re.search(r"(\d{2,4})\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일|(\d{2,4})[-./]\d{1,2}[-./]\d{1,2}", user_text or ""):
            return False

        normalized_expiry_date = normalize_expiry_date(user_text)
        result = complete_pending_registration_logged(normalized_expiry_date)
        session_state["suppress_gemini_until_turn_complete"] = True
        await safe_send_json(
            {
                "type": "tool_call",
                "name": "complete_pending_registration",
                "args": {"expiry_date": normalized_expiry_date},
                "result": result,
            }
        )
        await safe_send_json({"type": "gemini", "text": result.get("spoken_response", "")})
        await safe_send_json({"type": "turn_complete"})
        logger.info(
            "[%s] Pending registration auto-completed from text expiry_date=%s",
            connection_id,
            normalized_expiry_date,
        )
        return True

    async def receive_from_client():
        try:
            while not disconnected.is_set():
                message = await websocket.receive()

                if message.get("bytes"):
                    session_state["last_client_heartbeat"] = time.monotonic()
                    session_state["audio_chunks_received"] += 1
                    dropped, queued = enqueue_latest(
                        audio_input_queue,
                        message["bytes"],
                        "audio_chunks_dropped",
                    )
                    if (
                        session_state["audio_chunks_received"] <= 3
                        or session_state["audio_chunks_received"] % 50 == 0
                    ):
                        logger.info(
                            "[%s] Client audio chunk=%s bytes=%s dropped=%s queue=%s/%s total_dropped=%s",
                            connection_id,
                            session_state["audio_chunks_received"],
                            len(message["bytes"]),
                            dropped,
                            audio_input_queue.qsize(),
                            AUDIO_QUEUE_MAXSIZE,
                            session_state["audio_chunks_dropped"],
                        )
                    elif dropped:
                        logger.warning(
                            "[%s] Dropped stale audio chunks=%s total_dropped=%s",
                            connection_id,
                            dropped,
                            session_state["audio_chunks_dropped"],
                        )
                    if not queued:
                        logger.warning("[%s] Failed to enqueue latest audio chunk", connection_id)
                    continue

                if message.get("type") == "websocket.disconnect":
                    logger.info(
                        "[%s] Client sent websocket.disconnect code=%s",
                        connection_id,
                        message.get("code"),
                    )
                    disconnected.set()
                    break

                if not message.get("text"):
                    logger.debug("[%s] Ignoring websocket message without text", connection_id)
                    continue

                raw_text = message["text"]
                session_state["last_client_heartbeat"] = time.monotonic()
                logger.info("[%s] Client text payload length=%s", connection_id, len(raw_text))
                try:
                    payload = json.loads(raw_text)
                except json.JSONDecodeError:
                    logger.info("[%s] Plain text user message", connection_id)
                    begin_user_turn("plain_text", raw_text)
                    if await maybe_complete_pending_registration_from_text(raw_text):
                        continue
                    turn_text = compose_turn_text(
                        raw_text,
                        session_state["latest_frame_b64"],
                        session_state["pending_registration_items"],
                        session_state["selected_language"],
                    )
                    while text_input_queue.full():
                        try:
                            text_input_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    text_input_queue.put_nowait(turn_text)
                    continue

                if not isinstance(payload, dict):
                    logger.info("[%s] Non-dict JSON payload treated as text", connection_id)
                    begin_user_turn("json_non_dict", raw_text)
                    if await maybe_complete_pending_registration_from_text(raw_text):
                        continue
                    turn_text = compose_turn_text(
                        raw_text,
                        session_state["latest_frame_b64"],
                        session_state["pending_registration_items"],
                        session_state["selected_language"],
                    )
                    while text_input_queue.full():
                        try:
                            text_input_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    text_input_queue.put_nowait(turn_text)
                    continue

                if payload.get("type") == "settings":
                    session_state["selected_language"] = normalize_response_language(
                        payload.get("language")
                    )
                    logger.info(
                        "[%s] Session language updated language=%s",
                        connection_id,
                        session_state["selected_language"],
                    )
                    settings_text = (
                        "[FreshCheck live session setting]\n"
                        f"- preferred_response_language: {session_state['selected_language']}\n"
                        f"- The user may speak in {session_state['selected_language']} from now on.\n"
                        f"- Recognize and respond in {session_state['selected_language']}."
                    )
                    while text_input_queue.full():
                        try:
                            text_input_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    text_input_queue.put_nowait(settings_text)
                    continue

                if payload.get("type") == "heartbeat":
                    logger.debug("[%s] Client heartbeat received", connection_id)
                    continue

                if payload.get("type") == "client_disconnect":
                    logger.info(
                        "[%s] Client requested disconnect reason=%s",
                        connection_id,
                        payload.get("reason"),
                    )
                    disconnected.set()
                    break

                if payload.get("type") == "image":
                    session_state["latest_frame_b64"] = payload.get("data", "")
                    image_data = base64.b64decode(payload["data"])
                    session_state["video_frames_received"] += 1
                    dropped, queued = enqueue_latest(
                        video_input_queue,
                        image_data,
                        "video_frames_dropped",
                    )
                    if (
                        session_state["video_frames_received"] <= 2
                        or session_state["video_frames_received"] % 10 == 0
                    ):
                        logger.info(
                            "[%s] Client image frame=%s bytes=%s dropped=%s queue=%s/%s total_dropped=%s",
                            connection_id,
                            session_state["video_frames_received"],
                            len(image_data),
                            dropped,
                            video_input_queue.qsize(),
                            VIDEO_QUEUE_MAXSIZE,
                            session_state["video_frames_dropped"],
                        )
                    if not queued:
                        logger.warning("[%s] Failed to enqueue latest video frame", connection_id)
                    continue

                if "text" in payload:
                    logger.info(
                        "[%s] JSON user text payload text=%s",
                        connection_id,
                        payload["text"],
                    )
                    begin_user_turn("json_text", payload["text"])
                    if await maybe_complete_pending_registration_from_text(payload["text"]):
                        continue
                    turn_text = compose_turn_text(
                        payload["text"],
                        session_state["latest_frame_b64"],
                        session_state["pending_registration_items"],
                        session_state["selected_language"],
                    )
                    while text_input_queue.full():
                        try:
                            text_input_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    text_input_queue.put_nowait(turn_text)
                    continue

                logger.warning("[%s] Unknown JSON payload=%s", connection_id, payload)
        except WebSocketDisconnect:
            logger.info("[%s] WebSocketDisconnect from client=%s", connection_id, client_label)
            disconnected.set()
        except asyncio.CancelledError:
            logger.info("[%s] receive_from_client cancelled", connection_id)
            disconnected.set()
            raise
        except Exception as exc:
            logger.exception("[%s] Error receiving from client: %s", connection_id, exc)
            disconnected.set()
        finally:
            logger.info("[%s] receive_from_client finished", connection_id)
            disconnected.set()

    receive_task = asyncio.create_task(receive_from_client())

    async def heartbeat_watchdog():
        try:
            while not disconnected.is_set():
                await asyncio.sleep(2)
                idle_seconds = time.monotonic() - session_state["last_client_heartbeat"]
                if idle_seconds > HEARTBEAT_TIMEOUT_SECONDS:
                    logger.warning(
                        "[%s] Heartbeat timeout idle_seconds=%.2f timeout=%.2f. Closing stale session.",
                        connection_id,
                        idle_seconds,
                        HEARTBEAT_TIMEOUT_SECONDS,
                    )
                    disconnected.set()
                    try:
                        await websocket.close(code=1001, reason="heartbeat_timeout")
                    except Exception:
                        pass
                    break
        except asyncio.CancelledError:
            logger.info("[%s] heartbeat_watchdog cancelled", connection_id)
            raise

    heartbeat_task = asyncio.create_task(heartbeat_watchdog())

    async def run_session():
        logger.info("[%s] Gemini session loop starting", connection_id)
        async for event in gemini_client.start_session(
            audio_input_queue=audio_input_queue,
            video_input_queue=video_input_queue,
            text_input_queue=text_input_queue,
            audio_output_callback=audio_output_callback,
            audio_interrupt_callback=audio_interrupt_callback,
        ):
            if disconnected.is_set():
                logger.info("[%s] Stop forwarding Gemini events because client disconnected", connection_id)
                break
            if session_state["suppress_gemini_until_turn_complete"]:
                event_type = event.get("type") if isinstance(event, dict) else None
                if event_type == "turn_complete":
                    logger.info(
                        "[%s] Suppression window closed on turn_complete",
                        connection_id,
                    )
                    session_state["suppress_gemini_until_turn_complete"] = False
                    continue
                if event_type in {"gemini", "tool_call", "error", "interrupted"}:
                    logger.info(
                        "[%s] Suppressing Gemini event during forced registration completion type=%s",
                        connection_id,
                        event_type,
                    )
                    continue
            if event:
                if (
                    isinstance(event, dict)
                    and event.get("type") == "user"
                    and session_state.get("pending_registration_items")
                    and re.search(
                        r"(\d{2,4})\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일|(\d{2,4})[-./]\d{1,2}[-./]\d{1,2}",
                        event.get("text", "") or "",
                    )
                ):
                    await safe_send_json(event)
                    if await maybe_complete_pending_registration_from_text(event.get("text", "")):
                        continue
                logger.info(
                    "[%s] Gemini event type=%s",
                    connection_id,
                    event.get("type") if isinstance(event, dict) else type(event).__name__,
                )
                sent = await safe_send_json(event)
                if not sent:
                    logger.info("[%s] Failed to forward Gemini event to client", connection_id)
                    break
        logger.info("[%s] Gemini session loop finished", connection_id)

    try:
        await run_session()
    except Exception as exc:
        logger.exception("[%s] Error in Gemini session: %s", connection_id, exc)
    finally:
        logger.info("[%s] websocket_endpoint cleanup starting", connection_id)
        disconnected.set()
        receive_task.cancel()
        heartbeat_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("[%s] websocket_endpoint cleanup finished", connection_id)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    logger.info("Starting FreshCheck server host=%s port=%s log_level=%s", host, port, LOG_LEVEL)
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=LOG_LEVEL.lower(),
        access_log=True,
    )
