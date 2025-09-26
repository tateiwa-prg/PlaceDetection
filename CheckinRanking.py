import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import japanize_matplotlib

# --- 設定項目 ---
# ----------------------------------------------------------------------
# --- 基本設定 ---
# 解析対象のExcelファイル
EXCEL_DATA_FOLDER = 'data'
EXCEL_FILE_NAME = '辻アプリ_20250926.xlsx'

# グラフの出力先フォルダとファイル名
OUTPUT_FOLDER = 'output_files'
OUTPUT_IMAGE_FILE = 'check_in_ranking.png'

# --- 集計期間設定 ---
# 開始日と終了日を指定 (この日付も集計に含まれます)
START_DATE = '2025-09-16'
END_DATE = '2025-09-25'
# ----------------------------------------------------------------------


def create_checkin_ranking_graph():
    """
    Excelデータから指定期間内のチェックイン回数ランキングを算出し、
    棒グラフとして保存する。
    """
    # --- 1. ファイルパスの準備 ---
    excel_file_path = os.path.join(EXCEL_DATA_FOLDER, EXCEL_FILE_NAME)

    # 出力先フォルダがなければ作成
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    output_image_path = os.path.join(OUTPUT_FOLDER, OUTPUT_IMAGE_FILE)

    # --- 2. Excelデータの読み込み ---
    try:
        print(f"STEP 1: '{excel_file_path}' を読み込みます...")
        df = pd.read_excel(excel_file_path)
    except FileNotFoundError:
        print(f"エラー: ファイル '{excel_file_path}' が見つかりません。")
        return
    except Exception as e:
        print(f"エラー: Excelファイルの読み込み中にエラーが発生しました: {e}")
        return

    # --- 3. データの前処理とフィルタリング ---
    # CheckInTime列をdatetime型に変換（エラーは無視）
    df['CheckInTime'] = pd.to_datetime(df['CheckInTime'], errors='coerce')
    # 日付変換でエラーになった行（NaT）を削除
    df.dropna(subset=['CheckInTime'], inplace=True)

    # 開始日と終了日をdatetime型に変換
    start_dt = pd.to_datetime(START_DATE)
    # 終了日はその日の終わり（23:59:59）までを範囲に含める
    end_dt = pd.to_datetime(END_DATE) + \
        pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    # 指定期間内のデータに絞り込む
    mask = (df['CheckInTime'] >= start_dt) & (df['CheckInTime'] <= end_dt)
    filtered_df = df[mask]

    if filtered_df.empty:
        print("指定された期間に該当するチェックインデータがありませんでした。")
        return

    print(f"STEP 2: {START_DATE} から {END_DATE} までのデータを集計します。")

    # --- 4. チェックイン回数の集計 ---
    # Userごとのチェックイン回数をカウントし、降順にソート
    checkin_counts = filtered_df['User'].value_counts().reset_index()
    checkin_counts.columns = ['User', 'CheckinCount']  # 列名を分かりやすく変更

    print("チェックイン回数ランキング:")
    print(checkin_counts)

    # --- 5. グラフの描画 ---
    print(f"STEP 3: グラフを描画して '{output_image_path}' に保存します...")
    plt.style.use('seaborn-v0_8-talk')  # グラフのスタイルを指定
    fig, ax = plt.subplots(figsize=(12, 8))

    # 棒グラフを作成
    sns.barplot(x='CheckinCount', y='User',
                data=checkin_counts, ax=ax, palette='viridis')

    # グラフの各種設定
    ax.set_title(f'チェックイン回数ランキング ({START_DATE} ~ {END_DATE})', fontsize=18)
    ax.set_xlabel('チェックイン回数', fontsize=14)
    ax.set_ylabel('ユーザー名', fontsize=14)
    ax.grid(axis='x', linestyle='--', alpha=0.7)

    # 棒グラフに数値ラベルを追加
    for container in ax.containers:
        ax.bar_label(container, fmt='%d回', padding=5)

    # レイアウトを自動調整
    plt.tight_layout()

    # --- 6. グラフの保存と表示 ---
    plt.savefig(output_image_path, dpi=300)
    print("グラフの保存が完了しました。")
    # plt.show() # ローカル環境で即座に確認したい場合はこの行のコメントを外す


if __name__ == '__main__':
    create_checkin_ranking_graph()
