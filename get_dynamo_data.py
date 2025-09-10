import boto3
import pandas as pd
from boto3.dynamodb.conditions import Key
from dotenv import load_dotenv
import os
import logging
import json  # JSONを扱うために追加
import time

# ----------------------------------------------------------------------
# 設定項目 (データを取得したい条件に合わせてここを編集してください)
# ----------------------------------------------------------------------

# DynamoDBのテーブル名
TABLE_NAME = 'mmms_rowdata'

# パーティションキー(pk)の値
PK_VALUE = 'tama_b'

# 取得したい期間の開始日時 (YYYY/MM/DD HH:MM:SS.ms)
START_DATETIME = '2025/09/01 08:00:00.000'

# 取得したい期間の終了日時 (YYYY/MM/DD HH:MM:SS.ms)
END_DATETIME = '2025/10/01 00:00:00.000'

# 出力するCSVファイル名
OUTPUT_CSV_FILE = 'processed_tag_data.csv'

time_sleep_second = 0.5
# ----------------------------------------------------------------------

# ログ設定
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_all_data_from_dynamo():
    """
    DynamoDBから指定された期間のデータを全て取得します。
    """
    # .envファイルから環境変数を読み込む
    load_dotenv()

    if not all([os.getenv('AWS_ACCESS_KEY_ID'), os.getenv('AWS_SECRET_ACCESS_KEY'), os.getenv('AWS_DEFAULT_REGION')]):
        logging.error(
            ".envファイルにAWSの認証情報（AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION）を設定してください。")
        return None

    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)
        logging.info(f"テーブル '{TABLE_NAME}' への接続を試みます。")

        all_items = []
        exclusive_start_key = None

        logging.info(f"データの取得を開始します。")
        logging.info(f"PartitionKey (bukken): {PK_VALUE}")
        logging.info(f"期間 (datetime): {START_DATETIME} から {END_DATETIME}")

        while True:
            query_params = {
                'KeyConditionExpression': Key('bukken').eq(PK_VALUE) & Key('datetime').between(START_DATETIME, END_DATETIME)
            }
            if exclusive_start_key:
                query_params['ExclusiveStartKey'] = exclusive_start_key

            response = table.query(**query_params)
            items = response.get('Items', [])
            if items:
                all_items.extend(items)
                logging.info(
                    f"{len(items)}件のデータを取得しました。(累計: {len(all_items)}件)")

            # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
            # ここを修正しました (LastEvaluatedKey)
            exclusive_start_key = response.get('LastEvaluatedKey', None)
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

            if not exclusive_start_key:
                break
            else:
                logging.info(f"次のページを取得します。{time_sleep_second}秒待機...")
                time.sleep(time_sleep_second)

        logging.info(f"合計 {len(all_items)} 件の全データ取得が完了しました。")
        return all_items

    except Exception as e:
        logging.error(f"DynamoDBからのデータ取得中にエラーが発生しました: {e}")
        return None


def process_and_save_csv(data, filename):
    """
    【NEW】取得したデータを解析・整形し、新しい形式でCSVファイルに保存します。
    """
    if not data:
        logging.warning("処理するデータがありません。CSVファイルは作成されませんでした。")
        return

    # 整形後のデータを格納するリスト
    processed_records = []
    logging.info("rowdataのJSON解析とデータ整形を開始します...")

    for item in data:
        try:
            # 必須項目を取得
            record_datetime = item.get('datetime')
            rowdata_str = item.get('rowdata')

            if not all([record_datetime, rowdata_str]):
                logging.warning(
                    f"必要なデータ(datetime or rowdata)が欠損しているためスキップします: {item}")
                continue

            # rowdata(文字列)をJSONオブジェクト(辞書)に変換
            rowdata_json = json.loads(rowdata_str)

            # node IDを取得
            node_id = rowdata_json.get('node', {}).get('id')
            if not node_id:
                logging.warning(
                    f"node IDが見つかりませんでした。スキップします: {record_datetime}")
                continue

            # tagのリストをループ処理
            for tag in rowdata_json.get('tag', []):
                tag_id = tag.get('id')
                tag_rssi = tag.get('rssi')
                tag_volt = tag.get('volt')

                # tagのIDとRSSIが存在する場合のみレコードを追加
                if tag_id is not None and tag_rssi is not None:
                    processed_records.append({
                        'datetime': record_datetime,
                        'node_id': node_id,
                        'tag_id': tag_id,
                        'tag_rssi': tag_rssi,
                        'tag_volt': tag_volt
                    })

        except json.JSONDecodeError:
            logging.error(f"JSONの解析に失敗しました。スキップします。データ: {item.get('rowdata')}")
        except Exception as e:
            logging.error(f"データ処理中に予期せぬエラーが発生しました: {e}。対象アイテム: {item}")

    if not processed_records:
        logging.warning("整形後のデータが1件もありませんでした。CSVファイルは作成されません。")
        return

    logging.info(f"整形後のレコード {len(processed_records)}件 をCSVファイルに保存します。")
    try:
        # 整形後のデータリストをDataFrameに変換
        df = pd.DataFrame(processed_records)

        # CSVファイルとして保存
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logging.info(f"データを '{filename}' に正常に保存しました。")

    except Exception as e:
        logging.error(f"CSVファイルへの保存中にエラーが発生しました: {e}")


if __name__ == '__main__':
    # 1. DynamoDBからデータを取得
    retrieved_data = get_all_data_from_dynamo()

    # 2. 取得したデータを解析・整形してCSVに保存
    if retrieved_data is not None:
        process_and_save_csv(retrieved_data, OUTPUT_CSV_FILE)
