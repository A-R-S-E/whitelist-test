import json
import os
import signal
import sys
import time
from mcstatus import MinecraftServer
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv
from minecraft import authentication
from minecraft.compat import input
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection
from minecraft.networking.packets import Packet, clientbound, serverbound

load_dotenv()

class TryConnect():
    def __init__(self):
        self.conn = psycopg2.connect(database=os.environ['POSTGRES_DATABASE'], user=os.environ['POSTGRES_USER'],
                                password=os.environ['POSTGRES_PASSWORD'], host=os.environ['POSTGRES_HOST'], port=os.environ['POSTGRES_PORT'])
        self.server_id = server_id

    @property
    def random_user(self):
        with self.conn.cursor() as c:
            c.execute("SELECT u.username FROM users u INNER JOIN server_users su ON u.id = su.user_id WHERE su.server_id = %s ORDER BY random() LIMIT 1;", (self.server_id,))
            result = c.fetchone()
            if len(result) > 0:
                return result[0]
            else:
                return

    @property
    def address(self):
        with self.conn.cursor() as c:
            c.execute("select ip, port from servers where id = 766;", (self.server_id,))
            ip, port = c.fetchone()
            return ip, port

    def motd_ping(self):
        ipstr = "{}:{}".format(*self.address)
        try:
            status = MinecraftServer.lookup(ipstr).status(retries=2)
        except (socket.timeout, ConnectionRefusedError, ConnectionResetError, OSError):
            pass
        else:
            if status.players.online < 1:
                return True
        finally:
            return False
