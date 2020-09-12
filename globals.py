import os
from aiogram import Bot
from telethon import TelegramClient

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
client = TelegramClient(DIR_PATH + '/data' + '/feed_session',
                        int(os.environ['API_ID']),
                        os.environ['API_HASH'])
bot = Bot(token=os.environ['BOT_TOKEN'])
USER_ID: int = int(os.environ['USER_ID'])
MARK_AS_UNREAD: bool = bool(os.environ['MARK_UNREAD'])
