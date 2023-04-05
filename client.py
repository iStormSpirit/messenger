import asyncio
from asyncio import AbstractEventLoop, StreamReader, StreamWriter
from typing import Optional

from aioconsole import ainput


class Client:
    def __init__(self, loop: AbstractEventLoop, server_ip: str = "127.0.0.1", server_port: int = 8000):
        self._server_ip: str = server_ip
        self._server_port: int = server_port
        self._loop: AbstractEventLoop = loop
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None

    @property
    def server_ip(self):
        return self._server_ip

    @property
    def server_port(self):
        return self._server_port

    def loop(self):
        return self._loop

    @property
    def reader(self):
        return self._reader

    @property
    def writer(self):
        return self._writer

    async def connect_to_server(self):
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.server_ip, self.server_port)
            await asyncio.gather(
                self.receive_messages(),
                self.start_client_cli()
            )
        except Exception as ex:
            print("An error has occurred: " + ex)
        print("Shutting down")

    async def receive_messages(self):
        server_message: Optional[str] = None
        while server_message != "quit":
            server_message = await self.get_server_message()
            await asyncio.sleep(0.1)
            print(server_message)

        if loop.is_running():
            loop.stop()

    async def get_server_message(self):
        return str((await self.reader.read(255)).decode("utf8"))

    async def start_client_cli(self):
        client_message = None
        while client_message != "quit":
            client_message = await ainput("")
            self.writer.write(client_message.encode("utf8"))
            await self.writer.drain()

        if loop.is_running():
            loop.stop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    client = Client(loop)
    asyncio.run(client.connect_to_server())
