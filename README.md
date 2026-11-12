# Dragon Team Builder

《龍魂旅人》台服角色資料與隊伍組成工具。

## 功能

- 角色瀏覽與搜尋
- 陣營、職業、品質與「技能、能力」多條件篩選
- 最多 6 人隊伍組成
- 角色圖片、陣營標誌與職業圖示
- 技能類型與元素機制說明
- 技能狀態、控制效果與元素反應可點擊查看說明
- 技能描述中的技能名稱自動依技能類型上色
- 可勾選擁有的角色，並只用擁有角色篩選隊伍候選
- 技能、能力下拉選單支援文字搜尋
- 詳細資料支援搜尋目前角色的技能與敘述
- 工具列可儲存與載入擁有角色清單
- GameKee、TapTap 與台服公告資料匯入工具
- 台服官方公告每日檢查與角色資料自動更新，更新前會建立本機備份

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

執行檔執行時，使用者更新後的角色資料會保存於：

```text
%LOCALAPPDATA%\DragonTeamBuilder\data\
```

自動更新前的角色資料備份會保存於該目錄下的 `backups` 子目錄。

## 資料來源

- 台服官方公告：https://sod.game-beans.com/jx/sodNotice/index.html
- GameKee：https://www.gamekee.com/lhlr/
- TapTap：https://www.taptap.cn/
- Dragon Companion：https://www.dragoncompanion.com/

## 建置

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name DragonTeamBuilder `
  --distpath . `
  --paths .\src `
  --add-data ".\src\dragon_team_builder\data;dragon_team_builder\data" `
  .\src\dragon_team_builder\__main__.py
```
