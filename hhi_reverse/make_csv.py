import pandas as pd
from datetime import timedelta


def _effective_count(series) -> float:
    """
    シェア p_i から 1 / sum(p_i^2) を計算して有効拠点数を返す。
    series: 集計単位内での「カテゴリ」（place / area / floor など）
    """
    counts = series.value_counts(dropna=True).astype(float)
    if counts.empty:
        return 0.0
    p = counts / counts.sum()
    hhi = (p ** 2).sum()
    if hhi == 0:
        return 0.0
    return 1.0 / hhi


def _mode_or_none(series):
    """代表値として最頻値（mode）を1つ返す。なければ None。"""
    if series is None or len(series) == 0:
        return None
    s = series.dropna()
    if s.empty:
        return None
    m = s.mode()
    return m.iloc[0] if not m.empty else None


def make_effective_location_tables(
    src_path: str = "../closest_node_per_interval_with_names.csv",
    daily_path: str = "effective_locations_daily.csv",
    weekly_path: str = "effective_locations_weekly.csv",
    monthly_path: str = "effective_locations_monthly.csv",
) -> None:
    """
    closest_node_per_interval_with_names.csv から
    - effective_locations_daily.csv
    - effective_locations_weekly.csv
    - effective_locations_monthly.csv
    を生成する。

    出力フォーマットは既存ファイルと同じカラム構成:
      日次:   tag_name, date,       eff_loc_place, eff_loc_area, eff_loc_floor, department, floor, west_to_east
      週次:   tag_name, week_start, eff_loc_place, eff_loc_area, eff_loc_floor, department, floor, west_to_east
      月次:   tag_name, month_start,eff_loc_place, eff_loc_area, eff_loc_floor, department, floor, west_to_east
    """

    print("元データを読み込みます:", src_path)
    df = pd.read_csv(src_path)

    # 不要カラムを落とす（あっても無視されるが念のため）
    if "Unnamed: 4" in df.columns:
        df = df.drop(columns=["Unnamed: 4"])

    # 日付系カラムの作成
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date

    # 週の開始日は「その週の月曜日」とする
    weekday = df["datetime"].dt.weekday  # Monday=0
    df["week_start"] = (df["datetime"] - weekday.map(lambda d: timedelta(days=int(d)))).dt.date

    # 月の開始日は「その月の1日」
    df["month_start"] = df["datetime"].dt.to_period("M").dt.to_timestamp().dt.date

    # tag_name が欠損している行は除外
    df = df[df["tag_name"].notna()].copy()

    # ============ 日次テーブル ============
    print("日次テーブルを集計中...")
    daily_records = []
    for (tag, date), sub in df.groupby(["tag_name", "date"]):
        rec = {
            "tag_name": tag,
            "date": date,
            # 場所（place_name 単位）の有効拠点数
            "eff_loc_place": _effective_count(sub["place_name"]),
            # エリア（floor × west_to_east の組み合わせ）単位の有効拠点数
            "eff_loc_area": _effective_count(pd.Series(list(zip(sub["floor"], sub["west_to_east"])))),
            # フロア単位の有効拠点数
            "eff_loc_floor": _effective_count(sub["floor"]),
            "department": _mode_or_none(sub["department"]),
            "floor": _mode_or_none(sub["floor"]),
            "west_to_east": _mode_or_none(sub["west_to_east"]),
        }
        daily_records.append(rec)

    df_daily = pd.DataFrame(daily_records)
    df_daily = df_daily.sort_values(["tag_name", "date"]).reset_index(drop=True)
    df_daily = df_daily[
        [
            "tag_name",
            "date",
            "eff_loc_place",
            "eff_loc_area",
            "eff_loc_floor",
            "department",
            "floor",
            "west_to_east",
        ]
    ]
    df_daily.to_csv(daily_path, index=False)
    print("日次CSVを書き出しました:", daily_path)

    # ============ 週次テーブル ============
    print("週次テーブルを集計中...")
    weekly_records = []
    for (tag, week_start), sub in df.groupby(["tag_name", "week_start"]):
        rec = {
            "tag_name": tag,
            "week_start": week_start,
            "eff_loc_place": _effective_count(sub["place_name"]),
            "eff_loc_area": _effective_count(pd.Series(list(zip(sub["floor"], sub["west_to_east"])))),
            "eff_loc_floor": _effective_count(sub["floor"]),
            "department": _mode_or_none(sub["department"]),
            "floor": _mode_or_none(sub["floor"]),
            "west_to_east": _mode_or_none(sub["west_to_east"]),
        }
        weekly_records.append(rec)

    df_weekly = pd.DataFrame(weekly_records)
    df_weekly = df_weekly.sort_values(["tag_name", "week_start"]).reset_index(drop=True)
    df_weekly = df_weekly[
        [
            "tag_name",
            "week_start",
            "eff_loc_place",
            "eff_loc_area",
            "eff_loc_floor",
            "department",
            "floor",
            "west_to_east",
        ]
    ]
    df_weekly.to_csv(weekly_path, index=False)
    print("週次CSVを書き出しました:", weekly_path)

    # ============ 月次テーブル ============
    print("月次テーブルを集計中...")
    monthly_records = []
    for (tag, month_start), sub in df.groupby(["tag_name", "month_start"]):
        rec = {
            "tag_name": tag,
            "month_start": month_start,
            "eff_loc_place": _effective_count(sub["place_name"]),
            "eff_loc_area": _effective_count(pd.Series(list(zip(sub["floor"], sub["west_to_east"])))),
            "eff_loc_floor": _effective_count(sub["floor"]),
            "department": _mode_or_none(sub["department"]),
            "floor": _mode_or_none(sub["floor"]),
            "west_to_east": _mode_or_none(sub["west_to_east"]),
        }
        monthly_records.append(rec)

    df_monthly = pd.DataFrame(monthly_records)
    df_monthly = df_monthly.sort_values(["tag_name", "month_start"]).reset_index(drop=True)
    df_monthly = df_monthly[
        [
            "tag_name",
            "month_start",
            "eff_loc_place",
            "eff_loc_area",
            "eff_loc_floor",
            "department",
            "floor",
            "west_to_east",
        ]
    ]
    df_monthly.to_csv(monthly_path, index=False)
    print("月次CSVを書き出しました:", monthly_path)

    print("すべてのCSV生成が完了しました。")


if __name__ == "__main__":
    make_effective_location_tables()
