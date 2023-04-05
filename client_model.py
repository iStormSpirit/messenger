from asyncio import StreamReader, StreamWriter
from datetime import datetime
from typing import Optional


class ClientModel:
    def __init__(self, reader: StreamReader, writer: StreamWriter, time_ban=4):
        self._reader: StreamReader = reader
        self._writer: StreamWriter = writer
        self._ip: str = writer.get_extra_info('peername')[0]
        self._port: int = writer.get_extra_info('peername')[1]
        self.nickname: str = str(writer.get_extra_info('peername'))
        self.complaint_count: int = 0
        self.banned_time: Optional[datetime] = None
        self.first_message: Optional[datetime] = None
        self.message_count: int = 0
        self.time_ban: int = time_ban

    def __str__(self):
        return f"{self.nickname} {self.ip}:{self.port}"

    @property
    def ip(self):
        return self._ip

    @property
    def port(self):
        return self._port

    async def get_message(self):
        return str((await self._reader.read(255)).decode('utf8'))

    def send_message(self, message: str):
        return self._writer.write(message)

    def ban_time(self):
        if self.banned_time:
            time_left = datetime.now() - self.banned_time
            if (time_left.seconds / 60) >= (self.time_ban * 60):
                self.complaint_count = 0

    def messaging_time(self):
        if self.first_message:
            time_left = datetime.now() - self.first_message
            if (time_left.seconds / 60) >= 60:
                self.message_count = 0
