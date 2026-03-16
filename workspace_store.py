import json
import logging
from datetime import datetime, timezone

from json_storage import JsonStorageTarget

logger = logging.getLogger(__name__)


DEFAULT_WORKSPACE_STATE = {
    "recipes": [],
    "currentRecipe": None,
    "recipeDetails": {},
    "lastRecipePreference": "",
    "activeWorkspace": "inventory",
    "activeLocation": "all",
    "selectedLanguage": "ko",
    "updatedAt": "",
}


class WorkspaceStore:
    def __init__(self, file_path):
        self.storage = JsonStorageTarget(file_path)
        self.state = dict(DEFAULT_WORKSPACE_STATE)
        self._load()
        logger.info("WorkspaceStore initialized path=%s", self.storage.describe())

    def _load(self):
        if not self.storage.exists():
            logger.info("Workspace file not found path=%s", self.storage.describe())
            self.state = dict(DEFAULT_WORKSPACE_STATE)
            return

        try:
            raw = json.loads(self.storage.read_text())
        except (json.JSONDecodeError, OSError):
            logger.exception("Workspace load failed path=%s", self.storage.describe())
            self.state = dict(DEFAULT_WORKSPACE_STATE)
            return

        self.state = self._normalize(raw)
        logger.info(
            "Workspace loaded path=%s recipes=%s activeWorkspace=%s",
            self.storage.describe(),
            len(self.state["recipes"]),
            self.state["activeWorkspace"],
        )

    def _save(self):
        self.storage.write_text(json.dumps(self.state, ensure_ascii=False, indent=2))
        logger.info(
            "Workspace saved path=%s recipes=%s activeWorkspace=%s",
            self.storage.describe(),
            len(self.state["recipes"]),
            self.state["activeWorkspace"],
        )

    def _refresh(self):
        self._load()

    def _normalize(self, payload):
        normalized = dict(DEFAULT_WORKSPACE_STATE)
        if isinstance(payload, dict):
            if isinstance(payload.get("recipes"), list):
                normalized["recipes"] = payload["recipes"]
            current_recipe = payload.get("currentRecipe")
            if current_recipe is None or isinstance(current_recipe, dict):
                normalized["currentRecipe"] = current_recipe
            if isinstance(payload.get("recipeDetails"), dict):
                normalized["recipeDetails"] = payload["recipeDetails"]
            if isinstance(payload.get("lastRecipePreference"), str):
                normalized["lastRecipePreference"] = payload["lastRecipePreference"]
            if isinstance(payload.get("activeWorkspace"), str):
                normalized["activeWorkspace"] = payload["activeWorkspace"]
            if isinstance(payload.get("activeLocation"), str):
                normalized["activeLocation"] = payload["activeLocation"]
            if isinstance(payload.get("selectedLanguage"), str):
                normalized["selectedLanguage"] = payload["selectedLanguage"]
            if isinstance(payload.get("updatedAt"), str):
                normalized["updatedAt"] = payload["updatedAt"]
        return normalized

    def get_state(self):
        self._refresh()
        return dict(self.state)

    def save_state(self, payload):
        self._refresh()
        self.state = self._normalize(payload)
        self.state["updatedAt"] = datetime.now(timezone.utc).isoformat()
        self._save()
        return self.get_state()
