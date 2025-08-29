import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
import japanize_matplotlib

# (設定項目は変更可能)
# ----------------------------------------------------------------------
INPUT_CSV_FILE = 'processed_tag_data.csv'
ANALYZED_CSV_FILE = 'closest_node_per_interval.csv'
OUTPUT_IMAGE_FILE = 'tag_movement_graph.png'
TIME_INTERVAL_MINUTES = 5
AGGREGATION_METHOD = 'max'  # mean, max, sum から選択

TAGS_TO_PLOT = [
    '0081f9860356',
    '0081f9860866',
    '0081f986053f',
]
TAGS_TO_PLOT = None

NODE_NAME_CSV_FILE = 'node_names.csv'
# ▼▼▼ 追加箇所 ▼▼▼
# tag_id とグラフに表示する名前を関連付けるCSVファイル
# (例: tag_id,tag_name のヘッダーで、'0081f9860356','作業員A' のように記載)
TAG_NAME_CSV_FILE = 'tag_names.csv'
# ▲▲▲ 追加ここまで ▲▲▲
# ----------------------------------------------------------------------

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    # ... (STEP 1のデータ読み込みと集計部分は変更なし) ...
    try:
        logging.info(f"STEP 1: '{INPUT_CSV_FILE}' を読み込んで解析を開始します...")
        df = pd.read_csv(INPUT_CSV_FILE, parse_dates=['datetime'])
    except FileNotFoundError:
        logging.error(f"エラー: 入力ファイル '{INPUT_CSV_FILE}' が見つかりません。")
        return

    grouper = pd.Grouper(key='datetime', freq=f'{TIME_INTERVAL_MINUTES}T')

    if AGGREGATION_METHOD == 'max':
        logging.info("各時間間隔において、RSSI最大値を記録したnodeを抽出します。")
        max_rssi_indices = df.groupby([grouper, 'tag_id'])['tag_rssi'].idxmax()
        analyzed_df = df.loc[max_rssi_indices].sort_values(
            by=['datetime', 'tag_id']).reset_index(drop=True)
    elif AGGREGATION_METHOD == 'mean':
        logging.info("各時間間隔において、平均RSSIが最も高いnodeを抽出します。")
        mean_rssi_df = df.groupby(
            [grouper, 'tag_id', 'node_id'])['tag_rssi'].mean().reset_index()
        max_mean_indices = mean_rssi_df.groupby(
            ['datetime', 'tag_id'])['tag_rssi'].idxmax()
        analyzed_df = mean_rssi_df.loc[max_mean_indices].sort_values(
            by=['datetime', 'tag_id']).reset_index(drop=True)
    elif AGGREGATION_METHOD == 'sum':
        logging.info("各時間間隔において、合計RSSIが最も高いnodeを抽出します。")
        sum_rssi_df = df.groupby(
            [grouper, 'tag_id', 'node_id'])['tag_rssi'].sum().reset_index()
        max_sum_indices = sum_rssi_df.groupby(
            ['datetime', 'tag_id'])['tag_rssi'].idxmax()
        analyzed_df = sum_rssi_df.loc[max_sum_indices].sort_values(
            by=['datetime', 'tag_id']).reset_index(drop=True)
    else:
        logging.error(
            f"エラー: 不明な集計方法 '{AGGREGATION_METHOD}' です。'max', 'mean', 'sum'のいずれかを指定してください。")
        return

    analyzed_df.to_csv(ANALYZED_CSV_FILE, index=False, encoding='utf-8-sig')
    logging.info(f"解析結果を '{ANALYZED_CSV_FILE}' に保存しました。({len(analyzed_df)} 件)")
    if analyzed_df.empty:
        logging.warning("解析後のデータが0件でした。グラフ作成はスキップします。")
        return

    logging.info(f"STEP 2: 解析結果をもとにグラフ作成を開始します...")

    # --- 場所名 (node_id -> place_name) のマージ ---
    node_names_df = None
    try:
        node_names_df = pd.read_csv(NODE_NAME_CSV_FILE)
        # データ型を合わせてからマージする
        analyzed_df['node_id'] = analyzed_df['node_id'].astype(
            node_names_df['node_id'].dtype)
        plot_base_df = pd.merge(
            analyzed_df, node_names_df, on='node_id', how='left')

        if plot_base_df['place_name'].isnull().any():
            missing_nodes = plot_base_df[plot_base_df['place_name'].isnull(
            )]['node_id'].unique()
            logging.warning(f"警告: 次のnode_idに対応する場所名が見つかりません: {missing_nodes}")
            # 見つからなかった場合はnode_idをそのまま場所名として使う
            plot_base_df['place_name'] = plot_base_df['place_name'].fillna(
                plot_base_df['node_id'].astype(str))
    except FileNotFoundError:
        logging.warning(f"'{NODE_NAME_CSV_FILE}' が見つかりません。Y軸にはnode_idを使用します。")
        plot_base_df = analyzed_df.copy()
        plot_base_df['place_name'] = plot_base_df['node_id'].astype(str)
    except Exception as e:
        logging.error(f"場所名定義ファイルの読み込み中にエラーが発生しました: {e}")
        return

    # ▼▼▼ 変更箇所 ▼▼▼
    # --- タグ名 (tag_id -> tag_name) のマージ ---
    try:
        tag_names_df = pd.read_csv(TAG_NAME_CSV_FILE)
        # マージ前にデータ型を合わせる (文字列として扱う)
        plot_base_df['tag_id'] = plot_base_df['tag_id'].astype(str)
        tag_names_df['tag_id'] = tag_names_df['tag_id'].astype(str)

        plot_base_df = pd.merge(
            plot_base_df, tag_names_df, on='tag_id', how='left')

        # タグ名が見つからなかった場合は、元のtag_idを名前として使用する
        plot_base_df['tag_name'] = plot_base_df['tag_name'].fillna(
            plot_base_df['tag_id'])

    except FileNotFoundError:
        logging.warning(f"'{TAG_NAME_CSV_FILE}' が見つかりません。凡例にはtag_idを使用します。")
        plot_base_df['tag_name'] = plot_base_df['tag_id']
    except Exception as e:
        logging.error(f"タグ名定義ファイルの読み込み中にエラーが発生しました: {e}")
        # エラー時も凡例にはtag_idを使用する
        plot_base_df['tag_name'] = plot_base_df['tag_id']
    # ▲▲▲ 変更ここまで ▲▲▲

    # ... (デバッグ出力 ① は変更なし) ...
    print("\n" + "="*50)
    print("--- ① マージ直後のデータ確認 ---")
    print("plot_base_dfのユニークなnode_idとplace_name:")
    print(plot_base_df[['node_id', 'place_name']
                       ].drop_duplicates().sort_values('node_id'))
    print("="*50 + "\n")

    if TAGS_TO_PLOT:
        df_plot = plot_base_df[plot_base_df['tag_id'].isin(TAGS_TO_PLOT)]
        if df_plot.empty:
            logging.warning("指定されたタグIDのデータが見つかりませんでした。")
            return
    else:
        df_plot = plot_base_df

    # ... (デバッグ出力 ② は変更なし) ...
    print("\n" + "="*50)
    print("--- ② グラフ描画直前のデータ確認 ---")
    print("df_plotのユニークなnode_idとplace_name:")
    print(df_plot[['node_id', 'place_name']
                  ].drop_duplicates().sort_values('node_id'))
    print("="*50 + "\n")

    # ▼▼▼ 変更箇所 ▼▼▼
    logging.info(f"グラフ描画対象タグ: {df_plot['tag_name'].unique().tolist()}")
    # ▲▲▲ 変更ここまで ▲▲▲

    plt.figure(figsize=(16, 8))
    # ▼▼▼ 変更箇所 ▼▼▼
    # hue (色分け) と style (線種) を 'tag_id' から 'tag_name' に変更
    sns.lineplot(
        data=df_plot, x='datetime', y='place_name', hue='tag_name',
        style='tag_name', marker='o', markersize=8, sort=False
    )
    # ▲▲▲ 変更ここまで ▲▲▲

    plt.title('タグの移動履歴（時間ごとに最も近いNode）', fontsize=16)
    plt.xlabel('時刻', fontsize=12)
    plt.ylabel('場所（最も近いNode）', fontsize=12)

    all_plot_labels = df_plot['place_name'].unique().tolist()
    ordered_labels = all_plot_labels  # デフォルトはプロットデータ順
    if node_names_df is not None:
        defined_order = node_names_df['place_name'].tolist()
        ordered_labels = [
            label for label in defined_order if label in all_plot_labels]
        undefined_labels = [
            label for label in all_plot_labels if label not in defined_order]
        ordered_labels.extend(sorted(undefined_labels))

    # ... (デバッグ出力 ③ は変更なし) ...
    print("\n" + "="*50)
    print("--- ③ Y軸のラベル確認 ---")
    print("グラフのY軸に設定されるラベルのリスト:")
    print(ordered_labels)
    print("="*50 + "\n")

    if ordered_labels:
        plt.gca().set_yticks(ordered_labels)

    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.xticks(rotation=30, ha='right')

    # ▼▼▼ 変更箇所 ▼▼▼
    # 凡例のタイトルを 'Tag Name' に変更
    plt.legend(title='Tag Name', bbox_to_anchor=(1.02, 1), loc='upper left')
    # ▲▲▲ 変更ここまで ▲▲▲

    plt.tight_layout(rect=[0, 0, 0.88, 1])

    plt.savefig(OUTPUT_IMAGE_FILE, dpi=300)
    logging.info(f"グラフを '{OUTPUT_IMAGE_FILE}' に保存しました。")
    plt.show()


if __name__ == '__main__':
    main()
