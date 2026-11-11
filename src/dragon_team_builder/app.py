"""PySide6 桌面介面。"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

from PySide6.QtCore import (
    Qt,
    Signal,
    QUrl,
    QSize,
    QSignalBlocker,
    QSettings,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QComboBox,
    QFileDialog,
    QFormLayout,
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
    QToolBar,
)

from .data_loader import load_characters
from .models import Character, Skill
from .factions import faction_info
from .mechanics import ELEMENTAL_MECHANICS, MECHANICS
from .professions import profession_info


DATA_PATH = Path(__file__).parent / "data" / "characters.json"
MAX_TEAM_SIZE = 6
OWNED_FILE_VERSION = 1
REQUIRED_SKILL_TYPES = ("天賦", "奧義", "絕技", "秘技", "特技")


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
    def _fill_combo(combo: QComboBox, first: str, values: set[str]) -> None:
        combo.addItem(first)
        combo.addItems(sorted(value for value in values if value))

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
        self.search.setPlaceholderText("搜尋目前角色的技能、能力或詳細敘述")
        self.search.textChanged.connect(self._find_text)
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

    def _find_text(self, text: str) -> None:
        """在目前角色詳細資料中尋找文字。"""

        self.text.moveCursor(QTextCursor.MoveOperation.Start)
        if text.strip():
            self.text.find(text.strip())

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
        if character.source:
            sections.append(
                f'<p><small>角色資料來源：'
                f'<a href="{character.source.url}">{character.source.title}</a>'
                f"</small></p>"
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
        for character in characters:
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


class MainWindow(QMainWindow):
    """角色資料與隊伍組成主視窗。"""

    def __init__(self, characters: list[Character]) -> None:
        super().__init__()
        self.characters = characters
        self.filtered_characters: list[Character] = []
        self.team: list[Character] = []
        self.owned_ids: set[str] = set()
        self.settings = QSettings("DragonTeamBuilder", "DragonTeamBuilder")
        self._load_owned_settings()
        self.setWindowTitle("龍魂旅人角色與隊伍組成器")
        self.resize(1280, 800)
        self._build_ui()
        self._refresh_characters()

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_browser_tab(), "角色瀏覽器")
        tabs.addTab(self._build_team_tab(), "隊伍組成器")
        self.setCentralWidget(tabs)
        self._build_toolbar()
        self._refresh_team_candidates()
        self.statusBar().showMessage(f"已載入 {len(self.characters)} 名角色")

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("角色工具")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.owned_filter_action = QAction("只顯示已擁有角色", self)
        self.owned_filter_action.setCheckable(True)
        self.owned_filter_action.toggled.connect(self._set_owned_filter)
        toolbar.addAction(self.owned_filter_action)

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

        team_panel = QGroupBox(f"目前隊伍（最多 {MAX_TEAM_SIZE} 人）")
        team_layout = QVBoxLayout(team_panel)
        self.team_list = QListWidget()
        team_layout.addWidget(self.team_list)
        remove_button = QPushButton("移除選取角色")
        remove_button.clicked.connect(self._remove_selected_from_team)
        clear_button = QPushButton("清空隊伍")
        clear_button.clicked.connect(self._clear_team)
        team_layout.addWidget(remove_button)
        team_layout.addWidget(clear_button)

        splitter.addWidget(candidate_panel)
        splitter.addWidget(self.team_details)
        splitter.addWidget(team_panel)
        splitter.setSizes([360, 570, 280])
        layout.addWidget(splitter)
        return tab

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
        if self.owned_filter_action.isChecked():
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
        stored = self.settings.value("owned_character_ids", [])
        if isinstance(stored, str):
            stored = [stored]
        if isinstance(stored, list):
            self.owned_ids = {
                value for value in stored if isinstance(value, str) and value
            }

    def _save_owned_settings(self) -> None:
        self.settings.setValue(
            "owned_character_ids",
            sorted(self.owned_ids),
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
        self._save_owned_settings()
        super().closeEvent(event)

    def _add_selected_to_team(self) -> None:
        character = self.team_candidates.current_character()
        if character is None:
            return
        if any(member.id == character.id for member in self.team):
            return
        if len(self.team) >= MAX_TEAM_SIZE:
            QMessageBox.information(
                self,
                "隊伍已滿",
                f"隊伍最多只能放入 {MAX_TEAM_SIZE} 名角色。",
            )
            return
        self.team.append(character)
        self.team_list.addItem(character.name)

    def _remove_selected_from_team(self) -> None:
        row = self.team_list.currentRow()
        if row < 0:
            return
        self.team.pop(row)
        self.team_list.takeItem(row)

    def _clear_team(self) -> None:
        self.team.clear()
        self.team_list.clear()


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow(load_characters(DATA_PATH))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
