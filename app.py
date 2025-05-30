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
    "Control": "コントロール",
    "Gun Run": "ガンゲーム",
    "Team Deathmatch": "チームデスマッチ",
    "Unknown": "不明、エラー"
}

def translate(name):
    return MAP_TRANSLATIONS.get(name, name)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
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

    if user_message != "?マップ":
        return

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        api_key = os.getenv("APEX_API_KEY")
        url = f"https://api.mozambiquehe.re/maprotation?version=2&auth={api_key}"

        try:
            response = requests.get(url)
            data = response.json()

            if "battle_royale" not in data:
                reply_text = f"APIエラー: {data.get('Error', '不明なエラー')}"
            else:
                # カジュアルとランク
                def format_mode(mode, label, emoji):
                    curr = mode.get("current", {})
                    nxt = mode.get("next", {})
                    curr_map = translate(curr.get("map", "不明"))
                    curr_time = curr.get("remainingTimer", "不明")
                    nxt_map = translate(nxt.get("map", "不明"))
                    return f"{emoji} {label} \n現在のマップ: {curr_map}（あと{curr_time}）\n次のマップ: {nxt_map}\n"

                # ミックステープ
                def format_mixtape(mode):
                    curr = mode.get("current", {})
                    nxt = mode.get("next", {})
                    curr_mode = translate(curr.get("gameMode", "不明"))
                    curr_map = translate(curr.get("map", "不明"))
                    curr_time = curr.get("remainingTimer", "不明")
                    nxt_mode = translate(nxt.get("gameMode", "不明"))
                    nxt_map = translate(nxt.get("map", "不明"))
                    return (
                        f"🎮 ミックステープ \n"
                        f"現在のモード: {curr_mode}（マップ: {curr_map}、あと{curr_time}）\n"
                        f"次のモード: {nxt_mode}（マップ: {nxt_map}）"
                    )

                reply_text = (
                    format_mode(data["battle_royale"], "カジュアル", "🗺") + "\n" +
                    format_mode(data["ranked"], "ランクリーグ", "🏆") + "\n" +
                    format_mixtape(data["mixtape"])
                )

        except Exception as e:
            app.logger.error("マップAPI取得エラー: %s", e)
            reply_text = "マップ情報を取得できませんでした。"

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
