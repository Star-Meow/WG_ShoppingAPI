# 購物車結算系統(WisdomGarden Dev 面試題 MVP)

電商購物車,最終依「促銷折扣」與「優惠券」計算結算金額。

## 目前完成範圍

- 商品目錄:4 個品類、共 18 項商品
- `GET /api/products`:依品類分組回傳商品(價格為字串)
- 前端商品瀏覽頁 `http://127.0.0.1:8000/`
- 自動化測試(pytest)

尚未實作(已建立空殼,未含邏輯):購物車、促銷折扣、優惠券、結算、後台管理、CLI。

## 環境設定

### 1. 建立虛擬環境

macOS / Linux:

```bash
python3 -m venv .venv
```

Windows:

```powershell
python -m venv .venv
```

### 2. 啟用虛擬環境

macOS / Linux:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. 安裝依賴

開發環境(含測試工具):

```bash
pip install -r requirements-dev.txt
```

僅執行環境:

```bash
pip install -r requirements.txt
```

## 啟動伺服器

```bash
uvicorn cart.main:app --reload --app-dir src
```

啟動後可開啟:

- 商品瀏覽頁:<http://127.0.0.1:8000/>
- API 文件:<http://127.0.0.1:8000/docs>
- 商品 API:<http://127.0.0.1:8000/api/products>

## 執行測試

```bash
pytest
```

## 目錄結構

```
shopping_cart/
├── docs/              # 需求與架構文件
├── data/              # 資料檔(seed.json)
├── src/cart/
│   ├── main.py        # FastAPI 進入點
│   ├── config.py      # 路徑設定
│   ├── domain/        # 領域層:目錄、模型、錯誤(不依賴任何 web 模組)
│   ├── services/      # 服務層:結算流程
│   ├── repository/    # 檔案讀寫(唯一碰檔案的地方)
│   ├── api/           # API 層:schema、router(極薄)
│   ├── cli/           # 命令列工具與文字解析
│   └── web/           # 前端靜態檔(純 HTML + 原生 JS)
└── tests/             # 單元測試與 API 測試
```

分層與依賴方向、程式風格規則詳見 [docs/architecture.md](docs/architecture.md);
已確認的業務規則詳見 [docs/requirements.md](docs/requirements.md)。
