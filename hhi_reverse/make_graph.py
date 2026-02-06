import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# =========================================================
# 共通設定
# =========================================================
# OSに合わせて日本語フォントを自動選択
system_name = platform.system()
if system_name == 'Windows':
    plt.rcParams['font.family'] = 'Meiryo'
elif system_name == 'Darwin':  # Mac
    plt.rcParams['font.family'] = 'Hiragino Sans'
else:
    plt.rcParams['font.family'] = 'IPAGothic'

print("データの読み込みを開始します...")

# CSVファイルの読み込み
try:
    df_daily = pd.read_csv('effective_locations_daily.csv')
    df_weekly = pd.read_csv('effective_locations_weekly.csv')
    df_monthly = pd.read_csv('effective_locations_monthly.csv')
except FileNotFoundError as e:
    print(f"エラー: ファイルが見つかりません。先にCSV作成プログラムを実行してください。\n詳細: {e}")
    exit()

print("読み込み完了。グラフ作成を開始します...")

# =========================================================
# 1. 箱ひげ図：期間別（日・週・月）の分布 (Graph 1)
# =========================================================


def create_boxplot(data, period_name, filename, color_palette="Blues"):
    plt.figure(figsize=(15, 8))

    # 中央値が高い順に並べ替え
    # データが存在しない場合はスキップ
    if data.empty:
        print(f"警告: {period_name}のデータが空のためスキップします。")
        return

    sort_order = data.groupby('tag_name')['eff_loc_area'].median(
    ).sort_values(ascending=False).index

    sns.boxplot(
        data=data,
        x='tag_name',
        y='eff_loc_area',
        hue='department',
        dodge=False,
        order=sort_order,
        palette=color_palette  # パレットを指定可能に
    )

    plt.title(f'【{period_name}】人ごとの有効拠点数分布 (エリア単位)', fontsize=16)
    plt.ylabel('有効拠点数', fontsize=12)
    plt.xlabel('氏名', fontsize=12)
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"保存完了: {filename}")


# --- 1-1. 日次 (Daily) ---
create_boxplot(df_daily, "日次", "graph1_daily_distribution.png", "Blues")

# --- 1-2. 週次 (Weekly) ---
create_boxplot(df_weekly, "週次", "graph1_weekly_distribution.png", "Greens")

# --- 1-3. 月次 (Monthly) ---
# ※データが1ヶ月分しかない場合、箱ひげ図ではなく横線のみになる場合があります
create_boxplot(df_monthly, "月次", "graph1_monthly_distribution.png", "Reds")


# =========================================================
# 2. 働き方タイプ分析：日次 vs 月次 (Graph 3 & 4)
# =========================================================

# --- データ結合処理 ---
# それぞれ平均値をとって代表値にする
daily_agg = df_daily.groupby(['tag_name', 'department'])[
    'eff_loc_area'].mean().reset_index()
daily_agg.rename(columns={'eff_loc_area': 'Daily_Avg'}, inplace=True)

weekly_agg = df_weekly.groupby('tag_name')['eff_loc_area'].mean().reset_index()
weekly_agg.rename(columns={'eff_loc_area': 'Weekly_Avg'}, inplace=True)

monthly_agg = df_monthly.groupby(
    'tag_name')['eff_loc_area'].mean().reset_index()
monthly_agg.rename(columns={'eff_loc_area': 'Monthly_Avg'}, inplace=True)

# マージ
merged_df = daily_agg.merge(weekly_agg, on='tag_name', how='outer').merge(
    monthly_agg, on='tag_name', how='outer')
# 欠損がある場合は埋めるか、そのまま表示（今回はそのまま）

# --- Graph 3. 散布図（働き方タイプ分類） ---
plt.figure(figsize=(10, 8))
sns.scatterplot(
    data=merged_df,
    x='Daily_Avg',
    y='Monthly_Avg',
    hue='department',
    style='department',
    s=150,  # 点を大きく
    alpha=0.8
)

# 平均線の描画
plt.axvline(x=merged_df['Daily_Avg'].mean(), color='gray',
            linestyle='--', alpha=0.5, label='日次平均')
plt.axhline(y=merged_df['Monthly_Avg'].mean(),
            color='gray', linestyle='--', alpha=0.5, label='月次平均')

# 名前ラベルの表示
for i in range(merged_df.shape[0]):
    # NaNチェック
    if pd.notna(merged_df.Daily_Avg[i]) and pd.notna(merged_df.Monthly_Avg[i]):
        plt.text(
            merged_df.Daily_Avg[i]+0.02,
            merged_df.Monthly_Avg[i],
            merged_df.tag_name[i],
            fontsize=9, alpha=0.8
        )

plt.title('【分類】働き方タイプマップ (活動量 vs テリトリー)', fontsize=16)
plt.xlabel('日次の活動量 (Daily Avg)', fontsize=12)
plt.ylabel('月次のテリトリー (Monthly Avg)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.3)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig('graph3_workstyle_scatter.png')
plt.close()
print("保存完了: graph3_workstyle_scatter.png")


# =========================================================
# Graph 4 改: 3点ダンベルプロット（日・週・月の推移）
# =========================================================

# データ準備
dumbbell_df = merged_df[['tag_name', 'department',
                         'Daily_Avg', 'Weekly_Avg', 'Monthly_Avg']].copy()

# 月次の値が大きい順に並べ替え（グラフの見た目を整える）
dumbbell_df = dumbbell_df.sort_values('Monthly_Avg', ascending=True)

plt.figure(figsize=(14, 10))

# 1. 横線を描く（日次から月次までの範囲）
# minとmaxを使って、点が前後しても線が引けるようにする
row_min = dumbbell_df[['Daily_Avg', 'Weekly_Avg', 'Monthly_Avg']].min(axis=1)
row_max = dumbbell_df[['Daily_Avg', 'Weekly_Avg', 'Monthly_Avg']].max(axis=1)

plt.hlines(
    y=dumbbell_df['tag_name'],
    xmin=row_min,
    xmax=row_max,
    color='gray',
    alpha=0.3,
    linewidth=2
)

# 2. 日次の点を描く（青）
plt.scatter(
    dumbbell_df['Daily_Avg'],
    dumbbell_df['tag_name'],
    color='#1f77b4',  # 青
    alpha=1.0,
    s=100,
    label='日次平均 (Daily)',
    zorder=3  # 線より手前に表示
)

# 3. 週次の点を描く（オレンジ）
plt.scatter(
    dumbbell_df['Weekly_Avg'],
    dumbbell_df['tag_name'],
    color='#ff7f0e',  # オレンジ
    alpha=1.0,
    s=100,
    label='週次平均 (Weekly)',
    zorder=3
)

# 4. 月次の点を描く（緑）
plt.scatter(
    dumbbell_df['Monthly_Avg'],
    dumbbell_df['tag_name'],
    color='#2ca02c',  # 緑
    alpha=1.0,
    s=100,
    label='月次平均 (Monthly)',
    zorder=3
)

plt.title('期間拡大による有効拠点数の広がり (日→週→月)', fontsize=16)
plt.xlabel('有効拠点数 (エリア単位)', fontsize=12)
plt.ylabel('氏名', fontsize=12)
plt.grid(axis='x', linestyle='--', alpha=0.5)

# 凡例の位置調整
plt.legend(title="集計期間", loc='lower right', framealpha=0.9)
plt.tight_layout()

plt.savefig('graph4_dumbbell_3points.png')
plt.close()
print("保存完了: graph4_dumbbell_3points.png")


print("すべての処理が完了しました。")
