const STORAGE = {
  owned: "dragon-owned",
  ownedProfiles: "dragon-owned-profiles",
  activeOwnedProfile: "dragon-active-owned-profile",
  teams: "dragon-teams",
  activeTeam: "dragon-active-team",
  enemy: "dragon-enemy",
};
const MAX_TEAM_SIZE = 6;
const TEAM_POSITIONS = 9;
const SKILL_TYPES = ["天賦", "奧義", "絕技", "秘技", "特技"];
const ELEMENTS = ["灼燒", "感電", "寒冷", "冰凍", "引爆", "急冷", "蒸發", "激爆"];
const FACTIONS = {
  "曠野": ["wild_spirit.webp", "#27ae60", "曠野之靈"],
  "聖堂": ["sanctum_glory.webp", "#f1c40f", "聖堂榮光"],
  "彼岸": ["otherworld_return.webp", "#22c55e", "彼岸再臨"],
  "幻境": ["illusion_veil.webp", "#9b59b6", "幻境秘影"],
  "元素": ["elemental_echo.webp", "#e67e22", "元素迴響"],
  "奧術": ["arcane_wisdom.webp", "#2980b9", "奧術智慧"],
};
const PROFESSION = {
  "守衛": ["守", "#3867d6"], "牧師": ["牧", "#f7b731"], "刺客": ["刺", "#b33939"],
  "戰士": ["戰", "#e67e22"], "射手": ["射", "#20bf6b"], "法師": ["法", "#8854d0"],
};
const PROFESSION_ORDER = ["守衛", "牧師", "刺客", "戰士", "射手", "法師"];
const SKILL_COLORS = { "天賦": "#c0392b", "奧義": "#8e44ad", "絕技": "#d35400", "秘技": "#2471a3", "特技": "#16805c" };
const GOOGLE_FORM_URL = "https://forms.gle/2ZaLSUfowj9iR5g59";
const state = {
  characters: [],
  version: {},
  officialNoticeData: {},
  mechanics: {},
  owned: new Set(readJson(STORAGE.owned, [])),
  ownedProfiles: readJson(STORAGE.ownedProfiles, null),
  activeOwnedProfile: localStorage.getItem(STORAGE.activeOwnedProfile) || "預設",
  teams: readJson(STORAGE.teams, { "隊伍 1": Array(TEAM_POSITIONS).fill(null) }),
  activeTeam: localStorage.getItem(STORAGE.activeTeam) || "隊伍 1",
  enemy: readJson(STORAGE.enemy, Array(TEAM_POSITIONS).fill(null)),
  selectedBrowser: null,
  selectedTeam: null,
  selectedTeamCandidate: null,
  selectedTeamPosition: null,
  browserFilters: {},
  teamFilters: {},
  imagesVisible: true,
  ownedFilter: false,
  ownedFilterMode: "all",
};

if (!state.ownedProfiles || typeof state.ownedProfiles !== "object") {
  state.ownedProfiles = { 預設: [...state.owned] };
}
if (!state.ownedProfiles[state.activeOwnedProfile]) {
  state.activeOwnedProfile = Object.keys(state.ownedProfiles)[0] || "預設";
}
state.owned = new Set(state.ownedProfiles[state.activeOwnedProfile] || []);

function readJson(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch (error) {
    console.warn(`無法讀取瀏覽器資料：${key}`, error);
    return fallback;
  }
}
function saveJson(key, value) { localStorage.setItem(key, JSON.stringify(value)); }
function saveOwnedProfiles() {
  state.ownedProfiles[state.activeOwnedProfile] = [...state.owned];
  saveJson(STORAGE.ownedProfiles, state.ownedProfiles);
  saveJson(STORAGE.owned, [...state.owned]);
  localStorage.setItem(STORAGE.activeOwnedProfile, state.activeOwnedProfile);
}
function $(selector, root = document) { return root.querySelector(selector); }
function $all(selector, root = document) { return [...root.querySelectorAll(selector)]; }
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[char]));
}
function values(character, key) { return Array.isArray(character[key]) ? character[key] : []; }
function tags(character) { return [...values(character, "special_functions"), ...character.skills.flatMap((skill) => values(skill, "tags"))]; }
function factions(character) { return [...new Set([character.main_faction, character.secondary_faction].filter(Boolean))]; }
function character(id) { return state.characters.find((item) => item.id === id) || null; }
function imagePath(item) {
  if (item?.image_file) return `./data/${item.image_file.replace(/^data[\\/]/, "")}`;
  return item?.image_url || "";
}
function factionPath(name) { return FACTIONS[name] ? `./data/factions/${FACTIONS[name][0]}` : ""; }
function factionDisplay(name) { return FACTIONS[name]?.[2] || name; }
function positionRow(index) { return index < 3 ? "前排" : index < 6 ? "中排" : "後排"; }
function positionClass(index) { return index < 3 ? "row-front" : index < 6 ? "row-middle" : "row-back"; }
function allowedPositions(className) {
  if (className === "守衛") return new Set([0, 1, 2]);
  if (className === "戰士") return new Set([0, 1, 2, 3, 4, 5]);
  if (["牧師", "射手", "法師"].includes(className)) return new Set([3, 4, 5, 6, 7, 8]);
  return new Set([...Array(TEAM_POSITIONS).keys()]);
}
function setStatus(message) { $("#status-bar").textContent = message; }
const STROKE_ORDER = {
  "一": 1, "二": 2, "三": 3, "四": 5, "五": 4, "六": 4, "七": 2, "八": 2, "九": 2, "十": 2,
  "元": 4, "全": 6, "分": 4, "加": 5, "功": 5, "化": 4, "單": 12, "增": 15, "減": 12, "控": 11,
  "效": 10, "攻": 7, "族": 11, "治": 8, "消": 10, "爆": 19, "現": 11, "真": 10, "益": 10, "禁": 13,
  "群": 13, "範": 15, "輸": 16, "出": 5, "技": 7, "能": 10, "防": 7, "禦": 16, "療": 17, "傷": 13,
  "速": 11, "冷": 7, "卻": 7, "召": 5, "喚": 12, "免": 7, "疫": 9, "護": 21, "盾": 9, "無": 12,
  "敵": 15, "復": 12, "活": 9, "閃": 10, "避": 16, "沉": 7, "默": 16, "石": 5, "暈": 13, "眩": 10,
  "麻": 11, "痺": 13, "魅": 14, "惑": 12, "嘲": 15, "諷": 10, "擊": 17, "退": 9, "飛": 9, "牽": 11,
  "引": 4, "聚": 14, "怪": 8, "冰": 6, "凍": 10, "放": 8, "逐": 10, "偷": 11, "取": 8, "反": 4,
  "身": 7,
};
// 與桌面版 stroke_sort_key 相同：逐字比較（筆畫, 字元碼），較短者在前。
function compareStroke(a = "", b = "") {
  const left = [...String(a)];
  const right = [...String(b)];
  for (let index = 0; index < Math.min(left.length, right.length); index += 1) {
    const strokeDifference = (STROKE_ORDER[left[index]] ?? 99) - (STROKE_ORDER[right[index]] ?? 99);
    if (strokeDifference) return strokeDifference;
    const codeDifference = left[index].codePointAt(0) - right[index].codePointAt(0);
    if (codeDifference) return codeDifference;
  }
  return left.length - right.length;
}
function compareProfession(a, b) {
  const order = (value) => { const index = PROFESSION_ORDER.indexOf(value); return index < 0 ? PROFESSION_ORDER.length : index; };
  return order(a) - order(b) || compareStroke(a, b);
}
function compareCharacters(a, b) {
  return compareProfession(a.class_name, b.class_name)
    || compareStroke(a.quality, b.quality)
    || compareStroke(a.main_faction, b.main_faction)
    || compareStroke(a.secondary_faction, b.secondary_faction)
    || compareStroke(a.name, b.name);
}
function allFilterValues() {
  return [...new Set(state.characters.flatMap((item) => tags(item)).filter((value) => value && !ELEMENTS.includes(value)))].sort(compareStroke);
}

// 可輸入文字搜尋（包含比對、不分大小寫）的下拉選單，對應桌面版 SearchableComboBox / 帶圖示的 QComboBox。
function createCombo({ items, firstLabel, searchable = false, placeholder = "", onChange }) {
  const root = document.createElement("div");
  root.className = "combo";
  root.innerHTML = `<input class="combo-input" type="text" ${searchable ? "" : "readonly"} placeholder="${esc(placeholder)}" autocomplete="off"><span class="combo-arrow">▾</span><div class="combo-list" hidden></div>`;
  const input = root.querySelector("input");
  const list = root.querySelector(".combo-list");
  const arrow = root.querySelector(".combo-arrow");
  const isMobile = window.matchMedia("(max-width: 700px)").matches;
  if (searchable && isMobile) input.readOnly = true;
  const all = [{ value: "", label: firstLabel }, ...items];
  let current = "";
  let longPressTimer = null;
  let longPressReady = false;
  let mobileSearchMode = false;
  const labelOf = (value) => (all.find((item) => item.value === value) || all[0]).label;
  const renderList = (query = "") => {
    const keyword = query.trim().toLocaleLowerCase();
    const shown = all.filter((item) => !keyword || item.label.toLocaleLowerCase().includes(keyword));
    list.innerHTML = shown.map((item) => `<div class="combo-option ${item.value === current ? "active" : ""}" data-value="${esc(item.value)}">${item.icon ? `<img src="${item.icon}" alt="">` : ""}<span>${esc(item.label)}</span></div>`).join("") || '<div class="combo-empty">沒有符合的選項</div>';
  };
  const close = () => {
    list.hidden = true;
    if (searchable && isMobile) {
      mobileSearchMode = false;
      input.readOnly = true;
    }
    input.value = labelOf(current);
  };
  const open = (query = "") => { renderList(query); list.hidden = false; };
  const setValue = (value, notify = true) => {
    current = value;
    input.value = labelOf(value);
    list.hidden = true;
    if (notify && onChange) onChange(value);
  };
  input.value = firstLabel;
  input.addEventListener("focus", () => {
    if (searchable && (!isMobile || mobileSearchMode)) input.select();
    if (!isMobile || !searchable || mobileSearchMode) open();
  });
  input.addEventListener("click", () => {
    if (isMobile && searchable && input.readOnly) {
      list.hidden ? open() : close();
      return;
    }
    open(input.value);
  });
  input.addEventListener("input", () => open(input.value));
  if (searchable && isMobile) {
    input.addEventListener("pointerdown", () => {
      clearTimeout(longPressTimer);
      longPressReady = false;
      longPressTimer = setTimeout(() => {
        longPressReady = true;
      }, 550);
    });
    input.addEventListener("pointerup", () => {
      clearTimeout(longPressTimer);
      if (!longPressReady) return;
      longPressReady = false;
      mobileSearchMode = true;
      input.readOnly = false;
      input.focus({ preventScroll: true });
      input.select();
      open(input.value);
    });
    const cancelLongPress = () => {
      clearTimeout(longPressTimer);
      longPressReady = false;
    };
    input.addEventListener("pointercancel", cancelLongPress);
    input.addEventListener("pointerleave", cancelLongPress);
  }
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
    if (event.key === "Enter") {
      event.preventDefault();
      const first = list.querySelector(".combo-option");
      if (first) setValue(first.dataset.value);
    }
  });
  arrow.addEventListener("pointerdown", (event) => event.preventDefault());
  arrow.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (list.hidden) {
      open();
    } else {
      close();
    }
  });
  list.addEventListener("mousedown", (event) => {
    const option = event.target.closest(".combo-option");
    if (!option) return;
    event.preventDefault();
    setValue(option.dataset.value);
    input.blur();
  });
  input.addEventListener("blur", close);
  root.getValue = () => current;
  root.setValue = (value, notify = false) => setValue(value, notify);
  root.setDisabled = (disabled) => { input.disabled = disabled; root.classList.toggle("disabled", disabled); };
  return root;
}

async function loadData() {
  try {
    const cacheBust = Date.now();
    const response = await fetch(`./data/characters.json?v=${cacheBust}`);
    if (!response.ok) throw new Error(`角色資料載入失敗（HTTP ${response.status}）`);
    state.characters = await response.json();
    const versionResponse = await fetch(`./data/data_version.json?v=${cacheBust}`);
    const version = versionResponse.ok ? await versionResponse.json() : {};
    state.version = version;
    const mechanicsResponse = await fetch(`./data/mechanics.json?v=${cacheBust}`);
    if (!mechanicsResponse.ok) throw new Error(`戰鬥機制資料載入失敗（HTTP ${mechanicsResponse.status}）`);
    state.mechanics = await mechanicsResponse.json();
    const noticeResponse = await fetch(`./data/official_maintenance_notices.json?v=${cacheBust}`);
    state.officialNoticeData = noticeResponse.ok ? await noticeResponse.json() : {};
    $("#data-version").textContent = `資料版本：${version.version || version.updated_at || "未知"}`;
    if (!state.teams[state.activeTeam]) state.activeTeam = Object.keys(state.teams)[0] || "隊伍 1";
    renderAll();
    setStatus(`已載入 ${state.characters.length} 名角色`);
  } catch (error) {
    setStatus(error.message || "角色資料載入失敗");
  }
}

function createFilterPanel(target, includeOwned = false) {
  const root = document.createElement("div");
  root.innerHTML = `<h3>篩選條件</h3>
    <div class="filter-row"><label>關鍵字</label><input data-filter="search" type="search" placeholder="搜尋角色名稱或暱稱"></div>
    <div class="filter-row"><label>陣營</label><div data-faction-combo></div></div>
    <div class="filter-row"><label>職業</label><select data-filter="class"><option value="">全部職業</option></select></div>
    <div class="filter-row"><label>品質</label><select data-filter="quality"><option value="">全部品質</option></select></div>
    <div class="filter-row"><label>技能、能力 <span class="mobile-skill-search-hint">（長按搜尋）</span></label><div data-skill-rows></div><button class="add-filter" type="button" data-add-skill>＋新增技能篩選</button></div>
    <div class="filter-row"><label>元素機制</label><select data-filter="element"><option value="">全部元素機制</option></select></div>
    ${includeOwned ? '<div class="check-row"><input data-filter="owned" type="checkbox"><label>只顯示已擁有角色</label></div>' : ""}`;
  const filters = target === "browser" ? state.browserFilters : state.teamFilters;
  root.querySelector("[data-filter='class']").innerHTML += [...new Set(state.characters.map((item) => item.class_name))].filter(Boolean).sort(compareProfession).map((item) => `<option>${esc(item)}</option>`).join("");
  root.querySelector("[data-filter='quality']").innerHTML += [...new Set(state.characters.map((item) => item.quality).filter(Boolean))].sort(compareStroke).map((item) => `<option>${esc(item)}</option>`).join("");
  root.querySelector("[data-filter='element']").innerHTML += [...ELEMENTS].sort(compareStroke).map((item) => `<option>${item}</option>`).join("");
  const elementSelect = root.querySelector("[data-filter='element']");
  const updateElementFilter = () => {
    const enabled = !filters.faction || filters.faction === "元素";
    elementSelect.disabled = !enabled;
    if (!enabled) {
      elementSelect.value = "";
      filters.element = "";
    }
  };
  const factionCombo = createCombo({
    firstLabel: "全部陣營",
    items: [...new Set(state.characters.flatMap(factions))].sort().map((name) => ({ value: name, label: factionDisplay(name), icon: factionPath(name) })),
    onChange: (value) => { filters.faction = value; updateElementFilter(); refresh(target); },
  });
  root.querySelector("[data-faction-combo]").append(factionCombo);
  const skillValues = () => $all("[data-skill-rows] .combo", root).map((combo) => combo.getValue()).filter(Boolean);
  const addSkillRow = () => {
    const row = document.createElement("div");
    row.className = "skill-filter-row";
    const combo = createCombo({
      firstLabel: "全部技能效果",
      searchable: true,
      placeholder: "輸入文字搜尋技能或能力",
      items: allFilterValues().map((value) => ({ value, label: value })),
      onChange: () => { filters.skills = skillValues(); refresh(target); },
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      if ($all("[data-skill-rows] .skill-filter-row", root).length <= 1) combo.setValue("", false);
      else row.remove();
      filters.skills = skillValues();
      refresh(target);
    });
    row.append(combo, remove);
    root.querySelector("[data-skill-rows]").append(row);
  };
  addSkillRow();
  root.querySelector("[data-add-skill]").addEventListener("click", () => addSkillRow());
  $all("[data-filter]", root).forEach((input) => {
    const key = input.dataset.filter;
    input.addEventListener(input.type === "checkbox" ? "change" : "input", () => {
      filters[key] = input.type === "checkbox" ? input.checked : input.value;
      if (key === "owned") filters.ownedMode = input.checked ? "owned" : "all";
      refresh(target);
    });
  });
  updateElementFilter();
  return root;
}

function filterMatches(item, filters) {
  const searchable = [item.name, ...values(item, "aliases"), item.guide_notes].join(" ").toLocaleLowerCase();
  const selectedSkills = filters.skills || [];
  const ownedMode = filters.ownedMode || (filters.owned ? "owned" : "all");
  const ownedMatches = ownedMode === "owned"
    ? state.owned.has(item.id)
    : ownedMode === "unowned"
      ? !state.owned.has(item.id)
      : true;
  return (!filters.search || searchable.includes(filters.search.toLocaleLowerCase()))
    && (!filters.faction || factions(item).includes(filters.faction))
    && (!filters.class || item.class_name === filters.class)
    && (!filters.quality || item.quality === filters.quality)
    && (!filters.element || item.skills.some((skill) => skill.description.includes(filters.element) || values(skill, "tags").includes(filters.element)))
    && selectedSkills.every((skill) => tags(item).includes(skill))
    && ownedMatches;
}

function listItem(item, selected, checkable = true) {
  const prof = PROFESSION[item.class_name] || ["?", "#777"];
  return `<div class="character-row ${selected ? "selected" : ""}" data-character="${esc(item.id)}">
    ${state.imagesVisible && imagePath(item) ? `<img src="${imagePath(item)}" alt="">` : `<span class="profession-icon" style="background:${prof[1]}">${prof[0]}</span>`}
    <span class="row-main"><span class="row-name">${esc(item.name)}${missingSkills(item).length ? " <span title=\"技能資料待補\">[技能待補]</span>" : ""}</span><span class="row-meta">${esc(item.class_name)}　${esc(item.quality || "未確認")}</span></span>
    ${checkable ? `<input class="row-check" type="checkbox" data-owned="${esc(item.id)}" ${state.owned.has(item.id) ? "checked" : ""} title="已擁有">` : ""}
  </div>`;
}
function missingSkills(item) { return SKILL_TYPES.filter((type) => !item.skills.some((skill) => skill.skill_type === type)); }
function renderList(target) {
  const list = target === "browser" ? $("#browser-list") : $("#team-list");
  const filters = target === "browser" ? state.browserFilters : state.teamFilters;
  const items = state.characters.filter((item) => filterMatches(item, filters))  .sort(compareCharacters);
  if (target === "browser") $("#browser-count").textContent = `${items.length}/${state.characters.length} 名角色`;
  list.innerHTML = items.map((item) => listItem(item, item.id === (target === "browser" ? state.selectedBrowser : state.selectedTeamCandidate), true)).join("") || '<p class="hint">目前沒有符合條件的角色。</p>';
  $all("[data-character]", list).forEach((row) => {
    let longPressTimer = null;
    const startLongPress = (event) => {
      if (event.target.matches("[data-owned]")) return;
      if (!window.matchMedia("(max-width: 700px)").matches) return;
      longPressTimer = window.setTimeout(() => {
        longPressTimer = null;
        row.classList.add("long-pressed");
        const item = character(row.dataset.character);
        if (item) showCharacterModal(item);
      }, 550);
    };
    const cancelLongPress = () => {
      if (longPressTimer !== null) window.clearTimeout(longPressTimer);
      longPressTimer = null;
    };
    row.addEventListener("pointerdown", startLongPress);
    row.addEventListener("pointerup", cancelLongPress);
    row.addEventListener("pointercancel", cancelLongPress);
    row.addEventListener("pointerleave", cancelLongPress);
    row.addEventListener("contextmenu", (event) => {
      if (window.matchMedia("(max-width: 700px)").matches) event.preventDefault();
    });
    row.addEventListener("click", (event) => {
      if (event.target.matches("[data-owned]")) return;
      if (target === "browser") { state.selectedBrowser = row.dataset.character; renderList("browser"); renderDetails("browser"); }
      else { state.selectedTeamCandidate = row.dataset.character; state.selectedTeam = row.dataset.character; renderList("team"); renderDetails("team"); }
    });
    row.addEventListener("dblclick", () => { if (target === "team") addSelectedToTeam(); });
  });
  $all("[data-owned]", list).forEach((checkbox) => checkbox.addEventListener("change", () => {
    if (checkbox.checked) state.owned.add(checkbox.dataset.owned); else state.owned.delete(checkbox.dataset.owned);
    saveOwnedProfiles(); refresh("browser"); refresh("team"); renderDetails("browser"); renderDetails("team");
  }));
}

function renderDetails(target) {
  const id = target === "browser" ? state.selectedBrowser : state.selectedTeam;
  const root = target === "browser" ? $("#browser-details") : $("#team-details");
  const item = character(id);
  if (!item) { root.innerHTML = "<p class='hint'>請選擇角色查看詳細資料。</p>"; return; }
  root.innerHTML = characterDetailsMarkup(item);
}
function formatSkillDescription(item, skill) {
  const references = [];
  item.skills.forEach((value) => {
    if (value.name && !references.some((reference) => reference.name === value.name)) {
      references.push({ name: value.name, type: "skill", color: SKILL_COLORS[value.skill_type] || "#555" });
    }
  });
  Object.keys(state.mechanics).forEach((name) => {
    if (!references.some((reference) => reference.name === name)) references.push({ name, type: "mechanic" });
  });
  if (!references.length) return esc(skill.description);
  const pattern = new RegExp(references.sort((a, b) => b.name.length - a.name.length).map((reference) => reference.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "g");
  let result = "";
  let cursor = 0;
  for (const match of skill.description.matchAll(pattern)) {
    result += esc(skill.description.slice(cursor, match.index));
    const reference = references.find((value) => value.name === match[0]);
    if (reference.type === "skill") {
      result += `<span class="skill-reference" style="color:${reference.color}">${esc(match[0])}</span>`;
    } else {
      result += `<button type="button" class="mechanic-link" data-mechanic="${esc(match[0])}">${esc(match[0])}</button>`;
    }
    cursor = match.index + match[0].length;
  }
  return result + esc(skill.description.slice(cursor));
}
function characterDetailsMarkup(item) {
  const prof = PROFESSION[item.class_name] || ["?", "#777"];
  const badges = factions(item).map((name) => `<span class="faction-badge" style="background:${FACTIONS[name]?.[1] || "#ddd"}">${factionPath(name) ? `<img src="${factionPath(name)}" alt="">` : ""}${esc(factionDisplay(name))}</span>`).join("");
  return `<div class="details-header">${state.imagesVisible && imagePath(item) ? `<img src="${imagePath(item)}" alt="${esc(item.name)}">` : ""}
    <div><h2>${esc(item.name)}</h2><div class="profession-line"><span class="profession-icon" style="background:${prof[1]}">${prof[0]}</span>職業：${esc(item.class_name)}</div>
    <div class="faction-badges">${badges}</div><p class="muted">品質：${esc(item.quality || "未確認")}　TIER：${esc(item.tier || "未評級")}</p></div></div>
    <div class="detail-section"><h3>特殊功能</h3><p>${values(item, "special_functions").map((value) => esc(value)).join("、") || "尚未整理"}</p></div>
    ${item.guide_notes ? `<div class="detail-section"><h3>攻略備註</h3><p>${esc(item.guide_notes)}</p></div>` : ""}
    <div class="detail-section"><h3>技能</h3>${item.skills.filter((skill) => !["神格", "God Skill"].includes(skill.skill_type)).map((skill) => `<h4 class="skill-title">${esc(skill.name)} <span class="skill-tag" style="color:${SKILL_COLORS[skill.skill_type] || "#555"}">${esc(skill.skill_type || "技能")}：</span>${values(skill, "tags").map((tag) => `<span class="skill-tag">${esc(tag)}</span>`).join("、")}</h4><p class="skill-text">${formatSkillDescription(item, skill)}</p>`).join("")}</div>`;
}
function showCharacterModal(item) {
  showModal(item.name, characterDetailsMarkup(item));
}

function refresh(target) { renderList(target); if (target === "browser") renderDetails("browser"); if (target === "team") renderDetails("team"); }
function renderTeamSelectors() {
  $("#team-selector").innerHTML = Object.keys(state.teams).map((name) => `<option>${esc(name)}</option>`).join("");
  $("#team-selector").value = state.activeTeam;
  $("#team-selector").onchange = () => { state.activeTeam = $("#team-selector").value; localStorage.setItem(STORAGE.activeTeam, state.activeTeam); state.selectedTeamPosition = null; renderTeam(); };
}
function activePositions() { return state.teams[state.activeTeam] || (state.teams[state.activeTeam] = Array(TEAM_POSITIONS).fill(null)); }
function renderTeam() {
  renderTeamSelectors();
  const positions = activePositions();
  $("#team-grid").innerHTML = positions.map((id, index) => {
    const item = character(id);
    return `<button class="team-slot ${positionClass(index)} ${state.selectedTeamPosition === index ? "selected" : ""}" data-position="${index}">${item ? (state.imagesVisible && imagePath(item) ? `<img src="${imagePath(item)}" alt="">` : "") + `<span class="slot-name">${esc(positionRow(index))}<br>${esc(item.name)}</span><span class="slot-class">${esc(item.class_name)}</span>` : `<span class="slot-name">${positionRow(index)}<br>空位</span>`}</button>`;
  }).join("");
  $all("[data-position]", $("#team-grid")).forEach((button) => button.addEventListener("click", () => {
    state.selectedTeamPosition = Number(button.dataset.position);
    const item = character(activePositions()[state.selectedTeamPosition]);
    state.selectedTeam = item?.id || null;
    $("#team-position-label").textContent = item ? `已選擇：${item.name}` : `已選擇：${positionRow(state.selectedTeamPosition)}空位`;
    renderTeam();
    renderDetails("team");
  }));
  const members = positions.map(character).filter(Boolean);
  $("#team-analysis").innerHTML = members.length ? `<p>目前隊伍：${members.map((item) => `${esc(item.name)}（${esc(item.class_name)}）`).join("、")}</p><p>人數：${members.length} / ${MAX_TEAM_SIZE}</p>` : "<p>尚未組成隊伍。</p>";
  if (members.length) setStatus(`目前隊伍「${state.activeTeam}」：${members.length} / 6 人`);
}
function saveTeam() { saveJson(STORAGE.teams, state.teams); localStorage.setItem(STORAGE.activeTeam, state.activeTeam); }
function addSelectedToTeam() {
  const item = character(state.selectedTeamCandidate);
  if (!item) { setStatus("請先從候選角色清單選擇角色。"); return; }
  const positions = activePositions();
  const selectedPosition = state.selectedTeamPosition;
  if (selectedPosition !== null) {
    if (!allowedPositions(item.class_name).has(selectedPosition)) {
      setStatus(`${item.class_name}不能站在這個位置。`);
      return;
    }
    if (positions[selectedPosition] === item.id) {
      setStatus("該角色已在選取的位置。");
      return;
    }
    const existingPosition = positions.indexOf(item.id);
    if (existingPosition >= 0) {
      positions[existingPosition] = null;
    }
    positions[selectedPosition] = item.id;
    state.selectedTeam = item.id;
    saveTeam();
    renderTeam();
    renderList("team");
    renderDetails("team");
    return;
  }
  if (positions.includes(item.id)) { setStatus("同一角色不可重複放入隊伍。"); return; }
  if (positions.filter(Boolean).length >= MAX_TEAM_SIZE) { setStatus("隊伍最多只能放入 6 名角色。"); return; }
  const position = positions.findIndex((id, index) => !id && allowedPositions(item.class_name).has(index));
  if (position < 0) { setStatus(`沒有符合${item.class_name}站位規則的空位。`); return; }
  positions[position] = item.id; state.selectedTeamPosition = position; saveTeam(); renderTeam(); renderList("team");
}
function removeSelectedFromTeam() {
  const positions = activePositions();
  if (state.selectedTeamPosition === null) { setStatus("請先選擇九宮格位置。"); return; }
  positions[state.selectedTeamPosition] = null; saveTeam(); renderTeam(); renderList("team");
}

function renderEnemyBoard() {
  const own = activePositions();
  const ownVisual = own.map((id, position) => ({
    id,
    position,
    visual: (position % 3) * 3 + (2 - Math.floor(position / 3)),
  })).sort((a, b) => a.visual - b.visual);
  const enemyVisual = state.enemy.map((id, position) => ({
    id,
    position,
    visual: (2 - (position % 3)) * 3 + Math.floor(position / 3),
  })).sort((a, b) => a.visual - b.visual);
  $("#own-board").innerHTML = ownVisual.map(({ id, position }) => boardSlot(character(id), position, true)).join("");
  $("#enemy-board").innerHTML = enemyVisual.map(({ id, position }) => boardSlot(character(id), position, false)).join("");
  renderEnemyAnalysis();
}
function boardSlot(item, index, own) {
  const mobileRow = own ? Math.floor(index / 3) + 1 : 3 - Math.floor(index / 3);
  const mobileColumn = index % 3 + 1;
  return `<button class="board-slot ${positionClass(index)}" style="--mobile-row:${mobileRow};--mobile-column:${mobileColumn}" data-slot-number="${index + 1}" ${own ? `data-own-position="${index}"` : `data-enemy-position="${index}"`}>${item ? (state.imagesVisible && imagePath(item) ? `<img src="${imagePath(item)}" alt="">` : "") + `<span class="slot-name">${esc(positionRow(index))}<br>${esc(item.name)}</span><span class="slot-class">${esc(item.class_name)}</span>` : `<span class="slot-name">${positionRow(index)}<br>空位</span>`}</button>`;
}
function renderEnemyAnalysis() {
  const members = state.enemy.map(character).filter(Boolean);
  const abilities = [...new Set(members.flatMap((item) => values(item, "special_functions")))];
  const controls = abilities.filter((value) => value.startsWith("控制-"));
  const benefits = abilities.filter((value) => value.startsWith("增益"));
  const debuffs = abilities.filter((value) => value.startsWith("減益"));
  const healing = abilities.filter((value) => value.includes("療傷") || value.includes("治療"));
  const requirements = [];
  if (controls.length) requirements.push("解控", "控制免疫");
  if (benefits.length) requirements.push("驅散增益", "偷取增益");
  if (debuffs.length) requirements.push("淨化", "驅散");
  if (healing.length) requirements.push("治療增強", "淨化");
  $("#enemy-analysis").innerHTML = `<h3>敵方已知威脅</h3><p><b>控制：</b>${esc(controls.join("、") || "無")}<br><b>增益：</b>${esc(benefits.join("、") || "無")}<br><b>減益：</b>${esc(debuffs.join("、") || "無")}<br><b>治療相關：</b>${esc(healing.join("、") || "無")}</p><p><b>建議反制需求：</b>${esc([...new Set(requirements)].join("、") || "暫無")}</p>`;
}

function renderSources(version = {}, officialNoticeData = {}) {
  const known = [["筱宮璃紗、MDM、佳里等製作團隊", "https://reurl.cc/0Kq5dk"], ["GameKee", "https://www.gamekee.com/lhlr/"], ["TapTap", "https://www.taptap.cn/"], ["Dragon Companion", "https://www.dragoncompanion.com/"], ["台服官方公告", "https://sod.game-beans.com/jx/sodNotice/index.html"]];
  $("#sources-content").innerHTML = `<h3>資料版本</h3><p><b>版本：</b>${esc(version.version || "未知")}<br><b>更新日期：</b>${esc(version.updated_at || "未知")}<br><b>角色數：</b>${state.characters.length}<br><b>官網上次檢查：</b>${esc(officialNoticeData.last_checked_at || officialNoticeData.accessed_at || "未知")}</p>${known.map(([name, url]) => `<p><b>${esc(name)}</b><br><a href="${url}" target="_blank" rel="noreferrer">${esc(url)}</a></p>`).join("")}`;
}

function showModal(title, content, onReady) {
  $("#modal-root").innerHTML = `<div class="modal-backdrop"><div class="modal"><div class="modal-header"><h2>${esc(title)}</h2><button class="modal-close" data-close>×</button></div><div class="modal-body">${content}</div></div></div>`;
  $all("[data-close]").forEach((button) => button.addEventListener("click", closeModal));
  $(".modal-backdrop").addEventListener("click", (event) => { if (event.target.classList.contains("modal-backdrop")) closeModal(); });
  if (onReady) onReady($(".modal"));
}
function closeModal() { $("#modal-root").innerHTML = ""; }
function ownedManager() {
  let selectedIds = new Set(state.owned);
  const profileOptions = Object.keys(state.ownedProfiles).sort(compareStroke).map((name) => `<option>${esc(name)}</option>`).join("");
  showModal("擁有角色管理", `<p>勾選已擁有角色，按「確定」後套用至角色瀏覽器與隊伍組成器。</p>
    <div class="team-actions"><label>設定檔 <select data-manager-profile>${profileOptions}</select></label><button data-manager-new>新增</button><button data-manager-delete>刪除</button></div>
    <div class="manager-filters"><input data-manager-search type="search" placeholder="搜尋角色名稱或暱稱"><select data-manager-class><option value="">全部職業</option></select><select data-manager-quality><option value="">全部品質</option></select><select data-manager-faction><option value="">全部陣營</option></select></div>
    <div class="modal-actions"><button data-manager-all>全選</button><button data-manager-none>全部取消</button></div>
    <div class="recommend-list" data-manager-list></div>
    <div class="modal-actions"><button data-close>取消</button><button class="primary" data-manager-apply>確定</button></div>`, (modal) => {
    const profile = modal.querySelector("[data-manager-profile]");
    profile.value = state.activeOwnedProfile;
    const classSelect = modal.querySelector("[data-manager-class]");
    const qualitySelect = modal.querySelector("[data-manager-quality]");
    const factionSelect = modal.querySelector("[data-manager-faction]");
    const addOptions = (select, valuesToAdd, compare = compareStroke) => { select.innerHTML += [...new Set(valuesToAdd)].filter(Boolean).sort(compare).map((value) => `<option>${esc(value)}</option>`).join(""); };
    addOptions(classSelect, state.characters.map((item) => item.class_name), compareProfession);
    addOptions(qualitySelect, state.characters.map((item) => item.quality));
    addOptions(factionSelect, state.characters.flatMap(factions));
    const renderManagerList = () => {
      const search = modal.querySelector("[data-manager-search]").value.toLocaleLowerCase();
      const className = classSelect.value;
      const quality = qualitySelect.value;
      const faction = factionSelect.value;
      const filtered = state.characters.filter((item) => {
        const searchable = [item.id, item.name, ...values(item, "aliases")].join(" ").toLocaleLowerCase();
        return (!search || searchable.includes(search)) && (!className || item.class_name === className)
          && (!quality || item.quality === quality) && (!faction || factions(item).includes(faction));
      }).sort(compareCharacters);
      modal.querySelector("[data-manager-list]").innerHTML = filtered.map((item) => `<label><input type="checkbox" data-manager-owned="${esc(item.id)}" ${selectedIds.has(item.id) ? "checked" : ""}> ${esc(item.name)}　| 職業：${esc(item.class_name)}　品質：${esc(item.quality || "未標註")}　陣營：${esc(factions(item).join("／") || "未分類")}</label>`).join("") || "<p class='hint'>沒有符合條件的角色。</p>";
      $all("[data-manager-owned]", modal).forEach((input) => input.addEventListener("change", () => { if (input.checked) selectedIds.add(input.dataset.managerOwned); else selectedIds.delete(input.dataset.managerOwned); }));
    };
    const syncProfile = () => { state.ownedProfiles[state.activeOwnedProfile] = [...selectedIds]; };
    profile.addEventListener("change", () => { syncProfile(); state.activeOwnedProfile = profile.value; selectedIds = new Set(state.ownedProfiles[state.activeOwnedProfile] || []); renderManagerList(); });
    modal.querySelector("[data-manager-search]").addEventListener("input", renderManagerList);
    [classSelect, qualitySelect, factionSelect].forEach((select) => select.addEventListener("change", renderManagerList));
    modal.querySelector("[data-manager-all]").addEventListener("click", () => { $all("[data-manager-owned]", modal).forEach((input) => { input.checked = true; selectedIds.add(input.dataset.managerOwned); }); });
    modal.querySelector("[data-manager-none]").addEventListener("click", () => { $all("[data-manager-owned]", modal).forEach((input) => { input.checked = false; selectedIds.delete(input.dataset.managerOwned); }); });
    modal.querySelector("[data-manager-new]").addEventListener("click", () => { const name = prompt("請輸入設定檔名稱："); if (!name || state.ownedProfiles[name]) return; syncProfile(); state.ownedProfiles[name] = []; state.activeOwnedProfile = name; selectedIds = new Set(); profile.innerHTML = Object.keys(state.ownedProfiles).sort(compareStroke).map((item) => `<option>${esc(item)}</option>`).join(""); profile.value = name; renderManagerList(); });
    modal.querySelector("[data-manager-delete]").addEventListener("click", () => { const names = Object.keys(state.ownedProfiles); if (names.length <= 1) { setStatus("至少要保留一個擁有角色設定檔。"); return; } delete state.ownedProfiles[state.activeOwnedProfile]; state.activeOwnedProfile = Object.keys(state.ownedProfiles)[0]; selectedIds = new Set(state.ownedProfiles[state.activeOwnedProfile]); profile.innerHTML = Object.keys(state.ownedProfiles).sort(compareStroke).map((item) => `<option>${esc(item)}</option>`).join(""); profile.value = state.activeOwnedProfile; renderManagerList(); });
    modal.querySelector("[data-manager-apply]").addEventListener("click", () => { state.owned = selectedIds; syncProfile(); saveOwnedProfiles(); closeModal(); refresh("browser"); refresh("team"); renderDetails("browser"); renderDetails("team"); });
    renderManagerList();
  });
}
function editEnemy() {
  const options = `<option value="">空位</option>${[...state.characters].sort((a, b) => compareProfession(a.class_name, b.class_name) || compareStroke(a.name, b.name)).map((item) => `<option value="${esc(item.id)}">${esc(item.name)}（${esc(item.class_name)}）</option>`).join("")}`;
  showModal("敵隊輸入", `<p>敵隊角色清單不受已擁有角色影響。</p><div class="enemy-editor-grid">${state.enemy.map((id, index) => `<label>${positionRow(index)} ${index + 1}<select data-enemy-edit="${index}">${options}</select></label>`).join("")}</div><div class="modal-actions"><button data-close>取消</button><button class="primary" data-enemy-apply>確定</button></div>`, (modal) => {
    $all("[data-enemy-edit]", modal).forEach((select) => { select.value = state.enemy[Number(select.dataset.enemyEdit)] || ""; });
    modal.querySelector("[data-enemy-apply]").addEventListener("click", () => {
      const selected = $all("[data-enemy-edit]", modal).map((select) => select.value).filter(Boolean);
      if (new Set(selected).size !== selected.length) { setStatus("同一角色不可重複放入敵隊。"); return; }
      if (selected.length > MAX_TEAM_SIZE) { setStatus("敵隊最多只能放入 6 名角色。"); return; }
      state.enemy = $all("[data-enemy-edit]", modal).map((select) => select.value || null); saveJson(STORAGE.enemy, state.enemy); closeModal(); renderEnemyBoard();
    });
  });
}
function recommend() {
  const enemyMembers = state.enemy.map(character).filter(Boolean);
  if (!enemyMembers.length) { setStatus("請先輸入敵隊角色。"); return; }
  const requirements = [...new Set(enemyMembers.flatMap((item) => values(item, "special_functions")).flatMap((value) => value.startsWith("控制-") ? ["解控", "控制免疫"] : value.startsWith("增益") ? ["驅散增益", "偷取增益"] : value.startsWith("減益") ? ["淨化", "驅散"] : value.includes("療傷") || value.includes("治療") ? ["治療增強", "淨化"] : []))];
  const available = state.characters.filter((item) => !state.ownedFilter || state.owned.has(item.id));
  const selected = [];
  const covered = new Set();
  for (let count = 0; count < MAX_TEAM_SIZE; count += 1) {
    const candidate = available.filter((item) => !selected.includes(item)).sort((a, b) => score(b, requirements, covered) - score(a, requirements, covered))[0];
    if (!candidate) break;
    selected.push(candidate);
    requirements.forEach((requirement) => { if (covers(candidate, requirement)) covered.add(requirement); });
  }
  const candidates = available.filter((item) => !selected.includes(item) && requirements.some((requirement) => covers(item, requirement)));
  showModal("推薦隊伍", `<label class="check-row"><input type="checkbox" data-recommend-owned ${state.ownedFilter ? "checked" : ""}> 推薦僅使用已擁有角色</label><p><b>推薦角色：</b>${selected.map((item) => `${esc(item.name)}（${esc(item.class_name)}）${state.owned.has(item.id) ? "" : "【不建議使用】"}`).join("、") || "無"}</p><p><b>已涵蓋反制需求：</b>${esc(requirements.filter((item) => covered.has(item)).join("、") || "尚未找到對應能力")}<br><b>尚未涵蓋：</b>${esc(requirements.filter((item) => !covered.has(item)).join("、") || "無")}<br><b>輸出：</b>已優先確保隊伍包含輸出角色</p><p>具備反制能力的候選角色（可勾選加入隊伍）：</p><div class="recommend-list">${candidates.map((item) => `<label><input type="checkbox" data-counter="${esc(item.id)}"> ${esc(item.name)}（${esc(item.class_name)}）｜陣營：${esc(factions(item).join("、") || "未分類")}</label>`).join("") || "無"}</div><div class="modal-actions"><button data-close>關閉</button><button class="primary" data-recommend-apply>套用到目前隊伍</button></div>`, (modal) => {
    modal.querySelector("[data-recommend-owned]").addEventListener("change", (event) => { state.ownedFilter = event.target.checked; closeModal(); recommend(); });
    modal.querySelector("[data-recommend-apply]").addEventListener("click", () => {
      const extra = $all("[data-counter]:checked", modal).map((input) => character(input.dataset.counter)).filter(Boolean);
      const combined = [...extra, ...selected].slice(0, MAX_TEAM_SIZE);
      const positions = Array(TEAM_POSITIONS).fill(null);
      for (const item of combined) { const position = positions.findIndex((id, index) => !id && allowedPositions(item.class_name).has(index)); if (position >= 0) positions[position] = item.id; }
      if (combined.length !== positions.filter(Boolean).length) { setStatus("勾選的反制候選角色與推薦組合無法同時組成合法隊伍。"); return; }
      state.teams[state.activeTeam] = positions; saveTeam(); closeModal(); renderTeam(); renderEnemyBoard();
    });
  });
}
function covers(item, requirement) {
  const abilities = tags(item);
  if (requirement === "解控" || requirement === "控制免疫") return abilities.some((value) => value.includes("解控") || value.includes("免疫控制") || value.includes("免控"));
  if (requirement === "驅散增益" || requirement === "驅散") return abilities.some((value) => value.includes("驅散") || value.includes("清除增益"));
  if (requirement === "偷取增益") return abilities.some((value) => value.includes("偷取"));
  if (requirement === "淨化") return abilities.some((value) => value.includes("淨化") || value.includes("驅散"));
  if (requirement === "治療增強") return abilities.some((value) => value.includes("治療") || value.includes("回復"));
  return false;
}
function score(item, requirements, covered) { return requirements.filter((requirement) => !covered.has(requirement) && covers(item, requirement)).length * 10 + (["射手", "法師"].includes(item.class_name) ? 3 : 0) + (item.class_name === "守衛" ? 2 : 0) + tags(item).length; }

function download(name, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = name; link.click(); URL.revokeObjectURL(link.href);
}
function loadFile(input, callback) {
  if (window.matchMedia("(max-width: 700px)").matches) {
    showModal(
      "選擇 JSON 檔案",
      `<p class="hint">請選擇要載入的 JSON 檔案。</p><input class="mobile-file-picker" type="file" accept=".json,application/json">`,
      (modal) => {
        const picker = modal.querySelector(".mobile-file-picker");
        picker.addEventListener("change", async () => {
          const file = picker.files?.[0];
          if (!file) return;
          try {
            callback(JSON.parse(await file.text()));
            closeModal();
          } catch (error) {
            setStatus(`檔案讀取失敗：${error.message}`);
          }
        });
      },
    );
    return;
  }
  input.onchange = async () => {
    const file = input.files?.[0];
    if (!file) return;
    try {
      callback(JSON.parse(await file.text()));
    } catch (error) {
      setStatus(`檔案讀取失敗：${error.message}`);
    } finally {
      input.value = "";
    }
  };
  input.click();
}
function toolbarAction(action) {
  if (action === "mobile-menu") {
    const menu = document.querySelector(".toolbar-menu");
    const toggle = document.querySelector(".mobile-menu-toggle");
    const expanded = menu.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(expanded));
    return;
  }
  if (action === "owned-manager") ownedManager();
  if (action === "owned-filter") {
    const button = $("#owned-toggle");
    const modes = ["all", "owned", "unowned"];
    const mode = modes[(modes.indexOf(state.ownedFilterMode) + 1) % modes.length];
    const labels = { all: "顯示全部角色", owned: "只顯示已擁有角色", unowned: "只顯示未擁有角色" };
    state.ownedFilterMode = mode;
    state.ownedFilter = mode === "owned";
    button.textContent = labels[mode];
    button.classList.toggle("is-on", mode !== "all");
    state.browserFilters.owned = state.ownedFilter;
    state.teamFilters.owned = state.ownedFilter;
    state.browserFilters.ownedMode = mode;
    state.teamFilters.ownedMode = mode;
    $all("[data-filter='owned']").forEach((input) => { input.checked = mode === "owned"; });
    refresh("browser");
    refresh("team");
  }
  if (action === "images") { state.imagesVisible = !state.imagesVisible; $("#images-toggle").classList.toggle("is-on", state.imagesVisible); renderAll(); }
  if (action === "save-owned") download("owned_characters.json", { version: 1, owned_character_ids: [...state.owned] });
  if (action === "load-owned") loadFile($("#owned-file-input"), (data) => {
    const ids = data.owned_character_ids || data.character_ids;
    if (!Array.isArray(ids) || !ids.every((id) => typeof id === "string")) {
      setStatus("載入失敗：檔案缺少有效的 owned_character_ids 陣列。");
      return;
    }
    const validIds = new Set(state.characters.map((item) => item.id));
    const invalidCount = ids.filter((id) => !validIds.has(id)).length;
    state.owned = new Set(ids.filter((id) => validIds.has(id)));
    saveOwnedProfiles();
    renderAll();
    setStatus(invalidCount ? `已載入 ${state.owned.size} 名角色，忽略 ${invalidCount} 個未知角色。` : `已載入 ${state.owned.size} 名已擁有角色。`);
  });
  if (action === "clear-owned") { state.owned.clear(); saveOwnedProfiles(); renderAll(); }
  if (action === "export-team") download("teams.json", { version: 2, teams: state.teams, active_team: state.activeTeam });
  if (action === "import-team") loadFile($("#team-file-input"), (data) => { if (data.teams) { state.teams = data.teams; state.activeTeam = data.active_team || Object.keys(state.teams)[0]; saveTeam(); renderAll(); } });
  if (action === "official-check") setStatus("GitHub Actions 每日自動檢查台服官方公告首頁與第二頁；有新資料時會自動部署，請稍後重新整理頁面。");
  if (action === "official-report") showOfficialReport();
  if (action === "report") window.open(GOOGLE_FORM_URL, "_blank", "noopener,noreferrer");
}
async function showOfficialReport() {
  try {
    const response = await fetch("./data/official_maintenance_notices.json");
    const payload = await response.json();
    const notices = Array.isArray(payload) ? payload : payload.notices || [];
    showModal("台服官方更新公告", `<p>網頁版顯示已同步的台服維護公告清單。</p><div class="recommend-list">${notices.map((notice) => `<p><b>${esc(notice.date || "未知日期")}</b> <a href="${esc(notice.url || "#")}" target="_blank" rel="noreferrer">${esc(notice.title || "未命名公告")}</a><br>新增角色：${esc((notice.new_characters || []).join("、") || "無")}<br>更新角色數值：${notice.updates_character_values ? "是" : "否"}</p>`).join("")}</div>`);
  } catch (error) {
    setStatus(`公告讀取失敗：${error.message}`);
  }
}
function renderAll() {
  $("#browser-filters").replaceChildren(createFilterPanel("browser"));
  $("#team-filters").replaceChildren(createFilterPanel("team"));
  refresh("browser"); refresh("team"); renderTeam(); renderEnemyBoard(); renderSources(state.version, state.officialNoticeData);
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-mechanic]");
  if (!button) return;
  const name = button.dataset.mechanic;
  const description = state.mechanics[name];
  if (description) showModal(`${name}說明`, `<p>${esc(description)}</p>`);
});
$all(".tab").forEach((tab) => tab.addEventListener("click", () => { $all(".tab, .tab-panel").forEach((element) => element.classList.remove("is-active")); tab.classList.add("is-active"); $(`#${tab.dataset.tab}-tab`).classList.add("is-active"); }));
$all("[data-action]").forEach((button) => button.addEventListener("click", () => {
  const action = button.dataset.action;
  if (action === "add-selected") addSelectedToTeam();
  else if (action === "remove-selected") removeSelectedFromTeam();
  else if (action === "clear-team") { state.teams[state.activeTeam] = Array(TEAM_POSITIONS).fill(null); saveTeam(); renderTeam(); renderEnemyBoard(); }
  else if (action === "new-team") { const name = prompt("請輸入隊伍名稱："); if (name && !state.teams[name]) { state.teams[name] = Array(TEAM_POSITIONS).fill(null); state.activeTeam = name; saveTeam(); renderTeam(); } }
  else if (action === "rename-team") { const name = prompt("請輸入新的隊伍名稱：", state.activeTeam); if (name && (name === state.activeTeam || !state.teams[name])) { state.teams[name] = state.teams[state.activeTeam]; delete state.teams[state.activeTeam]; state.activeTeam = name; saveTeam(); renderTeam(); } }
  else if (action === "delete-team") { if (Object.keys(state.teams).length <= 1) setStatus("至少要保留一個隊伍。"); else { delete state.teams[state.activeTeam]; state.activeTeam = Object.keys(state.teams)[0]; saveTeam(); renderTeam(); } }
  else if (action === "edit-enemy") editEnemy();
  else if (action === "recommend") recommend();
  else if (action === "refresh-enemy") renderEnemyBoard();
  else toolbarAction(action);
}));
$("#own-board").addEventListener("click", (event) => { const button = event.target.closest("[data-own-position]"); if (button) { state.selectedTeamPosition = Number(button.dataset.ownPosition); document.querySelector("[data-tab='team']").click(); renderTeam(); } });
$("#enemy-board").addEventListener("click", (event) => { if (event.target.closest("[data-enemy-position]")) editEnemy(); });
loadData();
