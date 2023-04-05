import asyncio
from asyncio import StreamReader, StreamWriter
from datetime import datetime, timedelta
from enum import Enum
from threading import Timer

from loguru import logger

from client_model import ClientModel


class Command(Enum):
    QUIT = "quit"
    NICK = "/nick"
    PRIVATE = "/pm"
    DELAY = "/delay"
    COMPLAINT = "/complaint"
    WELCOME = (
        "Welcome to chat \n"
        "Write /nick <your nickname> for chose nickname\n"
        "Write /pm <nickname> <message> for private chat\n"
        "Write /complaint <nick> to block user\n"
        "Write /delay <minutes> <message> for delay message\n"
        "Write quit to leave chat \n"
    )


class Server:
    def __init__(self, ip: str = "127.0.0.1", port: int = 8000):
        self._ip: str = ip
        self._port: int = port
        self._clients: dict[asyncio.Task, ClientModel] = {}

        logger.info(f"Server Initialized with {self.ip}:{self.port}")

    @property
    def ip(self):
        return self._ip

    @property
    def port(self):
        return self._port

    @property
    def clients(self):
        return self._clients

    async def run_server(self):
        try:
            srv = await asyncio.start_server(
                self.accept_client, self.ip, self.port
            )
            async with srv:
                await srv.serve_forever()

        except Exception as e:
            logger.error(e)
        except KeyboardInterrupt:
            logger.warning("Keyboard Interrupt Detected. Shutting down!")

    def accept_client(self, reader: StreamReader, writer: StreamWriter):
        client = ClientModel(reader, writer)
        task = asyncio.Task(self.incoming_client_message_cb(client))
        self.clients[task] = client
        writer.write(Command.WELCOME.value.encode())
        client_ip, client_port = writer.get_extra_info("peername")
        logger.info(f"New Connection: {client_ip}:{client_port}")
        task.add_done_callback(self.disconnect_client)

    @staticmethod
    def access_checker(client: ClientModel):
        client.ban_time()
        client.messaging_time()
        if not client.complaint_count < 3:
            client.send_message(f"Your account was baned to {client.time_ban} hour".encode("utf8"))
        if not client.message_count <= 20:
            client.send_message("Message limit, wait 1 hour".encode("utf8"))
        else:
            return True

    async def incoming_client_message_cb(self, client: ClientModel):
        while True:
            client_message = await client.get_message()
            if client.message_count == 0:
                client.first_message = datetime.now()
            if client_message.startswith(Command.QUIT.value):
                break
            elif client_message.startswith("/"):
                self.handle_client_command(client, client_message)
            else:
                if self.access_checker(client):
                    self.broadcast_message(
                        f"{client.nickname}: {client_message}".encode("utf8"))
                    client.message_count += 1
            logger.info(f"{client_message}")
            await client._writer.drain()
        logger.info("Client Disconnected!")

    def handle_client_command(self, client: ClientModel, message: str):
        message = message.replace("\n", "").replace("\r", "")
        if message.startswith(Command.NICK.value):
            self.new_nick(client, message)
        elif message.startswith(Command.PRIVATE.value):
            self.private_message(client, message)
        elif message.startswith(Command.COMPLAINT.value):
            self.complaint(client, message)
        elif message.startswith(Command.DELAY.value):
            self.send_in_time(client, message)
        else:
            client.send_message("Invalid Command\n".encode("utf8"))

    @staticmethod
    def parse_command(client: ClientModel, message: str):
        split_client_message = message.split(" ")
        if len(split_client_message) >= 2:
            return split_client_message[1]
        else:
            logger.info(f"{client.nickname} send wrong command")
            client.send_message("Invalid Command\n".encode("utf8"))

    def send_in_time(self, client: ClientModel, message: str):
        now = datetime.now()
        through = self.parse_command(client, message)
        send_at = now + timedelta(minutes=int(through))
        delay = (send_at - now).total_seconds()
        clear_msg = message.replace(
            "/delay", ""
        ).replace(
            f"{through}", f"{client.nickname}: "
        ).encode()
        timer = Timer(delay, self.broadcast_message, args=(clear_msg,))
        timer.start()

    def complaint(self, client: ClientModel, message: str):
        complaint_to = self.parse_command(client, message)
        for target in self.clients.values():
            if target.nickname == complaint_to:
                target.complaint_count += 1
                if target.complaint_count == 3:
                    target.banned_time = datetime.now()

    def broadcast_message(self, message: bytes, exclusion_list: list = []):
        logger.info(self.clients)
        for client in self.clients.values():
            if client not in exclusion_list:
                client.send_message(message)

    def new_nick(self, client: ClientModel, message: str) -> None:
        new_nickname = self.parse_command(client, message)
        if new_nickname is not None:
            client.nickname = new_nickname
            client.send_message(f"Nickname changed to {client.nickname}\n".encode("utf8"))
            return
        else:
            client.send_message(f"Please write /nick <your nick>\n".encode("utf8"))

    def private_message(self, client: ClientModel, client_message):
        msg_for = self.parse_command(client, client_message)
        if msg_for == client.nickname:
            client.send_message("Can't send massage yourself".encode("utf8"))
        if msg_for not in [i.nickname for i in self.clients.values()]:
            client.send_message(f"No user with nickname: {msg_for}".encode("utf8"))
        for target in self.clients.values():
            if (msg_for == target.nickname) and (msg_for != client.nickname):
                target.send_message(
                    (client_message.replace("/pm", f"\nprivate message from {client.nickname}: ")
                     .replace(f"{msg_for}", "")).encode("utf8")
                )

    def disconnect_client(self, task: asyncio.Task):
        client = self.clients[task]
        self.broadcast_message(
            f"{client.nickname} has left!".encode("utf8"), [client]
        )
        del self.clients[task]
        client.send_message("quit".encode("utf8"))
        client._writer.close()
        logger.info("End Connection")


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.run_server())
