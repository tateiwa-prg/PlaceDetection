import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
import japanize_matplotlib
import os

# (設定項目は変更可能)
# ----------------------------------------------------------------------
# --- 基本設定 ---
INPUT_CSV_FILE = 'processed_tag_data.csv'
ANALYZED_CSV_FILE = 'closest_node_per_interval_with_names.csv'  # ファイル名を変更
OUTPUT_IMAGE_FILE = 'tag_movement_comparison_graph.png'
TIME_INTERVAL_MINUTES = 5
AGGREGATION_METHOD = 'max'  # mean, max, sum から選択

# --- グラフ化対象タグ ---
TAGS_TO_PLOT = None  # Noneにすると全タグを描画
TAGS_TO_PLOT = [
    # '0081f9860866',
    # '0081f986053f',
    # '0081f98607c1',
    # '0081f986054d',
    # '0081f98602f6',
    '0081f9860248',
    '0081f986075f',
    '0081f98609cf',
    '0081f9860a37',
]

# --- 外部ファイル設定 ---
NODE_NAME_CSV_FILE = 'node_names.csv'
TAG_NAME_CSV_FILE = 'tag_names.csv'

# --- 比較対象Excelファイル設定 ---
EXCEL_DATA_FOLDER = 'data'
# EXCEL_FILE_NAME = '居場所集計_20250904.xlsx'
EXCEL_FILE_NAME = '辻アプリ_20250926.xlsx'

EXCEL_FILE_PATH = os.path.join(EXCEL_DATA_FOLDER, EXCEL_FILE_NAME)

# --- 下のグラフ(Excel)のY軸設定 ---
# 'Area' または 'SeatNumber' を指定
EXCEL_Y_AXIS = 'SeatNumber'
EXCEL_Y_AXIS = 'Area'
# ----------------------------------------------------------------------

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def process_excel_data(file_path, interval_minutes):
    """Excelの滞在時間データを読み込み、グラフ描画用に変換する"""
    try:
        logging.info(f"STEP 3: 比較用Excelファイル '{file_path}' を読み込みます...")
        df_excel_raw = pd.read_excel(file_path)
    except FileNotFoundError:
        logging.error(f"エラー: 比較用Excelファイル '{file_path}' が見つかりません。")
        return None
    except Exception as e:
        logging.error(f"Excelファイルの読み込み中にエラーが発生しました: {e}")
        return None

    df_excel_raw['CheckInTime'] = pd.to_datetime(df_excel_raw['CheckInTime'])
    df_excel_raw['CheckOutTime'] = pd.to_datetime(df_excel_raw['CheckOutTime'])

    resampled_data = []
    for _, row in df_excel_raw.iterrows():
        time_range = pd.date_range(
            start=row['CheckInTime'],
            end=row['CheckOutTime'],
            freq=f'{interval_minutes}T'
        )
        if not time_range.empty:
            temp_df = pd.DataFrame(time_range, columns=['datetime'])
            temp_df['User'] = row['User']
            temp_df['SeatNumber'] = row['SeatNumber']
            temp_df['Area'] = row['Area']
            resampled_data.append(temp_df)

    if not resampled_data:
        logging.warning("Excelファイルから描画対象となるデータが抽出できませんでした。")
        return None

    df_excel_plot = pd.concat(resampled_data, ignore_index=True)
    logging.info(f"Excelデータをグラフ描画用に変換しました。({len(df_excel_plot)} 件)")
    return df_excel_plot


def main():
    # --- STEP 1: CSVファイルの読み込みと解析 ---
    try:
        logging.info(f"STEP 1: '{INPUT_CSV_FILE}' を読み込んで解析を開始します...")
        df = pd.read_csv(INPUT_CSV_FILE, parse_dates=['datetime'])
    except FileNotFoundError:
        logging.error(f"エラー: 入力ファイル '{INPUT_CSV_FILE}' が見つかりません。")
        return

    grouper = pd.Grouper(key='datetime', freq=f'{TIME_INTERVAL_MINUTES}T')
    if AGGREGATION_METHOD == 'max':
        max_rssi_indices = df.groupby([grouper, 'tag_id'])['tag_rssi'].idxmax()
        analyzed_df = df.loc[max_rssi_indices]
    elif AGGREGATION_METHOD == 'mean':
        mean_rssi_df = df.groupby([grouper, 'tag_id', 'node_id'])[
            'tag_rssi'].mean().reset_index()
        max_mean_indices = mean_rssi_df.groupby(['datetime', 'tag_id'])[
            'tag_rssi'].idxmax()
        analyzed_df = mean_rssi_df.loc[max_mean_indices]
    else:  # 'sum'
        sum_rssi_df = df.groupby([grouper, 'tag_id', 'node_id'])[
            'tag_rssi'].sum().reset_index()
        max_sum_indices = sum_rssi_df.groupby(['datetime', 'tag_id'])[
            'tag_rssi'].idxmax()
        analyzed_df = sum_rssi_df.loc[max_sum_indices]

    analyzed_df = analyzed_df.sort_values(
        by=['datetime', 'tag_id']).reset_index(drop=True)

    # --- STEP 2: 解析結果に名前情報を追加 ---
    logging.info("STEP 2: 解析結果に名前情報を追加します...")
    node_names_df = None  # 後続処理のために初期化
    try:
        node_names_df = pd.read_csv(NODE_NAME_CSV_FILE)
        analyzed_df['node_id'] = analyzed_df['node_id'].astype(
            node_names_df['node_id'].dtype)
        analyzed_df = pd.merge(analyzed_df, node_names_df,
                               on='node_id', how='left')
        analyzed_df['place_name'] = analyzed_df['place_name'].fillna(
            analyzed_df['node_id'].astype(str))
    except FileNotFoundError:
        logging.warning(f"'{NODE_NAME_CSV_FILE}' が見つかりません。Y軸にはnode_idを使用します。")
        analyzed_df['place_name'] = analyzed_df['node_id'].astype(str)

    try:
        tag_names_df = pd.read_csv(TAG_NAME_CSV_FILE)
        analyzed_df['tag_id'] = analyzed_df['tag_id'].astype(str)
        tag_names_df['tag_id'] = tag_names_df['tag_id'].astype(str)

        # ▼▼▼【変更点】departmentカラムもマージ ▼▼▼
        analyzed_df = pd.merge(analyzed_df, tag_names_df,
                               on='tag_id', how='left')

        # 紐づかない場合に備えて、デフォルト値を設定
        analyzed_df['tag_name'] = analyzed_df['tag_name'].fillna(
            analyzed_df['tag_id'])
        analyzed_df['department'] = analyzed_df['department'].fillna(
            '所属なし')  # departmentがない場合の値を設定
        # ▲▲▲ 変更ここまで ▲▲▲

    except FileNotFoundError:
        logging.warning(f"'{TAG_NAME_CSV_FILE}' が見つかりません。凡例にはtag_idを使用します。")
        analyzed_df['tag_name'] = analyzed_df['tag_id']
        analyzed_df['department'] = '所属なし'  # ファイルがない場合も列を追加

    # 名前情報を追加したデータフレームをCSVに保存
    analyzed_df.to_csv(ANALYZED_CSV_FILE, index=False, encoding='utf-8-sig')
    logging.info(
        f"名前情報を追加した解析結果を '{ANALYZED_CSV_FILE}' に保存しました。({len(analyzed_df)} 件)")

    if analyzed_df.empty:
        logging.warning("タグの解析後データが0件でした。グラフ作成はスキップします。")
        return

    # --- STEP 3: 比較用Excelデータの処理 ---
    df_excel_plot = process_excel_data(EXCEL_FILE_PATH, TIME_INTERVAL_MINUTES)

    # --- グラフ描画対象データの絞り込み ---
    if TAGS_TO_PLOT:
        df_plot = analyzed_df[analyzed_df['tag_id'].isin(TAGS_TO_PLOT)].copy()
        if df_plot.empty:
            logging.warning("指定されたタグIDのデータが見つかりませんでした。")
            return
    else:
        df_plot = analyzed_df.copy()

    # --- STEP 4: グラフ描画 ---
    logging.info(f"STEP 4: グラフ描画を開始します...")
    fig, axes = plt.subplots(2, 1, figsize=(18, 12), sharex=True)

    tag_names_to_plot = df_plot['tag_name'].unique()

    if df_excel_plot is not None:
        df_excel_plot_filtered = df_excel_plot[df_excel_plot['User'].isin(
            tag_names_to_plot)].copy()
    else:
        df_excel_plot_filtered = None

    excel_users = df_excel_plot['User'].unique(
    ).tolist() if df_excel_plot is not None else []
    all_names = sorted(list(set(tag_names_to_plot) | set(excel_users)))
    palette = {name: color for name, color in zip(
        all_names, sns.color_palette('tab20', n_colors=len(all_names)))}

    # --- 上のグラフ (タグデータ) の描画 ---
    ax1 = axes[0]
    sns.lineplot(
        data=df_plot, x='datetime', y='place_name', hue='tag_name',
        style='tag_name', marker='o', markersize=7, sort=False,
        ax=ax1, palette=palette
    )
    ax1.set_title('タグの移動履歴 (センサーデータ)', fontsize=16)
    ax1.set_ylabel('場所 (最も近いNode)', fontsize=12)
    ax1.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax1.legend(title='Tag Name', bbox_to_anchor=(
        1.01, 1), loc='upper left', ncol=2)

    if node_names_df is not None:
        all_plot_labels = df_plot['place_name'].unique().tolist()
        defined_order = node_names_df['place_name'].tolist()
        ordered_labels = [
            label for label in defined_order if label in all_plot_labels]
        undefined_labels = [
            label for label in all_plot_labels if label not in defined_order]
        ordered_labels.extend(sorted(undefined_labels))
        if ordered_labels:
            ax1.set_yticks(ordered_labels)

    # --- 下のグラフ (Excelデータ) の描画 ---
    ax2 = axes[1]
    if df_excel_plot_filtered is not None and not df_excel_plot_filtered.empty:
        sns.lineplot(
            data=df_excel_plot_filtered, x='datetime', y=EXCEL_Y_AXIS, hue='User',
            style='User', marker='o', markersize=7, sort=False,
            ax=ax2, palette=palette
        )
        ax2.set_title('滞在履歴 (予約データ)', fontsize=16)
        ax2.set_ylabel(f'場所 ({EXCEL_Y_AXIS})', fontsize=12)
        ax2.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax2.legend(title='User Name', bbox_to_anchor=(
            1.01, 1), loc='upper left', ncol=2)

        y_labels_excel = df_excel_plot_filtered.sort_values('datetime')[
            EXCEL_Y_AXIS].unique()
        ax2.set_yticks(y_labels_excel)

        if EXCEL_Y_AXIS == 'SeatNumber':
            ax2.tick_params(axis='y', labelsize=8)
        else:
            ax2.tick_params(axis='y', labelsize=10)
    else:
        ax2.text(0.5, 0.5, '比較対象となるユーザーデータがありません',
                 horizontalalignment='center', verticalalignment='center',
                 transform=ax2.transAxes, fontsize=12, color='gray')

    # --- 共通のグラフ設定 ---
    plt.xlabel('時刻', fontsize=12)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout(rect=[0, 0, 0.9, 1])

    plt.savefig(OUTPUT_IMAGE_FILE, dpi=300)
    logging.info(f"比較グラフを '{OUTPUT_IMAGE_FILE}' に保存しました。")
    plt.show()


if __name__ == '__main__':
    main()
