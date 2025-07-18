# -*- coding: utf-8 -*-

import os
import sys
import requests
import sqlite3
import re
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
	Configuration, ApiClient, MessagingApi,
	ReplyMessageRequest, TextMessage, ImageMessage
)
from linebot.v3.webhooks import (
	MessageEvent, TextMessageContent
)
from linebot.v3.exceptions import InvalidSignatureError

app = Flask(__name__)

# 環境変数から取得
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
if channel_secret is None or channel_access_token is None:
	print("環境変数が足りません")
	sys.exit(1)

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)
import sqlite3

# DBに接続する関数
def get_db_connection():
    conn = sqlite3.connect("dictionary.db")
    conn.row_factory = sqlite3.Row
    return conn

# 辞書を追加する関数
def add_dictionary_entry(term, content, user_id, is_private):
    conn = get_db_connection()
    conn.execute(
        "INSERT OR REPLACE INTO dictionary (term, content, added_by, is_private) VALUES (?, ?, ?, ?)",
        (term, content, user_id, int(is_private))
    )
    conn.commit()
    conn.close()

# 辞書を削除する関数
def delete_dictionary_entry(term, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dictionary WHERE term = ?", (term,))
    row = cursor.fetchone()
    if row and row["added_by"] == user_id:
        cursor.execute("DELETE FROM dictionary WHERE term = ?", (term,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# 英語マップ名→日本語マップ名の辞書
MAP_TRANSLATIONS = {
	"World's Edge": "ワールズエッジ",
	"Fragment East": "フラグメント・イースト",
	"Fragment West": "フラグメント・ウエスト",
	"Fragment": "フラグメント",
	"Storm Point": "ストームポイント",
	"Broken Moon": "ブロークンムーン",
	"Olympus": "オリンパス",
	"Kings Canyon": "キングスキャニオン",
	"Thunderdome": "サンダードーム",
	"Overflow": "オーバーフロー",
	"Habitat 4": "生息地4",
	"Encore": "アンコール",
	"Production Yard": "生産工場",
	"Skulltown": "スカルタウン",
	"Monument": "モニュメント",
	"E-District": "エレクトロ地区",
	"Siphon": "ラバサイフォン",
	"Estates": "エステート",
	"Control": "コントロール", # モード名
	"Gun Run": "ガンゲーム",
	"Team Deathmatch": "チームデスマッチ",
	"Unknown": "不明、エラー"
}

# 武器の返答辞書
WEAPON_RESPONSES = {
	"?ハボック": (
		"🔫 ハボックライフル\n"
		"- 短縮名: ハボック\n"
		"- 武器種: アサルトライフル\n"
		"- 使用アモ: エネルギーアモ\n"
		"- 製造元(共同開発): 시완(Siwhan) Industries\n"
		"- 製造元(共同開発): Wonyeon\n"
		"- 射撃モード: フルオート(/セミオート)\n"
		"- 連射速度: 11.2発/秒\n"
		"- ダメージ: 素20 頭26 脚15\n"
		"- 装填数: 素18 白21 青25 紫29\n"
		"- リロード時間(秒): 素3.20 白3.09 青2.99 紫2.88\n"
		"- スピンアップ時間(秒): 素0.42 タボチャ0.01\n"
		"- 弾速: 約774メートル/秒\n"
		"- 初取り出しモーション時間: 1.5秒\n"
		"- ヘッドショット有効距離: 300メートル\n"
		"- ADS時移動速度倍率: x0.5"
	),
	"?ヘムロック": (
		"🔫 ヘムロックバーストAR\n"
		"- 短縮名: ヘムロック\n"
		"- 武器種: アサルトライフル\n"
		"- 使用アモ: ヘビーアモ\n"
		"- 製造元: Wonyeon\n"
		"- 射撃モード: 3点バースト/セミオート\n"
		"- 連射速度(バースト): 15.5発/秒\n"
		"- バースト連射ディレイ: 0.28秒\n"
		"- 連射速度(セミオート): 6.4発/秒\n"
		"- ダメージ: 素20 頭26 脚15\n"
		"- 装填数: 素21 白24 青27 紫30\n"
		"- タクティカルリロード時間(秒): 素2.40 白2.32 青2.24 紫2.16\n"
		"- フルリロード時間(秒): 素2.85 白2.76 青2.66 紫2.57\n"
		"- 弾速: 約698メートル/秒\n"
		"- 初取り出しモーション時間: 1.25秒\n"
		"- ヘッドショット有効距離: 300メートル\n"
		"- ADS時移動速度倍率: x0.5"
	),
	"?フラットライン": (
		"🔫 VK-47フラットライン\n"
		"- 短縮名: フラットライン\n"
		"- 武器種: アサルトライフル\n"
		"- 使用アモ: ヘビーアモ\n"
		"- 製造元: Wonyeon\n"
		"- 射撃モード: フルオート/セミオート\n"
		"- 連射速度(共通): 10発/秒\n"
		"- 連射速度(アンビル・セミオート): 2.9発/秒\n"
		"- ダメージ: 素19 頭25 脚14\n"
		"- 装填数: 素19 白23 青27 紫29\n"
		"- タクティカルリロード時間(秒): 素2.40 白2.32 青2.24 紫2.16\n"
		"- フルリロード時間(秒): 素3.10 白3.00 青2.89 紫2.79\n"
		"- 弾速: 約609メートル/秒\n"
		"- 初取り出しモーション時間: 1.25秒\n"
		"- ヘッドショット有効距離: 300メートル\n"
		"- ADS時移動速度倍率: x0.5"
	),
	"?R-301": (
		"🔫 R-301カービン\n"
		"- 短縮名: R-301\n"
		"- 武器種: アサルトライフル\n"
		"- 使用アモ: ライトアモ\n"
		"- 製造元: Lastimosa Armory\n"
		"- 射撃モード: フルオート/セミオート\n"
		"- 連射速度(共通): 13.5発/秒\n"
		"- 連射速度(アンビル・セミオート): 3.5発/秒\n"
		"- ダメージ: 素14 頭28 脚11\n"
		"- 装填数: 素21 白23 青28 紫31\n"
		"- タクティカルリロード時間(秒): 素2.40 白2.32 青2.24 紫2.16\n"
		"- フルリロード時間(秒): 素3.2 白3.09 青2.99 紫2.88\n"
		"- 弾速: 約736メートル/秒\n"
		"- 初取り出しモーション時間: 1.1秒\n"
		"- ヘッドショット有効距離: 300メートル\n"
		"- ADS時移動速度倍率: x0.5"
	),
	"?ネメシス": (
		"🔫 ネメシスバーストAR\n"
		"- 短縮名: ネメシス\n"
		"- 武器種: アサルトライフル\n"
		"- 使用アモ: エネルギーアモ\n"
		"- 製造元(デザイナー): ランパート\n"
		"- 製造元: The Sisters\n"
		"- 射撃モード: 4点バースト\n"
		"- 連射速度(共通): 18発/秒\n"
		"- バースト連射ディレイ(開始時): 0.31秒\n"
		"- バースト連射ディレイ(最大時): 0.19秒\n"
		"- ダメージ: 素17 頭22 脚13\n"
		"- 装填数: 素20 白24 青28 紫32\n"
		"- タクティカルリロード時間(秒): 素2.70 白2.61 青2.52 紫2.43\n"
		"- フルリロード時間(秒): 素3.00 白2.90 青2.80 紫2.70\n"
		"- 弾速: 約812メートル/秒\n"
		"- 初取り出しモーション時間: 1.3秒\n"
		"- ヘッドショット有効距離: 300メートル\n"
		"- ADS時移動速度倍率: x0.5"
	),
	"?オルタネーター": (
		"🔫 オルタネーターSMG\n"
		"- 短縮名: オルタネーター\n"
		"- 武器種: サブマシンガン\n"
		"- 使用アモ: ライトアモ\n"
		"- 製造元: Burrell Defense\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 10発/秒\n"
		"- ダメージ: 素18 頭23 脚14\n"
		"- 装填数: 素20 白24 青27 紫29\n"
		"- タクティカルリロード時間(秒): 素1.90 白1.84 青1.77 紫1.71\n"
		"- フルリロード時間(秒): 素2.23 白2.16 青2.08 紫2.01\n"
		"- 弾速: 約482メートル/秒\n"
		"- 初取り出しモーション時間: 1.2秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x0.75"
	),
	"?プラウラー": (
		"🔫 プラウラーバーストPDW\n"
		"- 短縮名: プラウラー\n"
		"- 武器種: サブマシンガン\n"
		"- 使用アモ: ヘビーアモ\n"
		"- 製造元: Lastimosa Armory\n"
		"- 射撃モード: 5点バースト/フルオート\n"
		"- 連射速度(バースト): 21発/秒\n"
		"- バースト射撃ディレイ: 0.28秒\n"
		"- 連射速度(フルオート): 13.25発/秒\n"
		"- ダメージ: 素16 頭20 脚13\n"
		"- 装填数: 素20 白25 青30 紫35\n"
		"- タクティカルリロード時間(秒): 素2.00 白1.93 青1.87 紫1.80\n"
		"- フルリロード時間(秒): 素2.60 白2.51 青2.43 紫2.34\n"
		"- 弾速: 約457メートル/秒\n"
		"- 初取り出しモーション時間: 1.4秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x0.75"
	),
	"?R-99": (
		"🔫 R-99 SMG\n"
		"- 短縮名: R-99\n"
		"- 武器種: サブマシンガン\n"
		"- 使用アモ: ライトアモ\n"
		"- 製造元: Lastimosa Armory\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 18発/秒\n"
		"- ダメージ: 素13 頭16 脚10\n"
		"- 装填数: 素18 白21 青24 紫27\n"
		"- タクティカルリロード時間(秒): 素1.80 白1.74 青1.68 紫1.62\n"
		"- フルリロード時間(秒): 素2.45 白2.37 青2.29 紫2.21\n"
		"- 弾速: 約482メートル/秒\n"
		"- 初取り出しモーション時間: 1.0秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x0.825"
	),
	"?ボルト": (
		"🔫 ボルトSMG\n"
		"- 短縮名: ボルト\n"
		"- 武器種: サブマシンガン\n"
		"- 使用アモ: エネルギーアモ\n"
		"- 製造元: 不詳\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 12発/秒\n"
		"- ダメージ: 素16 頭20 脚12\n"
		"- 装填数: 素20 白22 青24 紫27\n"
		"- タクティカルリロード時間(秒): 素1.44 白1.39 青1.34 紫1.3\n"
		"- フルリロード時間(秒): 素2.03 白1.96 青1.89 紫1.83\n"
		"- 弾速: 約596メートル/秒\n"
		"- 初取り出しモーション時間: 1.0秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x0.75"
	),
	"?CAR": (
		"🔫 C.A.R. SMG\n"
		"- 短縮名: CAR\n"
		"- 武器種: サブマシンガン\n"
		"- 使用アモ: ヘビーアモ/ライトアモ\n"
		"- 製造元: 시완(Siwhan) Industries\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 15.4発/秒\n"		
		"- ダメージ: 素14 頭18 脚11\n"
		"- 装填数: 素20 白23 青25 紫28\n"
		"- タクティカルリロード時間(秒): 素1.70 白1.64 青1.59 紫1.53\n"
		"- フルリロード時間(秒): 素2.13 白2.06 青1.99 紫1.92\n"
		"- 弾速: 約456メートル/秒\n"
		"- 初取り出しモーション時間: 1.1秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x0.75"
	),
	"?ディヴォーション": (
		"🔫 ディヴォーションLMG\n"
		"- 短縮名: ディヴォーション\n"
		"- 武器種: ライトマシンガン\n"
		"- 使用アモ: エネルギーアモ\n"
		"- 製造元: 不詳\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度(初速): 5発/秒\n"
		"- 連射速度(タボチャ初速): 6.8発/秒\n"
		"- 連射速度(最大): 15発/秒\n"
		"- 最大連射速度までの時間: 不詳\n"
		"- 最大連射速度までの時間(タボチャ): 0.85秒\n"
		"- ダメージ: 素16 頭20 脚14\n"
		"- 装填数: 素36 白40 青44 紫52\n"
		"- タクティカルリロード時間(秒): 素2.80 白2.71 青2.52 (紫 不詳)\n"
		"- フルリロード時間(秒): 素3.63 白3.51 青3.27 (紫 不詳)\n"
		"- 弾速: 約850メートル/秒\n"
		"- 初取り出しモーション時間: 1.45秒\n"
		"- ヘッドショット有効距離: 57メートル\n"
		"- ADS時移動速度倍率: x0.4"
	),
	"?L-スター": (
		"🔫 L-スターEMG\n"
		"- 短縮名: L-スター\n"
		"- 武器種: ライトマシンガン\n"
		"- 使用アモ: エネルギーアモ\n"
		"- 製造元: Wonyeon\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 10発/秒\n"		
		"- ダメージ: 素19 頭24 脚16\n"
		"- 連射時オーバーヒートする弾数: 素24 白26 青28 紫30\n"
		"- クールダウン開始時間: 0.08秒\n"
		"- 標準ストック、拡張マガジンによるクールダウン率倍率: 素100% 白96.7% 青93.3% 紫(金)90%\n"
		"- オーバーヒート時クール(秒): 素1.19 白1.15 青1.11 紫1.07 金0.83\n"
		"- リロード時間(秒): 現在はなし、不詳\n"
		"- 弾速: 約610メートル/秒\n"
		"- 初取り出しモーション時間: 1.45秒\n"
		"- ヘッドショット有効距離: 57メートル\n"
		"- ADS時移動速度倍率: x0.4"
	),
	"?スピットファイア": (
		"🔫 M600スピットファイア\n"
		"- 短縮名: スピットファイア\n"
		"- 武器種: ライトマシンガン\n"
		"- 使用アモ: ライトアモ\n"
		"- 製造元: 시완(Siwhan) Industries\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 9発/秒\n"		
		"- ダメージ: 素21 頭26 脚18\n"
		"- 装填数: 素35 白40 青45 紫50\n"
		"- タクティカルリロード時間(秒): 素3.40 白3.29 青3.17 紫3.06\n"
		"- フルリロード時間(秒): 素4.20 白4.06 青3.92 紫3.78\n"
		"- 弾速: 約697メートル/秒\n"
		"- 初取り出しモーション時間: 1.45秒\n"
		"- ヘッドショット有効距離: 57メートル\n"
		"- ADS時移動速度倍率: x0.4"
	),
	"?ランページ": (
		"🔫 ランページLMG\n"
		"- 短縮名: ランページ\n"
		"- 武器種: ライトマシンガン\n"
		"- 使用アモ: ヘビーアモ\n"
		"- 製造元(デザイナー): ランパート\n"
		"- 製造元: SWCC\n"
		"- 特殊ギミック: チャージ\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 5発/秒\n"
		"- 連射速度(チャージ時): 6.5発/秒\n"
		"- ダメージ: 素29 頭36 脚25\n"
		"- 装填数: 素28 白32 青36 紫40\n"
		"- タクティカルリロード時間(秒): 素3.10 白3.00 青2.89 紫2.79\n"
		"- フルリロード時間(秒): 素4.00 白3.87 青3.73 紫3.60\n"
		"- チャージ時間: 3.7秒\n"
		"- チャージ持続時間: 90秒\n"
		"- チャージ時射撃1発ごとの持続時間減少量: 0.6秒/射撃\n"
		"- 弾速: 約672メートル/秒\n"
		"- 初取り出しモーション時間: 1.45秒\n"
		"- ヘッドショット有効距離: 57メートル\n"
		"- ADS時移動速度倍率: x0.4"
	),
	"?G7スカウト": (
		"🔫 G7スカウト\n"
		"- 短縮名: G7スカウト\n"
		"- 武器種: マークスマン\n"
		"- 使用アモ: ライトアモ\n"
		"- 製造元: Lastimosa Armory\n"
		"- 射撃モード: セミオート(/2点バースト)\n"
		"- 連射速度: 3.9発/秒\n"
		"- 連射速度(バースト): 10発/秒\n"
		"- バースト射撃ディレイ: 0.375秒\n"
		"- ダメージ: 素36 頭58 脚27\n"
		"- 装填数: 素10 白15 青18 紫20\n"
		"- タクティカルリロード時間(秒): 素2.40 白2.32 青2.24 紫2.16\n"
		"- フルリロード時間(秒): 素3.00 白2.90 青2.80 紫2.70\n"
		"- 弾速: 約761メートル/秒\n"
		"- 初取り出しモーション時間: 1.42秒\n"
		"- ヘッドショット有効距離: 450メートル\n"
		"- ADS時移動速度倍率: x0.425"
	),
	"?トリプルテイク": (
		"🔫 トリプルテイク\n"
		"- 短縮名: トリプルテイク\n"
		"- 武器種: マークスマン\n"
		"- 使用アモ: ミシックエネルギーアモ (エネルギーアモ)\n"
		"- 製造元: Burrell Defense\n"
		"- 射撃モード: セミオート\n"
		"- 連射速度: 1.75発/秒\n"
		"- チョーク速度: 0.5秒\n"
		"- ダメージ: 素23x3 頭37x3 脚21x3\n"
		"- 装填数: 12発\n"
		"- 予備弾薬: 72発\n"
		"- タクティカルリロード時間(秒): 2.60\n"
		"- フルリロード時間(秒): 3.40\n"
		"- 弾速: 約812メートル/秒\n"
		"- 初取り出しモーション時間: 1.42秒\n"
		"- ヘッドショット有効距離: 450メートル\n"
		"- ADS時移動速度倍率: x0.425"
	),
	"?30-30": (
		"🔫 30-30リピーター\n"
		"- 短縮名: G7スカウト\n"
		"- 武器種: マークスマン\n"
		"- 使用アモ: ヘビーアモ\n"
		"- 製造元: Holdener Arms\n"
		"- 射撃モード: セミオート\n"
		"- 連射速度: 3.85発/秒\n"
		"- チャージ時間: 0.35秒\n"
		"- ADS後チャージ開始ディレイ: 0.3秒\n"
		"- ダメージ: 素43~65 頭69~104 脚37~55\n"
		"- スカピ装着時頭ダメージ: 86~130ダメージ\n"
		"- 装填数: 素6 白7 青8 紫10\n"
		"- リロード時間(1発目): (通常)0.33秒 (フル)0.75秒\n"
		"- リロード時間: 0.4秒/1発\n"
		"- 弾速: 約736メートル/秒\n"
		"- 初取り出しモーション時間: 1.4秒\n"
		"- ヘッドショット有効距離: 300メートル\n"
		"- ADS時移動速度倍率: x0.425"
	),
	"?ボセック": (
		"🏹 ボセックコンパウンドボウ\n"
		"- 短縮名: ボセック\n"
		"- 武器種: マークスマン\n"
		"- 使用アモ: アロー\n"
		"- 製造元: 不詳\n"
		"- 射撃モード: セミオート\n"
		"- 連射速度: 3.0発/秒\n"
		"- 最大チャージ連射速度: 1.15発/秒\n"
		"- チャージ時間: 0.54秒\n"
		"- 射撃に必要な最低チャージ割合: 15%\n"
		"- チャージレベル(0から5): 0%, 10%, 20%, 35%, 55%, 100%\n"
		"- ADS後チャージ開始ディレイ: 0.3秒\n"
		"- ダメージ(レベル1): 素35 頭56 脚28\n"
		"- ダメージ(レベル2): 素42 頭67 脚33\n"
		"- ダメージ(レベル3): 素47 頭75 脚37\n"
		"- ダメージ(レベル4): 素54 頭86 脚43\n"
		"- ダメージ(レベル5): 素65 頭106 脚52\n"
		"- 装填数: 40発\n"
		"- 弾速: 約254~711メートル/秒\n"
		"- 初取り出しモーション時間: 1.4秒\n"
		"- ヘッドショット有効距離: 300メートル\n"
		"- ADS時移動速度倍率(Lv0~5): x0.85 x0.82 x0.78 x0.73 x0.66 x0.50"
	),
	"?チャージライフル": (
		"🔫 チャージライフル\n"
		"- 武器種: スナイパーライフル\n"
		"- 使用アモ: スナイパーアモ\n"
		"- 製造元: Vinson Dynamics\n"
		"- 射撃モード: セミオート/フルオート\n"
		"- 連射速度(セミオート): 0.43発/秒\n"
		"- 連射速度(フルオート): 1.4発/秒\n"	
		"- チャージ時間(セミオート): 0.85秒\n"
		"- チャージ時間(フルオート): 約0.5秒\n"
		"- ダメージ(セミオート): 素75-110 頭135-198 脚68-99\n"
		"- ダメージ(フルオート): 素56-83 頭101-149 脚50-74\n"
		"- 装填数: 素6 白7 青8 紫9\n"
		"- タクティカルリロード時間(秒): 素3.50 白3.38 青3.27 紫3.15\n"
		"- フルリロード時間(秒): 素4.60 白4.45 青4.29 紫4.14\n"
		"- 弾速: 約864メートル/秒\n"
		"- 初取り出しモーション時間: 1.5秒\n"
		"- ヘッドショット有効距離: 不詳(おそらく無限)\n"
		"- ADS時移動速度倍率: x0.35"
	),
	"?ロングボウ": (
		"🔫 ロングボウDMR\n"
		"- 武器種: スナイパーライフル\n"
		"- 短縮名: ロングボウ\n"
		"- 使用アモ: スナイパーアモ\n"
		"- 製造元: Wonyeon\n"
		"- 射撃モード: セミオート\n"
		"- 連射速度: 1.3発/秒\n"
		"- ダメージ *(スカピ): 素60 頭108(頭129) 脚48\n"
		"- 装填数: 素6 白8 青10 紫12\n"
		"- タクティカルリロード時間(秒): 素2.66 白2.58 青2.48 紫2.39\n"
		"- フルリロード時間(秒): 素3.66 白3.54 青3.41 紫3.29\n"
		"- 弾速: 約774メートル/秒\n"
		"- 初取り出しモーション時間: 1.6秒\n"
		"- ヘッドショット有効距離: 750メートル\n"
		"- ADS時移動速度倍率: x0.35"
	),
	"?センチネル": (
		"🔫 センチネル\n"
		"- 武器種: スナイパーライフル\n"
		"- 使用アモ: スナイパーアモ\n"
		"- 製造元: Paradinha Arsenal\n"
		"- 射撃モード: セミオート\n"
		"- 連射速度: 約0.51発/秒\n"
		"- リチャンバー時間: 1.6秒\n"
		"- 増幅時間: 150秒\n"
		"- 射撃による増幅時間の減少量: 14秒/発\n"
		"- ダメージ(通常): 素70 頭126 脚63\n"
		"- ダメージ(増幅): 素88 頭158 脚72\n"
		"- 装填数: 素4 白5 青6 紫7\n"
		"- タクティカルリロード時間(秒): 素3.00 白2.90 青2.80 紫2.70\n"
		"- フルリロード時間(秒): 素4.00 白3.87 青3.73 紫3.60\n"
		"- 弾速: 約787メートル/秒\n"
		"- 初取り出しモーション時間: 1.6秒\n"
		"- ヘッドショット有効距離: 750メートル\n"
		"- ADS時移動速度倍率: x0.35"
	),
	"?クレーバー": (
		"🔫 クレーバー.50スナイパー\n"
		"- 武器種: スナイパーライフル\n"
		"- 短縮名: クレーバー\n"
		"- 使用アモ: ミシックスナイパーアモ\n"
		"- 製造元: Lastimosa Armory\n"
		"- 射撃モード: セミオート\n"
		"- 連射速度: 約0.42発/秒\n"
		"- リチャンバー時間: 1.6秒 (ADS中リチャンバー不可)\n"
		"- ダメージ: 素150 頭210 脚120\n"
		"- 装填数: 4発\n"
		"- 予備弾薬数: 12発\n"
		"- タクティカルリロード時間: 3.2秒\n"
		"- フルリロード時間: 4.3秒\n"
		"- 弾速: 約749メートル/秒\n"
		"- 初取り出しモーション時間: 1.5秒\n"
		"- ヘッドショット有効距離: 750メートル\n"
		"- ADS時移動速度倍率: x0.35"
	),
	"?EVA-8": (
		"🔫 EVA-8オート\n"
		"- 武器種: ショットガン\n"
		"- 短縮名: EVA-8\n"
		"- 使用アモ: ショットガンシェル(アモ)\n"
		"- 製造元: Wonyeon\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 素3.1 白3.35 青約3.57 紫金3.85発/秒\n"
		"- 発射ペレット数: 8ペレット\n"
		"- １ペレット当りのダメージ: 6ダメージ\n"
		"- 最大ダメージ: 48ダメージ\n"
		"- 装填数: 8弾\n"
		"- タクティカルリロード時間(秒): 素2.75 白2.65 青2.56 紫2.48\n"
		"- フルリロード時間(秒): 素3.00 白2.9 青2.79 紫2.7\n"
		"- 弾速: 約406メートル/秒\n"
		"- 初取り出しモーション時間: 1.35秒\n"
		"- ヘッドショット有効距離: 38メートル (ただし判定なし)\n"
		"- ADS時移動速度倍率: x0.9"
	),
	"?マスティフ": (
		"🔫 マスティフショットガン\n"
		"- 武器種: ショットガン\n"
		"- 短縮名: マスティフ\n"
		"- 使用アモ: ショットガンシェル(アモ)\n"
		"- 製造元: Lastimosa Armory\n"
		"- 射撃モード: セミオート\n"
		"- 連射速度: 素1.1 白約1.22 青約1.27 紫金約1.32発/秒\n"
		"- 発射ペレット数: 6ペレット\n"
		"- １ペレット当りのダメージ: 胴16ダメージ\n"
		"- 最大ダメージ: 96ダメージ\n"
		"- 装填数: 5弾\n"
		"- タクティカルリロード時間(秒): 素2.75 白2.65 青2.56 紫2.48\n"
		"- リロード時間(1発目): (通常)0.90秒 (フル)1.6秒\n"
		"- リロード時間(2発目以降): 0.51秒/1発\n"
		"- リロード時間(最後の1発): 0.55秒/1発\n"
		"- 弾速: 約305メートル/秒\n"
		"- 初取り出しモーション時間: 1.25秒\n"
		"- ヘッドショット有効距離: 38メートル (ただし判定なし)\n"
		"- ADS時移動速度倍率: x0.9"
	),
	"?モザンビーク": (
		"🔫 モザンビークショットガン\n"
		"＊アキンボ状態性能は下記参照\n"
		"- 武器種: ショットガン\n"
		"- 短縮名: モザンビーク\n"
		"- 使用アモ: ショットガンシェル(アモ)\n"
		"- 製造元: Altamirano Armory\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 素約2.7 白約2.93 青約3.1 紫金3.2発/秒\n"
		"- 発射ペレット数: 3ペレット\n"
		"- １ペレット当りのダメージ: 素・脚17 頭21\n"
		"- 胴体の最大ダメージ: 51ダメージ\n"
		"- 装填数: 5弾\n"
		"- タクティカルリロード時間(秒): 2.10秒\n"
		"- フルリロード時間(秒): 2.60秒\n"
		"- 弾速: 約254メートル/秒\n"
		"- 初取り出しモーション時間: 1秒\n"
		"- 取り出しモーション時間: 0.2秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x1.0\n"
		"- \n"
		"🔫 モザンビーク-二丁拳銃\n"
		"＊シングル状態性能は上記参照\n"
		"- 武器種: ショットガン\n"
		"- 短縮名: モザンビーク\n"
		"- 使用アモ: ショットガンシェル(アモ)\n"
		"- 製造元: Altamirano Armory\n"
		"- 射撃モード: フルオート(二丁/シングル切替有)\n"
		"- 連射速度: 素約2.92 白約3.22 青3.35 紫金3.5発/秒\n"
		"- 発射ペレット数: 3ペレット\n"
		"- １ペレット当りのダメージ: 素・脚17 頭21\n"
		"- 胴体の最大ダメージ: 51ダメージ\n"
		"- 装填数: 10弾\n"
		"- タクティカルリロード時間(秒): 2.50秒\n"
		"- フルリロード時間(秒): 3.00秒\n"
		"- 弾速: 約254メートル/秒\n"
		"- 初取り出しモーション時間: 1.09秒\n"
		"- 取り出しモーション時間: 1秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x1.0"
		"- 備考: アキンボ状態時にADSすると、スコープは仕様不可だがペレットの拡散は狭まる。"
	),
	"?ピースキーパー": (
		"🔫 ピースキーパー\n"
		"- 武器種: ショットガン\n"
		"- 短縮名: ピースキーパー\n"
		"- 使用アモ: ミシックショットガンシェル\n"
		"- 製造元: 不詳\n"
		"- 射撃モード: セミオート\n"
		"- 連射速度: 約0.83/秒\n"
		"- リチャンバー時間: 0.95秒\n"		
		"- 発射ペレット数: 9ペレット\n"
		"- １ペレット当りのダメージ: 素・脚12ダメージ 頭15ダメージ\n"
		"- 胴最大ダメージ: 108ダメージ\n"
		"- チャージ速度: 0.6秒\n"
		"- 装填数: 5弾^\n"
		"- 予備弾薬数: 20弾^\n"
		"- タクティカルリロード時間: 2.45秒\n"
		"- フルリロード時間: 3.35秒\n"
		"- 弾速: 約508メートル/秒\n"
		"- 初取り出しモーション時間: 1.4秒\n"
		"- ヘッドショット有効距離(通常): 100メートル\n"
		"- ヘッドショット有効距離(チャージ時): 300メートル\n"
		"- ADS時移動速度倍率: x0.9"
	),
	"?RE-45": (
		"🔫 RE-45オート\n"
		"- 短縮名: RE-45\n"
		"- 武器種: ピストル\n"
		"- 使用アモ: ライトアモ\n"
		"- 製造元: Paradinha Arsenal\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 9発/秒\n"		
		"- ダメージ: 素14 頭18 脚12\n"
		"- 装填数: 素20 白21 青23 紫26\n"
		"- タクティカルリロード時間: 1.5秒\n"
		"- フルリロード時間(秒): 1.95\n"
		"- 弾速: 約495メートル/秒\n"
		"- 初取り出しモーション時間: 1.1秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x1.0"
	),
	"?P2020": (
		"🔫 P2020\n"
		"＊アキンボ状態性能は下記参照\n"
		"- 武器種: ピストル\n"
		"- 使用アモ: ライトアモ\n"
		"- 製造元: Lastimosa Armory\n"
		"- 射撃モード: セミオート\n"
		"- 連射速度: 7発/秒\n"
		"- ダメージ: 素24 頭30 脚22\n"
		"- 装填数: 素8 白9 青10 紫11\n"
		"- リロード時間: 1.25秒\n"
		"- 弾速: 約470メートル/秒\n"
		"- 初取り出しモーション時間: 1.1秒\n"
		"- 取り出しモーション時間: 0.225秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x1.0\n"
		"- \n"
		"🔫 P2020-二丁拳銃\n"
		"- 短縮名: P2020\n"
		"- 武器種: ピストル\n"
		"- 使用アモ: ライトアモ\n"
		"- 製造元: Lastimosa Armory\n"
		"- 射撃モード: フルオート(二丁/シングル切替有)\n"
		"- 連射速度: 8発/秒\n"
		"- ダメージ: 素24 頭30 脚22\n"
		"- 装填数: 素16 白18 青20 紫22\n"
		"- タクティカルリロード時間(秒): 2.10秒\n"
		"- フルリロード時間(秒): 2.60秒\n"
		"- 弾速: 約470メートル/秒\n"
		"- 初取り出しモーション時間: 1.2秒\n"
		"- 取り出しモーション時間: 1秒\n"
		"- ヘッドショット有効距離: 38メートル\n"
		"- ADS時移動速度倍率: x1.0\n"
		"- 備考: アキンボ状態時にADSすると、スコープは仕様不可だが弾の拡散は狭まる。"
	),
	"?ウィングマン": (
		"🔫 ウィングマン\n"
		"- 短縮名: ウィングマン\n"
		"- 武器種: ピストル\n"
		"- 使用アモ: スナイパーアモ\n"
		"- 製造元: Paradinha Arsenal\n"
		"- 射撃モード: フルオート\n"
		"- 連射速度: 2.8発/秒\n"		
		"- ダメージ*(スカピ): 素48 頭72(頭96) 脚43\n"
		"- 装填数: 素5 白6 青7 紫8\n"
		"- リロード時間: 2.1秒\n"
		"- 弾速: 約457メートル/秒\n"
		"- 初取り出しモーション時間: 1.45秒\n"
		"- ヘッドショット有効距離: 254メートル\n"
		"- ADS時移動速度倍率: x1.0"
	)
}

# レジェンドの返答辞書
LEGEND_RESPONSES = {
	"?バンガロール": (
		"バンガロール\n"
		"「あなたの選んだ武器で、勝ってあげる。」\n"
		"職業軍人\n"
		"\n"
		"本名: アニータ・ウィリアムズ\n"
		"年齢: 40歳\n"
		"生年: 2695年\n"
		"性別: 女性\n"
		"身長: 183cm\n"
		"体重: 82kg\n"
		"母星: グリッドアイアン\n"
		"レジェンド説明文: 「?バンガロール説明文」で表示\n"
		"\n"
		"クラス: アサルト\n"
		"パッシブアビリティ: 「駆け足」\n"
		"スプリント中に被弾すると、移動速度が短時間向上する\n"
		"(詳細な情報は「?駆け足」で表示)\n"
		"\n"
		"戦術アビリティ：「スモークランチャー」\n"
		"発煙缶を高速射出し、着弾時の爆発で煙の壁を作り出す。\n"
		"(詳細な情報は「?スモークランチャー」で表示)\n"
		"\n"
		"アルティメットアビリティ: 「ローリングサンダー」\n"
		"一帯をゆっくりと巡る支援砲撃を要請する。\n"
		"(詳細な情報は「?ローリングサンダー」で表示)"
	)
}

# アビリティの返答辞書
ABILITY_RESPONSES = {
	"?駆け足": (
		"バンガロールのパッシブアビリティ\n"
		"スプリント中に被弾すると、移動速度が短時間向上する。\n"
		"\n"
		"発動条件: スプリント中に自身に攻撃が命中する\n"
		"発動条件2: スプリント中に、敵の銃弾や手榴弾、アビリティなどが自身からおよそ半径5メートル以内を通過した際\n"
		"効果時間: 2秒\n"
		"移動速度倍率: x1.3\n"
		"自我のおまけ情報: ジブのドームシールド(半径5m)内だとだいたい発動するよ！"
	),
	"?スモークランチャー": (
		"バンガロールの戦術アビリティ\n"
		"発煙缶を高速射出し、着弾時の爆発で煙の壁を作り出す。\n"
		"\n"
		"- 最大スタック数: 2\n"
		"- クールタイム: 35秒 (対応アップグレード選択で-5秒)\n"
		"- スモーク半径(1つ当り): 6.5m\n"
		"- 効果時間: 8秒\n"
		"- 起爆時のダメージ: 10\n"
		"- 弾速(初速): 63.5メートル/毎秒\n"
		"- 戦術ボタンを長押しで発射を遅らせることができる。\n"
		"- コントローラーのエイムアシストを無効化することができる。\n"
		"- 着弾後、発射方向垂直に３つに分裂し起爆する。\n"
		"- 起爆から8秒経過後の3秒間ではわずかに薄くなるのみで視界不良は続き、次の1秒間で完全に消散する。\n"
		"- 同じスモーク内の20m以内にいるプレイヤーのアウトラインを白く強調表示する。\n"
		"- 基本スキャン効果のある能力を防ぐことはできない。"
		"- 自我おまけ情報: 起爆後のスモークは半径6.5mの円形が3つ、それぞれ別の当たり判定(ゲーム内では見えないが内部で存在)になるため、スモーク内から同じスモーク内にいるように見える敵にからピンを刺しても敵ピンが刺さらなかったりする。\n"
		" この各スモークの当たり判定は一方向なもので、外側から内側には壁があるように判定が遮断されるが、内側から外側へは遮断されない。\n"
		" そのため、スモークの内側から敵ピンを連打すると(擬似的に)一方的に敵のことを視認できたり、スモークの内側から外側の敵を撃つ場合にはエイムアシストが発動する。"
	),
	"?ローリングサンダー": (
		"バンガロールのアルティメットアビリティ\n"
		"一帯をゆっくりと巡る支援砲撃を要請する。\n"
		"発動するとフレア弾を構え、攻撃キーで投擲。\n"
		"\n"
		"- クールタイム: 270秒 (対応アップグレード選択で-60秒)\n"
		"- 発動からリチャージ開始までの時間: 40秒\n"
		"- 爆発時ダメージ: 30\n"
		"- 爆発半径: 8.9メートル\n"
		"- 設置ミサイル数: 36 (6x6)\n"
		"- フレアの着弾2秒後から、前面およそ70mの範囲に規則的にミサイルを振り注ぎ、各ミサイルが着弾6秒後に爆発する。\n"
		"- 爆発に巻き込まれると、ダメージに加え6秒間の移動速度低下(-25%)と視界不良を受ける。\n"
		"- 爆発は自分に当たる。味方に当たった際ははダメージ以外の効果を与える。"
	)
}

#武器返信の添付画像
WEAPON_IMAGES = {
	"?ハボック": "https://apexlegends.wiki.gg/images/e/ec/HAVOC_Rifle.png",
	"?ヘムロック": "https://apexlegends.wiki.gg/images/7/74/Hemlok_Burst_AR.png",
	"?フラットライン": "https://apexlegends.wiki.gg/images/f/f1/VK-47_Flatline.png",
	"?R-301": "https://apexlegends.wiki.gg/images/f/f1/R-301_Carbine.png",
	"?ネメシス": "https://apexlegends.wiki.gg/images/b/b8/Nemesis_Burst_AR.png",
	"?オルタネーター": "https://apexlegends.wiki.gg/images/e/e9/Alternator_SMG.png",
	"?プラウラー": "https://apexlegends.wiki.gg/images/b/bf/Prowler_Burst_PDW.png",
	"?R-99": "https://apexlegends.wiki.gg/images/d/d5/R-99_SMG.png",
	"?ボルト": "https://apexlegends.wiki.gg/images/6/60/Volt_SMG.png",
	"?CAR": "https://apexlegends.wiki.gg/images/1/13/C.A.R._SMG.png",
	"?ディヴォーション": "https://apexlegends.wiki.gg/images/8/8c/Devotion_LMG.png",
	"?L-スター": "https://apexlegends.wiki.gg/images/0/01/L-STAR_EMG.png",
	"?スピットファイア": "https://apexlegends.wiki.gg/images/f/f2/M600_Spitfire.png",
	"?ランページ": "https://apexlegends.wiki.gg/images/2/20/Rampage_LMG.png",
	"?G7スカウト": "https://apexlegends.wiki.gg/images/e/eb/G7_Scout.png",
	"?トリプルテイク": "https://apexlegends.wiki.gg/images/d/d9/Triple_Take.png",
	"?30-30": "https://apexlegends.wiki.gg/images/8/86/30-30_Repeater.png",
	"?ボセック": "https://apexlegends.wiki.gg/images/0/02/Bocek_Compound_Bow.png",
	"?チャージライフル": "https://apexlegends.wiki.gg/images/2/2b/Charge_Rifle.png",
	"?ロングボウ": "https://apexlegends.wiki.gg/images/4/46/Longbow_DMR.png",
	"?センチネル": "https://apexlegends.wiki.gg/images/9/91/Sentinel.png",
	"?クレーバー": "https://apexlegends.wiki.gg/images/f/f5/Kraber_.50-Cal_Sniper.png",
	"?EVA-8": "https://apexlegends.wiki.gg/images/9/97/EVA-8_Auto.png",
	"?マスティフ": "https://apexlegends.wiki.gg/images/c/c9/Mastiff_Shotgun.png",
	"?モザンビーク": "https://apexlegends.wiki.gg/images/a/ae/Mozambique_Shotgun.png",
	"?ピースキーパー": "https://apexlegends.wiki.gg/images/6/64/Peacekeeper.png",
	"?RE-45": "https://apexlegends.wiki.gg/images/2/25/RE-45_Auto.png",
	"?P2020": "https://apexlegends.wiki.gg/images/c/c1/P2020.png",
	"?ウィングマン": "https://apexlegends.wiki.gg/images/0/09/Wingman.png",
	# 必要に応じて追加
}

#レジェンド返信の添付画像
LEGEND_IMAGES = {
	# "?ハボック": "https://apexlegends.wiki.gg/images/e/ec/HAVOC_Rifle.png",
	# a
}

#レジェンド返信の添付画像
ABILITY_IMAGES = {
	# "?駆け足": "https://apexlegends.wiki.gg/images/e/ec/HAVOC_Rifle.png",
}

def translate_map_name(name):
	return MAP_TRANSLATIONS.get(name, name)

@app.route("/callback", methods=['POST'])
def callback():
	signature = request.headers['X-Line-Signature']
	body = request.get_data(as_text=True)
	app.logger.info("Request body: " + body)

	try:
		handler.handle(body, signature)
	except InvalidSignatureError:
		abort(400)

	return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
	user_message = event.message.text
	messages = None  # 最初に定義しておく

	with ApiClient(configuration) as api_client:
		line_bot_api = MessagingApi(api_client)

		# ?マップの処理
		if user_message == "?マップ":
			api_key = os.getenv("APEX_API_KEY")
			url = f"https://api.mozambiquehe.re/maprotation?auth={api_key}&version=2"

			try:
				response = requests.get(url)
				data = response.json()
				app.logger.info("APIレスポンス: %s", data)

				reply_lines = []

				if "battle_royale" in data:
					br = data["battle_royale"]
					reply_lines.append("\U0001F5FA カジュアル")
					reply_lines.append(f"現在のマップ: {translate_map_name(br['current']['map'])}（あと{br['current']['remainingTimer']}）")
					reply_lines.append(f"次のマップ: {translate_map_name(br['next']['map'])}")
					reply_lines.append("")

				if "ranked" in data:
					rk = data["ranked"]
					reply_lines.append("\U0001F3C6 ランクリーグ")
					reply_lines.append(f"現在のマップ: {translate_map_name(rk['current']['map'])}（あと{rk['current']['remainingTimer']}）")
					reply_lines.append(f"次のマップ: {translate_map_name(rk['next']['map'])}")
					reply_lines.append("")

				if "ltm" in data:
					ltm = data["ltm"]
					cur_mode = ltm["current"]
					next_mode = ltm["next"]
					known_mix = ["Control", "Gun Run", "Team Deathmatch"]
					if cur_mode["eventName"] in known_mix:
						reply_lines.append("\U0001F3AE ミックステープ")
						reply_lines.append(f"現在のモード: {translate_map_name(cur_mode['eventName'])}（マップ: {translate_map_name(cur_mode['map'])}、あと{cur_mode['remainingTimer']}）")
						reply_lines.append(f"次のモード: {translate_map_name(next_mode['eventName'])}（マップ: {translate_map_name(next_mode['map'])}）")
						reply_lines.append("")
					else:
						reply_lines.append("⏱ 期間限定モード")
						reply_lines.append(f"現在: {translate_map_name(cur_mode['eventName'])}（マップ: {translate_map_name(cur_mode['map'])}、あと{cur_mode['remainingTimer']}）")
						reply_lines.append(f"次: {translate_map_name(next_mode['eventName'])}（マップ: {translate_map_name(next_mode['map'])}）")
						reply_lines.append("")
				else:
					reply_lines.append("⏱ 期間限定モード")
					reply_lines.append("現在: ❌ 開催されていません")

				reply_text = "\n".join(reply_lines)
				messages = [TextMessage(text=reply_text)]

			except Exception as e:
				app.logger.error(f"APIエラー: {e}")
				messages = [TextMessage(text="APIの取得に失敗しました。後でもう一度試してください。")]

		# 武器情報の応答
		elif user_message in WEAPON_RESPONSES:
			reply_text = WEAPON_RESPONSES[user_message]
			messages = [TextMessage(text=reply_text)]
			image_url = WEAPON_IMAGES.get(user_message)
			if image_url:
				messages.append(ImageMessage(
					original_content_url=image_url,
					preview_image_url=image_url
				))
				
		# レジェンド情報の応答
		elif user_message in LEGEND_RESPONSES:
			reply_text = LEGEND_RESPONSES[user_message]
			messages = [TextMessage(text=reply_text)]
			image_url = LEGEND_IMAGES.get(user_message)
			if image_url:
				messages.append(ImageMessage(
					original_content_url=image_url,
					preview_image_url=image_url
				))
				
		# アビリティ情報の応答
		elif user_message in ABILITY_RESPONSES:
			reply_text = ABILITY_RESPONSES[user_message]
			messages = [TextMessage(text=reply_text)]
			# image_url = ABILITY_IMAGES.get(user_message)
			# if image_url:
			#	messages.append(ImageMessage(
			#		original_content_url=image_url,
			#		preview_image_url=image_url
			#	))

		# 辞書機能の処理
		elif user_message.startswith("辞書 "):
		    args = user_message.split(maxsplit=2)
		    if len(args) < 2:
		        messages = [TextMessage(text="辞書コマンドの形式が正しくありません。")]
		    else:
		        subcmd = args[1]
		        # 追加コマンド
		        if subcmd == "追加" and len(args) == 3:
		            parts = args[2].split(maxsplit=1)
		            if len(parts) < 2:
		                messages = [TextMessage(text="「辞書 追加 単語 内容」の形式で送信してください。")]
		            else:
		                term = parts[0]
		                content = parts[1]
		                is_private = False
		                if content.endswith("--s") or content.endswith("-self"):
		                    is_private = True
		                    content = content.rsplit(maxsplit=1)[0]  # 最後の --s を除去
		                add_dictionary_entry(term, content, event.source.user_id, is_private)
		                messages = [TextMessage(text=f"「{term}」を辞書に追加しました。{'（自分専用）' if is_private else ''}")]
		        # 削除コマンド
		        elif subcmd == "削除" and len(args) == 3:
		            term = args[2]
		            if delete_dictionary_entry(term, event.source.user_id):
		                messages = [TextMessage(text=f"「{term}」を削除しました。")]
		            else:
		                messages = [TextMessage(text=f"削除できませんでした。自分が追加した単語のみ削除できます。")]
		        else:
		            messages = [TextMessage(text="「辞書 追加 単語 内容」または「辞書 削除 単語」の形式で送信してください。")]

		# 📌 呼び出し機能（単語だけ送信）
		elif True:
		    conn = get_db_connection()
		    cursor = conn.cursor()
		    term = user_message.strip()
		    user_id = event.source.user_id
		
		    cursor.execute(
		        "SELECT content FROM dictionary WHERE term = ? AND (is_private = 0 OR added_by = ?)",
		        (term, user_id)
		    )
		    row = cursor.fetchone()
		    conn.close()
		
		    if row:
		        reply_text = f"{term}：{row['content']}"
		        messages = [TextMessage(text=reply_text)]

		# 「辞書」のみ または 「辞書 [頭文字] [ページ数]」で一覧表示
		elif user_message.strip().startswith("辞書"):
		    match = re.match(r"辞書(?:\s+([^\d\s])?)?(?:\s+(\d+))?", user_message.strip())
		    initial = match.group(1) if match else None
		    page = int(match.group(2)) if match and match.group(2) else 1
		
		    conn = get_db_connection()
		    cursor = conn.cursor()
		    user_id = event.source.user_id
		
		    # 条件付きクエリ作成
		    sql = "SELECT term, content, added_by, is_private FROM dictionary WHERE (is_private = 0 OR added_by = ?)"
		    params = [user_id]
		    if initial:
		        sql += " AND term LIKE ?"
		        params.append(initial + "%")
		    
		    sql += " ORDER BY term ASC"
		    cursor.execute(sql, params)
		    rows = cursor.fetchall()
		    conn.close()
		
		    if not rows:
		        messages = [TextMessage(text="一致する単語が見つかりませんでした。")]
		    else:
		        per_page = 10
		        total_pages = (len(rows) + per_page - 1) // per_page
		        page = max(1, min(page, total_pages))
		        start = (page - 1) * per_page
		        end = start + per_page
		        display_rows = rows[start:end]
		
		        reply_lines = [f"📘 登録単語一覧（{page}/{total_pages}ページ）"]
		        for row in display_rows:
		            privacy = "（自分専用）" if row["is_private"] and row["added_by"] == user_id else ""
		            if not row["is_private"] or row["added_by"] == user_id:
		                reply_lines.append(f"・{row['term']}：{row['content']}{privacy}")
		        messages = [TextMessage(text="\n".join(reply_lines))]

		if user_message == "時間割":
			reply_text = (
				"月曜日の時間割は、\n"
				"1,理科\n"
				"2,音楽\n"
				"3,英語\n"
				"4,社会\n"
				"5,国語\n"
				"6,総合\n"
				" \n"
				"火曜日の時間割は、\n"
				"1,数学\n"
				"2,理科\n"
				"3,英語\n"
				"4,書写\n"
				"5,保健体育\n"
				"6,学活\n"
				" \n"
				"水曜日の時間割は、\n"
				"1,美術\n"
				"2,社会\n"
				"3,国語\n"
				"4,数学\n"
				"5,理科\n"
				"6,道徳\n"
				" \n"
				"木曜日の時間割は、\n"
				"1,社会\n"
				"2,数学\n"
				"3,体育\n"
				"4,体育\n"
				"5,英語\n"
				"6,総合\n"
				"\n"
				"金曜日の時間割は、\n"
				"1,数学\n"
				"2,国語\n"
				"3,家庭科\n"
				"4,技術\n"
				"5,英語\n"
				"6,なし\n"
				"\n"
				"となっております♪\n"
				"特別授業や変更となっている日は 、\n"
				"他の人に聞いたり教えたりしてくださいね。"
			)
			messages = [TextMessage(text=reply_text)]
		
		elif user_message == "?ヘルプ":
			reply_text = (
				"使用できるコマンド一覧：\n"
				"・?ヘルプ - コマンドの一覧を表示\n"
				"・?マップ - 現在のカジュアル・ランク・ミックステープのマップを表示\n"
				"以下武器情報表示\n"
				"・?ハボック ・?フラットライン\n"
				"・?ヘムロック ・?R-301\n"
				"・?ネメシス\n"
				"・?オルタネーター ・?プラウラー\n"
				"・?R-99 ・?ボルト\n"
				"・?CAR\n"
				"・?ディヴォーション ・?L-スター\n"
				"・?スピットファイア ・?ランページ\n"
				"・?G7スカウト ・?トリプルテイク\n"
				"・?30-30 ・?ボセック\n"
				"・?チャージライフル ・?ロングボウ\n"
				"・?クレーバー ・?センチネル\n"
				"・?EVA-8 ・?マスティフ\n"
				"・?ピースキーパー ・?モザンビーク\n"
				"・?RE-45 ・?ウィングマン"
			)
			messages = [TextMessage(text=reply_text)]
				
		# messages が定義された場合のみ返信
		if messages:
			line_bot_api.reply_message(
				ReplyMessageRequest(
					reply_token=event.reply_token,
					messages=messages
				)
			)



if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5000))
	app.run(host="0.0.0.0", port=port)
