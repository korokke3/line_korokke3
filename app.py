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
		"- 射撃モード: フルオート(/単発)\n"
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
		"- 射撃モード: 3点バースト/単発\n"
		"- 連射速度(バースト): 15.5発/秒\n"
		"- バースト連射ディレイ: 0.28秒\n"
		"- 連射速度(単発): 6.4発/秒\n"
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
		"- 射撃モード: フルオート/単発\n"
		"- 連射速度(共通): 10発/秒\n"
		"- 連射速度(アンビル・単発): 2.9発/秒\n"
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
		"- 射撃モード: フルオート/単発\n"
		"- 連射速度(共通): 13.5発/秒\n"
		"- 連射速度(アンビル・単発): 3.5発/秒\n"
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
		"- 短縮名: R-99\n"
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
