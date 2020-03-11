from minecraft import authentication
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection
from minecraft.networking.packets.clientbound import play, login
import sys

class MinecraftConnection():
    def __init__(self, ip, port, username, password):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.auth_token = authentication.AuthenticationToken()
        self.connection = None
        self.success = None
    
    def run(self):
        if self.login():
            if not self.password:
                self.connection = Connection(self.ip, port=self.port, username=username)
            else:
                self.connection = Connection(self.ip, port=self.port, auth_token=self.auth_token)
            self.register_packet_listeners()
            self.run_until_complete()
        return self.success

    def login(self):
        if not self.password:
            return True
        try:
            self.auth_token.authenticate(self.username, self.password)
        except YggdrasilError as e:
            print(e)
        else:
            return True
        return False
    
    def run_until_complete(self):
        self.connection.connect()
        self.success = "connecting"
        while self.success == "connecting":
            pass
    
    def register_packet_listeners(self):
        self.connection.register_packet_listener(
                self.handle_join_game,
                play.JoinGamePacket
            )
        self.connection.register_packet_listener(
                self.handle_disconnect,
                play.DisconnectPacket,
                early=True
            )
        self.connection.register_packet_listener(
                self.handle_disconnect,
                login.DisconnectPacket,
                early=True
            )
    
    def handle_join_game(self, packet):
        print('logged in: %r' % packet)
        self.success = True
        self.connection.disconnect()

    def handle_disconnect(self, packet):
        print('disconnected')
        self.success = False
        self.connection.disconnect()

Connector("mc.salc1.com", 25565, "username", "password").run()