## 概要
**PlaceDetection** は、DynamoDB に保存されたタグ位置情報を取得し、在席状況やエリア滞在傾向を可視化するためのツール群です。

利用者は、基本的に以下の流れでツールを実行します。
- **データ取得 → 電圧確認 → 一次処理＆NFC比較 → 在席トレンド分析 → 1/HHI分析**
- 必要に応じて、**時刻別在席エリア推移** や **特定タグのみの抽出** も行えます。


## 事前準備
- **Python** がインストールされていること（動作確認済み: Python 3.12 系）
- このフォルダ（`PlaceDetection`）を作業用フォルダとして使用してください。
- コマンドは、特に断りがない限り **`PlaceDetection` フォルダ直下** で実行します。

※ 開発者向けの詳細な環境構築手順（仮想環境など）は別途管理とし、本書では操作手順のみを記載します。


## フォルダと主なファイル
- `get_dynamo_data.py`：DynamoDB から生データを取得し、`processed_tag_data.csv` を作成
- `discover_tag_volt.py`：各タグの最新電圧を集計し、`tag_voltages_latest.csv` を作成
- `analyze_closest_nodeANDexcel.py`：5分ごとの最強RSSIノードを算出し、一次分析結果と比較グラフを作成
- `totalling.py`：在席トレンドや部門別集計グラフを作成
- `hhi_reverse/make_csv.py`：1/HHI（有効拠点数）の各種 CSV を作成
- `hhi_reverse/make_graph.py`：1/HHI の分布・働き方タイプのグラフを作成
- `stay_area/main.py`：時刻別の在席エリア推移グラフを作成
- `tag_select/main.py`：特定タグのデータだけを抽出して CSV 出力

関連する入力ファイル（同一フォルダに配置）
- `processed_tag_data.csv`：DynamoDB から取得した生データ（本ツールの中心となる元データ）
- `tag_names.csv`：タグIDと氏名・部門の対応表
- `node_names.csv`：ノードIDと座席位置・フロア情報の対応表
- `data/辻アプリ_20260203.xlsx`：NFC（予約アプリ）の在席データ
- `input/～.csv`：月ごとなどに分けた `processed_tag_data` のコピー


## 全体の流れ
1. **DynamoDB から生データを取得**（`get_dynamo_data.py`）  
2. **タグ電圧の確認**（`discover_tag_volt.py`）  
3. **一次処理＆NFC比較グラフの作成**（`analyze_closest_nodeANDexcel.py`）  
4. **在席トレンド（部門・人物別）の集計**（`totalling.py`）  
5. **1/HHI（有効拠点数）の集計・グラフ作成**（`hhi_reverse/make_csv.py`, `hhi_reverse/make_graph.py`）  
6. （任意）**時刻別在席エリア推移**（`stay_area/main.py`）  
7. （任意）**特定タグのみ抽出**（`tag_select/main.py`）  

以下、各ステップの詳細です。


## 1. データ取得（DynamoDB → processed_tag_data.csv）

- **目的**：DynamoDB（`mmms_rowdata` テーブル）から指定期間・物件のデータを取得し、解析しやすい形に整形した `processed_tag_data.csv` を作成します。

### 実行コマンド
```bash
python get_dynamo_data.py
```

### 実行前に確認する設定
`get_dynamo_data.py` 冒頭の設定を、取得したい条件に合わせて編集します。
- **TABLE_NAME**：通常は `mmms_rowdata`
- **PK_VALUE**：物件（例：`'tama_b'`）
- **START_DATETIME / END_DATETIME**：取得したい期間（`YYYY/MM/DD HH:MM:SS.mmm` 形式）
- **OUTPUT_CSV_FILE**：通常は `processed_tag_data.csv`

※ `.env` ファイルに AWS 認証情報（`AWS_ACCESS_KEY_ID` など）が設定されている必要があります。

### 実行結果
- カレントフォルダに **`processed_tag_data.csv`** が作成されます。
- 形式：`datetime`, `node_id`, `tag_id`, `tag_rssi`, `tag_volt`

### 重要な運用上の注意
- **膨大なデータになるため、すでに取得済みの期間は再取得しないでください。**
- 期間を分けて取得する場合は、`START_DATETIME` / `END_DATETIME` を変更し、
  - 例：`processed_tag_data_2025-01.csv` のようにファイル名を変えて保存し、
  - それを後述の `input` フォルダ内のファイルとして利用します。
- `processed_tag_data.csv` を **月ごとなどにコピーして**、`input` フォルダに配置してください。


## 2. 電圧確認（各タグの最新電圧一覧）

- **目的**：`processed_tag_data.csv` の中から、各タグの最新時点の電圧（`tag_volt`）を集計します。

### 必要ファイル
- `processed_tag_data.csv`
- `tag_names.csv`（タグIDと人名・部門の対応表）

### 実行コマンド
```bash
python discover_tag_volt.py
```

### 処理内容
- `processed_tag_data.csv` の `datetime` 列をもとに、**タグごとに最新の1行**を抽出します。
- `tag_names.csv` と突き合わせ、名前情報を付与します。

### 実行結果
- **`tag_voltages_latest.csv`** が作成されます。
- 各行は「タグごとの最新日時と電圧」を示しており、電池交換の判断に利用できます。


## 3. 分析1：一次処理と NFC 比較（5分ごとの最強RSSI）

- **目的**：数か月分の `processed_tag_data_*.csv` を連結し、5分ごとに「そのタグにとって最もRSSIが強いノード」を選び、
  - 一次分析データ **`closest_node_per_interval_with_names.csv`** を作成
  - NFC（予約データ）と比較するグラフを作成

### 事前準備
1. `input` フォルダに、対象期間ごとの CSV を配置します  
   - 例：`input/processed_tag_data_Sep.csv`, `input/processed_tag_data_Oct.csv` … など
2. `analyze_closest_nodeANDexcel.py` 冒頭の **`INPUT_FILES_TO_CONCAT`** に、使用したいファイル名を列挙します。
3. `node_names.csv`（ノードIDと座席情報）、`tag_names.csv`（タグIDと氏名・部門）を同一フォルダに配置します。
4. `data/辻アプリ_20260203.xlsx` を `data` フォルダに配置します（NFC データ）。

### 実行コマンド
```bash
python analyze_closest_nodeANDexcel.py
```

### 主な処理
- `input` フォルダ内の指定 CSV を読み込み・連結
- `TIME_INTERVAL_MINUTES`（デフォルト 5分）ごとにグルーピング
- 各タグ・各時間帯で **最も RSSI が強いノード** を 1つ選択
- `node_names.csv` を参照して座席名・フロア情報を付与
- `tag_names.csv` を参照して人名・部門を付与（「所属なし」は自動で除外）
- 一次分析結果を **`closest_node_per_interval_with_names.csv`** として保存
- `data/辻アプリ_20260203.xlsx` を読み込み、NFC の滞在データを同じ時間粒度に変換し、
  - 上段：タグ移動履歴（センサーデータ）
  - 下段：NFC 予約データの滞在履歴  
  の比較グラフを作成します。

### 実行結果
- **`closest_node_per_interval_with_names.csv`**  
  （以降の処理の基本データとして使用）
- 比較グラフ画像（ファイル名：`tag_movement_comparison_graph.png`）


## 4. 分析2：在席トレンド（部門別・人物別）

- **目的**：`closest_node_per_interval_with_names.csv` をもとに、
  - 人別・部門別の **滞在エリア割合 / 滞在時間** を集計
  - 日別・週別・月別の **部門別トレンド** をグラフ化

### 必要ファイル
- `closest_node_per_interval_with_names.csv`

### 実行コマンド
```bash
python totalling.py
```

### 主な設定（必要に応じて変更）
- `TAGS_TO_EXCLUDE`：分析対象から除外したいタグIDのリスト  
  （来客用タグやテスト用タグなどをここに指定すると集計から外れます）

### 実行結果
すべて `output_files` フォルダに PNG として出力されます。
- **全体集計**
  - `overall_person_percentage.png`：人物別・エリア滞在割合
  - `overall_person_duration.png`：人物別・滞在時間
  - `overall_dept_percentage.png`：部門別・エリア滞在割合
  - `overall_dept_duration.png`：部門別・滞在時間
- **トレンド（部門別）**
  - `trends_日別_percentage.png` / `trends_日別_duration.png`
  - `trends_週別_percentage.png` / `trends_週別_duration.png`
  - `trends_月別_percentage.png` / `trends_月別_duration.png`


## 5. 分析3：1/HHI（有効拠点数）の算出とグラフ

### 5-1. CSV 作成（1/HHI の集計）

- **目的**：`closest_node_per_interval_with_names.csv` から、
  - 日次・週次・月次ごとの **1/HHI（有効拠点数）** を算出し、CSV にまとめます。

### 実行場所とコマンド
1. `hhi_reverse` フォルダに移動
   ```bash
   cd hhi_reverse
   ```
2. CSV 作成スクリプトを実行
   ```bash
   python make_csv.py
   ```

### 実行結果
- `hhi_reverse` フォルダ内に以下の CSV が生成されます。
  - `effective_locations_daily.csv`
  - `effective_locations_weekly.csv`
  - `effective_locations_monthly.csv`

いずれも、タグごとに「エリア単位・フロア単位の有効拠点数」などが集計されています。


### 5-2. グラフ作成（分布・働き方タイプ）

- **目的**：上記 CSV をもとに、
  - 日・週・月ごとの有効拠点数分布
  - 働き方タイプ（活動量 vs テリトリー）の散布図や、日→週→月の変化を表すダンベルチャート
  を作成します。

### 実行コマンド（`hhi_reverse` フォルダ内）
```bash
python make_graph.py
```

### 実行結果（`hhi_reverse` フォルダ内に出力）
- `graph1_daily_distribution.png`：日次の有効拠点数分布（箱ひげ図）
- `graph1_weekly_distribution.png`：週次の分布
- `graph1_monthly_distribution.png`：月次の分布
- `graph3_workstyle_scatter.png`：働き方タイプマップ（散布図）
- `graph4_dumbbell_3points.png`：日→週→月の有効拠点数の変化（ダンベルチャート）


## 6. その他の分析ツール

### 6-1. 時刻別在席エリア推移（`stay_area/main.py`）

- **目的**：時間帯ごとの各エリアの滞在人数の推移を可視化します。

#### 必要ファイル
- `closest_node_per_interval_with_names.csv`

#### 実行コマンド
```bash
python stay_area/main.py
```

#### 実行結果
- `stay_area/area_occupancy_trend.png`  
  - X軸：時刻  
  - Y軸：滞在人数  
  - 線の色：エリア（`place_name`）


### 6-2. 特定タグのみ抽出（`tag_select/main.py`）

- **目的**：`processed_tag_data.csv` から、特定の `tag_id` のデータだけを抜き出します。

#### 必要ファイル
- `processed_tag_data.csv`

#### 抽出対象タグの変更方法
- `tag_select/main.py` 内の以下行を、抽出したいタグIDに書き換えます。
  - `target_id = '0081f986054d'`

#### 実行コマンド
```bash
python tag_select/main.py
```

#### 実行結果
- `tag_select/output.csv`  
  - 指定した `tag_id` の行だけが格納された CSV が出力されます。


## 運用上のヒント・注意点
- **期間の重複取得に注意**：`get_dynamo_data.py` で同じ期間を何度も取得すると、不要な重複データが増えます。未取得期間のみを狙って指定してください。
- **ファイル名で期間を管理**：`processed_tag_data_YYYYMM.csv` のように月ごとのファイル名にしておくと、`input` フォルダに並べる際に分かりやすくなります。
- **除外タグの設定**：在席トレンド分析（`totalling.py`）では、`TAGS_TO_EXCLUDE` に来客用やテスト用タグを入れておくと、集計結果のノイズを減らせます。
- **入力ファイルの所在**：エラーが出た場合は、スクリプト内で指定されているファイル名・フォルダ名（`input`, `data`, `hhi_reverse` など）に、必要な CSV / Excel が存在するか確認してください。