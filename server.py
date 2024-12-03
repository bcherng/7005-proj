import socket
import argparse
import select

# main process to handle reading and displaying incoming messages
class Server:
    def __init__(self):
        self.state = "parse_args" 
        self.received_data = {} 

    # state function: parse arguments
    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--listen-ip", required=True, help="Listening IP address")
        parser.add_argument("--listen-port", type=int, required=True, help="Listening port")
        args = parser.parse_args()
        self.ip, self.port = args.listen_ip, args.listen_port
        self.state = "set_socket" 

    # state function: set function
    def set_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        print("(Server) Reading...")
        self.state = "read_packet"

    # state function: continuously read incoming packets and return acknowledgement
    def read_packet(self):
        readable, _, _ = select.select([self.socket], [], [], 0.0002)
        if readable:
            packet, client_address = self.socket.recvfrom(1024)
            try:
                session, length, data, index = packet.decode().split(":", 3)
                session, length, index = int(session), int(length), int(index)

                if session not in self.received_data:
                    self.received_data[session] = [length, [None] * length]
                if (index < len(self.received_data[session][1])):
                    self.received_data[session][1][index] = data
                else:
                    raise ValueError
                ack = f"{session}:{self.received_data[session][1]}"
                self.socket.sendto(ack.encode(), client_address)
                if not None in self.received_data[session][1]:
                    print(f"(Server) received message: {"".join(self.received_data[session][1])}")

            except ValueError:
                print("(Server) Discarded invalid packet")

    # cleanup function: close socket
    def terminate(self):
        print("(Server) terminating...")
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()

    # run: execute until success/failure state is reached
    def run(self):
        while self.state not in  ["success", "failure"]:
            try:
                getattr(self, self.state)() 
            except KeyboardInterrupt:
                self.state = "success"
            except Exception as e:
                self.state = "failure" 
                print(f"(Server) error in run: {e}")

        self.terminate() 

if __name__ == "__main__":
    server = Server()  
    server.run()  
