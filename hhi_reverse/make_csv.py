import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# =========================================================
# 設定：日本語フォントとファイル読み込み
# =========================================================
# OSに合わせてフォントを自動選択
system_name = platform.system()
if system_name == 'Windows':
    plt.rcParams['font.family'] = 'Meiryo'
elif system_name == 'Darwin':  # Mac
    plt.rcParams['font.family'] = 'Hiragino Sans'
else:
    plt.rcParams['font.family'] = 'IPAGothic'

print("データの読み込みを開始します...")

# CSVファイルの読み込み（ご提示のコードで出力されたファイル）
try:
    df_daily = pd.read_csv('effective_locations_daily.csv')
    df_weekly = pd.read_csv('effective_locations_weekly.csv')
    df_monthly = pd.read_csv('effective_locations_monthly.csv')
except FileNotFoundError as e:
    print(f"エラー: ファイルが見つかりません。先にCSV作成プログラムを実行してください。\n詳細: {e}")
    exit()

print("読み込み完了。グラフ作成を開始します...")

# =========================================================
# 1. 箱ひげ図：粒度別の分布比較 (Graph 1 & 2)
# =========================================================

# --- 1-1. 推奨（エリア単位）の分布 ---
plt.figure(figsize=(15, 8))
# 中央値が高い順に並べ替え
sort_order = df_daily.groupby(
    'tag_name')['eff_loc_area'].median().sort_values(ascending=False).index

sns.boxplot(
    data=df_daily,
    x='tag_name',
    y='eff_loc_area',
    hue='department',
    dodge=False,
    order=sort_order
)
plt.title('【日次】人ごとの有効拠点数分布 (エリア単位 - 電波ブレ除去版)', fontsize=16)
plt.ylabel('有効拠点数', fontsize=12)
plt.xlabel('氏名', fontsize=12)
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig('graph1_daily_distribution_area.png')
plt.close()
print("保存完了: graph1_daily_distribution_area.png")

# --- 1-2. 粒度の比較（Place vs Area vs Floor） ---
# データを縦持ちに変換
df_melt = df_daily.melt(
    id_vars=['tag_name'],
    value_vars=['eff_loc_place', 'eff_loc_area', 'eff_loc_floor'],
    var_name='Metric',
    value_name='Score'
)

plt.figure(figsize=(16, 8))
sns.boxplot(
    data=df_melt,
    x='tag_name',
    y='Score',
    hue='Metric',
    order=sort_order  # 上記と同じ並び順
)
plt.title('【検証】集計粒度による有効拠点数の違い', fontsize=16)
plt.ylabel('有効拠点数', fontsize=12)
plt.xticks(rotation=45)
# 凡例ラベルの変更
handles, labels = plt.gca().get_legend_handles_labels()
plt.legend(handles=handles, labels=[
           '場所(Place)', 'エリア(Area)', 'フロア(Floor)'], title='集計粒度')
plt.tight_layout()
plt.savefig('graph2_granularity_comparison.png')
plt.close()
print("保存完了: graph2_granularity_comparison.png")


# =========================================================
# 2. 働き方タイプ分析：日次 vs 月次 (Graph 3 & 4)
# =========================================================

# --- データ結合処理 ---
# 日次は「平均値」をとって代表値にする
daily_agg = df_daily.groupby(['tag_name', 'department'])[
    'eff_loc_area'].mean().reset_index()
daily_agg.rename(columns={'eff_loc_area': 'Daily_Avg'}, inplace=True)

# 週次は「平均値」をとる
weekly_agg = df_weekly.groupby('tag_name')['eff_loc_area'].mean().reset_index()
weekly_agg.rename(columns={'eff_loc_area': 'Weekly_Avg'}, inplace=True)

# 月次は「平均値」をとる（1ヶ月分ならそのままの値）
monthly_agg = df_monthly.groupby(
    'tag_name')['eff_loc_area'].mean().reset_index()
monthly_agg.rename(columns={'eff_loc_area': 'Monthly_Avg'}, inplace=True)

# マージ
merged_df = daily_agg.merge(weekly_agg, on='tag_name').merge(
    monthly_agg, on='tag_name')

# --- 2-1. 散布図（働き方タイプ分類） ---
plt.figure(figsize=(10, 8))
sns.scatterplot(
    data=merged_df,
    x='Daily_Avg',
    y='Monthly_Avg',
    hue='department',
    style='department',
    s=100
)

# 平均線の描画
plt.axvline(x=merged_df['Daily_Avg'].mean(), color='gray',
            linestyle='--', alpha=0.5, label='日次平均')
plt.axhline(y=merged_df['Monthly_Avg'].mean(),
            color='gray', linestyle='--', alpha=0.5, label='月次平均')

# 名前ラベルの表示
for i in range(merged_df.shape[0]):
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

# --- 2-2. 棒グラフ（期間による積み上がり） ---
df_period_melt = merged_df.melt(
    id_vars=['tag_name', 'department'],
    value_vars=['Daily_Avg', 'Weekly_Avg', 'Monthly_Avg'],
    var_name='Period',
    value_name='Effective_Locations'
)

plt.figure(figsize=(15, 8))
# 月次の値が大きい順にソート
sort_order_monthly = merged_df.sort_values(
    'Monthly_Avg', ascending=False)['tag_name']

sns.barplot(
    data=df_period_melt,
    x='tag_name',
    y='Effective_Locations',
    hue='Period',
    order=sort_order_monthly,
    palette='viridis'
)
plt.title('期間の拡大に伴う有効拠点数の変化', fontsize=16)
plt.ylabel('有効拠点数', fontsize=12)
plt.xlabel('氏名', fontsize=12)
plt.xticks(rotation=45)
plt.legend(title='集計期間', labels=['日次平均', '週次平均', '月次平均'])
plt.tight_layout()
plt.savefig('graph4_period_stack.png')
plt.close()
print("保存完了: graph4_period_stack.png")

print("すべての処理が完了しました。")
