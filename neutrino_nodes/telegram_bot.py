import telebot, requests, json, time
import traceback
from telebot.apihelper import ApiTelegramException
import os, sys
from requests.exceptions import ConnectionError, ReadTimeout

height_url = "http://address_of_your_height_file" #  for example "https://some_address.com/height.txt"
token = "telegram_bot_token" # find in Telegram @BotFather and use command /newbot
bot = telebot.TeleBot(token)

@bot.message_handler(content_types=['text'])

def response(message):
    global some_count
    some_count = 0
    msg = message.text.strip().lower()
    if msg == "/start":
        while True:
            if some_count == 200:
                break
            if some_count == 0 or some_count>60:
                url = 'http://nodes.wavesplatform.com/blocks/height'
                response_decoded_json = requests.get(url)
                response_json = response_decoded_json.json()
                height = int(response_json['height'])
                height_node = int(requests.get(height_url).json())
                out_text = "height="+str(height)+" height_node="+str(height_node)+" /stop"
                if some_count == 0:
                    bot.send_message(message.from_user.id, out_text)
                else:
                    if abs(height-height_node)>=3:
                        bot.send_message(message.from_user.id, out_text)
                some_count = 1
            some_count = some_count+1
            time.sleep(1)

    if msg == "/stop":
        some_count = 200
        bot.send_message(message.from_user.id, "Bot is stopped. /start ")

try:
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
except (ConnectionError, ReadTimeout) as e:
    sys.stdout.flush()
    os.execv(sys.argv[0], sys.argv)
else:
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
