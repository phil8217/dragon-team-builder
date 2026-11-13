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

## 網頁版

網頁版位於 [web/](./web/)，採用不需要後端的靜態網頁架構，可部署至 GitHub Pages，
並以桌面版的工具列與分頁操作為介面規格：

- 角色瀏覽器三欄配置、關鍵字／陣營／職業／品質／技能／元素機制篩選
- 擁有角色管理、匯入／匯出、只顯示已擁有角色與圖片顯示開關
- 隊伍組成器候選清單、九宮格、多隊伍與隊伍分析
- 敵隊分析雙九宮格、反制需求與推薦隊伍
- 台服官方更新公告清單
- 角色資料與隊伍資料保存於瀏覽器 LocalStorage

本機預覽：

```powershell
python -m http.server 8000
```

然後開啟 `http://localhost:8000/web/`。GitHub Pages 部署設定位於
[.github/workflows/deploy-pages.yml](./.github/workflows/deploy-pages.yml)；
第一次部署前，請在 GitHub repository 的 Pages 設定將來源設為 `GitHub Actions`。

網頁版資料與桌面版目前由同一份角色資料產生。台服官方公告由
[update-official-notices.yml](./.github/workflows/update-official-notices.yml) 每日台灣時間
上午 9 點抓取官方公告首頁與第二頁；有公告資料變更時，GitHub Actions 會自動提交
公告清單、角色資料與資料版本，提交 `web/data/official_maintenance_notices.json`、
`web/data/characters.json` 與 `web/data/data_version.json`，並重新部署 GitHub Pages。也可以在
GitHub repository 的 Actions 頁面手動執行這個 workflow。瀏覽器本身不直接抓取官方網站，
避免跨來源限制與靜態頁面無法安全保存更新資料的問題。
公告更新 workflow 完成後，部署 workflow 會透過 `workflow_run` 事件重新發布網頁，
避免 GitHub Actions 使用 `GITHUB_TOKEN` 提交的變更無法再次觸發一般 push workflow。
資料來源頁面會顯示官網上次檢查時間，格式為台灣時間 `YYYY-MM-DD HH:MM:SS`。
