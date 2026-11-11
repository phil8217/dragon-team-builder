"""PySide6 桌面介面。"""

from __future__ import annotations

import sys
import html
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QUrl, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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
)

from .data_loader import load_characters
from .models import Character
from .factions import faction_info
from .mechanics import MECHANICS
from .professions import profession_info


DATA_PATH = Path(__file__).parent / "data" / "characters.json"
MAX_TEAM_SIZE = 6


def needs_skill_review(character: Character) -> bool:
    """判斷角色是否有技能資料待補或仍含英文描述。"""

    if not character.skills:
        return True
    if not any(skill.skill_type == "天賦" for skill in character.skills):
        return True
    return any(
        any(char.isascii() and char.isalpha() for char in skill.description)
        for skill in character.skills
    )


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


class FilterPanel(QGroupBox):
    """角色篩選條件面板。"""

    filter_changed = Signal()

    def __init__(self, characters: list[Character]) -> None:
        super().__init__("篩選條件")
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜尋角色名稱或暱稱")
        self.faction = QComboBox()
        self.class_name = QComboBox()
        self.quality = QComboBox()
        self.function = QComboBox()
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
            tag for character in characters for tag in character.skill_tags
        }
        self._fill_combo(
            self.function,
            "全部特殊功能",
            {
                function
                for character in characters
                for function in character.special_functions
            },
        )

        form = QFormLayout(self)
        form.addRow("關鍵字", self.search)
        form.addRow("陣營", self.faction)
        form.addRow("職業", self.class_name)
        form.addRow("品質", self.quality)
        form.addRow("技能", skill_container)
        form.addRow("功能", self.function)
        add_skill_button = QPushButton("＋新增技能篩選")
        add_skill_button.clicked.connect(self.add_skill_filter)
        form.addRow("", add_skill_button)

        for widget in (
            self.search,
            self.faction,
            self.class_name,
            self.quality,
            self.function,
        ):
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._emit_changed)
            else:
                widget.currentTextChanged.connect(self._emit_changed)
        self.add_skill_filter()

    def add_skill_filter(self) -> None:
        """新增一個技能效果條件。"""

        row = QHBoxLayout()
        combo = QComboBox()
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

    def matches(self, character: Character) -> bool:
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
        if any(tag not in character.skill_tags for tag in selected_skills):
            return False
        if (
            self.function.currentIndex()
            and self.function.currentText() not in character.special_functions
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
        layout.addWidget(self.text)

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
            self.text.setHtml("<p>請選擇角色查看詳細資料。</p>")
            return

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
            description = html.escape(skill.description).replace("\n", "<br>")
            for mechanic in MECHANICS:
                description = description.replace(
                    mechanic,
                    f'<a href="mechanic:{mechanic}" '
                    f'title="點擊查看{mechanic}說明">{mechanic}</a>',
                )
            skill_type_colors = {
                "天賦": "#c0392b",
                "奧義": "#8e44ad",
                "絕技": "#d35400",
                "秘技": "#2471a3",
                "特技": "#16805c",
            }
            skill_type = html.escape(skill.skill_type or "技能")
            skill_type_color = skill_type_colors.get(skill.skill_type, "#555555")
            sections.append(
                f"<h3>{html.escape(skill.name)} "
                f'<span style="font-size: inherit; color: {skill_type_color};">'
                f"{skill_type}：</span>{tags}</h3>"
                f'<p style="color: #202020;">{description}</p>'
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

    def set_characters(self, characters: list[Character]) -> None:
        self.clear()
        for character in characters:
            review_marker = "  [技能待補]" if needs_skill_review(character) else ""
            item = QListWidgetItem(
                f"{character.name}  [{character.class_name}] "
                f"{character.quality or '未確認'}{review_marker}"
            )
            item.setIcon(profession_icon(character.class_name))
            item.setData(Qt.ItemDataRole.UserRole, character)
            if needs_skill_review(character):
                item.setToolTip(
                    "此角色有缺少技能資料，或技能描述仍含英文，請補充資料。"
                )
            self.addItem(item)

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
        self.setWindowTitle("龍魂旅人角色與隊伍組成器")
        self.resize(1280, 800)
        self._build_ui()
        self._refresh_characters()

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_browser_tab(), "角色瀏覽器")
        tabs.addTab(self._build_team_tab(), "隊伍組成器")
        self.setCentralWidget(tabs)
        self._refresh_team_candidates()
        self.statusBar().showMessage(f"已載入 {len(self.characters)} 名角色")

    def _build_browser_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.browser_filters = FilterPanel(self.characters)
        self.browser_filters.filter_changed.connect(self._refresh_characters)
        self.browser_list = CharacterList()
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

        self.team_filters = FilterPanel(self.characters)
        self.team_filters.filter_changed.connect(self._refresh_team_candidates)
        self.team_candidates = CharacterList()
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
            if self.browser_filters.matches(character)
        ]
        self.browser_list.set_characters(self.filtered_characters)
        self.statusBar().showMessage(
            f"符合條件：{len(self.filtered_characters)} / {len(self.characters)} 名角色"
        )

    def _refresh_team_candidates(self) -> None:
        candidates = [
            character
            for character in self.characters
            if self.team_filters.matches(character)
        ]
        self.team_candidates.set_characters(candidates)

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
