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
OUTPUT_DATA_FILE = 'department_dispersion_data.csv'
OUTPUT_GRAPH_FILE = 'department_dispersion_graph.png'
OUTPUT_HEATMAP_FILE = 'department_dispersion_heatmap.png'

# 集計する時間間隔 ('D': 日ごと, 'W': 週ごと, 'M': 月ごと)
TIME_FREQ = 'M'

# 分析対象の部門
DEPARTMENTS_TO_ANALYZE = ['airtro', 'giken']
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


def calculate_dispersion_index(df, freq='D'):
    """
    【★分析アプローチ2★】
    部門のHHI（集中度）と分散指数を計算する
    (個人(tag_name)を無視し、部門全体で計算)
    """
    logging.info(f"'{freq}' 間隔で部門分散指数の計算を開始します...")

    df['date_group'] = df['datetime'].dt.to_period(freq)

    # 1. 期間ごと・部門ごと・場所ごとの「のべ滞在回数」をカウント
    # (★ tag_name を groupby から除外するのがキモ)
    stay_counts = df.groupby(
        ['date_group', 'department', 'place_name']
    ).size()
    stay_counts.name = 'stay_counts'

    # 2. 期間ごと・部門ごとの「総滞在回数」を計算
    total_counts = stay_counts.groupby(
        level=['date_group', 'department']
    ).transform('sum')

    # 3. 滞在比率 (%) を計算 (部門の総滞在のうち、何%がその場所か)
    stay_ratio_pct = (stay_counts / total_counts) * 100

    # 4. 比率の二乗 (HHIの素) を計算
    ratio_sq = stay_ratio_pct.pow(2)
    ratio_sq.name = 'ratio_sq'

    # 5. 期間ごと・部門ごとに比率の二乗を合計して HHI を算出
    # (これが「部門集中度指数」)
    hhi_index = ratio_sq.groupby(
        level=['date_group', 'department']
    ).sum().reset_index()
    hhi_index = hhi_index.rename(columns={'ratio_sq': 'Department_HHI'})

    # 6. 分散指数 (Dispersion Index) を計算
    # (10000 - HHI)
    hhi_index['Dispersion_Index'] = 10000 - hhi_index['Department_HHI']

    # 7. date_group (Period) を グラフ化しやすい datetime に戻す
    hhi_index['date'] = hhi_index['date_group'].dt.to_timestamp()

    logging.info(f"部門分散指数の計算が完了しました。 {len(hhi_index)} 件")
    return hhi_index


def plot_line_graph(df, output_path):
    """
    部門分散指数の時系列折れ線グラフを保存する
    (2部門を1つのグラフで比較)
    """
    logging.info(f"折れ線グラフを作成中... -> {output_path}")
    plt.figure(figsize=(16, 6))  # 1段なので縦は短め

    ax = sns.lineplot(
        data=df,
        x='date',
        y='Dispersion_Index',
        hue='department',  # 部門で色分け
        marker='o',
        style='department'  # 部門でマーカーも変える
    )

    ax.set_title(f'部門 分散指数の時系列変化 (集計単位: {TIME_FREQ})', fontsize=16)
    ax.set_ylabel('部門 分散指数 (高いほど分散)', fontsize=12)
    ax.set_xlabel('日付', fontsize=12)
    ax.set_ylim(-500, 10500)  # 0〜10000 が基本
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='best')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    logging.info("折れ線グラフを保存しました。")


def plot_heatmap(df, output_path):
    """
    部門分散指数のヒートマップを保存する
    """
    logging.info(f"ヒートマップを作成中... -> {output_path}")

    # データをヒートマップ用にピボット (行が部門、列が日付)
    try:
        pivot_df = df.pivot(index='department',
                            columns='date', values='Dispersion_Index')
    except Exception as e:
        logging.warning(f"ヒートマップ用のデータ整形に失敗しました: {e} スキップします。")
        return

    # 日付のフォーマットを簡潔にする (例: '2025-09-26')
    pivot_df.columns = pivot_df.columns.strftime('%Y-%m-%d')

    # グラフの高さは固定 (2部門のため)、幅を日付の数で可変に
    plt.figure(figsize=(max(15, len(pivot_df.columns) * 0.5), 5))

    ax = sns.heatmap(
        pivot_df,
        annot=True,          # 数値をセルに表示
        fmt=".0f",           # 整数で表示
        cmap='viridis',      # 色のテーマ (低い:紫 -> 高い:黄)
        linewidths=.5,
        vmin=0, vmax=10000,  # 色の尺度を固定
        cbar_kws={'label': '部門 分散指数 (高いほど分散)'}
    )

    ax.set_title(f'部門 分散指数ヒートマップ (集計単位: {TIME_FREQ})', fontsize=16)
    ax.set_xlabel('日付', fontsize=12)
    ax.set_ylabel('部門 (department)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    logging.info("ヒートマップを保存しました。")


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

    # --- 1.5 対象部門でデータをフィルタリング ---
    logging.info(f"対象部門 {DEPARTMENTS_TO_ANALYZE} でデータを絞り込みます。")
    df_filtered = df[df['department'].isin(DEPARTMENTS_TO_ANALYZE)].copy()

    if df_filtered.empty:
        logging.warning(f"対象部門 {DEPARTMENTS_TO_ANALYZE} のデータが見つかりませんでした。")
        return
    logging.info(f"絞り込み後のデータ件数: {len(df_filtered)} 件")

    # --- 2. 部門分散指数の計算 ---
    df_index = calculate_dispersion_index(df_filtered, freq=TIME_FREQ)

    if df_index.empty:
        logging.warning("指数計算後のデータが空です。処理を終了します。")
        return

    # --- 3. データ出力 ---
    df_index.to_csv(output_data_path, index=False, encoding='utf-8-sig')
    logging.info(f"計算結果を '{output_data_path}' に保存しました。")

    # --- 4. グラフ可視化 ---
    plot_line_graph(df_index, output_graph_path)
    plot_heatmap(df_index, output_heatmap_path)

    logging.info("すべての処理が完了しました。")


if __name__ == '__main__':
    main()
