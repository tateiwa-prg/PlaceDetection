'''
指定タグを抜き出すだけ
'''


import pandas as pd

# 1. 元のCSVファイルを読み込む
df = pd.read_csv('processed_tag_data.csv')

# 2. tag_id が 0081f986054d の行だけを抽出
# ※ IDが文字列として認識されるよう、条件を指定します
target_id = '0081f986054d'


filtered_df = df[df['tag_id'] == target_id]

# 3. 結果を新しいCSVファイルとして保存
filtered_df.to_csv('tag_select/output.csv', index=False)

print(f"抽出完了：{len(filtered_df)} 件のデータが見つかりました。")
