import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import japanize_matplotlib
import os
import logging

# --- 設定項目 (変更可能) ---
# ----------------------------------------------------------------------
# (HHIフォルダと同じ階層にある入力ファイル)
INPUT_CSV_FILE = '../closest_node_per_interval_with_names.csv'

# (HHIフォルダ内に出力されるファイル)
OUTPUT_DATA_FILE = 'mobility_index_data_by_dept.csv'  # (ファイル名変更)
OUTPUT_GRAPH_FILE = 'mobility_index_graph_by_dept.png'  # (ファイル名変更)
OUTPUT_HEATMAP_FILE = 'mobility_index_heatmap_by_dept.png'  # (ファイル名変更)

# 集計する時間間隔 ('D': 日ごと, 'W': 週ごと, 'M': 月ごと)
TIME_FREQ = 'M'

# 分析対象の部門
DEPARTMENTS_TO_ANALYZE = ['airtro', 'giken']

# グラフ化するタグ (Noneにすると全部門の全タグ)
TAGS_TO_PLOT = None
# ----------------------------------------------------------------------

# --- 出力先フォルダ設定 (スクリプトの場所基準) ---
output_dir = os.path.dirname(os.path.abspath(__file__))
output_data_path = os.path.join(output_dir, OUTPUT_DATA_FILE)
output_graph_path = os.path.join(output_dir, OUTPUT_GRAPH_FILE)
output_heatmap_path = os.path.join(output_dir, OUTPUT_HEATMAP_FILE)
input_file_path = os.path.join(output_dir, INPUT_CSV_FILE)

# ロギング設定
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def calculate_mobility_index(df, freq='D'):
    """
    HHI（集中度）と移動指数を計算する (部門列も保持)
    """
    logging.info(f"'{freq}' 間隔で移動指数の計算を開始します...")

    df['date_group'] = df['datetime'].dt.to_period(freq)

    # 1. 期間ごと・人ごと・場所ごとの滞在回数をカウント (★ department を追加)
    stay_counts = df.groupby(
        ['date_group', 'department', 'tag_name', 'place_name']
    ).size()
    stay_counts.name = 'stay_counts'

    # 2. 期間ごと・人ごとの総滞在回数を計算 (★ department を追加)
    total_counts = stay_counts.groupby(
        level=['date_group', 'department', 'tag_name']
    ).transform('sum')

    # 3. 滞在比率 (%) を計算
    stay_ratio_pct = (stay_counts / total_counts) * 100

    # 4. 比率の二乗 (HHIの素) を計算
    ratio_sq = stay_ratio_pct.pow(2)
    ratio_sq.name = 'ratio_sq'

    # 5. 期間ごと・人ごとに比率の二乗を合計して HHI を算出 (★ department を追加)
    hhi_index = ratio_sq.groupby(
        level=['date_group', 'department', 'tag_name']
    ).sum().reset_index()
    hhi_index = hhi_index.rename(columns={'ratio_sq': 'HHI'})

    # 6. 移動指数 (Mobility Index) を計算
    hhi_index['Mobility_Index'] = 10000 - hhi_index['HHI']

    # 7. date_group (Period) を グラフ化しやすい datetime に戻す
    hhi_index['date'] = hhi_index['date_group'].dt.to_timestamp()

    logging.info(f"移動指数の計算が完了しました。 {len(hhi_index)} 件")
    return hhi_index


def plot_line_graph(df, output_path):
    """
    【★変更】移動指数の時系列折れ線グラフを部門別(上下2段)で保存する
    """
    logging.info(f"折れ線グラフ（部門別）を作成中... -> {output_path}")

    # 上下2段のグラフ領域を作成 (X軸を共有)
    fig, axes = plt.subplots(2, 1, figsize=(16, 12), sharex=True)

    # --- 上のグラフ (airtro) ---
    ax1 = axes[0]
    df_airtro = df[df['department'] == 'airtro']
    if not df_airtro.empty:
        sns.lineplot(
            data=df_airtro, x='date', y='Mobility_Index',
            hue='tag_name', style='tag_name', marker='o', ax=ax1
        )
        ax1.set_title('airtro - 移動指数の時系列変化', fontsize=16)
        ax1.set_ylabel('移動指数 (高いほど分散)')
        ax1.set_ylim(-500, 10500)
        ax1.grid(True, linestyle='--', alpha=0.6)
        ax1.legend(bbox_to_anchor=(1.01, 1), loc='upper left')
    else:
        ax1.text(0.5, 0.5, 'airtro のデータがありません', transform=ax1.transAxes,
                 ha='center', va='center', color='gray')

    # --- 下のグラフ (giken) ---
    ax2 = axes[1]
    df_giken = df[df['department'] == 'giken']
    if not df_giken.empty:
        sns.lineplot(
            data=df_giken, x='date', y='Mobility_Index',
            hue='tag_name', style='tag_name', marker='o', ax=ax2
        )
        ax2.set_title('giken - 移動指数の時系列変化', fontsize=16)
        ax2.set_ylabel('移動指数 (高いほど分散)')
        ax2.set_ylim(-500, 10500)
        ax2.grid(True, linestyle='--', alpha=0.6)
        ax2.legend(bbox_to_anchor=(1.01, 1), loc='upper left')
    else:
        ax2.text(0.5, 0.5, 'giken のデータがありません', transform=ax2.transAxes,
                 ha='center', va='center', color='gray')

    # --- 共通設定 ---
    plt.xlabel('日付', fontsize=12)
    plt.tight_layout(rect=[0, 0, 0.88, 1])  # 凡例スペース確保

    plt.savefig(output_path, dpi=300)
    plt.close()
    logging.info("折れ線グラフ（部門別）を保存しました。")


def plot_heatmap(df, output_path):
    """
    【★変更】移動指数のヒートマップを部門別(上下2段)で保存する
    """
    logging.info(f"ヒートマップ（部門別）を作成中... -> {output_path}")

    # データをピボット (日付を列に、部門と名前を行にする)
    try:
        pivot_df = df.pivot_table(
            index=['department', 'tag_name'],
            columns='date',
            values='Mobility_Index'
        )
        # 日付のフォーマットを簡潔にする
        pivot_df.columns = pivot_df.columns.strftime('%Y-%m-%d')
    except Exception as e:
        logging.warning(f"ヒートマップ用のデータ整形に失敗: {e} スキップします。")
        return

    # 部門ごとにデータを分離
    try:
        pivot_airtro = pivot_df.loc['airtro']
    except KeyError:
        pivot_airtro = pd.DataFrame()
        logging.warning("ヒートマップ: airtro のデータがありません。")

    try:
        pivot_giken = pivot_df.loc['giken']
    except KeyError:
        pivot_giken = pd.DataFrame()
        logging.warning("ヒートマップ: giken のデータがありません。")

    # グラフの高さを行数に応じて動的に調整
    height_airtro = max(3, len(pivot_airtro) * 0.5)
    height_giken = max(3, len(pivot_giken) * 0.5)
    total_height = height_airtro + height_giken + 2  # タイトル等の余白

    # グラフの幅を列数に応じて動的に調整
    fig_width = max(15, len(pivot_df.columns) * 0.5)

    # 上下2段のグラフ領域を作成
    fig, axes = plt.subplots(
        2, 1,
        figsize=(fig_width, total_height),
        gridspec_kw={'height_ratios': [height_airtro, height_giken]}
    )

    common_cbar_kws = {
        'label': '移動指数 (高いほど分散)',
        'orientation': 'vertical'  # カラーバーを縦に
    }

    # --- 上のヒートマップ (airtro) ---
    ax1 = axes[0]
    if not pivot_airtro.empty:
        sns.heatmap(
            pivot_airtro,
            annot=True, fmt=".0f", cmap='viridis',
            linewidths=.5, ax=ax1,
            vmin=0, vmax=10000,  # 比較のため色の尺度を 0-10000 に固定
            cbar_kws=common_cbar_kws
        )
        ax1.set_title('airtro - 移動指数ヒートマップ', fontsize=16)
        ax1.set_xlabel('')  # X軸ラベルは一番下のみ
        ax1.set_ylabel('名前 (tag_name)', fontsize=12)
    else:
        ax1.text(0.5, 0.5, 'airtro のデータがありません', transform=ax1.transAxes,
                 ha='center', va='center', color='gray')

    # --- 下のヒートマップ (giken) ---
    ax2 = axes[1]
    if not pivot_giken.empty:
        sns.heatmap(
            pivot_giken,
            annot=True, fmt=".0f", cmap='viridis',
            linewidths=.5, ax=ax2,
            vmin=0, vmax=10000,  # 比較のため色の尺度を 0-10000 に固定
            cbar_kws=common_cbar_kws
        )
        ax2.set_title('giken - 移動指数ヒートマップ', fontsize=16)
        ax2.set_xlabel('日付', fontsize=12)
        ax2.set_ylabel('名前 (tag_name)', fontsize=12)
        plt.xticks(rotation=45, ha='right')
    else:
        ax2.text(0.5, 0.5, 'giken のデータがありません', transform=ax2.transAxes,
                 ha='center', va='center', color='gray')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    logging.info("ヒートマップ（部門別）を保存しました。")


def main():
    # --- 1. 入力CSVの読み込み ---
    try:
        logging.info(f"入力ファイルを読み込みます: {input_file_path}")
        df = pd.read_csv(input_file_path, parse_dates=['datetime'])
    except FileNotFoundError:
        logging.error(f"エラー: 入力ファイル '{input_file_path}' が見つかりません。")
        return
    except Exception as e:
        logging.error(f"ファイル読み込み中にエラーが発生しました: {e}")
        return

    if df.empty:
        logging.warning("入力ファイルが空です。処理を終了します。")
        return

    # --- 1.5 【★変更】対象部門でデータをフィルタリング ---
    logging.info(f"対象部門 {DEPARTMENTS_TO_ANALYZE} でデータを絞り込みます。")
    df_filtered = df[df['department'].isin(DEPARTMENTS_TO_ANALYZE)].copy()

    if df_filtered.empty:
        logging.warning(f"対象部門 {DEPARTMENTS_TO_ANALYZE} のデータが見つかりませんでした。")
        return
    logging.info(f"絞り込み後のデータ件数: {len(df_filtered)} 件")

    # --- 2. HHIと移動指数の計算 ---
    # (★ department 列が引き継がれるように calculate_mobility_index を修正済)
    df_index = calculate_mobility_index(df_filtered, freq=TIME_FREQ)

    if df_index.empty:
        logging.warning("指数計算後のデータが空です。処理を終了します。")
        return

    # --- 3. グラフ化対象の絞り込み (タグ指定) ---
    if TAGS_TO_PLOT:
        df_plot = df_index[df_index['tag_name'].isin(TAGS_TO_PLOT)].copy()
    else:
        df_plot = df_index.copy()

    if df_plot.empty:
        logging.warning("グラフ化対象のデータが見つかりませんでした。")
        return

    # --- 4. データ出力 ---
    # (★ department 列がCSVに含まれます)
    df_index.to_csv(output_data_path, index=False, encoding='utf-8-sig')
    logging.info(f"計算結果を '{output_data_path}' に保存しました。")

    # --- 5. グラフ可視化 ---
    # (★ グラフ関数は部門別描画に対応済)
    plot_line_graph(df_plot, output_graph_path)
    plot_heatmap(df_plot, output_heatmap_path)

    logging.info("すべての処理が完了しました。")


if __name__ == '__main__':
    main()
