import json
import os
import signal
import sys
import time
from mcstatus import MinecraftServer
from contextlib import contextmanager

import pika
import psycopg2
from dotenv import load_dotenv
from minecraft import authentication
from minecraft.compat import input
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection
from minecraft.networking.packets import Packet, clientbound, serverbound

load_dotenv()

@contextmanager
def timeout(time):
    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(time)

    try:
        yield
    except TimeoutError:
        pass
    finally:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


def raise_timeout(signum, frame):
    raise TimeoutError("Took too long")


class CallbackCallable():
    def __init__(self):
        self.connection = None
        self.done = False
        self.ip = None
        self.port = None
        self.username = "" # get from database

    def __call__(self, ch, method, properties, body):
        json_body = json.loads(body)
        self.ip = json_body["ip"]
        self.port = int(json_body["port"])
        try:
            ipstr = "{}:{}".format(self.ip, self.port)
            status = MinecraftServer.lookup(ipstr).status(retries=2)
            if status.players.online > 0:
                print("server {} skipped because of {} online players".format(ipstr, status.players.online))
                return
        except (socket.timeout, ConnectionRefusedError, ConnectionResetError, OSError):
            return
        try:
            self.connect()
        except Exception as e:
            self.disconnect(ch, method)
            print(e)
            return
        if self.connection.connected:
            self.connection.disconnect(immediate=True)
        self.disconnect(ch, method)

    def exception_handler(self, exception):
        print(exception)

    def connect(self):
        self.connection = Connection(
            self.ip, self.port, handle_exception=self.exception_handler, username=self.username)
        print("connecting to", self.ip)
        self.connection.register_packet_listener(
            self.handle_join_game, clientbound.play.JoinGamePacket)
        self.connection.register_packet_listener(
            self.on_login_disconnect_packet, clientbound.play.DisconnectPacket, early=True)
        # self.connection.register_packet_listener(self.print_packet, Packet, early=True)
        self.connection.register_packet_listener(
            self.on_login_disconnect_packet, clientbound.login.DisconnectPacket, early=True)
        with timeout(2):
            self.connection.connect()
            start = time.time()
            while not self.done:
                time.sleep(0.01)
                now = time.time()
                diff = now - start
                if diff > 2:
                    self.done = True

    def disconnect(self, ch, method):
        self.connection = None
        self.done = False
        ch.basic_ack(method.delivery_tag)

    def print_packet(self, packet):
        if type(packet) is Packet:
            return
        print('--> %s' % packet)

    def handle_join_game(self, join_game_packet):
        print("found server without whitelist")
        conn = psycopg2.connect(database=os.environ['POSTGRES_DATABASE'], user=os.environ['POSTGRES_USER'],
                                password=os.environ['POSTGRES_PASSWORD'], host=os.environ['POSTGRES_HOST'], port=os.environ['POSTGRES_PORT'])
        with conn.cursor() as c:
            pass # update database with crackd status
        conn.commit()
        self.done = True

    def on_login_disconnect_packet(self, packet):
        #print("disconnected from game:",packet)
        self.done = True


# get random servers from database