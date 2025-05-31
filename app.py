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
		"- 製造企業1: 시완(Siwhan) Industries\n"
		"- 製造企業2: Wonyeon\n"
		"- 連射速度: 11.2発/秒\n"
		"- ダメージ: 素20 頭26 脚15\n"
		"- 装填数: 素18 白21 青25 紫29\n"
		"- リロード時間(秒): 素3.2 白3.09 青2.99 紫2.88\n"
		"- スピンアップ時間(秒): 素0.42 タボチャ0.01\n"
		"- 弾速: 約774メートル/秒\n"
		"- 初取り出しモーション時間: 1.5秒\n"
		"- ヘッドショット有効距離: 300メートル\n"
		"- ADS時移動速度倍率: x0.5"
    ),
    "?R301": (
        "🔫 **R-301 カービン**\n"
        "- ライトアモを使用\n"
        "- 安定したフルオートAR\n"
        "- 中距離で信頼性の高い性能"
    ),
    "?ウィングマン": (
        "🔫 **ウィングマン**\n"
        "- ヘビーアモを使用（現在はスナイパーアモの可能性も）\n"
        "- 高ダメージの単発ピストル\n"
        "- エイム力が求められるが当たれば強力"
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
                ltm_modes = []
                if "ltm" in data:
                    ltm = data["ltm"]
                    cur_mode = ltm["current"]
                    next_mode = ltm["next"]

                    known_mix = ["Control", "Gun Run", "Team Deathmatch"]
                    if cur_mode["eventName"] in known_mix:
                        # ミックステープ
                        reply_lines.append("\U0001F3AE ミックステープ")
                        reply_lines.append(f"現在のモード: {translate_map_name(cur_mode['eventName'])}（マップ: {translate_map_name(cur_mode['map'])}、あと{cur_mode['remainingTimer']}）")
                        reply_lines.append(f"次のモード: {translate_map_name(next_mode['eventName'])}（マップ: {translate_map_name(next_mode['map'])}）")
                        reply_lines.append("")
                    else:
                        # 期間限定モード
                        reply_lines.append("⏱ 期間限定モード")
                        reply_lines.append(f"現在: {translate_map_name(cur_mode['eventName'])}（マップ: {translate_map_name(cur_mode['map'])}、あと{cur_mode['remainingTimer']}）")
                        reply_lines.append(f"次: {translate_map_name(next_mode['eventName'])}（マップ: {translate_map_name(next_mode['map'])}）")
                        reply_lines.append("")
                else:
                    reply_lines.append("⏱ 期間限定モード")
                    reply_lines.append("現在: ❌ 開催されていません")

                reply_text = "\n".join(reply_lines)

        elif user_message in WEAPON_RESPONSES:
            reply_text = WEAPON_RESPONSES[user_message]

        else:
            return  # それ以外は無視

        # ここで共通の返信処理
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text])
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
