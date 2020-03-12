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
    def __init__(self, ip, port, username, password, auth_token=None):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.auth_token = authentication.AuthenticationToken() if auth_token is None else auth_token
        self.skip_login = False if auth_token is None else True
        self.connection = None
        self.success_packet = None
    
    def run(self):
        login = True
        if not self.skip_login:
            login = self.login()
        if login:
            if not self.password:
                self.connection = Connection(self.ip, port=self.port, username=username)
            else:
                self.connection = Connection(self.ip, port=self.port, auth_token=self.auth_token)
            self.register_packet_listeners()
            self.run_until_complete()
        return self.success_packet

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
