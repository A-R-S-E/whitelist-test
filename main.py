import json
import os
import socket
import sys
import time

from datetime import datetime
import psycopg2
from dotenv import load_dotenv
from mcstatus import MinecraftServer
from minecraft import authentication
from minecraft.compat import input
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection
from minecraft.networking.packets import Packet, clientbound, serverbound
import connection
load_dotenv()


class ServerTester():
    def __init__(self):
        self.conn = psycopg2.connect(database=os.environ['POSTGRES_DATABASE'], user=os.environ['POSTGRES_USER'],
                                password=os.environ['POSTGRES_PASSWORD'], host=os.environ['POSTGRES_HOST'], port=os.environ['POSTGRES_PORT'])
        self.conn.autocommit = True
        self.server_id = None
        self.auth_token = connection.get_auth_token("laurinschmidt2001@gmail.com","emiliala1")

    def run(self):
        if self.motd_ping():
            cracked = self.test_cracked()
            if not cracked:
                self.test_whitelist()

    def run_on_random(self):
        self.randomize_server()
        self.run()

    def test_cracked(self):
        username = self.random_user
        packet = connection.MinecraftConnection(*self.address, username=username).run()
        if packet:
            self.write_packet(packet, cracked=True)
            return True

    def test_whitelist(self):
        packet = connection.MinecraftConnection(*self.address, auth_token=self.auth_token).run()
        if packet:
            self.write_packet(packet)
        
    def write_packet(self, packet, cracked=False):
        game_mode = packet.game_mode
        level_type = packet.level_type
        with self.conn.cursor() as c:
            c.execute("""UPDATE public.servers SET last_checked=%s, world_type=%s, not_whitelisted=true, cracked=%s, gamemode=%s WHERE ip=%s AND port=%s;""", (datetime.now(), level_type, cracked, game_mode, *self.address))
    
    def randomize_server(self):
        with self.conn.cursor() as c:
            c.execute("SELECT id FROM servers ORDER BY random() LIMIT 1;")
            self.server_id = c.fetchone()[0]

    @property
    def random_user(self):
        with self.conn.cursor() as c:
            c.execute("SELECT u.username FROM users u INNER JOIN server_users su ON u.id = su.user_id WHERE su.server_id = %s ORDER BY random() LIMIT 1;", (self.server_id,))
            result = c.fetchone()
            if result and len(result) > 0:
                return result[0]
            else:
                return "Server"

    @property
    def address(self):
        with self.conn.cursor() as c:
            c.execute("select ip, port from servers where id = %s;", (self.server_id,))
            ip, port = c.fetchone()
            return ip, port

    def motd_ping(self):
        return True
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

s = Server()
s.server_id = 28650
s.run()
