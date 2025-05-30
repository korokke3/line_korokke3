# -*- coding: utf-8 -*-

import os
import sys
import requests
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
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
        "🔫 ボセックコンパウンドボウ\n"
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
    )
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
    user_message = event.message.text.strip()
    reply_text = None  # 初期化

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if user_message == "?マップ":
            api_key = os.getenv("APEX_API_KEY")
            url = f"https://api.mozambiquehe.re/maprotation?auth={api_key}&version=2"

            try:
                response = requests.get(url)
                data = response.json()
                app.logger.info("APIレスポンス: %s", data)

                reply_lines = []

                # カジュアル
                if "battle_royale" in data:
                    br = data["battle_royale"]
                    reply_lines.append("\U0001F5FA カジュアル")
                    reply_lines.append(f"現在のマップ: {translate_map_name(br['current']['map'])}（あと{br['current']['remainingTimer']}）")
                    reply_lines.append(f"次のマップ: {translate_map_name(br['next']['map'])}")
                    reply_lines.append("")

                # ランク
                if "ranked" in data:
                    rk = data["ranked"]
                    reply_lines.append("\U0001F3C6 ランクリーグ")
                    reply_lines.append(f"現在のマップ: {translate_map_name(rk['current']['map'])}（あと{rk['current']['remainingTimer']}）")
                    reply_lines.append(f"次のマップ: {translate_map_name(rk['next']['map'])}")
                    reply_lines.append("")

                # LTM
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

            except Exception as e:
                app.logger.error(f"APIエラー: {e}")
                reply_text = "APIの取得に失敗しました。後でもう一度試してください。"

        elif user_message in WEAPON_RESPONSES:
            reply_text = WEAPON_RESPONSES[user_message]

        else:
            return  # それ以外は無視

        if reply_text:
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
