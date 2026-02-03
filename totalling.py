import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import japanize_matplotlib
import os
import matplotlib.cm as cm
import numpy as np

# --- 設定項目 ---
INPUT_CSV_FILE = 'closest_node_per_interval_with_names.csv'
OUTPUT_FOLDER = 'output_files'
TIME_INTERVAL_MINUTES = 5

TAGS_TO_EXCLUDE = ['f0f8f2cad80b', '0081f98607c1']


def plot_overall_stacked_bar_graph(df, group_by_col, title, output_filename, sorted_names, color_map, mode='percentage'):
    """ 期間全体での滞在グラフを作成する """
    print(f"--- {title} 作成開始 ---")
    counts = df.groupby([group_by_col, 'display_name']
                        ).size().reset_index(name='count')
    if counts.empty:
        return

    if mode == 'percentage':
        total_counts = counts.groupby(group_by_col)['count'].sum()
        counts['percentage'] = counts.apply(
            lambda row: 100 * row['count'] / total_counts[row[group_by_col]], axis=1)
        value_col, y_label = 'percentage', '滞在割合 (%)'
    else:
        counts['duration'] = counts['count'] * TIME_INTERVAL_MINUTES
        value_col, y_label = 'duration', '合計滞在時間 (分)'

    pivot_df = counts.pivot(
        index=group_by_col, columns='display_name', values=value_col).fillna(0)
    existing_sorted = [n for n in sorted_names if n in pivot_df.columns]
    pivot_df = pivot_df[existing_sorted]

    # ★ カスタムカラーリストを作成
    colors = [color_map[col] for col in pivot_df.columns]

    figsize = (16, 9) if group_by_col == 'tag_name' else (12, 7)
    fig, ax = plt.subplots(figsize=figsize)
    pivot_df.plot(kind='bar', stacked=True, ax=ax, color=colors,
                  width=0.8, edgecolor='white', linewidth=0.1)

    ax.set_title(title, fontsize=20, pad=20)
    ax.set_ylabel(y_label, fontsize=14)
    plt.xticks(rotation=45 if group_by_col == 'tag_name' else 0,
               ha='right' if group_by_col == 'tag_name' else 'center')
    if mode == 'percentage':
        ax.set_ylim(0, 100)

    ax.legend(title='エリア [階-位置_名称]', bbox_to_anchor=(1.02,
              1), loc='upper left', fontsize=9)
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.savefig(os.path.join(OUTPUT_FOLDER, output_filename), dpi=300)
    plt.close(fig)


def plot_trends_stacked_bar_graph(df, time_col, title_prefix, output_filename, sorted_names, color_map, mode='percentage'):
    """ 部門別の時系列推移グラフを作成する """
    print(f"--- {title_prefix} ({mode}) 作成開始 ---")
    counts = df.groupby([time_col, 'department', 'display_name']
                        ).size().reset_index(name='count')

    if mode == 'percentage':
        total_counts = counts.groupby([time_col, 'department'])[
            'count'].sum().reset_index(name='total_count')
        merged_df = pd.merge(counts, total_counts, on=[time_col, 'department'])
        merged_df['percentage'] = 100 * \
            merged_df['count'] / merged_df['total_count']
        value_col, y_label = 'percentage', '滞在割合 (%)'
    else:
        merged_df = counts
        merged_df['duration'] = merged_df['count'] * TIME_INTERVAL_MINUTES
        value_col, y_label = 'duration', '合計滞在時間 (分)'

    pivot_df = merged_df.pivot_table(
        index=[time_col, 'department'], columns='display_name', values=value_col).fillna(0)
    existing_sorted = [n for n in sorted_names if n in pivot_df.columns]
    pivot_df = pivot_df[existing_sorted]
    colors = [color_map[col] for col in pivot_df.columns]

    departments = pivot_df.index.get_level_values('department').unique()
    if len(departments) == 0:
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
        dept_data.plot(kind='bar', stacked=True, ax=ax, color=colors,
                       width=0.8, edgecolor='white', linewidth=0.1)
        ax.set_title(f"{title_prefix} - {department}", fontsize=16)
        ax.set_ylabel(y_label, fontsize=12)
        if mode == 'percentage':
            ax.set_ylim(0, 100)
        ax.legend(title='エリア [階-位置_名称]', bbox_to_anchor=(1.02,
                  1), loc='upper left', fontsize=8)

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout(rect=[0, 0, 0.9, 1])
    plt.savefig(os.path.join(OUTPUT_FOLDER, output_filename), dpi=300)
    plt.close(fig)


def main():
    try:
        df = pd.read_csv(INPUT_CSV_FILE, dtype={'tag_id': str})
        df['datetime'] = pd.to_datetime(df['datetime'])
    except FileNotFoundError:
        return

    # 1. 表示名の生成
    def format_display_name(row):
        f = f"{int(float(row['floor']))}" if pd.notnull(row['floor']) else "?"
        w = f"{int(float(row['west_to_east']))}" if pd.notnull(
            row['west_to_east']) else "?"
        return f"{f}-{w}_{row['place_name']}"
    df['display_name'] = df.apply(format_display_name, axis=1)

    # 2. フロア別カラーマップの自動生成
    place_info = df[['display_name', 'floor',
                     'west_to_east']].drop_duplicates()
    place_info['floor'] = pd.to_numeric(place_info['floor'], errors='coerce')
    place_info['west_to_east'] = pd.to_numeric(
        place_info['west_to_east'], errors='coerce')
    place_info = place_info.sort_values(by=['floor', 'west_to_east'])

    sorted_display_names = place_info['display_name'].unique().tolist()

    # フロアごとの色相セット
    cmaps = ['Blues', 'Oranges', 'Greens', 'Reds',
             'Purples', 'Greys', 'YlOrBr', 'PuRd']
    unique_floors = sorted(place_info['floor'].dropna().unique())
    floor_to_cmap = {floor: cmaps[i % len(cmaps)]
                     for i, floor in enumerate(unique_floors)}

    color_map = {}
    for floor in unique_floors:
        floor_data = place_info[place_info['floor'] == floor]
        n_items = len(floor_data)
        cmap = plt.get_cmap(floor_to_cmap[floor])
        # 0.3〜0.9の範囲でグラデーション（薄すぎず濃すぎない範囲）
        colors = [cmap(val) for val in np.linspace(0.4, 0.9, n_items)]
        for name, color in zip(floor_data['display_name'], colors):
            color_map[name] = color

    # フロア不明用
    for name in sorted_display_names:
        if name not in color_map:
            color_map[name] = (0.5, 0.5, 0.5, 1.0)

    if TAGS_TO_EXCLUDE:
        df = df[~df['tag_id'].isin(TAGS_TO_EXCLUDE)]

    # 3. グラフ作成実行
    args = (df, sorted_display_names, color_map)
    # 全体
    plot_overall_stacked_bar_graph(df.copy(
    ), 'tag_name', '【全体】人物別割合', 'overall_person_percentage.png', *args[1:], mode='percentage')
    plot_overall_stacked_bar_graph(df.copy(
    ), 'tag_name', '【全体】人物別時間', 'overall_person_duration.png', *args[1:], mode='duration')
    plot_overall_stacked_bar_graph(df.copy(
    ), 'department', '【全体】部門別割合', 'overall_dept_percentage.png', *args[1:], mode='percentage')
    plot_overall_stacked_bar_graph(df.copy(
    ), 'department', '【全体】部門別時間', 'overall_dept_duration.png', *args[1:], mode='duration')

    # 時系列
    df['date'], df['week'], df['month'] = df['datetime'].dt.to_period(
        'D'), df['datetime'].dt.to_period('W'), df['datetime'].dt.to_period('M')
    for period, label in zip(['date', 'week', 'month'], ['日別', '週別', '月別']):
        plot_trends_stacked_bar_graph(df.copy(
        ), period, f'部門別推移 ({label})', f'trends_{label}_percentage.png', *args[1:], mode='percentage')
        plot_trends_stacked_bar_graph(df.copy(
        ), period, f'部門別推移 ({label})', f'trends_{label}_duration.png', *args[1:], mode='duration')

    print(f"完了: {OUTPUT_FOLDER}")


if __name__ == '__main__':
    main()
