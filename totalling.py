import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import japanize_matplotlib
import os

# --- 設定項目 ---
INPUT_CSV_FILE = 'closest_node_per_interval_with_names.csv'
OUTPUT_FOLDER = 'output_files'
# 1コマあたりの分数（元スクリプトの設定に合わせてください）
TIME_INTERVAL_MINUTES = 5

# 除外したいタグIDをこのリストに追加
TAGS_TO_EXCLUDE = [
    'f0f8f2cad80b',
    '0081f98607c1',
]


def plot_overall_stacked_bar_graph(df, group_by_col, title, output_filename, mode='percentage'):
    """ 期間全体での滞在グラフを作成する（割合/実時間） """
    print(f"\n--- {title} グラフ作成開始 ---")

    counts = df.groupby([group_by_col, 'place_name']
                        ).size().reset_index(name='count')
    if counts.empty:
        print(f"集計データがありません: {title}")
        return

    value_col = ''
    y_label = ''
    if mode == 'percentage':
        total_counts = counts.groupby(group_by_col)['count'].sum()
        counts['percentage'] = counts.apply(
            lambda row: 100 * row['count'] / total_counts[row[group_by_col]], axis=1
        )
        value_col = 'percentage'
        y_label = '滞在割合 (%)'
    else:  # mode == 'duration'
        counts['duration'] = counts['count'] * TIME_INTERVAL_MINUTES
        value_col = 'duration'
        y_label = '合計滞在時間 (分)'

    pivot_df = counts.pivot(
        index=group_by_col, columns='place_name', values=value_col).fillna(0)

    figsize = (16, 9) if group_by_col == 'tag_name' else (12, 7)
    fig, ax = plt.subplots(figsize=figsize)
    pivot_df.plot(kind='bar', stacked=True, ax=ax, colormap='tab20', width=0.8)

    ax.set_title(title, fontsize=20, pad=20)
    ax.set_xlabel('人物名' if group_by_col == 'tag_name' else '部門名', fontsize=14)
    ax.set_ylabel(y_label, fontsize=14)
    plt.xticks(rotation=45 if group_by_col == 'tag_name' else 0,
               ha='right' if group_by_col == 'tag_name' else 'center')

    if mode == 'percentage':
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(plt.FuncFormatter('{:.0f}%'.format))

    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.legend(title='エリア', bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.tight_layout(rect=[0, 0, 0.85, 1])

    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    print(f"グラフを '{output_path}' に保存しました。")
    plt.close(fig)


def plot_trends_stacked_bar_graph(df, time_col, title_prefix, output_filename, mode='percentage'):
    """ 部門別の時系列推移グラフを作成する（割合/実時間） """
    print(
        f"\n--- {title_prefix} ({'割合' if mode == 'percentage' else '実時間'}) の推移グラフ作成開始 ---")

    counts = df.groupby([time_col, 'department', 'place_name']
                        ).size().reset_index(name='count')

    value_col = ''
    y_label = ''
    if mode == 'percentage':
        total_counts = counts.groupby([time_col, 'department'])[
            'count'].sum().reset_index(name='total_count')
        merged_df = pd.merge(counts, total_counts, on=[time_col, 'department'])
        merged_df['percentage'] = 100 * \
            merged_df['count'] / merged_df['total_count']
        value_col = 'percentage'
        y_label = '滞在割合 (%)'
    else:  # mode == 'duration'
        merged_df = counts
        merged_df['duration'] = merged_df['count'] * TIME_INTERVAL_MINUTES
        value_col = 'duration'
        y_label = '合計滞在時間 (分)'

    pivot_df = merged_df.pivot_table(
        index=[time_col, 'department'], columns='place_name', values=value_col
    ).fillna(0)

    departments = pivot_df.index.get_level_values('department').unique()
    if len(departments) == 0:
        print(f"描画対象の部門データがありません: {title_prefix}")
        return

    fig, axes = plt.subplots(nrows=len(departments), ncols=1, figsize=(
        16, 6 * len(departments)), sharex=True)
    if len(departments) == 1:
        axes = [axes]

    for i, department in enumerate(departments):
        ax = axes[i]
        dept_data = pivot_df.loc[(slice(None), department), :]
        dept_data.index = dept_data.index.get_level_values(
            time_col).astype(str)
        dept_data.plot(kind='bar', stacked=True, ax=ax,
                       colormap='tab20', width=0.8)

        ax.set_title(f"{title_prefix} - {department}", fontsize=16)
        ax.set_ylabel(y_label, fontsize=12)
        if mode == 'percentage':
            ax.set_ylim(0, 100)
            ax.yaxis.set_major_formatter(plt.FuncFormatter('{:.0f}%'.format))
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax.legend(title='エリア', bbox_to_anchor=(1.02, 1), loc='upper left')

    plt.xlabel('期間', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout(rect=[0, 0, 0.9, 1])

    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    print(f"グラフを '{output_path}' に保存しました。")
    plt.close(fig)


def main():
    """ メイン処理 """
    print(f"--- 処理開始: {INPUT_CSV_FILE} を読み込みます ---")
    try:
        df = pd.read_csv(INPUT_CSV_FILE, dtype={'tag_id': str})
        df['datetime'] = pd.to_datetime(df['datetime'])
    except FileNotFoundError:
        print(f"エラー: ファイル '{INPUT_CSV_FILE}' が見つかりません。")
        return

    print(f"処理前のデータ件数: {len(df)} 件")
    if TAGS_TO_EXCLUDE:
        df = df[~df['tag_id'].isin(TAGS_TO_EXCLUDE)]
        print(f"除外タグを除いた後のデータ件数: {len(df)} 件")
    if df.empty:
        print("集計対象のデータがありません。")
        return

    # --- 全体期間のグラフを作成 (割合と実時間) ---
    plot_overall_stacked_bar_graph(df.copy(
    ), 'tag_name', '【全体】人物ごとのエリア在席割合', 'overall_person_stay_percentage.png', mode='percentage')
    plot_overall_stacked_bar_graph(df.copy(
    ), 'tag_name', '【全体】人物ごとのエリア在席時間', 'overall_person_stay_duration.png', mode='duration')
    plot_overall_stacked_bar_graph(df.copy(), 'department', '【全体】部門ごとのエリア在席割合',
                                   'overall_department_stay_percentage.png', mode='percentage')
    plot_overall_stacked_bar_graph(df.copy(
    ), 'department', '【全体】部門ごとのエリア在席時間', 'overall_department_stay_duration.png', mode='duration')

    # --- 時系列推移グラフを作成 (割合と実時間) ---
    df['date'] = df['datetime'].dt.to_period('D')
    df['week'] = df['datetime'].dt.to_period('W')

    plot_trends_stacked_bar_graph(df.copy(), 'date', '部門別 滞在エリア割合の推移 (日別)',
                                  'department_trends_daily_percentage.png', mode='percentage')
    plot_trends_stacked_bar_graph(df.copy(
    ), 'date', '部門別 滞在エリア実時間の推移 (日別)', 'department_trends_daily_duration.png', mode='duration')
    plot_trends_stacked_bar_graph(df.copy(), 'week', '部門別 滞在エリア割合の推移 (週別)',
                                  'department_trends_weekly_percentage.png', mode='percentage')
    plot_trends_stacked_bar_graph(df.copy(), 'week', '部門別 滞在エリア実時間の推移 (週別)',
                                  'department_trends_weekly_duration.png', mode='duration')

    print("\n--- すべての処理が完了しました ---")


if __name__ == '__main__':
    main()
