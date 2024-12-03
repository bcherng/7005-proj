import argparse
import random
import socket
import threading
import time
import select

# thread class to manage forwarding packets
class ForwarderThread(threading.Thread):
    def __init__(self, terminate_flag, socket, shared_config):
        super().__init__()
        self.terminate_flag = terminate_flag
        self.socket = socket
        self.shared_config = shared_config
        self.state = "read_socket"

    # helper function: send packet after delay (thread)
    def apply_delay(self, data, forward_address, delay_time):
        try:
            time.sleep(delay_time / 1000.0) 
            self.socket.sendto(data, forward_address)
            print(f"(Forwarder) Packet forwarded to {forward_address} after delay {delay_time/1000.0}")
        except Exception as e:
            self.terminate_flag.set()
            print(f"(Forwarder) Error in delay: {e}")


    # helper function: manipulate and sends packet based on proxy configuration
    def manipulate_packet(self, data, sender_ip, sender_port):
        try:
            if (sender_ip, sender_port) == (self.shared_config["target_ip"], self.shared_config["target_port"]):
                forward_address = (self.shared_config["client_ip"], self.shared_config["client_port"])
                drop_chance = self.shared_config["server_drop"]
                delay_chance = self.shared_config["server_delay"]
                delay_time = self.shared_config["server_delay_time"]
            elif (sender_ip, sender_port) == (self.shared_config["client_ip"], self.shared_config["client_port"]):
                forward_address = (self.shared_config["target_ip"], self.shared_config["target_port"])
                drop_chance = self.shared_config["client_drop"]
                delay_chance = self.shared_config["client_delay"]
                delay_time = self.shared_config["client_delay_time"]
            else:
                print("(Forwarder) Error: Unrecognized sender")
                return

            print(f"drop chance: {drop_chance}")
            if random.randint(1, 100) <= drop_chance:
                print(f"(Forwarder) Dropping packet {data} with {drop_chance}% chance")
                return

            if random.randint(1, 100) <= delay_chance:
                print(f"(Forwarder) Delaying packet {data} by {delay_time} ms with {delay_chance}% chance")
                delay_thread = threading.Thread(target=self.apply_delay, args=(data, forward_address, delay_time))
                delay_thread.start()
                return

            self.socket.sendto(data, forward_address)

        except Exception as e:
            print(f"(Forwarder) Error in manipulate_packet: {e}")

    # state function: continuously read socket for, apply manipulation to, then forward any incoming packets
    def read_socket(self):
        readable, _, _ = select.select([self.socket], [], [], 0.01)
        if readable:
            try:
                data, sender_address = self.socket.recvfrom(1024)
                if sender_address != (self.shared_config["target_ip"], self.shared_config["target_port"]):
                    ip, port = sender_address
                    self.shared_config["client_ip"] = ip
                    self.shared_config["client_port"] = port
                sender_ip, sender_port = sender_address
                self.manipulate_packet(data, sender_ip, sender_port)
            except Exception as e:
                print(f"(Forwarder) Error in read_socket: {e}")
                self.terminate_flag.set()
                return
            
    # run: execute until terminate flag is set
    def run(self):
        while not self.terminate_flag.is_set():
            try:
                getattr(self, self.state)()
            except Exception as e:
                self.terminate_flag.set()
                print(f"(Forwarder) error in run: {e}")

# main process to handle updating manipulation configurations via command line input
class Proxy:
    def __init__(self):
        self.state = "parse_args"
        self.socket = None
        self.terminate_flag = threading.Event()

    # state function: parse command line arguments into shared_config
    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--listen-ip", type=str, required=True, help="IP address to bind the proxy server.")
        parser.add_argument("--listen-port", type=int, required=True, help="Port number to listen for incoming packets.")
        parser.add_argument("--target-ip", type=str, required=True, help="IP address of the server to forward packets to.")
        parser.add_argument("--target-port", type=int, required=True, help="Port number of the server.")
        parser.add_argument("--timeout", type=float, default=2, help="Timeout in seconds for retransmission.")
        parser.add_argument("--client-drop", type=int, default=0, help="Drop chance for client packets.")
        parser.add_argument("--server-drop", type=int, default=0, help="Drop chance for server packets.")
        parser.add_argument("--client-delay", type=int, default=0, help="Delay chance for client packets.")
        parser.add_argument("--server-delay", type=int, default=0, help="Delay chance for server packets.")
        parser.add_argument("--client-delay-time", type=int, default=0, help="Delay time for client packets in ms.")
        parser.add_argument("--server-delay-time", type=int, default=0, help="Delay time for server packets in ms.")

        args = parser.parse_args()

        self.shared_config = {
            "listen_ip": args.listen_ip,
            "listen_port": args.listen_port,
            "target_ip": args.target_ip,
            "target_port": args.target_port,
            "timeout": args.timeout,
            "client_drop": args.client_drop,
            "server_drop": args.server_drop,
            "client_delay": args.client_delay,
            "server_delay": args.server_delay,
            "client_delay_time": args.client_delay_time,
            "server_delay_time": args.server_delay_time
        }

        self.state = "set_socket"

    # state function: sets socket
    def set_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.shared_config["listen_ip"], self.shared_config["listen_port"]))
        self.socket.setblocking(False)
        self.state = "start_thread"

    # state function: start forwarder thread
    def start_thread(self):
        self.forwarder_thread = ForwarderThread(self.terminate_flag, self.socket, self.shared_config)
        self.forwarder_thread.start()
        self.state = "read_input"

    # state function: continuously read input for latest manipulation configuration
    def read_input(self):
        try:
            user_input = input(
                "(Proxy) Enter parameters (c_drop_chance, c_delay_chance, c_delay_time, s_drop_chance, s_delay_chance, s_delay_time): "
            )
            if self.terminate_flag.is_set():
                self.state = "success"
                return
            
            input_parts = user_input.split(",")
            parameters = {}
            for part in input_parts:
                key, value = part.split(":")
                key = key.strip()
                value = value.strip()
                parameters[key] = value

            self.shared_config["client_drop"] = int(parameters.get("c_drop_chance", self.shared_config["client_drop"]))
            self.shared_config["client_delay"] = int(parameters.get("c_delay_chance", self.shared_config["client_delay"]))
            self.shared_config["client_delay_time"] = float(parameters.get("c_delay_time", self.shared_config["client_delay_time"]))

            self.shared_config["server_drop"] = int(parameters.get("s_drop_chance", self.shared_config["server_drop"]))
            self.shared_config["server_delay"] = int(parameters.get("s_delay_chance", self.shared_config["server_delay"]))
            self.shared_config["server_delay_time"] = float(parameters.get("s_delay_time", self.shared_config["server_delay_time"]))
            print(f"(Proxy-Keyboard) Parameters updated:")
            print(f"  Client: drop={self.shared_config['client_drop']}%, delay={self.shared_config['client_delay']}%, delay_time={self.shared_config['client_delay_time']} ms")
            print(f"  Server: drop={self.shared_config['server_drop']}%, delay={self.shared_config['server_delay']}%, delay_time={self.shared_config['server_delay_time']} ms")

        except ValueError as ve:
            print(f"(Proxy) Invalid input format: {ve}")
        except KeyboardInterrupt:
            print("(Proxy) Shutting down server...")
            self.terminate_flag.set()
            self.state = "success"
        except Exception as e:
            print(f"(Proxy) Error: {e}")

    # cleanup function: sets terminate flag and wait for ForwarderThread to finish
    def terminate(self):
        print("(Proxy) Terminating...")
        try:
            self.forwarder_thread.join()
        except:
            print("Exit before thread could be started")
        self.terminate_flag.set()

    # run: execute until success/failure state or terminate flag is set
    def run(self):
        while self.state not in ["success", "failure"] and not self.terminate_flag.is_set():
            try:
                getattr(self, self.state)()
            except KeyboardInterrupt:
                self.state = "success"
            except Exception as e:
                self.state = "failure"
                print(f"(Proxy) Error in run: {e}")
        self.terminate()

if __name__ == "__main__":
    proxy_server = Proxy()
    proxy_server.run()
