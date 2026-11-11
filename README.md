# Dragon Team Builder

《龍魂旅人》台服角色資料與隊伍組成工具。

## 功能

- 角色瀏覽與搜尋
- 陣營、職業、品質、功能與多條件技能篩選
- 最多 6 人隊伍組成
- 角色圖片、陣營標誌與職業圖示
- 技能類型與元素機制說明
- GameKee、TapTap 與台服公告資料匯入工具

## 執行

需要 Python 3.11、PySide6：

```powershell
python -m pip install -e .
python -m dragon_team_builder
```

Windows 執行檔會在 GitHub Releases 提供。

## 資料更新

```powershell
python .\tools\import_guide_csv.py
python .\tools\import_dragoncompanion.py
python .\tools\import_gamekee_skills.py
python .\tools\import_taptap_skills.py
```

角色資料位於 `src/dragon_team_builder/data/characters.json`。匯入前請先備份資料檔，並確認來源內容完整。

## 資料來源

- 台服官方公告：https://sod.game-beans.com/jx/sodNotice/index.html
- GameKee：https://www.gamekee.com/lhlr/
- TapTap：https://www.taptap.cn/
- Dragon Companion：https://www.dragoncompanion.com/

## 建置

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name DragonTeamBuilder `
  --paths .\src `
  --add-data ".\src\dragon_team_builder\data;dragon_team_builder\data" `
  .\src\dragon_team_builder\__main__.py
```

