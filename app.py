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


# メッセージイベントの処理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text.strip()

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if user_message == "?マップ":
            api_key = os.getenv("APEX_API_KEY")
            url = f"https://api.mozambiquehe.re/maprotation?auth={api_key}"

            try:
                response = requests.get(url)
                app.logger.info("ステータスコード: %s", response.status_code)
                app.logger.info("レスポンス本文（raw）: %s", response.text)

                data = response.json()
                app.logger.info("APIレスポンス: %s", data)

                if "battle_royale" not in data:
                    reply_text = f"APIエラー: {data.get('Error', '不明なエラー')}"
                else:
                    current_map = data["battle_royale"]["current"]["map"]
                    remaining_timer = data["battle_royale"]["current"]["remainingTimer"]
                    next_map = data["battle_royale"]["next"]["map"]

                    reply_text = f"🗺 現在のマップ: {current_map}\n⏳ 終了まで: {remaining_timer}\n➡️ 次のマップ: {next_map}"

            except Exception as e:
                app.logger.error("マップAPI取得エラー: %s", e)
                reply_text = "マップ情報を取得できませんでした。"

        else:
            # 通常のエコー応答
            reply_text = f"受け取ったメッセージ: {user_message}"

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
