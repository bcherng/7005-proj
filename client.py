import argparse
import ast
import random
import socket
import threading
import time
import select
from grapher import Grapher
grapher = Grapher()

# thread class to handle removing acknowledged messages from pending_acks dict
class AckerThread(threading.Thread):
    def __init__(self, terminate_flag, socket, pending_acks):
        super().__init__()
        self.terminate_flag = terminate_flag
        self.socket = socket
        self.pending_acks = pending_acks
        self.state = "read_socket"

    # state function: continuously read socket and remove acknowledged messages from pending_acks 
    def read_socket(self):
        readable, _, _ = select.select([self.socket], [], [], 0.001)
        if readable:
            try:
                data, _ = self.socket.recvfrom(1024)
                session, message_parts = data.decode().split(":", 1)
                print(f"(Acker) Received packet: {session}:{message_parts}")
                session = int(session)
                grapher.log_packet_received()
                if session in self.pending_acks:
                    message_parts = ast.literal_eval(message_parts)
                    _retries, message, _last_sent_time, start_time = self.pending_acks[session]
                    if list(message) == message_parts:
                        print(f"Message acknowledged: {session}: {message_parts}")
                        grapher.log_message_received()
                        grapher.log_message_latency(time.time() - start_time)
                        del self.pending_acks[session]
            except Exception as e:
                print(f"(Acker) Error in read_socket: {e}")
                self.terminate_flag.set()
                return
            
    # run: execute until terminate flag is set
    def run(self):
        while not self.terminate_flag.is_set():
            try:
                getattr(self, self.state)()
            except Exception as e:
                self.terminate_flag.set()
                print(f"(Acker) error in run: {e}")

# thread class to handle sending and resending messages still in pending_acks dict
class SenderThread(threading.Thread):
    def __init__(self, terminate_flag, socket, pending_acks, ip_config):
        super().__init__()
        self.terminate_flag = terminate_flag
        self.socket = socket
        self.pending_acks = pending_acks
        self.ip_config = ip_config
        self.state = "handle_pending_messages"

    # helper function: fragmentate message into list of chars, and send each char
    def send_message(self, session_number, message, retries):
        message_parts = list(message)
        for index, fragment in enumerate(message_parts):
            packet = f"{session_number}:{len(message)}:{fragment}:{index}"
            if retries != 10:
                grapher.log_packet_retransmitted()
            grapher.log_packet_sent()
            self.socket.send(packet.encode())

    # state function: resend timed out pending messages, remove entries if out of retries
    def handle_pending_messages(self):
        current_time = time.time()
        for session_number, (retries, message, last_sent_time, start_time) in list(self.pending_acks.items()):
            if retries > 0:
                if retries == 10:
                    grapher.log_message_sent()
                    self.pending_acks[session_number] = (retries - 1, message, current_time, time.time()) 
                    self.send_message(session_number, message, retries) 
                elif current_time - last_sent_time > self.ip_config["timeout"]:
                    self.pending_acks[session_number] = (retries - 1, message, current_time, start_time)  
                    self.send_message(session_number, message, retries)
            elif retries <= 0:
                grapher.log_message_lost()
                print(f"Message lost: {self.pending_acks[session_number][1]}")
                del self.pending_acks[session_number]
        
        time.sleep(0.01) 

    # run: execute until terminate flag is set
    def run(self):
        while not self.terminate_flag.is_set():
            try:
                getattr(self, self.state)()
            except Exception as e:
                self.terminate_flag.set()
                print(f"(Sender) error in run: {e}")

# main process to handle accepting messages from command line and adding them to pending_acks
class Client:
    def __init__(self):
        self.state = "parse_args"
        self.socket = None
        self.terminate_flag = threading.Event()
        self.pending_acks = {}
    
    # state function: parse arguments 
    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--target-ip", type=str, required=True, help="Target IP address")
        parser.add_argument("--target-port", type=int, required=True, help="Target port")
        parser.add_argument("--timeout", type=float, default=2, help="Timeout in seconds")

        args = parser.parse_args()

        self.ip_config = {
            "target_ip": args.target_ip,
            "target_port": args.target_port,
            "timeout": args.timeout
        }

        self.state = "set_socket"

    # state function: set socket
    def set_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect((self.ip_config["target_ip"], self.ip_config["target_port"]))
        self.socket.setblocking(False)
        self.state = "start_threads"

    # state function: start AckerThread and SenderThread
    def start_threads(self):
        self.acker_thread = AckerThread(self.terminate_flag, self.socket, self.pending_acks)
        self.acker_thread.start()

        self.sender_thread = SenderThread(self.terminate_flag, self.socket, self.pending_acks, self.ip_config)
        self.sender_thread.start()

        self.state = "read_input"

    # state function: continuously read input to add to pending_acks
    def read_input(self):
        try:
            message = input("\n>> ")
            if len(message) < 1 or len(message) > 20:
                print("(Client) Message length must be between 1 and 20 inclusive!")
                return
            self.message = message
            self.state = "push_message"
        except KeyboardInterrupt:
            self.state = "success"

    # state function: generate unique session_number, then add message to pending_acks
    def push_message(self):
        while True:
            new_session = random.randint(1, 1000)
            if new_session not in self.pending_acks:
                self.session_number = new_session
                break

        self.pending_acks[self.session_number] = (10, self.message, time.time(), time.time())
        self.state = "read_input"

    # cleanup function: set terminate_flag, joins AckerThread and SenderThread
    def terminate(self):
        print("(Client) terminating...")
        
        self.terminate_flag.set()
        try:
            self.acker_thread.join()
            self.sender_thread.join()
            grapher.plot_message_stats()
            grapher.plot_packet_stats()
            grapher.plot_latency()
        except:
            print("Exit before thread could be started")

    # run: execute until success/failure state or terminate flag is set
    def run(self):
        while self.state not in ["success", "failure"] and not self.terminate_flag.is_set():
            try:
                getattr(self, self.state)()
            except KeyboardInterrupt:
                self.state = "success"
            except Exception as e:
                self.state = "failure"
                print(f"(Client) error in run: {e}")

        self.terminate()


if __name__ == "__main__":
    client = Client()
    client.run()
