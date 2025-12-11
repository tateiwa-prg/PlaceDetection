import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
import japanize_matplotlib
import os
import matplotlib.dates as mdates

# ----------------------------------------------------------------------
# --- 基本設定 ---
# ----------------------------------------------------------------------
INPUT_DATA_FOLDER = 'input'
INPUT_FILES_TO_CONCAT = [
    'processed_tag_data_Aug.csv',
    'processed_tag_data_Sep.csv',
    'processed_tag_data_Oct.csv',
    'processed_tag_data_Nov.csv',
    'processed_tag_data_Dec.csv',
]
ANALYZED_CSV_FILE = 'closest_node_per_interval_with_names.csv'
OUTPUT_IMAGE_FILE = 'tag_movement_comparison_graph.png'
TIME_INTERVAL_MINUTES = 5
AGGREGATION_METHOD = 'max'  # mean, max, sum から選択

# --- グラフ化対象タグ ---
TAGS_TO_PLOT = [
    # '0081f9860866',
    # '0081f986053f',
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
EXCEL_FILE_NAME = '辻アプリ_20250926.xlsx'
EXCEL_FILE_PATH = os.path.join(EXCEL_DATA_FOLDER, EXCEL_FILE_NAME)

# --- 下のグラフ(Excel)のY軸設定 ---
# EXCEL_Y_AXIS = 'SeatNumber'
EXCEL_Y_AXIS = 'Area'
# ----------------------------------------------------------------------

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def clean_id_column(df, col_name):
    """
    IDカラムをきれいな文字列に正規化する関数
    """
    if col_name not in df.columns:
        return df

    # 1. 文字列に変換
    df[col_name] = df[col_name].astype(str)
    # 2. "697.0" のような浮動小数点表記を "697" に戻す
    df[col_name] = df[col_name].apply(
        lambda x: x.split('.')[0] if '.' in x else x)
    # 3. 前後の空白削除
    df[col_name] = df[col_name].str.strip()
    return df


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

    df_excel_raw['CheckInTime'] = pd.to_datetime(
        df_excel_raw['CheckInTime'], errors='coerce')
    df_excel_raw['CheckOutTime'] = pd.to_datetime(
        df_excel_raw['CheckOutTime'], errors='coerce')
    df_excel_raw = df_excel_raw.dropna(subset=['CheckInTime', 'CheckOutTime'])

    resampled_data = []
    freq_str = f'{interval_minutes}min'

    for _, row in df_excel_raw.iterrows():
        try:
            time_range = pd.date_range(
                start=row['CheckInTime'],
                end=row['CheckOutTime'],
                freq=freq_str
            )
            if not time_range.empty:
                temp_df = pd.DataFrame(time_range, columns=['datetime'])
                temp_df['User'] = str(row['User'])
                temp_df['SeatNumber'] = str(row['SeatNumber'])
                temp_df['Area'] = str(row['Area'])
                resampled_data.append(temp_df)
        except Exception as e:
            continue

    if not resampled_data:
        logging.warning("Excelファイルから描画対象となるデータが抽出できませんでした。")
        return None

    df_excel_plot = pd.concat(resampled_data, ignore_index=True)
    logging.info(f"Excelデータをグラフ描画用に変換しました。({len(df_excel_plot)} 件)")
    return df_excel_plot


def main():
    # --- STEP 1: CSVファイルの読み込みと解析 ---
    logging.info(f"STEP 1: '{INPUT_DATA_FOLDER}' フォルダから複数CSVを読み込んで解析を開始します...")

    df_list = []
    for file_name in INPUT_FILES_TO_CONCAT:
        file_path = os.path.join(INPUT_DATA_FOLDER, file_name)
        try:
            df_temp = pd.read_csv(file_path, parse_dates=['datetime'])
            df_list.append(df_temp)
            logging.info(f"   ... '{file_path}' を読み込みました。")
        except FileNotFoundError:
            logging.warning(f"警告: ファイル '{file_path}' が見つかりません。スキップします。")
        except Exception as e:
            logging.warning(f"ファイル '{file_path}' の読み込み中にエラーが発生しました: {e}")

    if not df_list:
        logging.error("エラー: 読み込み可能なCSVデータがありませんでした。")
        return

    df = pd.concat(df_list, ignore_index=True)

    grouper = pd.Grouper(key='datetime', freq=f'{TIME_INTERVAL_MINUTES}min')
    df['tag_rssi'] = pd.to_numeric(df['tag_rssi'], errors='coerce')

    if AGGREGATION_METHOD == 'max':
        max_rssi_indices = df.groupby([grouper, 'tag_id'])['tag_rssi'].idxmax()
        analyzed_df = df.loc[max_rssi_indices]
    elif AGGREGATION_METHOD == 'mean':
        mean_rssi_df = df.groupby([grouper, 'tag_id', 'node_id'])[
            'tag_rssi'].mean().reset_index()
        max_mean_indices = mean_rssi_df.groupby(['datetime', 'tag_id'])[
            'tag_rssi'].idxmax()
        analyzed_df = mean_rssi_df.loc[max_mean_indices]
    else:
        sum_rssi_df = df.groupby([grouper, 'tag_id', 'node_id'])[
            'tag_rssi'].sum().reset_index()
        max_sum_indices = sum_rssi_df.groupby(['datetime', 'tag_id'])[
            'tag_rssi'].idxmax()
        analyzed_df = sum_rssi_df.loc[max_sum_indices]

    analyzed_df = analyzed_df.sort_values(
        by=['datetime', 'tag_id']).reset_index(drop=True)

    # --- STEP 2: 解析結果に名前情報とフロア情報を追加 ---
    logging.info("STEP 2: 解析結果に名前情報(Floor等含む)を追加します...")

    analyzed_df = clean_id_column(analyzed_df, 'node_id')
    analyzed_df = clean_id_column(analyzed_df, 'tag_id')

    # 1. Node Names のマージ
    node_names_df = None
    try:
        node_names_df = pd.read_csv(NODE_NAME_CSV_FILE, index_col=False)
        node_names_df = clean_id_column(node_names_df, 'node_id')

        if 'place_name' in node_names_df.columns:
            node_names_df['place_name'] = node_names_df['place_name'].astype(
                str)
        if 'floor' in node_names_df.columns:
            node_names_df['floor'] = pd.to_numeric(
                node_names_df['floor'], errors='coerce')
        if 'west_to_east' in node_names_df.columns:
            node_names_df['west_to_east'] = pd.to_numeric(
                node_names_df['west_to_east'], errors='coerce')

        analyzed_df = pd.merge(analyzed_df, node_names_df,
                               on='node_id', how='left')
        analyzed_df['place_name'] = analyzed_df['place_name'].fillna(
            analyzed_df['node_id'])

    except FileNotFoundError:
        logging.warning(f"'{NODE_NAME_CSV_FILE}' が見つかりません。")
        analyzed_df['place_name'] = analyzed_df['node_id']

    # 2. Tag Names のマージ
    try:
        tag_names_df = pd.read_csv(TAG_NAME_CSV_FILE)
        tag_names_df = clean_id_column(tag_names_df, 'tag_id')

        analyzed_df = pd.merge(analyzed_df, tag_names_df,
                               on='tag_id', how='left')

        # 名前だけ埋めておく（グラフの凡例用）
        analyzed_df['tag_name'] = analyzed_df['tag_name'].fillna(
            analyzed_df['tag_id'])

        # ★★★ 変更点: department が空のデータ（所属なし）を行ごと削除 ★★★
        before_len = len(analyzed_df)
        analyzed_df = analyzed_df.dropna(subset=['department'])
        # さらに明示的に「所属なし」という文字列が入っている場合も削除
        analyzed_df = analyzed_df[analyzed_df['department'] != '所属なし']

        logging.info(
            f"所属なしのデータを削除しました。 ({before_len} -> {len(analyzed_df)} 件)")

    except FileNotFoundError:
        logging.warning(
            f"'{TAG_NAME_CSV_FILE}' が見つかりません。所属情報がないため全データをスキップします。")
        analyzed_df = analyzed_df.iloc[0:0]  # 空にする

    # CSV保存
    analyzed_df.to_csv(ANALYZED_CSV_FILE, index=False, encoding='utf-8-sig')
    logging.info(f"解析結果を '{ANALYZED_CSV_FILE}' に保存しました。")

    if analyzed_df.empty:
        logging.warning("出力対象のデータが0件のため終了します。")
        return

    # --- STEP 3: 比較用Excelデータの処理 ---
    df_excel_plot = process_excel_data(EXCEL_FILE_PATH, TIME_INTERVAL_MINUTES)

    # --- グラフ描画対象データの絞り込み ---
    if TAGS_TO_PLOT:
        tags_str = [str(t) for t in TAGS_TO_PLOT]
        df_plot = analyzed_df[analyzed_df['tag_id'].isin(tags_str)].copy()
        if df_plot.empty:
            logging.warning("指定されたタグIDのデータが見つかりませんでした。")
            return
    else:
        df_plot = analyzed_df.copy()

    # ★ Y軸（場所名）の並び順ロジック ★
    if node_names_df is not None and 'place_name' in node_names_df.columns:

        sort_cols = []
        if 'floor' in node_names_df.columns:
            sort_cols.append('floor')
        if 'west_to_east' in node_names_df.columns:
            sort_cols.append('west_to_east')

        if sort_cols:
            sorted_nodes = node_names_df.sort_values(by=sort_cols)
            defined_order = sorted_nodes['place_name'].unique().tolist()
        else:
            defined_order = node_names_df['place_name'].unique().tolist()

        defined_order = [str(x) for x in defined_order]

        existing_places = df_plot['place_name'].unique().tolist()
        missing_in_definition = [
            p for p in existing_places if p not in defined_order]
        final_order = defined_order + sorted(missing_in_definition)

        df_plot['place_name'] = pd.Categorical(
            df_plot['place_name'], categories=final_order, ordered=True
        )

    # --- STEP 4: グラフ描画 ---
    logging.info(f"STEP 4: グラフ描画を開始します...")
    fig, axes = plt.subplots(2, 1, figsize=(18, 12), sharex=True)

    tag_names_to_plot = df_plot['tag_name'].unique()
    excel_users = df_excel_plot['User'].unique(
    ).tolist() if df_excel_plot is not None else []

    all_names = sorted(list(set(tag_names_to_plot) | set(excel_users)))
    palette = {name: color for name, color in zip(
        all_names, sns.color_palette('tab20', n_colors=len(all_names)))}

    if df_excel_plot is not None:
        df_excel_plot_filtered = df_excel_plot[df_excel_plot['User'].isin(
            all_names)].copy()
    else:
        df_excel_plot_filtered = None

    # --- 上のグラフ ---
    ax1 = axes[0]
    sns.lineplot(
        data=df_plot, x='datetime', y='place_name', hue='tag_name',
        style='tag_name', marker='o', markersize=8, sort=False,
        ax=ax1, palette=palette, dashes=False
    )
    ax1.set_title('タグの移動履歴 (センサーデータ)', fontsize=16)
    ax1.set_ylabel('場所', fontsize=12)
    ax1.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax1.legend(title='Tag Name', bbox_to_anchor=(
        1.01, 1), loc='upper left', ncol=1)

    # --- 下のグラフ ---
    ax2 = axes[1]
    if df_excel_plot_filtered is not None and not df_excel_plot_filtered.empty:
        df_excel_plot_filtered[EXCEL_Y_AXIS] = df_excel_plot_filtered[EXCEL_Y_AXIS].astype(
            str).str.replace(r'\.0$', '', regex=True)
        y_values = df_excel_plot_filtered[EXCEL_Y_AXIS].unique()

        try:
            y_values_sorted = sorted(y_values, key=lambda x: float(
                x) if x.replace('.', '', 1).isdigit() else x)
        except:
            y_values_sorted = sorted(y_values)

        df_excel_plot_filtered[EXCEL_Y_AXIS] = pd.Categorical(
            df_excel_plot_filtered[EXCEL_Y_AXIS], categories=y_values_sorted, ordered=True
        )

        sns.lineplot(
            data=df_excel_plot_filtered, x='datetime', y=EXCEL_Y_AXIS, hue='User',
            style='User', marker='o', markersize=8, sort=False,
            ax=ax2, palette=palette, dashes=False
        )
        ax2.set_title('滞在履歴 (予約データ)', fontsize=16)
        ax2.set_ylabel(f'場所 ({EXCEL_Y_AXIS})', fontsize=12)
        ax2.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax2.legend(title='User Name', bbox_to_anchor=(
            1.01, 1), loc='upper left', ncol=1)

        if EXCEL_Y_AXIS == 'SeatNumber':
            ax2.tick_params(axis='y', labelsize=8)
        else:
            ax2.tick_params(axis='y', labelsize=10)
    else:
        ax2.text(0.5, 0.5, 'データなし', transform=ax2.transAxes, ha='center')

    plt.xlabel('時刻', fontsize=12)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout(rect=[0, 0, 0.85, 1])

    plt.savefig(OUTPUT_IMAGE_FILE, dpi=300)
    logging.info(f"比較グラフを '{OUTPUT_IMAGE_FILE}' に保存しました。")
    plt.show()


if __name__ == '__main__':
    main()
