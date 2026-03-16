(function () {
  const STORAGE_KEY = "freshcheck-ui-state-v2";

  const TEXT = {
    ko: {
      lang: "ko",
      title: "FreshCheck Live",
      heroTitle: "냉장고를 보고 듣는 실시간 식재료 에이전트",
      heroCopy:
        "카메라와 음성으로 식재료를 등록하고, 어디에 있는지 찾고, 오늘 만들 수 있는 메뉴까지 추천받으세요.",
      featureTitles: ["실시간 멀티모달", "도구 실행", "자연스러운 대화 UX"],
      featureDescriptions: [
        "카메라와 마이크를 함께 사용해 냉장고 상황을 바로 이해합니다.",
        "등록, 조회, 삭제, 유통기한 확인, 레시피 추천을 실제 재고 데이터로 처리합니다.",
        "짧고 자연스럽게 응답하고, 도중에 정정하거나 끼어들 수도 있습니다.",
      ],
      languageLabel: "응답 언어",
      hint:
        '연결 예시: "이거 고등어야, 냉동에 넣어줘", "양파 어디 있어?", "유통기한 임박한 거 보여줘"',
      connect: "FreshCheck 연결",
      sessionEnded: "세션이 종료되었습니다.",
      restart: "다시 시작",
      liveView: "Live View",
      fridgeView: "냉장고 확인",
      videoPlaceholder: "카메라를 켜면 현재 장면이 전송됩니다.",
      quickScan: "재료 스캔",
      quickExpiry: "유통기한 확인",
      quickRecipe: "레시피 추천",
      quickPrompts: {
        scan: "지금 보이는 식재료를 정리해줘",
        expiry: "유통기한 임박한 재료 알려줘",
        recipe: "지금 재고로 만들 수 있는 메뉴 추천해줘",
      },
      textPlaceholder: '예: "이거 우유야 냉장에 넣어줘"',
      send: "전송",
      recentActivity: "최근 동작",
      workspace: "Workspace",
      workspaceTitle: "재료 / 레시피",
      inventoryTab: "재료 탭",
      recipeTab: "레시피 탭",
      summaryLabels: ["전체", "냉장", "냉동", "상온"],
      locationTabs: ["전체", "냉장", "냉동", "상온"],
      recipeEmpty: "레시피 추천을 요청하면 여기에 표시됩니다.",
      recipeBack: "추천 목록으로",
      status: {
        disconnected: "Disconnected",
        connected: "Connected",
        connecting: "Connecting...",
        error: "Connection Error",
      },
    },
    en: {
      lang: "en",
      title: "FreshCheck Live",
      heroTitle: "A real-time ingredient agent that sees and hears your fridge",
      heroCopy:
        "Register ingredients with camera and voice, find where they are, and get meal ideas from what you already have.",
      featureTitles: ["Real-time multimodal", "Tool execution", "Natural conversation UX"],
      featureDescriptions: [
        "It understands your fridge state using camera and microphone together.",
        "Register, lookup, delete, expiry checks, and recipe suggestions run on real inventory data.",
        "It replies briefly and naturally, and you can interrupt or correct it mid-conversation.",
      ],
      languageLabel: "Response language",
      hint:
        'Try: "This is mackerel, put it in the freezer", "Where are the onions?", "Show me what is about to expire."',
      connect: "Connect FreshCheck",
      sessionEnded: "The session has ended.",
      restart: "Start again",
      liveView: "Live View",
      fridgeView: "Fridge View",
      videoPlaceholder: "Turn on the camera to stream the current scene.",
      quickScan: "Scan items",
      quickExpiry: "Check expiry",
      quickRecipe: "Recipe ideas",
      quickPrompts: {
        scan: "Organize the ingredients visible right now.",
        expiry: "Show ingredients that are close to expiring.",
        recipe: "Recommend meals I can make with my current inventory.",
      },
      textPlaceholder: 'Example: "This is milk, put it in the fridge."',
      send: "Send",
      recentActivity: "Recent activity",
      workspace: "Workspace",
      workspaceTitle: "Inventory / Recipes",
      inventoryTab: "Inventory",
      recipeTab: "Recipes",
      summaryLabels: ["Total", "Fridge", "Freezer", "Pantry"],
      locationTabs: ["All", "Fridge", "Freezer", "Pantry"],
      recipeEmpty: "Recipe suggestions will appear here after you ask for them.",
      recipeBack: "Back to list",
      status: {
        disconnected: "Disconnected",
        connected: "Connected",
        connecting: "Connecting...",
        error: "Connection Error",
      },
    },
    ja: {
      lang: "ja",
      title: "FreshCheck Live",
      heroTitle: "冷蔵庫を見て聞くリアルタイム食材エージェント",
      heroCopy:
        "カメラと音声で食材を登録し、どこにあるかを探し、今ある材料で作れるメニューまで提案します。",
      featureTitles: ["リアルタイムマルチモーダル", "ツール実行", "自然な会話UX"],
      featureDescriptions: [
        "カメラとマイクを一緒に使って冷蔵庫の状態をすぐに理解します。",
        "登録、検索、削除、賞味期限確認、レシピ提案を実際の在庫データで処理します。",
        "短く自然に返答し、途中で訂正したり割り込んだりできます。",
      ],
      languageLabel: "応答言語",
      hint:
        '接続例: 「これはサバだから冷凍に入れて」「玉ねぎはどこ？」「賞味期限が近いものを見せて」',
      connect: "FreshCheckに接続",
      sessionEnded: "セッションが終了しました。",
      restart: "もう一度始める",
      liveView: "Live View",
      fridgeView: "冷蔵庫の確認",
      videoPlaceholder: "カメラをオンにすると現在の映像が送信されます。",
      quickScan: "食材スキャン",
      quickExpiry: "期限確認",
      quickRecipe: "レシピ提案",
      quickPrompts: {
        scan: "今見えている食材を整理して。",
        expiry: "賞味期限が近い食材を教えて。",
        recipe: "今の在庫で作れるメニューをおすすめして。",
      },
      textPlaceholder: '例: 「これは牛乳だから冷蔵に入れて」',
      send: "送信",
      recentActivity: "最近の動作",
      workspace: "Workspace",
      workspaceTitle: "食材 / レシピ",
      inventoryTab: "食材",
      recipeTab: "レシピ",
      summaryLabels: ["全体", "冷蔵", "冷凍", "常温"],
      locationTabs: ["全体", "冷蔵", "冷凍", "常温"],
      recipeEmpty: "レシピ提案を依頼するとここに表示されます。",
      recipeBack: "一覧に戻る",
      status: {
        disconnected: "Disconnected",
        connected: "Connected",
        connecting: "Connecting...",
        error: "Connection Error",
      },
    },
  };

  function getStoredLanguage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return "ko";
      const parsed = JSON.parse(raw);
      return typeof parsed?.selectedLanguage === "string"
        ? parsed.selectedLanguage
        : "ko";
    } catch (error) {
      console.warn("Failed to read UI language:", error);
      return "ko";
    }
  }

  function getText(lang) {
    return TEXT[lang] || TEXT.ko;
  }

  function setTextContent(selector, value) {
    const node = document.querySelector(selector);
    if (node) node.textContent = value;
  }

  function setAllTextContent(selector, values) {
    const nodes = Array.from(document.querySelectorAll(selector));
    nodes.forEach((node, index) => {
      if (values[index] != null) node.textContent = values[index];
    });
  }

  function setStatusText(value) {
    const statusDiv = document.getElementById("status");
    if (!statusDiv) return;
    if (statusDiv.textContent !== value) {
      statusDiv.textContent = value;
    }
  }

  function updateStatusLabel(texts) {
    const statusDiv = document.getElementById("status");
    if (!statusDiv) return;
    if (statusDiv.classList.contains("connected")) {
      setStatusText(texts.status.connected);
    } else if (statusDiv.classList.contains("error")) {
      setStatusText(texts.status.error);
    } else if (
      statusDiv.textContent.trim() === "Connecting..." ||
      statusDiv.textContent.trim() === texts.status.connecting
    ) {
      setStatusText(texts.status.connecting);
    } else {
      setStatusText(texts.status.disconnected);
    }
  }

  function updateStaticText(lang) {
    const texts = getText(lang);
    document.documentElement.lang = texts.lang;
    document.title = texts.title;

    setTextContent(".hero h1", texts.heroTitle);
    setTextContent(".hero-copy", texts.heroCopy);
    setAllTextContent(".feature-card h3", texts.featureTitles);
    setAllTextContent(".feature-card p", texts.featureDescriptions);
    setTextContent(".language-label", texts.languageLabel);
    setTextContent(".hint", texts.hint);
    setTextContent("#connectBtn", texts.connect);
    setTextContent(".session-end-section h2", texts.sessionEnded);
    setTextContent("#restartBtn", texts.restart);

    const panelLabels = Array.from(document.querySelectorAll(".panel-label"));
    if (panelLabels[0]) panelLabels[0].textContent = texts.liveView;
    if (panelLabels[1]) panelLabels[1].textContent = texts.workspace;

    setTextContent(".live-panel .panel-header h2", texts.fridgeView);

    const videoPlaceholder = document.getElementById("video-placeholder");
    if (videoPlaceholder && !videoPlaceholder.classList.contains("hidden")) {
      videoPlaceholder.textContent = texts.videoPlaceholder;
    }

    const chips = Array.from(document.querySelectorAll(".chip"));
    if (chips[0]) {
      chips[0].textContent = texts.quickScan;
      chips[0].dataset.prompt = texts.quickPrompts.scan;
    }
    if (chips[1]) {
      chips[1].textContent = texts.quickExpiry;
      chips[1].dataset.prompt = texts.quickPrompts.expiry;
    }
    if (chips[2]) {
      chips[2].textContent = texts.quickRecipe;
      chips[2].dataset.prompt = texts.quickPrompts.recipe;
    }

    const textInput = document.getElementById("textInput");
    if (textInput) textInput.placeholder = texts.textPlaceholder;
    setTextContent("#sendBtn", texts.send);
    setTextContent(".inline-event-box h3", texts.recentActivity);
    setTextContent(".workspace-header h2", texts.workspaceTitle);
    setTextContent("#openInventoryBtn", texts.inventoryTab);
    setTextContent("#openRecipeBtn", texts.recipeTab);
    setAllTextContent(".summary-card span", texts.summaryLabels);
    setAllTextContent(".tab-btn", texts.locationTabs);

    const recipeEmpty = document.querySelector("#recipe-list .empty-text");
    if (recipeEmpty) recipeEmpty.textContent = texts.recipeEmpty;
    setTextContent("#recipe-back-btn", texts.recipeBack);

    updateStatusLabel(texts);
  }

  function persistLanguage(lang) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      parsed.selectedLanguage = lang;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed));
    } catch (error) {
      console.warn("Failed to persist UI language:", error);
    }
  }

  function applyLanguage(lang) {
    updateStaticText(lang);
    persistLanguage(lang);
  }

  function bindLanguageButtons() {
    const buttons = Array.from(document.querySelectorAll(".language-option"));
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const lang = button.dataset.language || "ko";
        setTimeout(() => applyLanguage(lang), 0);
      });
    });
  }

  function observeStatus() {
    const statusDiv = document.getElementById("status");
    if (!statusDiv) return;
    const observer = new MutationObserver(() => {
      updateStatusLabel(getText(getStoredLanguage()));
    });
    observer.observe(statusDiv, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
    });
  }

  bindLanguageButtons();
  applyLanguage(getStoredLanguage());
  observeStatus();
})();
