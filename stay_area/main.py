import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import japanize_matplotlib
import matplotlib.dates as mdates

# --- 設定 ---
INPUT_CSV = 'closest_node_per_interval_with_names.csv'
OUTPUT_IMAGE = 'stay_area/area_occupancy_trend.png'


def plot_area_occupancy_trend(file_path):
    # 1. データの読み込み
    df = pd.read_csv(file_path, parse_dates=['datetime'])

    # 2. 時間とエリアごとにユニークなタグID（人数）をカウント
    # 5分ごとの集計データであることを前提に、datetimeとplace_nameでグループ化
    occupancy_df = df.groupby(['datetime', 'place_name'])[
        'tag_id'].nunique().reset_index()
    occupancy_df.columns = ['datetime', 'place_name', 'user_count']

    # 3. グラフ描画（ピボットテーブルに変換して、データがない時間を0で埋める）
    plot_data = occupancy_df.pivot(
        index='datetime', columns='place_name', values='user_count').fillna(0)

    # 4. 描画
    plt.figure(figsize=(15, 7))

    # 積み上げグラフにしたい場合は plt.stackplot、
    # 各エリアの動きを比較したい場合は sns.lineplot を使います
    # 今回は各エリアの推移を比較しやすい折れ線グラフを採用
    sns.lineplot(data=occupancy_df, x='datetime',
                 y='user_count', hue='place_name', marker='o')

    # グラフの整形
    plt.title('エリア別・時間帯別 滞在人数推移', fontsize=16)
    plt.xlabel('時刻', fontsize=12)
    plt.ylabel('滞在人数 (人)', fontsize=12)
    plt.grid(True, which='both', linestyle='--', alpha=0.5)

    # X軸のメモリ設定（データが数日にわたる場合を考慮）
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=30)

    # 凡例を外側に配置
    plt.legend(title='エリア名', bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE, dpi=300)
    print(f"グラフを {OUTPUT_IMAGE} に保存しました。")
    plt.show()


if __name__ == '__main__':
    try:
        plot_area_occupancy_trend(INPUT_CSV)
    except FileNotFoundError:
        print(f"エラー: {INPUT_CSV} が見つかりません。先に解析スクリプトを実行してください。")
