import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging

# ----------------------------------------------------------------------
# 設定項目 (解析・グラフ化したい条件に合わせてここを編集してください)
# ----------------------------------------------------------------------

# 1. 解析の入力ファイル (加工前のデータ)
INPUT_CSV_FILE = 'processed_tag_data.csv'

# 2. 解析結果を出力するCSVファイル
ANALYZED_CSV_FILE = 'closest_node_per_interval.csv'

# 3. グラフの画像ファイル名
OUTPUT_IMAGE_FILE = 'tag_movement_graph.png'

# 4. 集計する時間間隔（分）
TIME_INTERVAL_MINUTES = 10

# 5.【重要】グラフに表示したいtag_idをリストで指定します。
#   タグが多いとグラフが非常に見づらくなるため、見たいタグに絞ってください。
TAGS_TO_PLOT = [
    '0081f9860662',
    '0081f986053f',
    '0081f98602f6'
]

# ----------------------------------------------------------------------

# ログ設定
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    """
    メイン処理：データ解析、CSV保存、グラフ描画を連続して実行します。
    """

    # ==================================================================
    # STEP 1: 5分ごとの最強RSSIデータを抽出し、CSVに保存
    # ==================================================================
    try:
        logging.info(f"STEP 1: '{INPUT_CSV_FILE}' を読み込んで解析を開始します...")
        df = pd.read_csv(INPUT_CSV_FILE, parse_dates=['datetime'])
    except FileNotFoundError:
        logging.error(f"エラー: 入力ファイル '{INPUT_CSV_FILE}' が見つかりません。処理を中断します。")
        return

    # 時間間隔とtag_idでグループ化し、各グループでtag_rssiが最大の行を抽出
    grouper = pd.Grouper(key='datetime', freq=f'{TIME_INTERVAL_MINUTES}T')
    max_rssi_indices = df.groupby([grouper, 'tag_id'])['tag_rssi'].idxmax()
    analyzed_df = df.loc[max_rssi_indices].sort_values(
        by=['datetime', 'tag_id']).reset_index(drop=True)

    # 解析結果をCSVに保存
    try:
        analyzed_df.to_csv(ANALYZED_CSV_FILE, index=False,
                           encoding='utf-8-sig')
        logging.info(
            f"解析結果を '{ANALYZED_CSV_FILE}' に保存しました。({len(analyzed_df)} 件)")
    except Exception as e:
        logging.error(f"解析結果のCSV保存中にエラーが発生しました: {e}")
        return

    if analyzed_df.empty:
        logging.warning("解析後のデータが0件でした。グラフ作成はスキップします。")
        return

    # ==================================================================
    # STEP 2: STEP 1で作成したデータフレームを使ってグラフを作成
    # ==================================================================
    logging.info(f"STEP 2: 解析結果をもとにグラフ作成を開始します...")

    # --- グラフに描画するデータを準備 ---
    if TAGS_TO_PLOT:
        df_plot = analyzed_df[analyzed_df['tag_id'].isin(TAGS_TO_PLOT)]
        if df_plot.empty:
            logging.warning("指定されたタグIDのデータが見つかりませんでした。グラフは作成されません。")
            return
    else:
        df_plot = analyzed_df  # TAGS_TO_PLOTがNoneなら全タグを描画

    logging.info(f"グラフ描画対象タグ: {df_plot['tag_id'].unique().tolist()}")

    # --- グラフの描画 ---
    plt.figure(figsize=(16, 8))
    sns.lineplot(
        data=df_plot,
        x='datetime',
        y='node_id',
        hue='tag_id',
        style='tag_id',
        marker='o',
        markersize=8
    )

    # --- グラフの装飾 ---
    plt.title('Tag Movement Over Time (Closest Node)', fontsize=16)
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('Closest Node ID', fontsize=12)
    plt.yticks(df_plot['node_id'].unique())
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.xticks(rotation=30)
    plt.legend(title='Tag ID', bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.tight_layout()

    # --- グラフの保存と表示 ---
    try:
        plt.savefig(OUTPUT_IMAGE_FILE, dpi=300)
        logging.info(f"グラフを '{OUTPUT_IMAGE_FILE}' に保存しました。")
    except Exception as e:
        logging.error(f"グラフの保存中にエラーが発生しました: {e}")

    plt.show()


if __name__ == '__main__':
    main()
