import asyncio
from collections import OrderedDict

from telethon.tl.types import Message
from telethon.errors import RPCError, ChannelPrivateError
from telethon.tl.functions.messages import MarkDialogUnreadRequest

from database import Database, Channel
from utils import answer
from globals import client, MARK_AS_UNREAD


class Broadcaster:
    __slots__ = ['_db', '_queue', '_current_task']

    def __init__(self, db: Database):
        self._db = db
        self._queue = OrderedDict()
        self._current_task = None

    def __call__(self, event: Database.Event):
        if event.type == 'add':
            self._add_to_queue(self._db[event.feed][event.link])
            if not self._current_task:
                self._new_task()
        elif event.type == 'remove':
            key = event.feed, event.link
            if key in self._queue.keys():
                self._queue.pop(key).close()
            else:
                self._current_task = None

    async def start(self, _=None):
        for channel in self._db.channels():
            self._add_to_queue(channel)
        self._new_task()

    async def stop(self, _=None):
        if not self._current_task:
            return
        self._current_task.remove_done_callback(self._new_task)
        try:
            await asyncio.wait_for(self._current_task, timeout=1)
        except asyncio.TimeoutError:
            pass
        finally:
            for coro in self._queue.values():
                coro.close()
            self._queue.clear()
        self._current_task = None
        self._db.flush()

    async def _forward(self, ch: Channel):
        msgs = await self._messages(ch)
        if msgs:
            try:
                await client.forward_messages(ch.feed, msgs)
            # TODO feed unreachable
            except ConnectionError:
                await asyncio.sleep(60)
            except RPCError as e:
                await answer(f'RPCError occurred while forwarding messages'
                             f' from <a href="{ch.link}">channel</a> to'
                             f' <a href="{ch.feed}">feed</a>: '
                             + e.message
                             + '\nerror code: '
                             + str(e.code)
                             + '\nBot will sleep for 60 seconds',
                             parse_mode='HTML')
                await asyncio.sleep(60)
            else:
                ch.last_id = msgs[-1].id
                self._db.flush()
            if MARK_AS_UNREAD:
                await client(MarkDialogUnreadRequest(ch.feed, True))
        return await asyncio.sleep(len(msgs) or 1, ch)

    async def _messages(self, ch: Channel):
        msgs = []
        try:
            msgs = await client.get_messages(ch.link,
                                             500,
                                             min_id=ch.last_id,
                                             wait_time=5,
                                             reverse=True)
        except ConnectionError:
            await asyncio.sleep(60)
        except (ValueError, ChannelPrivateError):
            await answer('Channel is no longer available by this link -> '
                         + ch.link
                         + f'\nAnd will be removed from [feed]({ch.feed})')
            self._db.remove_channel(ch.link, ch.feed)
        except RPCError as e:
            await answer(f'RPCError occurred while getting new messages from'
                         f' [channel]({ch.link}): '
                         + e.message
                         + '\nerror code ->'
                         + str(e.code))
        feed_msgs = await client.get_messages(ch.feed, 50)
        ok_msgs = []
        for m in msgs:
            for fm in feed_msgs:
                if not self.is_msgs_identical(m, fm):
                    ok_msgs.append(m)
        print(ok_msgs)

        return [m for m in ok_msgs if isinstance(m, Message)]

    # TODO async def _forward_albums(self, msgs: TotalList):

    def _add_to_queue(self, channel: Channel):
        self._queue[(channel.feed, channel.link)] = self._forward(channel)

    def _new_task(self, future=None):
        if self._current_task:
            self._add_to_queue(future.result())
        if self._queue:
            _, coro = self._queue.popitem(last=False)
            self._current_task = asyncio.create_task(coro)
            self._current_task.add_done_callback(self._new_task)

    @staticmethod
    def is_msgs_identical(m1: Message, m2: Message):
        dict1 = m1.__dict__
        dict2 = m2.__dict__
        dict1.id = dict2.id = None
        dict1.date = dict2.date = None
        return dict1 == dict2
