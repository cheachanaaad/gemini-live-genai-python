const statusDiv = document.getElementById("status");
const authSection = document.getElementById("auth-section");
const appSection = document.getElementById("app-section");
const sessionEndSection = document.getElementById("session-end-section");
const restartBtn = document.getElementById("restartBtn");
const micBtn = document.getElementById("micBtn");
const cameraBtn = document.getElementById("cameraBtn");
const cameraFlipBtn = document.getElementById("cameraFlipBtn");
const screenBtn = document.getElementById("screenBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const videoPreview = document.getElementById("video-preview");
const videoPlaceholder = document.getElementById("video-placeholder");
const connectBtn = document.getElementById("connectBtn");
const chatLog = document.getElementById("chat-log");
const inventoryList = document.getElementById("inventory-list");
const recipeList = document.getElementById("recipe-list");
const recipeDetail = document.getElementById("recipe-detail");
const recipeDetailContent = document.getElementById("recipe-detail-content");
const recipeBackBtn = document.getElementById("recipe-back-btn");
const openInventoryBtn = document.getElementById("openInventoryBtn");
const openRecipeBtn = document.getElementById("openRecipeBtn");
const inventoryPanel = document.getElementById("inventory-panel");
const recipePanel = document.getElementById("recipe-panel");
const activityLog = document.getElementById("activity-log");
const toolToast = document.getElementById("tool-toast");
const toolToastTitle = document.getElementById("tool-toast-title");
const toolToastBody = document.getElementById("tool-toast-body");
const summaryTotal = document.getElementById("summary-total");
const summaryFridge = document.getElementById("summary-fridge");
const summaryFreezer = document.getElementById("summary-freezer");
const summaryPantry = document.getElementById("summary-pantry");
const tabButtons = Array.from(document.querySelectorAll(".tab-btn"));
const quickActionButtons = Array.from(document.querySelectorAll(".chip"));
const languageButtons = Array.from(document.querySelectorAll(".language-option"));
const UI_STATE_STORAGE_KEY = "freshcheck-ui-state-v2";
let workspacePersistTimer = null;

const LANGUAGE_CONFIG = {
  ko: {
    name: "Korean",
    intro:
      "안녕 FreshCheck. 지금부터 냉장고 재고를 관리해줘. 먼저 짧게 자기소개해줘.",
  },
  en: {
    name: "English",
    intro:
      "Hi FreshCheck. Please manage my fridge inventory from now on. First, introduce yourself briefly.",
  },
  ja: {
    name: "Japanese",
    intro:
      "こんにちは、FreshCheck。これから冷蔵庫の在庫を管理して。まずは短く自己紹介して。",
  },
};

LANGUAGE_CONFIG.ko.intro =
  "안녕 FreshCheck. 지금부터 냉장고 재고를 관리해줘. 먼저 짧게 자기소개해줘.";
LANGUAGE_CONFIG.ja.intro =
  "こんにちは、FreshCheck。これから冷蔵庫の在庫を管理して。まずは短く自己紹介して。";

const UI_RUNTIME_TEXT = {
  ko: {
    micStart: "마이크 시작",
    micStop: "마이크 중지",
    cameraStart: "카메라 시작",
    cameraStop: "카메라 중지",
    frontCamera: "전면 카메라",
    rearCamera: "후면 카메라",
    shareScreen: "화면 공유",
    stopSharing: "공유 중지",
    disconnect: "연결 종료",
    activityMicStopped: "마이크 입력을 중지했습니다.",
    activityMicStarted: "마이크 입력을 시작했습니다.",
    activityCameraStopped: "카메라 스트림을 중지했습니다.",
    activityCameraStarted: "카메라 스트림을 시작했습니다.",
    activityUsingCamera: "현재 {camera} 카메라를 사용 중입니다.",
    activityNextCamera: "다음 카메라 시작 시 {camera} 카메라를 사용합니다.",
    activitySwitchedCamera: "{camera} 카메라로 전환했습니다.",
    activityScreenStopped: "화면 공유를 중지했습니다.",
    activityScreenStarted: "화면 공유를 시작했습니다.",
    alertMic: "마이크를 시작할 수 없습니다.",
    alertCamera: "카메라에 접근할 수 없습니다.",
    alertCameraSwitch: "카메라 전환에 실패했습니다.",
    alertScreen: "화면을 공유할 수 없습니다.",
  },
  en: {
    micStart: "Start mic",
    micStop: "Stop mic",
    cameraStart: "Start camera",
    cameraStop: "Stop camera",
    frontCamera: "Front camera",
    rearCamera: "Rear camera",
    shareScreen: "Share screen",
    stopSharing: "Stop sharing",
    disconnect: "Disconnect",
    activityMicStopped: "Microphone input stopped.",
    activityMicStarted: "Microphone input started.",
    activityCameraStopped: "Camera stream stopped.",
    activityCameraStarted: "Camera stream started.",
    activityUsingCamera: "Currently using the {camera} camera.",
    activityNextCamera: "The next camera start will use the {camera} camera.",
    activitySwitchedCamera: "Switched to the {camera} camera.",
    activityScreenStopped: "Screen sharing stopped.",
    activityScreenStarted: "Screen sharing started.",
    alertMic: "Unable to start the microphone.",
    alertCamera: "Unable to access the camera.",
    alertCameraSwitch: "Failed to switch the camera.",
    alertScreen: "Unable to share the screen.",
  },
  ja: {
    micStart: "マイク開始",
    micStop: "マイク停止",
    cameraStart: "カメラ開始",
    cameraStop: "カメラ停止",
    frontCamera: "前面カメラ",
    rearCamera: "背面カメラ",
    shareScreen: "画面共有",
    stopSharing: "共有停止",
    disconnect: "接続終了",
    activityMicStopped: "マイク入力を停止しました。",
    activityMicStarted: "マイク入力を開始しました。",
    activityCameraStopped: "カメラ映像を停止しました。",
    activityCameraStarted: "カメラ映像を開始しました。",
    activityUsingCamera: "現在 {camera} を使用中です。",
    activityNextCamera: "次回のカメラ開始では {camera} を使います。",
    activitySwitchedCamera: "{camera} に切り替えました。",
    activityScreenStopped: "画面共有を停止しました。",
    activityScreenStarted: "画面共有を開始しました。",
    alertMic: "マイクを開始できません。",
    alertCamera: "カメラにアクセスできません。",
    alertCameraSwitch: "カメラの切り替えに失敗しました。",
    alertScreen: "画面共有ができません。",
  },
};

const appState = {
  inventory: [],
  summary: { total: 0, 냉장: 0, 냉동: 0, 상온: 0 },
  activeLocation: "all",
  recipes: [],
  currentRecipe: null,
  recipeDetails: {},
  lastRecipePreference: "",
  activeWorkspace: "inventory",
  activity: [],
  cameraFacingMode: "environment",
  selectedLanguage: "ko",
  videoMode: "none",
};

let currentGeminiMessageDiv = null;
let currentUserMessageDiv = null;
let pendingToolMessageDiv = null;
let toolToastTimer = null;
let isTearingDown = false;

const mediaHandler = new MediaHandler();
const geminiClient = new GeminiClient({
  onOpen: async () => {
    statusDiv.textContent = "Connected";
    statusDiv.className = "status connected";
    authSection.classList.add("hidden");
    appSection.classList.remove("hidden");
    sessionEndSection.classList.add("hidden");
    await syncInventoryFromServer();

    geminiClient.send(
      JSON.stringify({
        type: "settings",
        language: appState.selectedLanguage,
      })
    );
    geminiClient.sendText(
      (LANGUAGE_CONFIG[appState.selectedLanguage] || LANGUAGE_CONFIG.ko).intro
    );
  },
  onMessage: (event) => {
    if (typeof event.data === "string") {
      try {
        handleJsonMessage(JSON.parse(event.data));
      } catch (error) {
        console.error("Parse error:", error);
      }
    } else {
      mediaHandler.playAudio(event.data);
    }
  },
  onClose: () => {
    statusDiv.textContent = "Disconnected";
    statusDiv.className = "status disconnected";
    showSessionEnd();
  },
  onError: () => {
    statusDiv.textContent = "Connection Error";
    statusDiv.className = "status error";
  },
});

function appendMessage(type, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${type}`;
  msgDiv.textContent = text;
  chatLog.appendChild(msgDiv);
  chatLog.scrollTop = chatLog.scrollHeight;
  return msgDiv;
}

function getToolPendingText(toolName) {
  const map = {
    register_item: "등록중...",
    register_items: "여러 개 등록중...",
    find_item: "찾는중...",
    delete_item: "삭제중...",
    delete_items: "일괄 삭제중...",
    list_items: "불러오는중...",
    get_expiring_items: "확인중...",
    get_recipe_recommendations: "추천 준비중...",
    generate_recipe_plan: "레시피 만드는중...",
    complete_pending_registration: "유통기한 기록중...",
  };
  return map[toolName] || "처리중...";
}

function showPendingToolMessage(toolName) {
  const text = getToolPendingText(toolName);
  if (pendingToolMessageDiv) {
    pendingToolMessageDiv.textContent = text;
    return;
  }
  pendingToolMessageDiv = appendMessage("system", text);
}

function clearPendingToolMessage() {
  if (!pendingToolMessageDiv) return;
  pendingToolMessageDiv.remove();
  pendingToolMessageDiv = null;
}

function showToolToast(toolName, bodyText) {
  if (!toolToast || !toolToastTitle || !toolToastBody) return;
  if (toolToastTimer) {
    clearTimeout(toolToastTimer);
    toolToastTimer = null;
  }
  toolToastTitle.textContent = getToolPendingText(toolName);
  toolToastBody.textContent = bodyText || "잠시만 기다려주세요.";
  toolToast.classList.remove("hidden");
}

function hideToolToast(delay = 400) {
  if (!toolToast) return;
  if (toolToastTimer) {
    clearTimeout(toolToastTimer);
  }
  toolToastTimer = setTimeout(() => {
    toolToast.classList.add("hidden");
    toolToastTimer = null;
  }, delay);
}

function getToolToastBody(toolName, args) {
  const name = args?.name ? ` ${args.name}` : "";
  const map = {
    register_item: `${name} 등록을 처리하고 있습니다.`,
    register_items: "여러 재료 등록을 처리하고 있습니다.",
    find_item: `${name} 위치를 확인하고 있습니다.`,
    delete_item: `${name} 삭제를 처리하고 있습니다.`,
    delete_items: "여러 식재료 삭제를 처리하고 있습니다.",
    list_items: "현재 재고 목록을 불러오고 있습니다.",
    get_expiring_items: "유통기한 임박 재료를 확인하고 있습니다.",
    get_recipe_recommendations: "재고 기반 메뉴를 추천하고 있습니다.",
    generate_recipe_plan: "상세 레시피를 생성하고 있습니다.",
    complete_pending_registration: "유통기한 정보를 반영하고 있습니다.",
  };
  return map[toolName] || "요청을 처리하고 있습니다.";
}

function saveUiState() {
  const stateToPersist = buildWorkspaceStatePayload();
  try {
    localStorage.setItem(UI_STATE_STORAGE_KEY, JSON.stringify(stateToPersist));
  } catch (error) {
    console.warn("Failed to save UI state:", error);
  }
  scheduleWorkspaceStatePersist(stateToPersist);
}

function buildWorkspaceStatePayload() {
  return {
    recipes: appState.recipes,
    currentRecipe: appState.currentRecipe,
    recipeDetails: appState.recipeDetails,
    lastRecipePreference: appState.lastRecipePreference,
    activeWorkspace: appState.activeWorkspace,
    activeLocation: appState.activeLocation,
    selectedLanguage: appState.selectedLanguage,
  };
}

function applyStoredUiState(stored) {
  if (!stored || typeof stored !== "object") return;
  if (Array.isArray(stored.recipes)) appState.recipes = stored.recipes;
  if (stored.currentRecipe && typeof stored.currentRecipe === "object") {
    appState.currentRecipe = stored.currentRecipe;
  }
  if (stored.currentRecipe === null) {
    appState.currentRecipe = null;
  }
  if (stored.recipeDetails && typeof stored.recipeDetails === "object") {
    appState.recipeDetails = stored.recipeDetails;
  }
  if (typeof stored.lastRecipePreference === "string") {
    appState.lastRecipePreference = stored.lastRecipePreference;
  }
  if (typeof stored.activeWorkspace === "string") {
    appState.activeWorkspace = stored.activeWorkspace;
  }
  if (typeof stored.activeLocation === "string") {
    appState.activeLocation = stored.activeLocation;
  }
  if (typeof stored.selectedLanguage === "string") {
    appState.selectedLanguage = stored.selectedLanguage;
  }
}

function loadUiState() {
  try {
    const raw = localStorage.getItem(UI_STATE_STORAGE_KEY);
    if (!raw) return;
    applyStoredUiState(JSON.parse(raw));
  } catch (error) {
    console.warn("Failed to load UI state:", error);
  }
}

function scheduleWorkspaceStatePersist(state) {
  if (workspacePersistTimer) {
    clearTimeout(workspacePersistTimer);
  }
  workspacePersistTimer = setTimeout(() => {
    workspacePersistTimer = null;
    persistWorkspaceState(state);
  }, 120);
}

async function persistWorkspaceState(state) {
  try {
    await fetch("/api/workspace-state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
      keepalive: true,
    });
  } catch (error) {
    console.warn("Failed to persist workspace state:", error);
  }
}

function flushWorkspaceStatePersist() {
  const state = buildWorkspaceStatePayload();
  try {
    localStorage.setItem(UI_STATE_STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.warn("Failed to flush UI state to localStorage:", error);
  }

  if (workspacePersistTimer) {
    clearTimeout(workspacePersistTimer);
    workspacePersistTimer = null;
  }

  if (navigator.sendBeacon) {
    try {
      const blob = new Blob([JSON.stringify(state)], {
        type: "application/json",
      });
      navigator.sendBeacon("/api/workspace-state", blob);
      return;
    } catch (error) {
      console.warn("sendBeacon workspace persist failed:", error);
    }
  }

  persistWorkspaceState(state);
}

async function hydrateWorkspaceStateFromServer() {
  try {
    const response = await fetch("/api/workspace-state");
    if (!response.ok) return;
    const payload = await response.json();
    if (!payload.ok || !payload.state) return;
    applyStoredUiState(payload.state);
  } catch (error) {
    console.warn("Failed to hydrate workspace state:", error);
  }
}

function setWorkspaceTab(tabName) {
  appState.activeWorkspace = tabName;
  const isInventory = tabName === "inventory";
  inventoryPanel.classList.toggle("hidden", !isInventory);
  recipePanel.classList.toggle("hidden", isInventory);
  openInventoryBtn.classList.toggle("active", isInventory);
  openRecipeBtn.classList.toggle("active", !isInventory);
  openInventoryBtn.setAttribute("aria-selected", String(isInventory));
  openRecipeBtn.setAttribute("aria-selected", String(!isInventory));
  saveUiState();
}

function updateLanguageButtons() {
  languageButtons.forEach((button) => {
    const isActive = button.dataset.language === appState.selectedLanguage;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function getRuntimeText() {
  return UI_RUNTIME_TEXT[appState.selectedLanguage] || UI_RUNTIME_TEXT.ko;
}

function updateRuntimeLabels() {
  const texts = getRuntimeText();
  micBtn.textContent = mediaHandler.isRecording ? texts.micStop : texts.micStart;
  cameraBtn.textContent =
    appState.videoMode === "camera" ? texts.cameraStop : texts.cameraStart;
  screenBtn.textContent =
    appState.videoMode === "screen" ? texts.stopSharing : texts.shareScreen;
  cameraFlipBtn.textContent =
    appState.cameraFacingMode === "environment"
      ? texts.rearCamera
      : texts.frontCamera;
  disconnectBtn.textContent = texts.disconnect;
}

function localizeCameraName() {
  const texts = getRuntimeText();
  return appState.cameraFacingMode === "environment"
    ? texts.rearCamera
    : texts.frontCamera;
}

function addActivity(text) {
  appState.activity.unshift(text);
  appState.activity = appState.activity.slice(0, 6);
  renderActivity();
}

function renderActivity() {
  activityLog.innerHTML = "";
  if (!appState.activity.length) {
    activityLog.innerHTML =
      '<p class="empty-text">도구 호출이나 재고 변경이 있으면 여기에 기록됩니다.</p>';
    return;
  }

  for (const item of appState.activity) {
    const div = document.createElement("div");
    div.className = "activity-item";
    div.textContent = item;
    activityLog.appendChild(div);
  }
}

function updateCameraFlipLabel() {
  updateRuntimeLabels();
}

function updateInventoryState(payload) {
  if (!payload) return;
  if (Array.isArray(payload.items)) {
    appState.inventory = payload.items;
  }
  if (payload.summary) {
    appState.summary = payload.summary;
  }
  renderSummary();
  renderInventory();
}

function renderSummary() {
  summaryTotal.textContent = appState.summary.total ?? 0;
  summaryFridge.textContent = appState.summary["냉장"] ?? 0;
  summaryFreezer.textContent = appState.summary["냉동"] ?? 0;
  summaryPantry.textContent = appState.summary["상온"] ?? 0;
}

function renderInventory() {
  inventoryList.innerHTML = "";
  const items =
    appState.activeLocation === "all"
      ? appState.inventory
      : appState.inventory.filter(
          (item) => item.location === appState.activeLocation
        );

  if (!items.length) {
    inventoryList.innerHTML =
      '<p class="empty-text">아직 등록된 식재료가 없습니다. 카메라를 비추고 음성으로 추가해보세요.</p>';
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = "inventory-card";

    const imageMimeType = item.image_mime_type || "image/jpeg";
    const image = item.image
      ? `<img src="data:${imageMimeType};base64,${item.image}" alt="${item.name}" />`
      : "";
    const expiry = item.expiry_date
      ? `<p class="inventory-meta">유통기한: ${item.expiry_date}</p>`
      : "";
    const quantity = item.quantity
      ? `<p class="inventory-meta">수량: ${item.quantity}</p>`
      : "";
    const memo = item.memo
      ? `<p class="inventory-meta">메모: ${item.memo}</p>`
      : "";
    const registeredDate = item.registered_at
      ? new Date(item.registered_at).toLocaleDateString("ko-KR", {
          month: "numeric",
          day: "numeric",
        })
      : "";

    card.innerHTML = `
      <div class="inventory-card-media">${image}</div>
      <div class="inventory-card-body">
        <div class="inventory-head">
          <h3>${item.name}</h3>
          <span class="badge">${item.location}</span>
        </div>
        ${expiry}
        ${quantity}
        ${memo}
        ${
          registeredDate
            ? `<p class="inventory-meta inventory-date">등록일 ${registeredDate}</p>`
            : ""
        }
      </div>
    `;
    inventoryList.appendChild(card);
  }
}

function renderRecipes() {
  recipeList.innerHTML = "";
  if (appState.currentRecipe) {
    recipeList.classList.add("hidden");
    recipeDetail.classList.remove("hidden");
    renderRecipeDetail();
    return;
  }

  recipeList.classList.remove("hidden");
  recipeDetail.classList.add("hidden");
  if (!appState.recipes.length) {
    recipeList.innerHTML =
      '<p class="empty-text">레시피 추천을 요청하면 여기에 표시됩니다.</p>';
    return;
  }

  for (const recipe of appState.recipes) {
    const card = document.createElement("article");
    card.className = "recipe-card";
    card.role = "button";
    card.tabIndex = 0;
    const matched = recipe.matched_ingredients?.length
      ? `<p>활용 재료: ${recipe.matched_ingredients.join(", ")}</p>`
      : "";
    const missing =
      recipe.missing_ingredients?.length > 0
        ? `<ul>${recipe.missing_ingredients
            .map((ingredient) => `<li>추가 필요: ${ingredient}</li>`)
            .join("")}</ul>`
        : "";
    card.innerHTML = `
      <h4>${recipe.name}</h4>
      <p>${recipe.description || ""}</p>
      ${matched}
      ${missing}
    `;
    card.addEventListener("click", () => {
      openRecipeDetail(recipe);
    });
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openRecipeDetail(recipe);
      }
    });
    recipeList.appendChild(card);
  }
}

function getRecipeKey(recipe) {
  return (
    recipe?.name ||
    recipe?.title ||
    recipe?.recommended_recipe_name ||
    ""
  ).trim();
}

function createRecipeCardFromPlan(recipePlan) {
  if (!recipePlan || typeof recipePlan !== "object") return null;

  const recipeKey = getRecipeKey(recipePlan);
  if (!recipeKey) return null;

  const matchedIngredients = Array.isArray(recipePlan.inventory_ingredients)
    ? recipePlan.inventory_ingredients
    : Array.isArray(recipePlan.ingredients)
    ? recipePlan.ingredients
        .filter((ingredient) => ingredient?.from_inventory)
        .map((ingredient) => ingredient.name)
    : [];

  const missingIngredients = Array.isArray(recipePlan.missing_ingredients)
    ? recipePlan.missing_ingredients
    : Array.isArray(recipePlan.ingredients)
    ? recipePlan.ingredients
        .filter((ingredient) => ingredient && ingredient.from_inventory === false)
        .map((ingredient) => ingredient.name)
    : [];

  return {
    name: recipeKey,
    description:
      recipePlan.summary || recipePlan.preference_reflection || "",
    matched_ingredients: matchedIngredients,
    missing_ingredients: missingIngredients,
  };
}

function mergeRecipeCards(existingRecipes, incomingRecipes) {
  const merged = [];
  const seen = new Set();

  for (const recipe of incomingRecipes || []) {
    const recipeKey = getRecipeKey(recipe);
    if (!recipeKey || seen.has(recipeKey)) continue;
    seen.add(recipeKey);
    merged.push(recipe);
  }

  for (const recipe of existingRecipes || []) {
    const recipeKey = getRecipeKey(recipe);
    if (!recipeKey || seen.has(recipeKey)) continue;
    seen.add(recipeKey);
    merged.push(recipe);
  }

  return merged;
}

function applyRecipeToolResult(result) {
  let changed = false;

  if (Array.isArray(result.recipes) && result.recipes.length) {
    appState.recipes = mergeRecipeCards(appState.recipes, result.recipes);
    appState.lastRecipePreference =
      result.recipe_preference || result.recipe_preference_summary || "";
    changed = true;
  }

  if (result.recipe_plan) {
    appState.currentRecipe = result.recipe_plan;
    const recipeKey = getRecipeKey(result.recipe_plan);
    if (recipeKey) {
      appState.recipeDetails[recipeKey] = result.recipe_plan;
      const recipeCard = createRecipeCardFromPlan(result.recipe_plan);
      if (recipeCard) {
        appState.recipes = mergeRecipeCards(appState.recipes, [recipeCard]);
      }
    }
    if (result.recipe_preference) {
      appState.lastRecipePreference = result.recipe_preference;
    }
    changed = true;
  }

  if (changed) {
    renderRecipes();
    setWorkspaceTab("recipe");
    saveUiState();
  }
}

async function openRecipeDetail(recipe) {
  const cacheKey = recipe.name || recipe.title;
  if (!cacheKey) return;

  if (appState.recipeDetails[cacheKey]) {
    appState.currentRecipe = appState.recipeDetails[cacheKey];
    renderRecipes();
    setWorkspaceTab("recipe");
    saveUiState();
    return;
  }

  addActivity(`${cacheKey} 상세 레시피를 불러오는 중입니다.`);

  try {
    const response = await fetch("/api/recipe-detail", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recipe_name: cacheKey,
        preference: appState.lastRecipePreference || cacheKey,
      }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok || !payload.recipe_plan) {
      throw new Error(payload.message || "상세 레시피를 불러오지 못했습니다.");
    }

    appState.recipeDetails[cacheKey] = payload.recipe_plan;
    appState.currentRecipe = payload.recipe_plan;
    const recipeCard = createRecipeCardFromPlan(payload.recipe_plan);
    if (recipeCard) {
      appState.recipes = mergeRecipeCards(appState.recipes, [recipeCard]);
    }
    renderRecipes();
    setWorkspaceTab("recipe");
    saveUiState();
  } catch (error) {
    console.error("Recipe detail load failed:", error);
    addActivity(`오류: ${error.message}`);
  }
}

function renderRecipeDetail() {
  const recipe = appState.currentRecipe;
  recipeDetailContent.innerHTML = "";

  if (!recipe) {
    recipeDetail.classList.add("hidden");
    recipeList.classList.remove("hidden");
    return;
  }

  const ingredientItems = (recipe.ingredients || [])
    .map(
      (ingredient) => `
        <li>
          <strong>${ingredient.name}</strong>
          <span>${ingredient.amount}</span>
          <em>${ingredient.from_inventory ? "재고 사용" : "추가 필요"}</em>
        </li>
      `
    )
    .join("");
  const stepItems = (recipe.steps || [])
    .map(
      (step, index) => `
        <li>
          <strong>${step.title || `Step ${index + 1}`}</strong>
          <p>${step.instruction || ""}</p>
        </li>
      `
    )
    .join("");
  const missingItems = (recipe.missing_ingredients || [])
    .map((item) => `<li>${item}</li>`)
    .join("");
  const tipItems = (recipe.tips || []).map((tip) => `<li>${tip}</li>`).join("");

  recipeDetailContent.innerHTML = `
    <article class="recipe-detail-card">
      <p class="recipe-kicker">FreshCheck Recipe</p>
      <h4>${recipe.title || "추천 레시피"}</h4>
      <p class="recipe-summary">${recipe.summary || ""}</p>
      <div class="recipe-meta-grid">
        <div><span>인분</span><strong>${recipe.servings ?? "-"}</strong></div>
        <div><span>조리 시간</span><strong>${recipe.cook_time_minutes ?? "-"}분</strong></div>
        <div><span>난이도</span><strong>${recipe.difficulty || "-"}</strong></div>
      </div>
      <section class="recipe-section">
        <h5>취향 반영</h5>
        <p>${recipe.preference_reflection || ""}</p>
      </section>
      <section class="recipe-section">
        <h5>재료</h5>
        <ul class="recipe-ingredients">${ingredientItems}</ul>
      </section>
      ${
        missingItems
          ? `<section class="recipe-section"><h5>추가로 있으면 좋은 재료</h5><ul>${missingItems}</ul></section>`
          : ""
      }
      <section class="recipe-section">
        <h5>조리 순서</h5>
        <ol class="recipe-steps">${stepItems}</ol>
      </section>
      ${
        tipItems
          ? `<section class="recipe-section"><h5>팁</h5><ul>${tipItems}</ul></section>`
          : ""
      }
    </article>
  `;
}

async function syncInventoryFromServer() {
  try {
    const response = await fetch("/api/inventory");
    if (!response.ok) return;
    const payload = await response.json();
    updateInventoryState(payload);
  } catch (error) {
    console.error("Inventory sync failed:", error);
  }
}

function handleJsonMessage(msg) {
  if (msg.type === "interrupted") {
    mediaHandler.stopAudioPlayback();
    currentGeminiMessageDiv = null;
    currentUserMessageDiv = null;
    addActivity("응답이 중단되어 새 대화를 받을 준비를 마쳤습니다.");
    return;
  }

  if (msg.type === "turn_complete") {
    currentGeminiMessageDiv = null;
    currentUserMessageDiv = null;
    return;
  }

  if (msg.type === "user") {
    if (currentUserMessageDiv) {
      currentUserMessageDiv.textContent += msg.text;
      chatLog.scrollTop = chatLog.scrollHeight;
    } else {
      currentUserMessageDiv = appendMessage("user", msg.text);
    }
    return;
  }

  if (msg.type === "gemini") {
    if (currentGeminiMessageDiv) {
      currentGeminiMessageDiv.textContent += msg.text;
      chatLog.scrollTop = chatLog.scrollHeight;
    } else {
      currentGeminiMessageDiv = appendMessage("gemini", msg.text);
    }
    return;
  }

  if (msg.type === "inventory_state") {
    updateInventoryState(msg);
    return;
  }

  if (msg.type === "tool_call_start") {
    showPendingToolMessage(msg.name);
    showToolToast(msg.name, getToolToastBody(msg.name, msg.args));
    return;
  }

  if (msg.type === "tool_call") {
    const result = msg.result || {};
    clearPendingToolMessage();
    hideToolToast();
    updateInventoryState(result);
    applyRecipeToolResult(result);
    if (Array.isArray(result.expiring_items) && msg.name === "get_expiring_items") {
      const names = result.expiring_items.length
        ? result.expiring_items
            .map((item) => `${item.name} D-${item.days_left}`)
            .join(", ")
        : "임박한 재료가 없습니다.";
      addActivity(`유통기한 확인: ${names}`);
    } else if (result.message) {
      addActivity(result.message);
    } else {
      addActivity(`${msg.name} 도구가 실행되었습니다.`);
    }
    return;
  }

  if (msg.type === "error") {
    clearPendingToolMessage();
    addActivity(`오류: ${msg.error}`);
  }
}

function resetUI() {
  authSection.classList.remove("hidden");
  appSection.classList.add("hidden");
  sessionEndSection.classList.add("hidden");
  mediaHandler.stopAudioPlayback();
  mediaHandler.stopAudio();
  mediaHandler.stopVideo(videoPreview);
  videoPlaceholder.classList.remove("hidden");
  micBtn.textContent = "마이크 시작";
  cameraBtn.textContent = "카메라 시작";
  appState.cameraFacingMode = "environment";
  updateCameraFlipLabel();
  screenBtn.textContent = "화면 공유";
  clearPendingToolMessage();
  chatLog.innerHTML = "";
  setWorkspaceTab("inventory");
  connectBtn.disabled = false;
  renderRecipes();
}

function teardownLiveSession(options = {}) {
  if (isTearingDown) return;
  isTearingDown = true;

  try {
    mediaHandler.stopAudioPlayback();
    mediaHandler.stopAudio();
    mediaHandler.stopVideo(videoPreview);
    geminiClient.disconnect(1000, options.reason || "client_teardown");
  } finally {
    appState.videoMode = "none";
    isTearingDown = false;
  }
}

function showSessionEnd() {
  appSection.classList.add("hidden");
  sessionEndSection.classList.remove("hidden");
  mediaHandler.stopAudioPlayback();
  mediaHandler.stopAudio();
  mediaHandler.stopVideo(videoPreview);
}

connectBtn.onclick = async () => {
  statusDiv.textContent = "Connecting...";
  connectBtn.disabled = true;

  try {
    teardownLiveSession({ reason: "before_reconnect" });
    await mediaHandler.initializeAudio();
    geminiClient.connect();
  } catch (error) {
    statusDiv.textContent = `Connection Failed: ${error.message}`;
    statusDiv.className = "status error";
    connectBtn.disabled = false;
  }
};

disconnectBtn.onclick = () => {
  teardownLiveSession({ reason: "manual_disconnect" });
};

micBtn.onclick = async () => {
  if (mediaHandler.isRecording) {
    mediaHandler.stopAudio();
    micBtn.textContent = "마이크 시작";
    addActivity("마이크 입력을 중지했습니다.");
    return;
  }

  try {
    await mediaHandler.startAudio((data) => {
      if (geminiClient.isConnected()) {
        geminiClient.send(data);
      }
    });
    micBtn.textContent = "마이크 중지";
    addActivity("마이크 입력을 시작했습니다.");
  } catch (error) {
    alert("마이크를 시작할 수 없습니다.");
  }
};

cameraBtn.onclick = async () => {
  if (cameraBtn.textContent === "카메라 중지") {
    mediaHandler.stopVideo(videoPreview);
    cameraBtn.textContent = "카메라 시작";
    screenBtn.textContent = "화면 공유";
    videoPlaceholder.classList.remove("hidden");
    addActivity("카메라 스트리밍을 중지했습니다.");
    return;
  }

  if (mediaHandler.videoStream) {
    mediaHandler.stopVideo(videoPreview);
    screenBtn.textContent = "화면 공유";
  }

  try {
    await mediaHandler.startVideo(
      videoPreview,
      (base64Data) => {
        if (geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      },
      { facingMode: appState.cameraFacingMode }
    );
    cameraBtn.textContent = "카메라 중지";
    screenBtn.textContent = "화면 공유";
    videoPlaceholder.classList.add("hidden");
    addActivity(
      `카메라 스트리밍을 시작했습니다. 현재 ${
        appState.cameraFacingMode === "environment" ? "후면" : "전면"
      } 카메라를 사용 중입니다.`
    );
  } catch (error) {
    alert("카메라에 접근할 수 없습니다.");
  }
};

cameraFlipBtn.onclick = async () => {
  appState.cameraFacingMode =
    appState.cameraFacingMode === "environment" ? "user" : "environment";
  updateCameraFlipLabel();

  if (cameraBtn.textContent !== "카메라 중지") {
    addActivity(
      `다음 카메라 시작 시 ${
        appState.cameraFacingMode === "environment" ? "후면" : "전면"
      } 카메라를 사용합니다.`
    );
    return;
  }

  try {
    mediaHandler.stopVideo(videoPreview);
    await mediaHandler.startVideo(
      videoPreview,
      (base64Data) => {
        if (geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      },
      { facingMode: appState.cameraFacingMode }
    );
    videoPlaceholder.classList.add("hidden");
    addActivity(
      `${
        appState.cameraFacingMode === "environment" ? "후면" : "전면"
      } 카메라로 전환했습니다.`
    );
  } catch (error) {
    appState.cameraFacingMode =
      appState.cameraFacingMode === "environment" ? "user" : "environment";
    updateCameraFlipLabel();
    alert("카메라 전환에 실패했습니다.");
  }
};

screenBtn.onclick = async () => {
  if (screenBtn.textContent === "공유 중지") {
    mediaHandler.stopVideo(videoPreview);
    screenBtn.textContent = "화면 공유";
    cameraBtn.textContent = "카메라 시작";
    videoPlaceholder.classList.remove("hidden");
    addActivity("화면 공유를 중지했습니다.");
    return;
  }

  if (mediaHandler.videoStream) {
    mediaHandler.stopVideo(videoPreview);
    cameraBtn.textContent = "카메라 시작";
  }

  try {
    await mediaHandler.startScreen(
      videoPreview,
      (base64Data) => {
        if (geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      },
      () => {
        screenBtn.textContent = "화면 공유";
        videoPlaceholder.classList.remove("hidden");
      }
    );
    screenBtn.textContent = "공유 중지";
    cameraBtn.textContent = "카메라 시작";
    videoPlaceholder.classList.add("hidden");
    addActivity("화면 공유를 시작했습니다.");
  } catch (error) {
    alert("화면을 공유할 수 없습니다.");
  }
};

sendBtn.onclick = sendText;
textInput.onkeypress = (event) => {
  if (event.key === "Enter") sendText();
};

function sendText() {
  const text = textInput.value.trim();
  if (!text || !geminiClient.isConnected()) return;
  appendMessage("user", text);
   clearPendingToolMessage();
  geminiClient.sendText(text);
  textInput.value = "";
}

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    appState.activeLocation = button.dataset.location;
    tabButtons.forEach((tabButton) =>
      tabButton.classList.toggle("active", tabButton === button)
    );
    renderInventory();
    saveUiState();
  });
});

quickActionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    textInput.value = button.dataset.prompt || "";
    sendText();
  });
});

restartBtn.onclick = () => {
  resetUI();
};

recipeBackBtn.onclick = () => {
  appState.currentRecipe = null;
  renderRecipes();
  saveUiState();
};

openInventoryBtn.onclick = () => {
  renderInventory();
  setWorkspaceTab("inventory");
};

openRecipeBtn.onclick = () => {
  renderRecipes();
  setWorkspaceTab("recipe");
};

languageButtons.forEach((button) => {
  button.addEventListener("click", () => {
    appState.selectedLanguage = button.dataset.language || "ko";
    updateLanguageButtons();
    saveUiState();
  });
});

window.addEventListener("beforeunload", () => {
  teardownLiveSession({ reason: "beforeunload" });
  flushWorkspaceStatePersist();
});

window.addEventListener("pagehide", () => {
  teardownLiveSession({ reason: "pagehide" });
  flushWorkspaceStatePersist();
});

loadUiState();
hydrateWorkspaceStateFromServer().finally(() => {
  renderRecipes();
  setWorkspaceTab(appState.activeWorkspace || "inventory");
});
syncInventoryFromServer();
updateCameraFlipLabel();
renderSummary();
renderInventory();
renderActivity();
updateLanguageButtons();
tabButtons.forEach((tabButton) =>
  tabButton.classList.toggle(
    "active",
    tabButton.dataset.location === appState.activeLocation
  )
);

appState.videoMode = appState.videoMode || "none";

function getRuntimeText() {
  return UI_RUNTIME_TEXT[appState.selectedLanguage] || UI_RUNTIME_TEXT.ko;
}

function localizeCameraName() {
  const texts = getRuntimeText();
  return appState.cameraFacingMode === "environment"
    ? texts.rearCamera
    : texts.frontCamera;
}

function updateRuntimeLabels() {
  const texts = getRuntimeText();
  micBtn.textContent = mediaHandler.isRecording ? texts.micStop : texts.micStart;
  cameraBtn.textContent =
    appState.videoMode === "camera" ? texts.cameraStop : texts.cameraStart;
  screenBtn.textContent =
    appState.videoMode === "screen" ? texts.stopSharing : texts.shareScreen;
  cameraFlipBtn.textContent = localizeCameraName();
  disconnectBtn.textContent = texts.disconnect;
}

function updateCameraFlipLabel() {
  updateRuntimeLabels();
}

function resetUI() {
  authSection.classList.remove("hidden");
  appSection.classList.add("hidden");
  sessionEndSection.classList.add("hidden");
  mediaHandler.stopAudio();
  mediaHandler.stopVideo(videoPreview);
  videoPlaceholder.classList.remove("hidden");
  appState.cameraFacingMode = "environment";
  appState.videoMode = "none";
  clearPendingToolMessage();
  chatLog.innerHTML = "";
  setWorkspaceTab("inventory");
  connectBtn.disabled = false;
  renderRecipes();
  updateRuntimeLabels();
}

micBtn.onclick = async () => {
  const texts = getRuntimeText();
  if (mediaHandler.isRecording) {
    mediaHandler.stopAudio();
    updateRuntimeLabels();
    addActivity(texts.activityMicStopped);
    return;
  }

  try {
    await mediaHandler.startAudio((data) => {
      if (geminiClient.isConnected()) {
        geminiClient.send(data);
      }
    });
    updateRuntimeLabels();
    addActivity(texts.activityMicStarted);
  } catch (error) {
    alert(texts.alertMic);
  }
};

cameraBtn.onclick = async () => {
  const texts = getRuntimeText();
  if (appState.videoMode === "camera") {
    mediaHandler.stopVideo(videoPreview);
    appState.videoMode = "none";
    updateRuntimeLabels();
    videoPlaceholder.classList.remove("hidden");
    addActivity(texts.activityCameraStopped);
    return;
  }

  if (mediaHandler.videoStream) {
    mediaHandler.stopVideo(videoPreview);
    appState.videoMode = "none";
    updateRuntimeLabels();
  }

  try {
    await mediaHandler.startVideo(
      videoPreview,
      (base64Data) => {
        if (geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      },
      { facingMode: appState.cameraFacingMode }
    );
    appState.videoMode = "camera";
    updateRuntimeLabels();
    videoPlaceholder.classList.add("hidden");
    addActivity(
      `${texts.activityCameraStarted} ${texts.activityUsingCamera.replace(
        "{camera}",
        localizeCameraName()
      )}`
    );
  } catch (error) {
    alert(texts.alertCamera);
  }
};

cameraFlipBtn.onclick = async () => {
  const texts = getRuntimeText();
  appState.cameraFacingMode =
    appState.cameraFacingMode === "environment" ? "user" : "environment";
  updateRuntimeLabels();

  if (appState.videoMode !== "camera") {
    addActivity(texts.activityNextCamera.replace("{camera}", localizeCameraName()));
    return;
  }

  try {
    mediaHandler.stopVideo(videoPreview);
    await mediaHandler.startVideo(
      videoPreview,
      (base64Data) => {
        if (geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      },
      { facingMode: appState.cameraFacingMode }
    );
    appState.videoMode = "camera";
    updateRuntimeLabels();
    videoPlaceholder.classList.add("hidden");
    addActivity(texts.activitySwitchedCamera.replace("{camera}", localizeCameraName()));
  } catch (error) {
    appState.cameraFacingMode =
      appState.cameraFacingMode === "environment" ? "user" : "environment";
    updateRuntimeLabels();
    alert(texts.alertCameraSwitch);
  }
};

screenBtn.onclick = async () => {
  const texts = getRuntimeText();
  if (appState.videoMode === "screen") {
    mediaHandler.stopVideo(videoPreview);
    appState.videoMode = "none";
    updateRuntimeLabels();
    videoPlaceholder.classList.remove("hidden");
    addActivity(texts.activityScreenStopped);
    return;
  }

  if (mediaHandler.videoStream) {
    mediaHandler.stopVideo(videoPreview);
    appState.videoMode = "none";
    updateRuntimeLabels();
  }

  try {
    await mediaHandler.startScreen(
      videoPreview,
      (base64Data) => {
        if (geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      },
      () => {
        appState.videoMode = "none";
        updateRuntimeLabels();
        videoPlaceholder.classList.remove("hidden");
      }
    );
    appState.videoMode = "screen";
    updateRuntimeLabels();
    videoPlaceholder.classList.add("hidden");
    addActivity(texts.activityScreenStarted);
  } catch (error) {
    alert(texts.alertScreen);
  }
};

languageButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setTimeout(() => {
      updateRuntimeLabels();
      if (geminiClient.isConnected()) {
        geminiClient.send(
          JSON.stringify({
            type: "settings",
            language: appState.selectedLanguage,
          })
        );
      }
    }, 0);
  });
});

updateRuntimeLabels();

function handleJsonMessage(msg) {
  if (msg.type === "interrupted") {
    mediaHandler.stopAudioPlayback();
    currentGeminiMessageDiv = null;
    currentUserMessageDiv = null;
    addActivity("응답이 중단되어 새 입력을 받을 준비를 마쳤습니다.");
    return;
  }

  if (msg.type === "turn_complete") {
    currentGeminiMessageDiv = null;
    currentUserMessageDiv = null;
    return;
  }

  if (msg.type === "user") {
    if (currentUserMessageDiv) {
      currentUserMessageDiv.textContent += msg.text;
      chatLog.scrollTop = chatLog.scrollHeight;
    } else {
      currentUserMessageDiv = appendMessage("user", msg.text);
    }
    return;
  }

  if (msg.type === "gemini") {
    if (currentGeminiMessageDiv) {
      currentGeminiMessageDiv.textContent += msg.text;
      chatLog.scrollTop = chatLog.scrollHeight;
    } else {
      currentGeminiMessageDiv = appendMessage("gemini", msg.text);
    }
    return;
  }

  if (msg.type === "inventory_state") {
    updateInventoryState(msg);
    return;
  }

  if (msg.type === "tool_call_start") {
    showPendingToolMessage(msg.name);
    showToolToast(msg.name, getToolToastBody(msg.name, msg.args));
    return;
  }

  if (msg.type === "tool_call") {
    const result = msg.result || {};
    clearPendingToolMessage();
    hideToolToast();
    updateInventoryState(result);
    applyRecipeToolResult(result);

    if (Array.isArray(result.expiring_items) && msg.name === "get_expiring_items") {
      const names = result.expiring_items.length
        ? result.expiring_items
            .map((item) => `${item.name} D-${item.days_left}`)
            .join(", ")
        : "임박한 재료가 없습니다.";
      addActivity(`유통기한 확인: ${names}`);
    } else if (result.message) {
      addActivity(result.message);
    } else {
      addActivity(`${msg.name} 요청이 실행되었습니다.`);
    }
    return;
  }

  if (msg.type === "error") {
    clearPendingToolMessage();
    hideToolToast(0);
    addActivity(`오류: ${msg.error}`);
  }
}
