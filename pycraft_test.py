import json
import os
import signal
import sys
import time
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

auth_token = authentication.AuthenticationToken()
try:
    auth_token.authenticate(sys.argv[1], sys.argv[2])
except YggdrasilError as e:
    print(e)
    time.sleep(60)
    sys.exit()

print("Logged in as %s..." % auth_token.username)


credentials = pika.PlainCredentials(
    os.environ['RABBIT_USER'], os.environ['RABBIT_PW'])
parameters = pika.ConnectionParameters(os.environ['RABBIT_HOST'],
                                       os.environ['RABBIT_PORT'],
                                       os.environ['RABBIT_VHOST'],
                                       credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()
channel.basic_qos(prefetch_count=2)
channel.queue_declare(queue=os.environ['RABBIT_MOTD_QUEUE'], durable=True)


class CallbackCallable():
    def __init__(self):
        self.connection = None
        self.done = False
        self.ip = None
        self.port = None
    
    def __call__(self, ch, method, properties, body):
        json_body = json.loads(body)
        self.ip = json_body["ip"]
        self.port = int(json_body["port"])
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
        self.connection = Connection(self.ip, self.port, auth_token=auth_token, handle_exception=self.exception_handler)
        print("connecting to", self.ip)
        self.connection.register_packet_listener(self.handle_join_game, clientbound.play.JoinGamePacket)
        self.connection.register_packet_listener(self.on_login_disconnect_packet, clientbound.play.DisconnectPacket, early=True)
        # self.connection.register_packet_listener(self.print_packet, Packet, early=True)
        self.connection.register_packet_listener(self.on_login_disconnect_packet, clientbound.login.DisconnectPacket, early=True)
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
        conn = psycopg2.connect(database=os.environ['POSTGRES_DATABASE'], user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'], host=os.environ['POSTGRES_HOST'], port=os.environ['POSTGRES_PORT'])
        with conn.cursor() as c:
            c.execute("INSERT INTO public.servers (ip, port) VALUES(%s, %s) ON CONFLICT DO NOTHING;", (self.ip, self.port))
        conn.commit()
        self.done = True
    
    def on_login_disconnect_packet(self, packet):
        #print("disconnected from game:",packet)
        self.done = True

channel.basic_consume(queue=os.environ['RABBIT_MOTD_QUEUE'], on_message_callback=CallbackCallable())
channel.start_consuming()
