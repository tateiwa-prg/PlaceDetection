import pandas as pd


def merge_latest_tag_data():
    """
    tag_names.csv と processed_tag_data.csv を読み込み、
    各タグの最新の日付と電圧情報を付加したCSVファイルを出力します。
    """
    try:
        # --- 1. CSVファイルの読み込み ---
        tag_names_df = pd.read_csv('tag_names.csv')
        processed_tag_data_df = pd.read_csv('processed_tag_data.csv')
        print("CSVファイルの読み込みが完了しました。")

        # --- 2. 最新のデータのみを抽出 ---
        # 'datetime'列をdatetime型に変換（エラーは無視）
        processed_tag_data_df['datetime'] = pd.to_datetime(
            processed_tag_data_df['datetime'], errors='coerce'
        )
        # 'datetime'でソートし、'tag_id'の重複を削除（最新のものを保持）
        latest_data_df = processed_tag_data_df.sort_values(
            'datetime', ascending=True
        ).drop_duplicates('tag_id', keep='last')
        print("各タグの最新データを抽出しました。")

        # --- 3. データの結合 ---
        # tag_namesデータフレームに、最新の日付と電圧情報を結合
        merged_df = pd.merge(
            tag_names_df,
            # ★変更点: 'datetime'列を追加
            latest_data_df[['tag_id', 'datetime', 'tag_volt']],
            on='tag_id',
            how='left'  # tag_names.csvに存在するすべてのタグを残す
        )
        print("データを結合しました。")

        # --- 4. 結果をCSVファイルに出力 ---
        output_filename = 'tag_voltages_latest.csv'
        merged_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        print(f"処理が完了しました！ 結果は '{output_filename}' に保存されました。")

    except FileNotFoundError as e:
        print(f"エラー: ファイルが見つかりません。")
        print(f"'{e.filename}' が、このスクリプトと同じディレクトリに存在することを確認してください。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")


if __name__ == '__main__':
    merge_latest_tag_data()
