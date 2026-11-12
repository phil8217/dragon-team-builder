"""PySide6 桌面介面。"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import (
    Qt,
    Signal,
    QUrl,
    QSize,
    QSignalBlocker,
    QSettings,
    QThread,
    QTimer,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QKeySequence,
    QIcon,
    QPainter,
    QPixmap,
    QShortcut,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QMessageBox,
    QCheckBox,
    QInputDialog,
    QToolBar,
)

from .data_loader import load_characters
from .abilities import stroke_sort_key
from .models import Character, Skill
from .factions import faction_info
from .mechanics import ELEMENTAL_MECHANICS, MECHANICS
from .professions import profession_info
from .official_updates import (
    apply_official_updates,
    check_official_updates,
)


DATA_PATH = Path(__file__).parent / "data" / "characters.json"
GUIDE_TEAMS_PATH = Path(__file__).parent / "data" / "guide_teams.json"
DATA_VERSION_PATH = Path(__file__).parent / "data" / "data_version.json"
MAX_TEAM_SIZE = 6
OWNED_FILE_VERSION = 1
TEAM_FILE_VERSION = 2
DEFAULT_PROFILE_NAME = "預設"
PROFESSION_ORDER = ("守衛", "牧師", "刺客", "戰士", "射手", "法師")
TEAM_POSITION_COUNT = 9
REQUIRED_SKILL_TYPES = ("天賦", "奧義", "絕技", "秘技", "特技")
ROW_COLORS = {
    "前排": "#edf3f5",
    "中排": "#f3f1e9",
    "後排": "#f1edf3",
}
OFFICIAL_UPDATE_DIR = (
    Path.home() / "AppData" / "Local" / "DragonTeamBuilder" / "tw_notices"
)
USER_DATA_DIR = (
    Path.home() / "AppData" / "Local" / "DragonTeamBuilder" / "data"
)
USER_CHARACTERS_PATH = USER_DATA_DIR / "characters.json"
USER_DATA_VERSION_PATH = USER_DATA_DIR / "data_version.json"
CHARACTER_BACKUP_DIR = USER_DATA_DIR / "backups"


class OfficialUpdateThread(QThread):
    completed = Signal(object, str)

    def __init__(
        self,
        characters: list[Character],
        output_dir: Path,
        data_path: Path,
        version_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.characters = characters
        self.output_dir = output_dir
        self.data_path = data_path
        self.version_path = version_path

    def run(self) -> None:
        try:
            if not self.data_path.exists():
                self.data_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(DATA_PATH, self.data_path)
            if not self.version_path.exists():
                self.version_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(DATA_VERSION_PATH, self.version_path)
            records = [
                {
                    "id": character.id,
                    "name": character.name,
                    "aliases": character.aliases,
                    "skills": [
                        {
                            "name": skill.name,
                            "description": skill.description,
                            "skill_type": skill.skill_type,
                        }
                        for skill in character.skills
                    ],
                }
                for character in self.characters
            ]
            report = check_official_updates(records, self.output_dir)
            changed_urls = [
                notice.get("url", "")
                for notice in report.get("changed_notices", [])
                if isinstance(notice, dict) and notice.get("url")
            ]
            applied = apply_official_updates(
                records,
                changed_urls,
                self.data_path,
                self.version_path,
                CHARACTER_BACKUP_DIR,
            )
            report["applied"] = applied
            self.completed.emit(report, "")
        except Exception as error:
            self.completed.emit({}, str(error))


def missing_skill_types(character: Character) -> list[str]:
    """回傳角色缺少的五種標準技能類型。"""

    skill_types = {skill.skill_type for skill in character.skills}
    return [
        skill_type
        for skill_type in REQUIRED_SKILL_TYPES
        if skill_type not in skill_types
    ]


def needs_skill_review(character: Character) -> bool:
    """判斷角色是否缺少五種標準技能的任一項。"""

    return bool(missing_skill_types(character))


def profession_sort_key(value: str) -> tuple:
    try:
        order = PROFESSION_ORDER.index(value)
    except ValueError:
        order = len(PROFESSION_ORDER)
    return order, stroke_sort_key(value)


def allowed_team_positions(class_name: str) -> set[int]:
    if class_name == "守衛":
        return {0, 1, 2}
    if class_name == "戰士":
        return {0, 1, 2, 3, 4, 5}
    if class_name in {"牧師", "射手", "法師"}:
        return {3, 4, 5, 6, 7, 8}
    return set(range(TEAM_POSITION_COUNT))


def counter_requirements(abilities: set[str]) -> list[str]:
    """依已知敵方能力產生可解釋的反制需求。"""

    requirements: set[str] = set()
    if any(ability.startswith("控制-") for ability in abilities):
        requirements.update({"解控", "控制免疫"})
    if any(ability.startswith("增益") for ability in abilities):
        requirements.update({"驅散增益", "偷取增益"})
    if any(ability.startswith("減益") for ability in abilities):
        requirements.update({"淨化", "驅散"})
    if any(
        "療傷" in ability or "治療" in ability
        for ability in abilities
    ):
        requirements.update({"治療增強", "淨化"})
    return sorted(requirements, key=stroke_sort_key)


def character_has_output(character: Character) -> bool:
    """判斷角色是否具備可用的輸出資料。"""

    output_keywords = ("輸出", "爆發", "傷害", "攻擊")
    return any(
        keyword in text
        for text in (
            *character.special_functions,
            *(skill.description for skill in character.skills),
        )
        for keyword in output_keywords
    )


def character_tooltip(character: Character) -> str:
    """建立九宮格角色提示，包含五種技能。"""

    factions = "、".join(character.factions) or "未確認"
    lines = [
        character.name,
        f"職業：{character.class_name}",
        f"品質：{character.quality or '未確認'}",
        f"陣營：{factions}",
        f"能力：{'、'.join(character.special_functions) or '無'}",
        "",
        "技能：",
    ]
    skills_by_type = {
        skill.skill_type: skill
        for skill in character.skills
        if skill.skill_type
    }
    for skill_type in REQUIRED_SKILL_TYPES:
        skill = skills_by_type.get(skill_type)
        if skill is None:
            lines.append(f"{skill_type}：未整理")
            continue
        lines.append(f"{skill_type}：{skill.name}")
        lines.append(f"  {skill.description}")
    return "\n".join(lines)


SKILL_TYPE_COLORS = {
    "天賦": "#c0392b",
    "奧義": "#8e44ad",
    "絕技": "#d35400",
    "秘技": "#2471a3",
    "特技": "#16805c",
}


def format_skill_description(
    description: str,
    skills: list[Skill],
) -> str:
    """將描述中的技能名稱與戰鬥機制轉成帶顏色或連結的 HTML。"""

    references: dict[str, tuple[str, str]] = {}
    for skill in skills:
        if skill.name and skill.name not in references:
            references[skill.name] = (
                "skill",
                SKILL_TYPE_COLORS.get(skill.skill_type, "#555555"),
            )
    for mechanic in MECHANICS:
        references.setdefault(mechanic, ("mechanic", ""))
    if not references:
        return html.escape(description).replace("\n", "<br>")

    pattern = re.compile(
        "|".join(
            re.escape(name)
            for name in sorted(references, key=len, reverse=True)
        )
    )
    parts: list[str] = []
    cursor = 0
    for match in pattern.finditer(description):
        parts.append(html.escape(description[cursor:match.start()]))
        name = match.group(0)
        reference_type, color = references[name]
        escaped_name = html.escape(name)
        if reference_type == "skill":
            parts.append(
                f'<span style="color: {color}; font-weight: bold;">'
                f"{escaped_name}</span>"
            )
        else:
            parts.append(
                f'<a href="mechanic:{escaped_name}" '
                f'title="點擊查看{escaped_name}說明">{escaped_name}</a>'
            )
        cursor = match.end()
    parts.append(html.escape(description[cursor:]))
    return "".join(parts).replace("\n", "<br>")


def profession_icon(name: str, size: int = 24) -> QIcon:
    """建立一致的職業圓形圖示，避免依賴外部圖片資源。"""

    info = profession_info(name)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(info.color if info else "#777777"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, size - 1, size - 1)
    painter.setPen(Qt.GlobalColor.white)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(max(10, size // 2))
    painter.setFont(font)
    painter.drawText(
        pixmap.rect(),
        Qt.AlignmentFlag.AlignCenter,
        info.glyph if info else "?",
    )
    painter.end()
    return QIcon(pixmap)


class SearchableComboBox(QComboBox):
    """可用文字搜尋選項的下拉選單。"""

    def __init__(self) -> None:
        super().__init__()
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setCompleter(QCompleter(self.model(), self))
        completer = self.completer()
        if completer:
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCompletionMode(
                QCompleter.CompletionMode.PopupCompletion
            )
        self.lineEdit().setPlaceholderText("輸入文字搜尋技能或能力")


class FilterPanel(QGroupBox):
    """角色篩選條件面板。"""

    filter_changed = Signal()

    def __init__(
        self,
        characters: list[Character],
        *,
        include_owned_filter: bool = False,
    ) -> None:
        super().__init__("篩選條件")
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜尋角色名稱或暱稱")
        self.faction = QComboBox()
        self.class_name = QComboBox()
        self.quality = QComboBox()
        self.element_mechanism = QComboBox()
        self.owned_only = QCheckBox("只顯示已擁有角色")
        self.skill_filters: list[QComboBox] = []
        self.skill_rows = QVBoxLayout()
        self.skill_rows.setContentsMargins(0, 0, 0, 0)
        skill_container = QWidget()
        skill_container.setLayout(self.skill_rows)

        self._fill_faction_combo({
            faction for character in characters for faction in character.factions
        })
        self._fill_combo(
            self.class_name,
            "全部職業",
            {character.class_name for character in characters},
            key=profession_sort_key,
        )
        self._fill_combo(
            self.quality,
            "全部品質",
            {character.quality for character in characters},
        )
        self.skill_values = {
            tag
            for character in characters
            for tag in character.skill_tags
            if tag not in ELEMENTAL_MECHANICS
        }
        self.skill_values.update(
            function
            for character in characters
            for function in character.special_functions
            if function not in ELEMENTAL_MECHANICS
        )
        self._fill_combo(
            self.element_mechanism,
            "全部元素機制",
            ELEMENTAL_MECHANICS,
        )
        form = QFormLayout(self)
        form.addRow("關鍵字", self.search)
        form.addRow("陣營", self.faction)
        form.addRow("職業", self.class_name)
        form.addRow("品質", self.quality)
        form.addRow("技能、能力", skill_container)
        add_skill_button = QPushButton("＋新增技能篩選")
        add_skill_button.clicked.connect(self.add_skill_filter)
        form.addRow("", add_skill_button)
        form.addRow("元素機制", self.element_mechanism)
        if include_owned_filter:
            form.addRow("", self.owned_only)

        for widget in (
            self.search,
            self.faction,
            self.class_name,
            self.quality,
            self.element_mechanism,
            self.owned_only,
        ):
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._emit_changed)
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(self._emit_changed)
            else:
                widget.currentTextChanged.connect(self._emit_changed)
        self.faction.currentIndexChanged.connect(
            self._update_element_mechanism_state
        )
        self.add_skill_filter()
        self._update_element_mechanism_state()

    def add_skill_filter(self) -> None:
        """新增一個技能效果條件。"""

        row = QHBoxLayout()
        combo = SearchableComboBox()
        self._fill_combo(combo, "全部技能效果", self.skill_values)
        remove_button = QPushButton("×")
        remove_button.setFixedWidth(28)
        remove_button.clicked.connect(
            lambda: self.remove_skill_filter(combo, row)
        )
        combo.currentTextChanged.connect(self._emit_changed)
        row.addWidget(combo)
        row.addWidget(remove_button)
        self.skill_rows.addLayout(row)
        self.skill_filters.append(combo)

    def remove_skill_filter(
        self, combo: QComboBox, row: QHBoxLayout
    ) -> None:
        """移除一個技能效果條件，至少保留一個。"""

        if len(self.skill_filters) <= 1:
            combo.setCurrentIndex(0)
            return
        self.skill_filters.remove(combo)
        while row.count():
            item = row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.skill_rows.removeItem(row)
        self._emit_changed()

    @staticmethod
    def _fill_combo(
        combo: QComboBox,
        first: str,
        values: set[str],
        *,
        key=stroke_sort_key,
    ) -> None:
        combo.addItem(first)
        combo.addItems(
            sorted(
                (value for value in values if value),
                key=key,
            )
        )

    def _fill_faction_combo(self, values: set[str]) -> None:
        """填入帶有陣營圖示的陣營選單。"""

        self.faction.setIconSize(QSize(22, 22))
        self.faction.addItem("全部陣營")
        for faction in sorted(value for value in values if value):
            info = faction_info(faction)
            icon = (
                QIcon(str(Path(__file__).parent / info.image_file))
                if info
                else QIcon()
            )
            self.faction.addItem(icon, info.name if info else faction)
            self.faction.setItemData(
                self.faction.count() - 1,
                faction,
                Qt.ItemDataRole.UserRole,
            )

    def _emit_changed(self) -> None:
        self.filter_changed.emit()

    def _update_element_mechanism_state(self) -> None:
        """只在全部陣營或元素陣營時啟用元素機制篩選。"""

        selected_faction = self.faction.currentData(Qt.ItemDataRole.UserRole)
        enabled = not selected_faction or selected_faction == "元素"
        self.element_mechanism.setEnabled(enabled)
        if not enabled:
            self.element_mechanism.setCurrentIndex(0)

    def matches(
        self,
        character: Character,
        owned_ids: set[str] | None = None,
    ) -> bool:
        keyword = self.search.text().strip().casefold()
        searchable = " ".join(
            [character.name, *character.aliases, character.guide_notes]
        ).casefold()
        if keyword and keyword not in searchable:
            return False
        if (
            self.faction.currentIndex()
            and self.faction.currentData(Qt.ItemDataRole.UserRole)
            not in character.factions
        ):
            return False
        if (
            self.class_name.currentIndex()
            and self.class_name.currentText() != character.class_name
        ):
            return False
        if (
            self.quality.currentIndex()
            and self.quality.currentText() != character.quality
        ):
            return False
        selected_skills = [
            combo.currentText()
            for combo in self.skill_filters
            if combo.currentIndex()
        ]
        available_skills = set(character.skill_tags)
        available_skills.update(character.special_functions)
        if any(skill not in available_skills for skill in selected_skills):
            return False
        if (
            self.owned_only.isChecked()
            and (owned_ids is None or character.id not in owned_ids)
        ):
            return False
        selected_element_mechanism = self.element_mechanism.currentText()
        if (
            self.element_mechanism.currentIndex()
            and not any(
                selected_element_mechanism in skill.tags
                or selected_element_mechanism in skill.description
                for skill in character.skills
            )
        ):
            return False
        return True


class CharacterDetails(QWidget):
    """顯示角色完整資料。"""

    def __init__(self) -> None:
        super().__init__()
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumHeight(135)
        self.faction_badges = QHBoxLayout()
        self.profession_icon_label = QLabel()
        self.profession_label = QLabel()
        self.search = QLineEdit()
        self.search.setPlaceholderText("尋找詳細資料（Ctrl+F）")
        self.search.textChanged.connect(self._find_text)
        self.search.returnPressed.connect(self._find_next)
        self.find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.find_shortcut.activated.connect(self._focus_search)
        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(False)
        self.text.setOpenLinks(False)
        self.text.anchorClicked.connect(self._show_link)
        layout = QVBoxLayout(self)
        layout.addWidget(self.image)
        profession_layout = QHBoxLayout()
        profession_layout.addWidget(self.profession_icon_label)
        profession_layout.addWidget(self.profession_label)
        profession_layout.addStretch()
        layout.addLayout(profession_layout)
        layout.addLayout(self.faction_badges)
        layout.addWidget(self.search)
        layout.addWidget(self.text)

    def set_image_visible(self, visible: bool) -> None:
        self.image.setVisible(visible)

    def _find_text(self, text: str) -> None:
        """輸入文字後從詳細資料開頭尋找。"""

        self.text.moveCursor(QTextCursor.MoveOperation.Start)
        if text.strip():
            self._find_next()

    def _find_next(self) -> None:
        """尋找下一個符合項目，找不到時從詳細資料開頭繼續。"""

        text = self.search.text().strip()
        if not text:
            return
        if not self.text.find(text):
            self.text.moveCursor(QTextCursor.MoveOperation.Start)
            self.text.find(text)

    def _focus_search(self) -> None:
        """將 Ctrl+F 導向角色詳細資料搜尋欄。"""

        self.search.setFocus()
        self.search.selectAll()

    def _show_link(self, url: QUrl) -> None:
        if url.scheme() != "mechanic":
            return
        name = url.toString().split(":", 1)[-1]
        description = MECHANICS.get(name)
        if description:
            QMessageBox.information(self, f"{name} 機制說明", description)

    def _clear_faction_badges(self) -> None:
        while self.faction_badges.count():
            item = self.faction_badges.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_character(self, character: Character | None) -> None:
        if character is None:
            self.image.clear()
            self.profession_icon_label.clear()
            self.profession_label.clear()
            self._clear_faction_badges()
            self.search.clear()
            self.text.setHtml("<p>請選擇角色查看詳細資料。</p>")
            return

        self.search.clear()
        image_path = (
            Path(__file__).parent / character.image_file
            if character.image_file
            else None
        )
        pixmap = QPixmap(str(image_path)) if image_path else QPixmap()
        if not pixmap.isNull():
            self.image.setPixmap(
                pixmap.scaled(
                    160,
                    190,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.image.clear()

        self.profession_icon_label.setPixmap(
            profession_icon(character.class_name, 28).pixmap(28, 28)
        )
        self.profession_icon_label.setToolTip(character.class_name)
        self.profession_label.setText(f"職業：{character.class_name}")

        self._clear_faction_badges()
        for faction in character.factions:
            info = faction_info(faction)
            badge = QWidget()
            badge.setToolTip(info.description if info else faction)
            badge.setStyleSheet(
                f"color: #202020; background: "
                f"{info.color if info else '#dddddd'}; "
                "border-radius: 5px; padding: 3px;"
            )
            badge_layout = QHBoxLayout(badge)
            badge_layout.setContentsMargins(2, 2, 2, 2)
            if info:
                logo = QPixmap(str(Path(__file__).parent / info.image_file))
                if not logo.isNull():
                    logo_label = QLabel()
                    logo_label.setPixmap(
                        logo.scaled(
                            24,
                            24,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    badge_layout.addWidget(logo_label)
            badge_layout.addWidget(QLabel(f"  {info.name if info else faction}  "))
            self.faction_badges.addWidget(badge)
        self.faction_badges.addStretch()

        factions = "、".join(character.factions) or "未確認"
        functions = "、".join(character.special_functions) or "尚未整理"
        sections = [
            f"<h2>{character.name}</h2>",
            f"<p><b>職業：</b>{character.class_name}<br>"
            f"<b>陣營：</b>{factions}<br>"
            f"<b>品質：</b>{character.quality or '未確認'} "
            f"<b>TIER：</b>{character.tier or '未評級'}</p>",
            f"<p><b>特殊功能：</b>{functions}</p>",
        ]
        if character.guide_notes:
            sections.append(f"<p><b>攻略備註：</b>{character.guide_notes}</p>")
        for skill in character.skills:
            if skill.skill_type in {"神格", "God Skill"}:
                continue
            tags = f"（{'、'.join(skill.tags)}）" if skill.tags else ""
            skill_type = html.escape(skill.skill_type or "技能")
            skill_type_color = SKILL_TYPE_COLORS.get(
                skill.skill_type,
                "#555555",
            )
            formatted_description = format_skill_description(
                skill.description,
                character.skills,
            )
            sections.append(
                f"<h3>{html.escape(skill.name)} "
                f'<span style="font-size: inherit; color: {skill_type_color};">'
                f"{skill_type}：</span>{tags}</h3>"
                f'<p style="color: #202020;">{formatted_description}</p>'
            )
        self.text.setHtml("".join(sections))


class CharacterList(QListWidget):
    """篩選後的角色清單。"""

    ownership_changed = Signal(str, bool)

    def __init__(self, *, checkable: bool = False) -> None:
        super().__init__()
        self.checkable = checkable
        self.owned_ids: set[str] = set()
        if checkable:
            self.itemChanged.connect(self._ownership_changed)

    def set_characters(self, characters: list[Character]) -> None:
        current_id = (
            self.current_character().id
            if self.current_character()
            else None
        )
        blocker = QSignalBlocker(self) if self.checkable else None
        self.clear()
        sorted_characters = sorted(
            characters,
            key=lambda character: (
                profession_sort_key(character.class_name),
                stroke_sort_key(character.quality),
                stroke_sort_key(character.main_faction),
                stroke_sort_key(character.secondary_faction),
                stroke_sort_key(character.name),
            ),
        )
        for character in sorted_characters:
            missing = missing_skill_types(character)
            review_marker = "  [技能待補]" if missing else ""
            item = QListWidgetItem(
                f"{character.name}  [{character.class_name}] "
                f"{character.quality or '未確認'}{review_marker}"
            )
            item.setIcon(profession_icon(character.class_name))
            item.setData(Qt.ItemDataRole.UserRole, character)
            if self.checkable:
                item.setFlags(
                    item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                item.setCheckState(
                    Qt.CheckState.Checked
                    if character.id in self.owned_ids
                    else Qt.CheckState.Unchecked
                )
            if missing:
                item.setToolTip(
                    f"缺少技能：{'、'.join(missing)}"
                )
            self.addItem(item)
        del blocker
        if current_id:
            for index in range(self.count()):
                item = self.item(index)
                character = item.data(Qt.ItemDataRole.UserRole)
                if character and character.id == current_id:
                    self.setCurrentItem(item)
                    break

    def _ownership_changed(self, item: QListWidgetItem) -> None:
        character = item.data(Qt.ItemDataRole.UserRole)
        if character is None:
            return
        owned = item.checkState() == Qt.CheckState.Checked
        if owned:
            self.owned_ids.add(character.id)
        else:
            self.owned_ids.discard(character.id)
        self.ownership_changed.emit(character.id, owned)

    def current_character(self) -> Character | None:
        item = self.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None


class OwnedCharactersDialog(QDialog):
    """讓使用者一次勾選並套用已擁有角色。"""

    def __init__(
        self,
        characters: list[Character],
        profiles: dict[str, set[str]],
        active_profile: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("擁有角色管理")
        self.resize(420, 600)
        self.characters = characters
        self.profiles = {
            name: set(ids)
            for name, ids in profiles.items()
        }
        self.active_profile = active_profile
        self.selected_id_set = set(
            self.profiles.get(active_profile, set())
        )
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(
            sorted(self.profiles, key=stroke_sort_key)
        )
        self.profile_combo.setCurrentText(active_profile)
        self.profile_combo.currentTextChanged.connect(
            self._switch_profile
        )
        self.class_filter = QComboBox()
        self.quality_filter = QComboBox()
        self.faction_filter = QComboBox()
        self._fill_filter(
            self.class_filter,
            "全部職業",
            {character.class_name for character in characters},
            key=profession_sort_key,
        )
        self._fill_filter(
            self.quality_filter,
            "全部品質",
            {character.quality for character in characters},
        )
        self._fill_filter(
            self.faction_filter,
            "全部陣營",
            {
                faction
                for character in characters
                for faction in character.factions
            },
        )
        for filter_box in (
            self.class_filter,
            self.quality_filter,
            self.faction_filter,
        ):
            filter_box.currentTextChanged.connect(self._refresh_list)

        self.character_list = QListWidget()
        self.character_list.itemChanged.connect(self._item_changed)

        select_all = QPushButton("全選")
        select_all.clicked.connect(
            lambda: self._set_all(Qt.CheckState.Checked)
        )
        clear_all = QPushButton("全部取消")
        clear_all.clicked.connect(
            lambda: self._set_all(Qt.CheckState.Unchecked)
        )
        actions = QHBoxLayout()
        actions.addWidget(select_all)
        actions.addWidget(clear_all)
        actions.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("設定檔"))
        profile_layout.addWidget(self.profile_combo)
        new_profile = QPushButton("新增")
        new_profile.clicked.connect(self._new_profile)
        profile_layout.addWidget(new_profile)
        delete_profile = QPushButton("刪除")
        delete_profile.clicked.connect(self._delete_profile)
        profile_layout.addWidget(delete_profile)
        layout.addLayout(profile_layout)
        layout.addWidget(
            QLabel("勾選已擁有角色，按「確定」後套用至角色瀏覽器與隊伍組成器。")
        )
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.class_filter)
        filter_layout.addWidget(self.quality_filter)
        filter_layout.addWidget(self.faction_filter)
        layout.addLayout(filter_layout)
        layout.addWidget(self.character_list)
        layout.addLayout(actions)
        layout.addWidget(buttons)
        self._refresh_list()

    def _switch_profile(self, name: str) -> None:
        if not name or name == self.active_profile:
            return
        self.profiles[self.active_profile] = set(self.selected_id_set)
        self.active_profile = name
        self.selected_id_set = set(self.profiles.get(name, set()))
        self._refresh_list()

    def _new_profile(self) -> None:
        name, accepted = QInputDialog.getText(
            self,
            "新增設定檔",
            "請輸入設定檔名稱：",
        )
        name = name.strip()
        if not accepted or not name:
            return
        if name in self.profiles:
            QMessageBox.warning(self, "新增失敗", "設定檔名稱已存在。")
            return
        self.profiles[self.active_profile] = set(self.selected_id_set)
        self.profiles[name] = set()
        self.profile_combo.addItem(name)
        self.profile_combo.setCurrentText(name)

    def _delete_profile(self) -> None:
        if len(self.profiles) <= 1:
            QMessageBox.information(
                self,
                "無法刪除",
                "至少要保留一個擁有角色設定檔。",
            )
            return
        answer = QMessageBox.question(
            self,
            "刪除設定檔",
            f"確定刪除「{self.active_profile}」設定檔？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        del self.profiles[self.active_profile]
        next_name = sorted(self.profiles, key=stroke_sort_key)[0]
        self.active_profile = next_name
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(
            sorted(self.profiles, key=stroke_sort_key)
        )
        self.profile_combo.setCurrentText(next_name)
        self.profile_combo.blockSignals(False)
        self.selected_id_set = set(self.profiles[next_name])
        self._refresh_list()

    @staticmethod
    def _fill_filter(
        combo: QComboBox,
        placeholder: str,
        values: set[str],
        *,
        key=stroke_sort_key,
    ) -> None:
        combo.addItem(placeholder)
        combo.addItems(sorted(values, key=key))

    def _matches(self, character: Character) -> bool:
        selected_class = self.class_filter.currentText()
        selected_quality = self.quality_filter.currentText()
        selected_faction = self.faction_filter.currentText()
        return (
            (selected_class == "全部職業"
             or character.class_name == selected_class)
            and (
                selected_quality == "全部品質"
                or character.quality == selected_quality
            )
            and (
                selected_faction == "全部陣營"
                or selected_faction in character.factions
            )
        )

    def _refresh_list(self) -> None:
        self.character_list.blockSignals(True)
        self.character_list.clear()
        filtered = sorted(
            (character for character in self.characters if self._matches(character)),
            key=lambda character: (
                profession_sort_key(character.class_name),
                stroke_sort_key(character.quality),
                stroke_sort_key(character.main_faction),
                stroke_sort_key(character.secondary_faction),
                stroke_sort_key(character.name),
            ),
        )
        for character in filtered:
            factions = "／".join(character.factions) or "未分類"
            item = QListWidgetItem(
                f"{character.name}  |  職業：{character.class_name}"
                f"  品質：{character.quality or '未標註'}"
                f"  陣營：{factions}"
            )
            item.setData(Qt.ItemDataRole.UserRole, character.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if character.id in self.selected_id_set
                else Qt.CheckState.Unchecked
            )
            self.character_list.addItem(item)
        self.character_list.blockSignals(False)

    def _item_changed(self, item: QListWidgetItem) -> None:
        character_id = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self.selected_id_set.add(character_id)
        else:
            self.selected_id_set.discard(character_id)

    def _set_all(self, state: Qt.CheckState) -> None:
        for row in range(self.character_list.count()):
            self.character_list.item(row).setCheckState(state)

    def selected_ids(self) -> set[str]:
        self.profiles[self.active_profile] = set(self.selected_id_set)
        return set(self.selected_id_set)

    def profile_data(self) -> tuple[str, dict[str, set[str]]]:
        self.profiles[self.active_profile] = set(self.selected_id_set)
        return self.active_profile, {
            name: set(ids)
            for name, ids in self.profiles.items()
        }


class EnemyTeamDialog(QDialog):
    """輸入敵方九宮格隊伍。"""

    def __init__(
        self,
        characters: list[Character],
        positions: list[str | None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.characters = characters
        self.setWindowTitle("敵隊輸入")
        self.resize(760, 620)
        self.position_boxes: list[QComboBox] = []
        self.position_labels: list[QLabel] = []
        character_options = sorted(
            characters,
            key=lambda character: (
                profession_sort_key(character.class_name),
                stroke_sort_key(character.name),
            ),
        )
        grid = QGridLayout()
        for position in range(TEAM_POSITION_COUNT):
            label = QLabel(
                f"{'前排' if position < 3 else '中排' if position < 6 else '後排'}"
                f" {position + 1}"
            )
            row_name = (
                "前排" if position < 3
                else "中排" if position < 6
                else "後排"
            )
            row_style = f"background-color: {ROW_COLORS[row_name]};"
            label.setStyleSheet(row_style)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.position_labels.append(label)
            combo = SearchableComboBox()
            combo.setStyleSheet(row_style)
            combo.setIconSize(QSize(40, 40))
            combo.addItem("空位", None)
            for character in character_options:
                icon = (
                    QIcon(
                        str(Path(__file__).parent / character.image_file)
                    )
                    if character.image_file
                    else QIcon()
                )
                combo.addItem(
                    icon,
                    f"{character.name} [{character.class_name}]",
                    character.id,
                )
            current_id = positions[position]
            index = combo.findData(current_id)
            combo.setCurrentIndex(index if index >= 0 else 0)
            self.position_boxes.append(combo)
            grid.addWidget(label, position // 3 * 3, position % 3)
            grid.addWidget(
                combo,
                position // 3 * 3 + 1,
                position % 3,
            )
            preview = QLabel("空位")
            preview.setStyleSheet(row_style)
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setMinimumHeight(64)
            self.position_labels[position].setProperty(
                "preview_label",
                preview,
            )
            grid.addWidget(
                preview,
                position // 3 * 3 + 2,
                position % 3,
            )

        self.validation_label = QLabel()
        self.validation_label.setStyleSheet("color: #c0392b;")
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        for combo in self.position_boxes:
            combo.currentIndexChanged.connect(self._selection_changed)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "選擇敵方角色與站位；角色列表不受擁有角色設定影響。"
        ))
        layout.addLayout(grid)
        layout.addWidget(self.validation_label)
        layout.addWidget(self.buttons)
        self._selection_changed()

    def _selection_changed(self) -> None:
        selected_ids = [
            combo.currentData()
            for combo in self.position_boxes
            if combo.currentData()
        ]
        duplicate = len(selected_ids) != len(set(selected_ids))
        too_many = len(selected_ids) > MAX_TEAM_SIZE
        if duplicate:
            message = "同一角色不可重複放入敵隊。"
        elif too_many:
            message = f"敵隊最多只能放入 {MAX_TEAM_SIZE} 名角色。"
        else:
            message = ""
        self.validation_label.setText(message)
        ok_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        if ok_button is not None:
            ok_button.setEnabled(not message)
        for position, combo in enumerate(self.position_boxes):
            preview = self.position_labels[position].property(
                "preview_label"
            )
            if not isinstance(preview, QLabel):
                continue
            character_id = combo.currentData()
            character = next(
                (
                    value
                    for value in self.characters
                    if value.id == character_id
                ),
                None,
            )
            if character is None:
                preview.setPixmap(QPixmap())
                preview.setText("空位")
                continue
            preview.setText(character.name)
            if character.image_file:
                preview.setPixmap(
                    QPixmap(
                        str(Path(__file__).parent / character.image_file)
                    ).scaled(
                        52,
                        52,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                preview.setPixmap(QPixmap())

    def positions(self) -> list[str | None]:
        return [
            combo.currentData()
            for combo in self.position_boxes
        ]


class MainWindow(QMainWindow):
    """角色資料與隊伍組成主視窗。"""

    def __init__(self, characters: list[Character]) -> None:
        super().__init__()
        self.characters = characters
        self.filtered_characters: list[Character] = []
        self.teams: dict[str, list[str | None]] = {}
        self.active_team_name = "隊伍 1"
        self.team_positions: list[str | None] = [
            None
        ] * TEAM_POSITION_COUNT
        self.selected_team_position: int | None = None
        self.enemy_positions: list[str | None] = [
            None
        ] * TEAM_POSITION_COUNT
        self.owned_ids: set[str] = set()
        self.owned_profiles: dict[str, set[str]] = {}
        self.active_owned_profile = DEFAULT_PROFILE_NAME
        self.settings = QSettings("DragonTeamBuilder", "DragonTeamBuilder")
        self.official_update_thread: OfficialUpdateThread | None = None
        self.guide_teams: list[dict] = []
        self.data_version: dict = {}
        self._load_guide_teams()
        self._load_data_version()
        self._load_owned_settings()
        self._load_teams_settings()
        self._load_enemy_settings()
        self.setWindowTitle("龍魂旅人角色與隊伍組成器")
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.resize(available.width() // 2, available.height() // 2)
        else:
            self.resize(1280, 800)
        self._build_ui()
        self._refresh_characters()

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_browser_tab(), "角色瀏覽器")
        tabs.addTab(self._build_team_tab(), "隊伍組成器")
        tabs.addTab(self._build_enemy_tab(), "敵隊分析")
        tabs.addTab(self._build_sources_tab(), "資料來源")
        self.setCentralWidget(tabs)
        self._build_toolbar()
        self._refresh_team_candidates()
        self.statusBar().showMessage(f"已載入 {len(self.characters)} 名角色")
        QTimer.singleShot(1500, self._maybe_check_official_updates)

    def _load_guide_teams(self) -> None:
        try:
            payload = json.loads(
                GUIDE_TEAMS_PATH.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            payload = []
        if isinstance(payload, list):
            self.guide_teams = [
                team
                for team in payload
                if isinstance(team, dict)
                and isinstance(team.get("character_ids"), list)
            ]

    def _load_data_version(self) -> None:
        version_path = (
            USER_DATA_VERSION_PATH
            if USER_DATA_VERSION_PATH.exists()
            else DATA_VERSION_PATH
        )
        try:
            payload = json.loads(
                version_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            self.data_version = payload

    def _build_guide_teams_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("模式："))
        self.guide_mode_filter = QComboBox()
        self.guide_mode_filter.addItem("全部模式", "")
        modes = sorted(
            {
                team.get("mode", "General")
                for team in self.guide_teams
                if isinstance(team.get("mode", "General"), str)
            },
            key=stroke_sort_key,
        )
        self.guide_mode_filter.addItems(modes)
        self.guide_mode_filter.currentIndexChanged.connect(
            self._refresh_guide_team_list
        )
        filter_layout.addWidget(self.guide_mode_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.guide_team_list = QListWidget()
        self.guide_team_list.currentRowChanged.connect(
            self._show_guide_team_details
        )
        self.guide_team_details = QTextBrowser()
        self.guide_team_details.setOpenExternalLinks(True)
        splitter.addWidget(self.guide_team_list)
        splitter.addWidget(self.guide_team_details)
        splitter.setSizes([420, 760])
        layout.addWidget(splitter)
        apply_button = QPushButton("載入到目前隊伍")
        apply_button.clicked.connect(self._apply_guide_team)
        layout.addWidget(apply_button)
        self._refresh_guide_team_list()
        return tab

    def _filtered_guide_teams(self) -> list[dict]:
        mode = self.guide_mode_filter.currentData()
        return [
            team
            for team in self.guide_teams
            if not mode or team.get("mode") == mode
        ]

    def _refresh_guide_team_list(self) -> None:
        if not hasattr(self, "guide_team_list"):
            return
        self.guide_team_list.blockSignals(True)
        self.guide_team_list.clear()
        for team in self._filtered_guide_teams():
            item = QListWidgetItem(
                f"{team.get('name', '未命名')} "
                f"[{team.get('mode', 'General')}]"
            )
            item.setData(Qt.ItemDataRole.UserRole, team.get("id", ""))
            self.guide_team_list.addItem(item)
        self.guide_team_list.blockSignals(False)
        if self.guide_team_list.count():
            self.guide_team_list.setCurrentRow(0)
        else:
            self.guide_team_details.setHtml("<p>目前沒有符合條件的攻略隊伍。</p>")

    def _selected_guide_team(self) -> dict | None:
        row = self.guide_team_list.currentRow()
        teams = self._filtered_guide_teams()
        return teams[row] if 0 <= row < len(teams) else None

    def _show_guide_team_details(self, _row: int) -> None:
        team = self._selected_guide_team()
        if team is None:
            return
        character_map = {
            character.id: character
            for character in self.characters
        }
        names = []
        missing = []
        for character_id in team.get("character_ids", []):
            character = character_map.get(character_id)
            if character is None:
                missing.append(str(character_id))
            else:
                owned = character.id in self.owned_ids
                suffix = "" if owned else "（未擁有／不建議使用）"
                names.append(f"{character.name}{suffix}")
        source_url = html.escape(team.get("source_url", ""))
        self.guide_team_details.setHtml(
            f"<h2>{html.escape(team.get('name', '未命名'))}</h2>"
            f"<p><b>模式：</b>{html.escape(team.get('mode', 'General'))}"
            f"<br><b>陣營：</b>{html.escape(team.get('faction', '未標註'))}"
            f"<br><b>角色：</b>{html.escape('、'.join(names) or '無')}"
            f"<br><b>資料來源：</b>{html.escape(team.get('source', '未知'))}"
            f"<br><a href=\"{source_url}\">{source_url}</a></p>"
            f"<p><b>資料缺失：</b>"
            f"{html.escape('、'.join(missing) or '無')}</p>"
            "<p>未擁有角色僅作為攻略參考，載入前請先確認自己的角色清單。</p>"
        )

    def _apply_guide_team(self) -> None:
        team = self._selected_guide_team()
        if team is None:
            return
        positions: list[str | None] = [None] * TEAM_POSITION_COUNT
        character_map = {
            character.id: character
            for character in self.characters
        }
        missing = []
        for character_id in team.get("character_ids", [])[:MAX_TEAM_SIZE]:
            character = character_map.get(character_id)
            if character is None:
                missing.append(str(character_id))
                continue
            position = next(
                (
                    index
                    for index, value in enumerate(positions)
                    if value is None
                    and index in allowed_team_positions(
                        character.class_name
                    )
                ),
                None,
            )
            if position is None:
                continue
            positions[position] = character.id
        if missing:
            QMessageBox.warning(
                self,
                "載入攻略隊伍",
                "部分角色資料不存在："
                + "、".join(missing),
            )
        self.team_positions = positions
        self.selected_team_position = None
        self._save_current_team()
        self._save_teams_settings()
        self._refresh_team_grid()

    def _build_sources_tab(self) -> QWidget:
        """集中顯示角色、技能與工具使用的資料來源。"""

        browser = QTextBrowser()
        sources: dict[str, str] = {}
        known_sites = {
            "www.gamekee.com": ("GameKee", "https://www.gamekee.com/lhlr/"),
            "www.taptap.cn": ("TapTap", "https://www.taptap.cn/"),
            "www.dragoncompanion.com": (
                "Dragon Companion",
                "https://www.dragoncompanion.com/",
            ),
            "sod.game-beans.com": (
                "台服官方公告",
                "https://sod.game-beans.com/jx/sodNotice/index.html",
            ),
            "docs.google.com": (
                "Google 試算表攻略",
                "https://docs.google.com/",
            ),
        }
        for character in self.characters:
            references = []
            if character.source:
                references.append(character.source)
            references.extend(
                source
                for skill in character.skills
                for source in skill.sources
            )
            for source in references:
                if source.url:
                    host = urlparse(source.url).netloc.lower()
                    if host in known_sites:
                        title, url = known_sites[host]
                    else:
                        title, url = host or source.title, source.url
                    sources[title] = url

        sections = [
            "<h2>資料來源</h2>",
            "<p>相同網站的不同分頁合併顯示為同一個資料來源。</p>",
            "<h3>資料版本</h3>",
            f"<p><b>版本：</b>{html.escape(str(self.data_version.get('version', '未知')))}"
            f"<br><b>更新日期：</b>{html.escape(str(self.data_version.get('updated_at', '未知')))}"
            f"<br><b>角色數：</b>{html.escape(str(self.data_version.get('character_count', len(self.characters))))}</p>",
        ]
        for title in sorted(sources):
            url = sources[title]
            sections.append(
                f"<p><b>{html.escape(title)}</b><br>"
                f'<a href="{html.escape(url)}">{html.escape(url)}</a></p>'
            )
        browser.setOpenExternalLinks(True)
        browser.setHtml("".join(sections))
        return browser

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("角色工具")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        owned_action = QAction("擁有角色管理", self)
        owned_action.triggered.connect(self._open_owned_dialog)
        toolbar.addAction(owned_action)

        self.owned_filter_action = QAction("只顯示已擁有角色", self)
        self.owned_filter_action.setCheckable(True)
        self.owned_filter_action.toggled.connect(self._set_owned_filter)
        toolbar.addAction(self.owned_filter_action)

        self.image_action = QAction("顯示角色圖片", self)
        self.image_action.setCheckable(True)
        self.image_action.setChecked(True)
        self.image_action.toggled.connect(self._set_images_visible)
        toolbar.addAction(self.image_action)

        toolbar.addSeparator()
        save_action = QAction("儲存擁有角色", self)
        save_action.triggered.connect(self._save_owned_file)
        toolbar.addAction(save_action)
        load_action = QAction("載入擁有角色", self)
        load_action.triggered.connect(self._load_owned_file)
        toolbar.addAction(load_action)
        clear_action = QAction("清除擁有角色", self)
        clear_action.triggered.connect(self._clear_owned_characters)
        toolbar.addAction(clear_action)
        toolbar.addSeparator()
        export_team_action = QAction("匯出隊伍", self)
        export_team_action.triggered.connect(self._save_team_file)
        toolbar.addAction(export_team_action)
        import_team_action = QAction("匯入隊伍", self)
        import_team_action.triggered.connect(self._load_team_file)
        toolbar.addAction(import_team_action)
        official_update_action = QAction("檢查官方更新", self)
        official_update_action.triggered.connect(
            self._start_official_update_check
        )
        toolbar.addAction(official_update_action)
        report_action = QAction("台服官方更新公告", self)
        report_action.triggered.connect(self._show_official_update_report)
        toolbar.addAction(report_action)

    def _maybe_check_official_updates(self) -> None:
        today = date.today().isoformat()
        if self.settings.value("official_update_checked_at", "") == today:
            return
        self._start_official_update_check(auto=True)

    def _start_official_update_check(self, auto: bool = False) -> None:
        if self.official_update_thread is not None:
            return
        self.statusBar().showMessage("正在檢查台服官方公告更新…")
        self.official_update_thread = OfficialUpdateThread(
            self.characters,
            OFFICIAL_UPDATE_DIR,
            USER_CHARACTERS_PATH,
            USER_DATA_VERSION_PATH,
            self,
        )
        self.official_update_thread.completed.connect(
            self._official_update_finished
        )
        self.official_update_thread.finished.connect(
            self._official_update_thread_finished
        )
        self.official_update_thread.start()

    def _official_update_thread_finished(self) -> None:
        self.official_update_thread = None

    def _official_update_finished(
        self,
        report: object,
        error: str,
    ) -> None:
        if error:
            self.statusBar().showMessage("官方公告更新檢查失敗")
            QMessageBox.warning(self, "官方更新檢查失敗", error)
            return
        self.settings.setValue(
            "official_update_checked_at",
            date.today().isoformat(),
        )
        if not isinstance(report, dict):
            return
        notices = report.get("notices", [])
        applied = report.get("applied", {})
        updated_characters = (
            applied.get("updated_characters", [])
            if isinstance(applied, dict)
            else []
        )
        self.statusBar().showMessage(
            f"官方公告檢查完成：找到 {len(notices)} 則維護公告，"
            f"自動套用 {len(updated_characters)} 名角色"
        )
        if updated_characters:
            self.characters = load_characters(USER_CHARACTERS_PATH)
            self._refresh_characters()
            self._refresh_team_candidates()
            self._refresh_team_analysis()
            self._refresh_enemy_tab()
            QMessageBox.information(
                self,
                "官方角色資料已更新",
                f"已自動套用 {len(updated_characters)} 名角色的官方資料。\n"
                f"套用前備份：{applied.get('backup', '')}",
            )

    def _show_official_update_report(self) -> None:
        report_path = OFFICIAL_UPDATE_DIR / "official_update_report.json"
        if not report_path.exists():
            QMessageBox.information(
                self,
                "官方更新報告",
                "目前尚未產生報告，請先執行「檢查官方更新」。",
            )
            return
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            QMessageBox.warning(
                self,
                "官方更新報告",
                f"報告讀取失敗：{error}",
            )
            return
        if not isinstance(report, dict):
            QMessageBox.warning(
                self,
                "官方更新報告",
                "報告格式無法辨識。",
            )
            return
        browser = QTextBrowser()
        sections = [
            "<h2>台服官方更新報告</h2>",
            f"<p><b>最後檢查日期：</b>"
            f"{html.escape(str(report.get('checked_at', '未知')))}</p>",
        ]
        notices = report.get("notices", [])
        if isinstance(notices, list) and notices:
            sections.append("<h3>台服官方維護公告</h3><ul>")
            for notice in notices:
                if not isinstance(notice, dict):
                    continue
                title = html.escape(str(notice.get("title", "未命名公告")))
                url = html.escape(str(notice.get("url", "")))
                notice_date_value = str(notice.get("date", "未知日期"))
                date_match = re.fullmatch(
                    r"(\d{4})-(\d{1,2})-(\d{1,2})",
                    notice_date_value,
                )
                if date_match:
                    notice_date_value = (
                        f"{date_match.group(1)}年"
                        f"{int(date_match.group(2))}月"
                        f"{int(date_match.group(3))}日"
                    )
                notice_date = html.escape(notice_date_value)
                new_characters = notice.get("new_characters", [])
                if isinstance(new_characters, list) and new_characters:
                    new_text = "、".join(
                        html.escape(str(name)) for name in new_characters
                    )
                else:
                    new_text = "無"
                updated = "是" if notice.get(
                    "updates_character_values", False
                ) else "否"
                sections.append(
                    f'<li><b>{notice_date}</b> '
                    f'<a href="{url}">{title}</a><br>'
                    f'新增角色：{new_text}<br>'
                    f'更新角色數值：{updated}</li>'
                )
            sections.append("</ul>")
        else:
            sections.append("<p>目前沒有找到符合條件的維護公告。</p>")
        browser.setHtml("".join(sections))
        browser.setOpenExternalLinks(True)
        dialog = QDialog(self)
        dialog.setWindowTitle("官方更新報告")
        dialog.resize(780, 560)
        layout = QVBoxLayout(dialog)
        layout.addWidget(browser)
        close_button = QPushButton("關閉")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def _set_images_visible(self, visible: bool) -> None:
        for details in (self.browser_details, self.team_details):
            details.set_image_visible(visible)
        self._refresh_team_grid()
        self._refresh_enemy_tab()

    def _open_owned_dialog(self) -> None:
        dialog = OwnedCharactersDialog(
            self.characters,
            self.owned_profiles,
            self.active_owned_profile,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        (
            self.active_owned_profile,
            self.owned_profiles,
        ) = dialog.profile_data()
        self.owned_ids = set(
            self.owned_profiles[self.active_owned_profile]
        )
        self._save_owned_settings()
        self._refresh_characters()
        self._refresh_team_candidates()

    def _build_browser_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.browser_filters = FilterPanel(self.characters)
        self.browser_filters.filter_changed.connect(self._refresh_characters)
        self.browser_list = CharacterList(checkable=True)
        self.browser_list.ownership_changed.connect(
            self._set_character_owned
        )
        self.browser_list.currentItemChanged.connect(
            lambda _current, _previous: self.browser_details.show_character(
                self.browser_list.current_character()
            )
        )
        self.browser_details = CharacterDetails()

        splitter.addWidget(self.browser_filters)
        splitter.addWidget(self.browser_list)
        splitter.addWidget(self.browser_details)
        splitter.setSizes([240, 350, 690])
        layout.addWidget(splitter)
        return tab

    def _build_team_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.team_filters = FilterPanel(
            self.characters,
        )
        self.team_filters.filter_changed.connect(self._refresh_team_candidates)
        self.team_candidates = CharacterList(checkable=True)
        self.team_candidates.ownership_changed.connect(
            self._set_character_owned
        )
        self.team_candidates.itemDoubleClicked.connect(
            lambda _item: self._add_selected_to_team()
        )
        self.team_details = CharacterDetails()
        self.team_candidates.currentItemChanged.connect(
            lambda _current, _previous: self.team_details.show_character(
                self.team_candidates.current_character()
            )
        )

        candidate_panel = QWidget()
        candidate_layout = QVBoxLayout(candidate_panel)
        candidate_layout.addWidget(self.team_filters)
        candidate_layout.addWidget(QLabel("勾選角色表示已擁有，可用篩選條件只顯示擁有角色"))
        candidate_layout.addWidget(self.team_candidates)
        add_button = QPushButton("加入隊伍")
        add_button.clicked.connect(self._add_selected_to_team)
        candidate_layout.addWidget(add_button)

        team_panel = QGroupBox("隊伍配置")
        team_layout = QVBoxLayout(team_panel)
        team_selector_layout = QHBoxLayout()
        self.team_selector = QComboBox()
        self.team_selector.currentTextChanged.connect(self._switch_team)
        team_selector_layout.addWidget(self.team_selector)
        new_team_button = QPushButton("新增")
        new_team_button.clicked.connect(self._new_team)
        team_selector_layout.addWidget(new_team_button)
        rename_team_button = QPushButton("重新命名")
        rename_team_button.clicked.connect(self._rename_team)
        team_selector_layout.addWidget(rename_team_button)
        delete_team_button = QPushButton("刪除")
        delete_team_button.clicked.connect(self._delete_team)
        team_selector_layout.addWidget(delete_team_button)
        team_layout.addLayout(team_selector_layout)

        self.team_grid = QGridLayout()
        self.team_position_buttons: list[QPushButton] = []
        for position in range(TEAM_POSITION_COUNT):
            button = QPushButton()
            button.setMinimumSize(120, 70)
            button.setIconSize(QSize(56, 56))
            button.clicked.connect(
                lambda _checked=False, index=position:
                self._select_team_position(index)
            )
            self.team_position_buttons.append(button)
            self.team_grid.addWidget(button, position // 3, position % 3)
        team_layout.addLayout(self.team_grid)
        self.team_position_label = QLabel("請先選擇九宮格位置")
        team_layout.addWidget(self.team_position_label)
        self.team_analysis = QLabel()
        self.team_analysis.setWordWrap(True)
        self.team_analysis.setTextFormat(
            Qt.TextFormat.RichText
        )
        analysis_panel = QGroupBox("隊伍分析")
        analysis_layout = QVBoxLayout(analysis_panel)
        analysis_scroll = QScrollArea()
        analysis_scroll.setWidgetResizable(True)
        analysis_scroll.setMinimumHeight(150)
        analysis_scroll.setWidget(self.team_analysis)
        analysis_layout.addWidget(analysis_scroll)
        team_layout.addWidget(analysis_panel)
        remove_button = QPushButton("移除選取角色")
        remove_button.clicked.connect(self._remove_selected_from_team)
        clear_button = QPushButton("清空隊伍")
        clear_button.clicked.connect(self._clear_team)
        team_layout.addWidget(remove_button)
        team_layout.addWidget(clear_button)

        splitter.addWidget(candidate_panel)
        splitter.addWidget(team_panel)
        splitter.addWidget(self.team_details)
        splitter.setSizes([360, 570, 280])
        layout.addWidget(splitter)
        self._refresh_team_selector()
        self._refresh_team_grid()
        self._refresh_team_analysis()
        return tab

    def _build_enemy_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        board_layout = QHBoxLayout()
        own_panel = QGroupBox("我方隊伍")
        enemy_panel = QGroupBox("敵方隊伍")
        own_grid = QGridLayout(own_panel)
        enemy_grid = QGridLayout(enemy_panel)
        self.enemy_own_buttons: list[QPushButton] = []
        self.enemy_opponent_buttons: list[QPushButton] = []
        for row in range(3):
            for column in range(3):
                own_position = row + (2 - column) * 3
                enemy_position = (2 - row) + column * 3
                own_button = QPushButton()
                enemy_button = QPushButton()
                for button in (own_button, enemy_button):
                    button.setMinimumSize(125, 92)
                    button.setIconSize(QSize(56, 56))
                own_button.clicked.connect(
                    lambda _checked=False, index=own_position:
                    self._select_team_position(index)
                )
                enemy_button.clicked.connect(self._open_enemy_dialog)
                self.enemy_own_buttons.append(own_button)
                self.enemy_opponent_buttons.append(enemy_button)
                own_grid.addWidget(own_button, row, column)
                enemy_grid.addWidget(enemy_button, row, column)
        board_layout.addWidget(own_panel)
        relation_label = QLabel("↔\n對位\n關係")
        relation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        relation_label.setMinimumWidth(60)
        board_layout.addWidget(relation_label)
        board_layout.addWidget(enemy_panel)
        layout.addLayout(board_layout)

        self.enemy_relation_text = QLabel()
        self.enemy_relation_text.setWordWrap(True)
        self.enemy_relation_text.setTextFormat(Qt.TextFormat.RichText)
        relation_panel = QGroupBox("站位與威脅分析")
        relation_layout = QVBoxLayout(relation_panel)
        relation_layout.addWidget(self.enemy_relation_text)
        layout.addWidget(relation_panel)
        edit_enemy_button = QPushButton("編輯敵隊")
        edit_enemy_button.clicked.connect(self._open_enemy_dialog)
        layout.addWidget(edit_enemy_button)
        recommend_button = QPushButton("依敵隊需求推薦隊伍")
        recommend_button.clicked.connect(
            lambda _checked=False: self._show_team_recommendation()
        )
        layout.addWidget(recommend_button)
        refresh_button = QPushButton("重新整理分析")
        refresh_button.clicked.connect(self._refresh_enemy_tab)
        layout.addWidget(refresh_button)
        self._refresh_enemy_tab()
        return tab

    def _set_board_button(
        self,
        button: QPushButton,
        character: Character | None,
        row_name: str,
    ) -> None:
        if character is None:
            button.setText(f"{row_name}\n空位")
            button.setIcon(QIcon())
            button.setToolTip(f"{row_name}\n空位")
            button.setStyleSheet(
                f"background-color: {ROW_COLORS[row_name]};"
            )
            return
        button.setText(
            f"{row_name}\n{character.name}\n{character.class_name}"
        )
        button.setToolTip(character_tooltip(character))
        button.setStyleSheet(
            f"background-color: {ROW_COLORS[row_name]};"
        )
        image_visible = getattr(
            self,
            "image_action",
            None,
        )
        if (
            character.image_file
            and (image_visible is None or image_visible.isChecked())
        ):
            button.setIcon(
                QIcon(str(Path(__file__).parent / character.image_file))
            )
        else:
            button.setIcon(QIcon())

    def _refresh_enemy_tab(self) -> None:
        if not hasattr(self, "enemy_relation_text"):
            return
        own_ids = self.team_positions
        enemy_ids = self.enemy_positions
        for position in range(TEAM_POSITION_COUNT):
            row_name = (
                "前排" if position < 3
                else "中排" if position < 6
                else "後排"
            )
            own_character = next(
                (
                    character
                    for character in self.characters
                    if character.id == own_ids[position]
                ),
                None,
            )
            enemy_character = next(
                (
                    character
                    for character in self.characters
                    if character.id == enemy_ids[position]
                ),
                None,
            )
            own_visual_index = (
                position % 3 * 3
                + (2 - position // 3)
            )
            self._set_board_button(
                self.enemy_own_buttons[own_visual_index],
                own_character,
                row_name,
            )
            self._set_board_button(
                self.enemy_opponent_buttons[
                    (2 - position % 3) * 3 + position // 3
                ],
                enemy_character,
                row_name,
            )
        enemy_members = [
            character
            for character_id in enemy_ids
            for character in self.characters
            if character.id == character_id
        ]
        abilities = {
            ability
            for character in enemy_members
            for ability in character.special_functions
        }
        controls = sorted(
            {
                ability
                for ability in abilities
                if ability.startswith("控制-")
            },
            key=stroke_sort_key,
        )
        benefits = sorted(
            {
                ability
                for ability in abilities
                if ability.startswith("增益")
            },
            key=stroke_sort_key,
        )
        debuffs = sorted(
            {
                ability
                for ability in abilities
                if ability.startswith("減益")
            },
            key=stroke_sort_key,
        )
        threats = controls + benefits + debuffs
        requirements = counter_requirements(set(threats))
        self.enemy_relation_text.setText(
            "<h3>敵方已知威脅</h3>"
            f"<b>控制：</b>{html.escape('、'.join(controls) or '無')}"
            f"<br><b>增益：</b>{html.escape('、'.join(benefits) or '無')}"
            f"<br><b>減益：</b>{html.escape('、'.join(debuffs) or '無')}"
            "<br><br><b>建議反制需求：</b>"
            f"{html.escape('、'.join(requirements) or '暫無')}"
            "<br><br><b>判讀說明：</b>九宮格會以相同排與列對齊，"
            "方便觀察我方後排、中排、前排與敵方前排、中排、後排的相對位置。"
            "目前不推定刺客突破、守衛或戰士阻擋，也不判定技能實際攻擊範圍；"
            "後續只會使用資料中已有的技能與能力資訊進行反制分析。"
        )

    def _refresh_characters(self) -> None:
        self.filtered_characters = [
            character
            for character in self.characters
            if self.browser_filters.matches(character, self.owned_ids)
        ]
        self.browser_list.owned_ids = self.owned_ids
        self.browser_list.set_characters(self.filtered_characters)
        self.statusBar().showMessage(
            f"符合條件：{len(self.filtered_characters)} / {len(self.characters)} 名角色"
        )

    def _refresh_team_candidates(self) -> None:
        candidates = [
            character
            for character in self.characters
            if self.team_filters.matches(character, self.owned_ids)
        ]
        self.team_candidates.owned_ids = self.owned_ids
        self.team_candidates.set_characters(candidates)

    def _set_character_owned(self, character_id: str, owned: bool) -> None:
        if owned:
            self.owned_ids.add(character_id)
        else:
            self.owned_ids.discard(character_id)
        self._save_owned_settings()
        if (
            self.browser_filters.owned_only.isChecked()
            or self.team_filters.owned_only.isChecked()
        ):
            self._refresh_characters()
            self._refresh_team_candidates()

    def _set_owned_filter(self, enabled: bool) -> None:
        for panel in (self.browser_filters, self.team_filters):
            blocker = QSignalBlocker(panel.owned_only)
            panel.owned_only.setChecked(enabled)
            del blocker
        self._refresh_characters()
        self._refresh_team_candidates()

    def _load_owned_settings(self) -> None:
        stored_profiles = self.settings.value("owned_profiles", "")
        profiles: object = {}
        if isinstance(stored_profiles, str) and stored_profiles:
            try:
                profiles = json.loads(stored_profiles)
            except json.JSONDecodeError:
                profiles = {}
        if isinstance(profiles, dict):
            self.owned_profiles = {
                name: {
                    value
                    for value in values
                    if isinstance(value, str) and value
                }
                for name, values in profiles.items()
                if isinstance(name, str)
                and isinstance(values, list)
            }
        if not self.owned_profiles:
            stored = self.settings.value("owned_character_ids", [])
            if isinstance(stored, str):
                stored = [stored]
            legacy_ids = (
                {
                    value
                    for value in stored
                    if isinstance(value, str) and value
                }
                if isinstance(stored, list)
                else set()
            )
            self.owned_profiles = {DEFAULT_PROFILE_NAME: legacy_ids}
        active = self.settings.value(
            "active_owned_profile",
            DEFAULT_PROFILE_NAME,
        )
        if (
            not isinstance(active, str)
            or active not in self.owned_profiles
        ):
            active = sorted(
                self.owned_profiles,
                key=stroke_sort_key,
            )[0]
        self.active_owned_profile = active
        self.owned_ids = set(self.owned_profiles[active])

    def _save_owned_settings(self) -> None:
        self.owned_profiles[self.active_owned_profile] = set(
            self.owned_ids
        )
        self.settings.setValue(
            "owned_character_ids",
            sorted(self.owned_ids),
        )
        self.settings.setValue(
            "owned_profiles",
            json.dumps(
                {
                    name: sorted(ids)
                    for name, ids in self.owned_profiles.items()
                },
                ensure_ascii=False,
            ),
        )
        self.settings.setValue(
            "active_owned_profile",
            self.active_owned_profile,
        )
        self.settings.sync()

    def _save_owned_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "儲存擁有角色",
            "owned_characters.json",
            "JSON 檔案 (*.json)",
        )
        if not path:
            return
        payload = {
            "version": OWNED_FILE_VERSION,
            "owned_character_ids": sorted(self.owned_ids),
        }
        try:
            Path(path).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            QMessageBox.warning(self, "儲存失敗", str(error))

    def _load_owned_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "載入擁有角色",
            "",
            "JSON 檔案 (*.json)",
        )
        if not path:
            return
        try:
            payload = json.loads(
                Path(path).read_text(encoding="utf-8")
            )
            values = payload.get("owned_character_ids")
            if not isinstance(values, list) or not all(
                isinstance(value, str) for value in values
            ):
                raise ValueError("檔案缺少有效的 owned_character_ids 陣列。")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            QMessageBox.warning(self, "載入失敗", str(error))
            return
        self.owned_ids = {value for value in values if value}
        self._save_owned_settings()
        self._refresh_characters()
        self._refresh_team_candidates()

    def _clear_owned_characters(self) -> None:
        self.owned_ids.clear()
        self._save_owned_settings()
        self._refresh_characters()
        self._refresh_team_candidates()

    def closeEvent(self, event) -> None:
        if self.official_update_thread is not None:
            self.official_update_thread.requestInterruption()
            self.official_update_thread.wait(30000)
        self._save_owned_settings()
        self._save_teams_settings()
        self._save_enemy_settings()
        super().closeEvent(event)

    def _refresh_team_selector(self) -> None:
        self.team_selector.blockSignals(True)
        self.team_selector.clear()
        self.team_selector.addItems(sorted(self.teams, key=stroke_sort_key))
        self.team_selector.setCurrentText(self.active_team_name)
        self.team_selector.blockSignals(False)

    def _switch_team(self, name: str) -> None:
        if not name or name == self.active_team_name:
            return
        self._save_current_team()
        self.active_team_name = name
        self.team_positions = list(self.teams[name])
        self.selected_team_position = None
        self._refresh_team_grid()
        self._refresh_enemy_tab()

    def _new_team(self) -> None:
        name, accepted = QInputDialog.getText(
            self,
            "新增隊伍",
            "請輸入隊伍名稱：",
        )
        name = name.strip()
        if not accepted or not name:
            return
        if name in self.teams:
            QMessageBox.warning(self, "新增失敗", "隊伍名稱已存在。")
            return
        self._save_current_team()
        self.teams[name] = [None] * TEAM_POSITION_COUNT
        self.active_team_name = name
        self.team_positions = list(self.teams[name])
        self._refresh_team_selector()
        self._refresh_team_grid()
        self._save_teams_settings()

    def _rename_team(self) -> None:
        name, accepted = QInputDialog.getText(
            self,
            "重新命名隊伍",
            "請輸入新的隊伍名稱：",
            text=self.active_team_name,
        )
        name = name.strip()
        if not accepted or not name or name == self.active_team_name:
            return
        if name in self.teams:
            QMessageBox.warning(self, "重新命名失敗", "隊伍名稱已存在。")
            return
        self._save_current_team()
        self.teams[name] = self.teams.pop(self.active_team_name)
        self.active_team_name = name
        self._refresh_team_selector()
        self._save_teams_settings()

    def _delete_team(self) -> None:
        if len(self.teams) <= 1:
            QMessageBox.information(
                self,
                "無法刪除",
                "至少要保留一個隊伍。",
            )
            return
        answer = QMessageBox.question(
            self,
            "刪除隊伍",
            f"確定刪除「{self.active_team_name}」？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        del self.teams[self.active_team_name]
        self.active_team_name = sorted(
            self.teams,
            key=stroke_sort_key,
        )[0]
        self.team_positions = list(self.teams[self.active_team_name])
        self.selected_team_position = None
        self._refresh_team_selector()
        self._refresh_team_grid()
        self._save_teams_settings()

    def _save_current_team(self) -> None:
        self.teams[self.active_team_name] = list(self.team_positions)

    def _save_teams_settings(self) -> None:
        self._save_current_team()
        self.settings.setValue(
            "teams",
            json.dumps(
                self.teams,
                ensure_ascii=False,
            ),
        )
        self.settings.setValue("active_team", self.active_team_name)
        self.settings.sync()

    def _load_enemy_settings(self) -> None:
        stored = self.settings.value("enemy_positions", "")
        positions: object = []
        if isinstance(stored, str) and stored:
            try:
                positions = json.loads(stored)
            except json.JSONDecodeError:
                positions = []
        if (
            isinstance(positions, list)
            and len(positions) == TEAM_POSITION_COUNT
        ):
            valid_ids = {character.id for character in self.characters}
            self.enemy_positions = [
                value if value in valid_ids else None
                for value in positions
            ]

    def _save_enemy_settings(self) -> None:
        self.settings.setValue(
            "enemy_positions",
            json.dumps(self.enemy_positions, ensure_ascii=False),
        )
        self.settings.sync()

    def _open_enemy_dialog(self) -> None:
        dialog = EnemyTeamDialog(
            self.characters,
            self.enemy_positions,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        positions = dialog.positions()
        selected_ids = [value for value in positions if value]
        if len(selected_ids) > MAX_TEAM_SIZE:
            QMessageBox.warning(
                self,
                "敵隊輸入失敗",
                f"敵隊最多只能放入 {MAX_TEAM_SIZE} 名角色。",
            )
            return
        if len(set(selected_ids)) != len(selected_ids):
            QMessageBox.warning(
                self,
                "敵隊輸入失敗",
                "同一角色不可重複放入敵隊。",
            )
            return
        self.enemy_positions = positions
        self._save_enemy_settings()
        self._refresh_enemy_tab()

    def _show_enemy_analysis(self) -> None:
        members = [
            character
            for character_id in self.enemy_positions
            for character in self.characters
            if character.id == character_id
        ]
        if not members:
            QMessageBox.information(
                self,
                "敵隊分析",
                "尚未輸入敵隊角色。",
            )
            return
        abilities = {
            ability
            for character in members
            for ability in character.special_functions
        }
        controls = sorted(
            {
                ability
                for ability in abilities
                if ability.startswith("控制-")
            },
            key=stroke_sort_key,
        )
        benefits = sorted(
            {
                ability
                for ability in abilities
                if ability.startswith("增益")
            },
            key=stroke_sort_key,
        )
        debuffs = sorted(
            {
                ability
                for ability in abilities
                if ability.startswith("減益")
            },
            key=stroke_sort_key,
        )
        requirements = counter_requirements(abilities)
        character_text = "、".join(
            f"{character.name}（{character.class_name}）"
            for character in members
        )
        text = (
            f"<b>敵隊角色：</b>{html.escape(character_text)}"
            f"<br><br><b>控制威脅：</b>"
            f"{html.escape('、'.join(controls) or '無')}"
            f"<br><b>增益威脅：</b>"
            f"{html.escape('、'.join(benefits) or '無')}"
            f"<br><b>減益威脅：</b>"
            f"{html.escape('、'.join(debuffs) or '無')}"
            f"<br><b>建議反制需求：</b>"
            f"{html.escape('、'.join(requirements) or '暫無')}"
            "<br><br><b>可用操作：</b>可從敵隊分析分頁開啟推薦隊伍。"
        )
        message = QMessageBox(self)
        message.setWindowTitle("敵隊分析")
        message.setTextFormat(Qt.TextFormat.RichText)
        message.setText(text)
        message.exec()

    def _character_covers(
        self,
        character: Character,
        requirement: str,
    ) -> bool:
        abilities = character.special_functions
        if requirement == "解控":
            return any(
                "解控" in ability or "淨化" in ability
                for ability in abilities
            )
        if requirement == "控制免疫":
            return any(
                "控制免疫" in ability or "免疫控制" in ability
                for ability in abilities
            )
        if requirement == "驅散增益":
            return any(
                "驅散" in ability or "清除增益" in ability
                for ability in abilities
            )
        if requirement == "偷取增益":
            return any("偷取" in ability for ability in abilities)
        if requirement == "淨化":
            return any(
                "淨化" in ability or "驅散" in ability
                for ability in abilities
            )
        if requirement == "驅散":
            return any("驅散" in ability for ability in abilities)
        if requirement == "治療增強":
            return any(
                "治療" in ability or "回復" in ability
                for ability in abilities
            )
        return False

    def _show_team_recommendation(
        self,
        direction: str | None = None,
        existing_dialog: QDialog | None = None,
        existing_browser: QTextBrowser | None = None,
        use_owned_only: bool | None = None,
    ) -> None:
        enemy_members = [
            character
            for character_id in self.enemy_positions
            for character in self.characters
            if character.id == character_id
        ]
        if not enemy_members:
            QMessageBox.information(
                self,
                "推薦隊伍",
                "請先輸入敵隊角色。",
            )
            return
        if direction is None:
            direction, accepted = QInputDialog.getItem(
                self,
                "推薦方向",
                "請選擇推薦方向：",
                ["綜合反制", "輸出優先", "同陣營優先"],
                0,
                False,
            )
            if not accepted:
                return
        if use_owned_only is None:
            use_owned_only = True
        pool = [
            character
            for character in self.characters
            if not use_owned_only or character.id in self.owned_ids
        ]
        if not pool:
            QMessageBox.information(
                self,
                "推薦隊伍",
                "目前沒有符合推薦條件的角色，請先設定已擁有角色，"
                "或關閉「推薦僅使用已擁有角色」。",
            )
            return
        enemy_abilities = {
            ability
            for character in enemy_members
            for ability in character.special_functions
        }
        requirements = counter_requirements(enemy_abilities)
        faction_counts: dict[str, int] = {}
        for character in pool:
            for faction in character.factions:
                faction_counts[faction] = faction_counts.get(faction, 0) + 1
        preferred_faction = (
            sorted(
                faction_counts,
                key=lambda faction: (
                    -faction_counts[faction],
                    stroke_sort_key(faction),
                ),
            )[0]
            if faction_counts
            else ""
        )
        selected: list[Character] = []
        covered: set[str] = set()
        output_class_weight = 3 if direction == "輸出優先" else 2
        output_weight = 2 if direction != "同陣營優先" else 1
        coverage_weight = 3 if direction == "綜合反制" else 2
        faction_weight = 4 if direction == "同陣營優先" else 1
        for _ in range(MAX_TEAM_SIZE):
            candidates = [
                character
                for character in pool
                if character.id not in {item.id for item in selected}
            ]
            if not candidates:
                break
            candidate = max(
                candidates,
                key=lambda character: (
                    int(
                        not any(
                            character_has_output(item)
                            for item in selected
                        )
                        and character.class_name in {"射手", "法師"}
                        and character_has_output(character)
                    ) * output_class_weight,
                    int(
                        not any(
                            character_has_output(item)
                            for item in selected
                        )
                        and character_has_output(character)
                    ) * output_weight,
                    sum(
                        requirement not in covered
                        and self._character_covers(character, requirement)
                        for requirement in requirements
                    ) * coverage_weight,
                    int(preferred_faction in character.factions)
                    * faction_weight,
                    int(character.class_name in {"守衛", "牧師"}),
                    len(character.special_functions),
                    tuple(
                        -value
                        for value in profession_sort_key(
                            character.class_name
                        )[:1]
                    ),
                    character.name,
                ),
            )
            selected.append(candidate)
            covered.update(
                requirement
                for requirement in requirements
                if self._character_covers(candidate, requirement)
            )
        positions: list[str | None] = [None] * TEAM_POSITION_COUNT
        placed: list[Character] = []
        for character in selected:
            position = next(
                (
                    index
                    for index, value in enumerate(positions)
                    if value is None
                    and index in allowed_team_positions(
                        character.class_name
                    )
                ),
                None,
            )
            if position is None:
                continue
            positions[position] = character.id
            placed.append(character)
        if not placed:
            QMessageBox.information(
                self,
                "推薦隊伍",
                "目前擁有角色無法依職業站位規則組成隊伍。",
            )
            return
        names = "、".join(
            f"{character.name}（{character.class_name}）"
            + (
                "【不建議使用】"
                if character.id not in self.owned_ids
                else ""
            )
            for character in placed
        )
        covered_text = "、".join(
            requirement
            for requirement in requirements
            if requirement in covered
        ) or "尚未找到對應能力"
        missing_text = "、".join(
            requirement
            for requirement in requirements
            if requirement not in covered
        ) or "無"
        factions = sorted(
            {
                faction
                for character in placed
                for faction in character.factions
            },
            key=stroke_sort_key,
        )
        faction_text = "、".join(factions) or "無"
        counter_candidates = [
            character
            for character in pool
            if character.id not in {item.id for item in placed}
            and any(
                self._character_covers(character, requirement)
                for requirement in requirements
            )
        ]
        message_html = (
            f"<b>推薦角色：</b>{html.escape(names)}"
            f"<br><br><b>已涵蓋反制需求：</b>"
            f"{html.escape(covered_text)}"
            f"<br><b>尚未涵蓋：</b>{html.escape(missing_text)}"
            f"<br><b>主要陣營：</b>{html.escape(faction_text)}"
            "<br><b>輸出：</b>已優先確保隊伍至少包含輸出角色"
            f"<br><b>推薦方向：</b>{html.escape(direction)}"
            f"<br><b>推薦模式：</b>"
            f"{'僅使用已擁有角色' if use_owned_only else '允許全部角色'}"
            "<br><b>標註說明：</b>未擁有角色標註為不建議使用"
        )
        if existing_browser is not None:
            existing_browser.setHtml(message_html)
            if existing_dialog is not None:
                setattr(existing_dialog, "recommended_positions", positions)
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("推薦隊伍")
        dialog.resize(620, 520)
        setattr(dialog, "recommended_positions", positions)
        layout = QVBoxLayout(dialog)
        owned_checkbox = QCheckBox("推薦僅使用已擁有角色")
        owned_checkbox.setChecked(bool(use_owned_only))
        layout.addWidget(owned_checkbox)
        candidate_list = QListWidget()
        for character in counter_candidates:
            factions = "、".join(character.factions) or "未分類"
            item = QListWidgetItem(
                f"{character.name}（{character.class_name}）"
                f"｜陣營：{factions}"
            )
            item.setData(Qt.ItemDataRole.UserRole, character.id)
            item.setFlags(
                item.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(Qt.CheckState.Unchecked)
            candidate_list.addItem(item)
        layout.addWidget(QLabel("具備反制能力的候選角色（可勾選加入隊伍）："))
        layout.addWidget(candidate_list)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(message_html)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
        )
        buttons.button(
            QDialogButtonBox.StandardButton.Apply
        ).setText("套用到目前隊伍")
        buttons.button(
            QDialogButtonBox.StandardButton.Apply
        ).clicked.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        owned_checkbox.toggled.connect(
            lambda checked: self._show_team_recommendation(
                direction,
                dialog,
                browser,
                checked,
            )
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected_candidate_ids = {
            candidate_list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(candidate_list.count())
            if candidate_list.item(index).checkState()
            == Qt.CheckState.Checked
        }
        apply_characters = [
            character
            for character in counter_candidates
            if character.id in selected_candidate_ids
        ] + placed
        final_positions: list[str | None] = [None] * TEAM_POSITION_COUNT
        for character in apply_characters:
            if any(value == character.id for value in final_positions):
                continue
            position = next(
                (
                    index
                    for index, value in enumerate(final_positions)
                    if value is None
                    and index in allowed_team_positions(character.class_name)
                ),
                None,
            )
            if position is None:
                continue
            final_positions[position] = character.id
            if sum(value is not None for value in final_positions) >= MAX_TEAM_SIZE:
                break
        requested_ids = {
            character.id for character in apply_characters
        }
        placed_ids = {
            character_id
            for character_id in final_positions
            if character_id is not None
        }
        if (
            len(requested_ids) > MAX_TEAM_SIZE
            or placed_ids != requested_ids
        ):
            QMessageBox.warning(
                self,
                "隊伍規則提醒",
                "勾選的反制候選角色與推薦組合無法同時組成合法隊伍。\n"
                f"隊伍最多只能放入 {MAX_TEAM_SIZE} 名角色，且必須符合職業站位限制。\n"
                "本次不會套用隊伍，請減少勾選角色或調整推薦設定。",
            )
            return
        self.team_positions = final_positions
        self.selected_team_position = None
        self._save_current_team()
        self._save_teams_settings()
        self._refresh_team_grid()

    def _load_teams_settings(self) -> None:
        stored = self.settings.value("teams", "")
        teams: object = {}
        if isinstance(stored, str) and stored:
            try:
                teams = json.loads(stored)
            except json.JSONDecodeError:
                teams = {}
        if isinstance(teams, dict):
            self.teams = {
                name: [
                    value if isinstance(value, str) else None
                    for value in positions[:TEAM_POSITION_COUNT]
                ] + [None] * max(
                    0,
                    TEAM_POSITION_COUNT - len(positions),
                )
                for name, positions in teams.items()
                if isinstance(name, str)
                and isinstance(positions, list)
            }
        if not self.teams:
            self.teams = {"隊伍 1": [None] * TEAM_POSITION_COUNT}
        active = self.settings.value("active_team", "隊伍 1")
        if not isinstance(active, str) or active not in self.teams:
            active = sorted(self.teams, key=stroke_sort_key)[0]
        self.active_team_name = active
        self.team_positions = list(self.teams[active])

    def _select_team_position(self, position: int) -> None:
        self.selected_team_position = position
        character_id = self.team_positions[position]
        character = next(
            (
                value
                for value in self.characters
                if value.id == character_id
            ),
            None,
        )
        self.team_details.show_character(character)
        self._refresh_team_grid()

    def _refresh_team_grid(self) -> None:
        for position, button in enumerate(self.team_position_buttons):
            character_id = self.team_positions[position]
            character = next(
                (
                    value
                    for value in self.characters
                    if value.id == character_id
                ),
                None,
            )
            row_name = (
                "前排" if position < 3
                else "中排" if position < 6
                else "後排"
            )
            button.setText(
                f"{row_name}\n{character.name}\n{character.class_name}"
                if character
                else f"{row_name}\n空位"
            )
            button.setToolTip(
                character_tooltip(character)
                if character
                else f"{row_name}\n空位"
            )
            image_visible = getattr(
                self,
                "image_action",
                None,
            )
            if (
                character
                and (image_visible is None or image_visible.isChecked())
                and character.image_file
            ):
                button.setIcon(
                    QIcon(str(Path(__file__).parent / character.image_file))
                )
            else:
                button.setIcon(QIcon())
            selected_style = (
                "border: 3px solid #2980b9;"
                if position == self.selected_team_position
                else ""
            )
            button.setStyleSheet(
                f"background-color: {ROW_COLORS[row_name]};"
                f"{selected_style}"
            )
        if self.selected_team_position is None:
            self.team_position_label.setText("請先選擇九宮格位置")
        else:
            self.team_position_label.setText(
                f"目前選取：第 {self.selected_team_position + 1} 格"
            )
        self._refresh_team_analysis()
        self._refresh_enemy_tab()

    def _refresh_team_analysis(self) -> None:
        if not hasattr(self, "team_analysis"):
            return
        members = [
            character
            for character_id in self.team_positions
            for character in self.characters
            if character.id == character_id
        ]
        role_counts: dict[str, int] = {}
        abilities: set[str] = set()
        for character in members:
            role_counts[character.class_name] = (
                role_counts.get(character.class_name, 0) + 1
            )
            abilities.update(character.special_functions)
        role_text = "、".join(
            f"{role} {role_counts.get(role, 0)}"
            for role in PROFESSION_ORDER
            if role_counts.get(role)
        ) or "尚未配置角色"
        controls = sorted(
            {
                ability
                for ability in abilities
                if ability.startswith("控制-")
            },
            key=stroke_sort_key,
        )
        benefits = sorted(
            {
                ability
                for ability in abilities
                if ability.startswith("增益")
            },
            key=stroke_sort_key,
        )
        debuffs = sorted(
            {
                ability
                for ability in abilities
                if ability.startswith("減益")
            },
            key=stroke_sort_key,
        )
        warnings = []
        if not role_counts.get("守衛"):
            warnings.append("缺少守衛")
        if not role_counts.get("牧師"):
            warnings.append("缺少牧師")
        if len(members) < MAX_TEAM_SIZE:
            warnings.append(f"尚有 {MAX_TEAM_SIZE - len(members)} 個空位")
        warning_text = "；".join(warnings) or "無"
        self.team_analysis.setText(
            "<h3>基本配置</h3>"
            f"<b>人數：</b>{len(members)} / {MAX_TEAM_SIZE}"
            f"<br><b>職業：</b>{html.escape(role_text)}"
            "<h3>我方能力</h3>"
            f"<b>控制：</b>{html.escape('、'.join(controls) or '無')}"
            f"<br><b>增益：</b>{html.escape('、'.join(benefits) or '無')}"
            f"<br><b>減益：</b>{html.escape('、'.join(debuffs) or '無')}"
            f"<h3>配置提醒</h3><b>"
            f"{html.escape(warning_text)}</b>"
        )

    def _add_selected_to_team(self) -> None:
        character = self.team_candidates.current_character()
        if character is None:
            return
        if character.id in self.team_positions:
            return
        position = self.selected_team_position
        if position is None:
            position = next(
                (
                    index
                    for index, value in enumerate(self.team_positions)
                    if value is None
                    and index in allowed_team_positions(character.class_name)
                ),
                None,
            )
        if position is None:
            QMessageBox.information(
                self,
                "無可用位置",
                "請選擇符合職業限制的空位。",
            )
            return
        if (
            sum(value is not None for value in self.team_positions)
            >= MAX_TEAM_SIZE
        ):
            QMessageBox.information(
                self,
                "隊伍已滿",
                f"隊伍最多只能放入 {MAX_TEAM_SIZE} 名角色。",
            )
            return
        if self.team_positions[position] is not None:
            QMessageBox.information(self, "位置已有角色", "請先選擇空位。")
            return
        if position not in allowed_team_positions(character.class_name):
            QMessageBox.information(
                self,
                "站位不符合",
                f"{character.class_name}不能站在這個位置。",
            )
            return
        self.team_positions[position] = character.id
        self.selected_team_position = None
        self._save_teams_settings()
        self._refresh_team_grid()

    def _remove_selected_from_team(self) -> None:
        if self.selected_team_position is None:
            return
        self.team_positions[self.selected_team_position] = None
        self.selected_team_position = None
        self._save_teams_settings()
        self._refresh_team_grid()

    def _clear_team(self) -> None:
        self.team_positions = [None] * TEAM_POSITION_COUNT
        self.selected_team_position = None
        self._save_teams_settings()
        self._refresh_team_grid()

    def _save_team_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出隊伍",
            "teams.json",
            "JSON 檔案 (*.json)",
        )
        if not path:
            return
        self._save_current_team()
        payload = {
            "version": TEAM_FILE_VERSION,
            "active_team": self.active_team_name,
            "teams": self.teams,
        }
        try:
            Path(path).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            QMessageBox.warning(self, "匯出失敗", str(error))

    def _load_team_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "匯入隊伍",
            "",
            "JSON 檔案 (*.json)",
        )
        if not path:
            return
        try:
            payload = json.loads(
                Path(path).read_text(encoding="utf-8")
            )
            raw_teams = payload.get("teams")
            if not isinstance(raw_teams, dict) or not raw_teams:
                raise ValueError("檔案缺少有效的 teams 資料。")
            valid_ids = {character.id for character in self.characters}
            loaded_teams: dict[str, list[str | None]] = {}
            for name, positions in raw_teams.items():
                if (
                    not isinstance(name, str)
                    or not name
                    or not isinstance(positions, list)
                    or len(positions) != TEAM_POSITION_COUNT
                    or any(
                        value is not None
                        and (
                            not isinstance(value, str)
                            or value not in valid_ids
                        )
                        for value in positions
                    )
                ):
                    raise ValueError("檔案包含無效的隊伍或角色位置。")
                if len({value for value in positions if value}) > MAX_TEAM_SIZE:
                    raise ValueError("單支隊伍不可超過六名角色。")
                loaded_teams[name] = positions
            active = payload.get("active_team")
            if not isinstance(active, str) or active not in loaded_teams:
                active = sorted(
                    loaded_teams,
                    key=stroke_sort_key,
                )[0]
        except (OSError, json.JSONDecodeError, ValueError) as error:
            QMessageBox.warning(self, "匯入失敗", str(error))
            return
        self.teams = loaded_teams
        self.active_team_name = active
        self.team_positions = list(self.teams[active])
        self.selected_team_position = None
        self._refresh_team_selector()
        self._refresh_team_grid()
        self.team_details.show_character(None)
        self._save_teams_settings()


def main() -> int:
    app = QApplication(sys.argv)
    character_paths = []
    if USER_CHARACTERS_PATH.exists():
        character_paths.append(USER_CHARACTERS_PATH)
        character_paths.extend(
            sorted(
                CHARACTER_BACKUP_DIR.glob("characters_*.json"),
                reverse=True,
            )
        )
    character_paths.append(DATA_PATH)
    characters = None
    for character_path in character_paths:
        try:
            characters = load_characters(character_path)
            break
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    if characters is None:
        QMessageBox.critical(
            None,
            "角色資料載入失敗",
            "無法載入內建或使用者角色資料，程式即將結束。",
        )
        return 1
    window = MainWindow(characters)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
