from minecraft import authentication
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection
from minecraft.networking.packets.clientbound import play, login
import sys

def get_auth_token(username, password):
    auth_token = authentication.AuthenticationToken()
    try:
        auth_token.authenticate(username, password)
    except YggdrasilError as e:
        print(e)
    else:
        return auth_token
    return False

class MinecraftConnection():
    def __init__(self, ip, port, username=None, auth_token=None):
        if not any((username, auth_token)):
            print("WARNING: no authentication provided")
        self.ip = ip
        self.port = port
        self.username = username
        self.auth_token = auth_token
        self.connection = None
        self.success_packet = None
    
    def make_connection(self):
        if self.username:
            self.connection = Connection(self.ip, port=self.port, username=self.username)
        if self.auth_token:
            self.connection = Connection(self.ip, port=self.port, auth_token=self.auth_token)
        if not self.connection:
            raise AttributeError("No authentication provided")
    
    def run(self):
        try:
            self.make_connection()
            self.register_packet_listeners()
            self.run_until_complete()
        except Exception as e:
            print(e)
        return self.success_packet

    def run_until_complete(self):
        self.connection.connect()
        self.success_packet = "connecting"
        while self.success_packet == "connecting":
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
        print('logged in: %r' % packet.__dict__)
        self.success_packet = packet
        self.connection.disconnect()

    def handle_disconnect(self, packet):
        print('disconnected')
        self.success_packet = False
        self.connection.disconnect()

#TODO: handle minecraft errors