import matplotlib.pyplot as plt

class Grapher:
    def __init__(self):
        self.packet_stats = {
            "sent": 0,
            "received": 0,
            "retransmitted": 0
        }
        self.message_stats = {
            "sent": 0,
            "received": 0,
            "lost":0,
            "latency": []  
        }

    def log_packet_sent(self):
        self.packet_stats["sent"] += 1

    def log_packet_received(self):
        self.packet_stats["received"] += 1

    def log_packet_retransmitted(self):
        self.packet_stats["retransmitted"] += 1

    def log_message_sent(self):
        self.message_stats["sent"] += 1

    def log_message_received(self):
        self.message_stats["received"] += 1

    def log_message_lost(self):
        self.message_stats["lost"] += 1

    def log_message_latency(self, latency):
        self.message_stats["latency"].append(latency)

    def plot_packet_stats(self):
        categories = ["Sent", "Received", "Retransmitted"]
        values = [
            self.packet_stats["sent"],
            self.packet_stats["received"],
            self.packet_stats["retransmitted"]
        ]

        plt.bar(categories, values, color=["blue", "green", "orange"])
        plt.title("Packet Statistics")
        plt.xlabel("Packet Type")
        plt.ylabel("Count")
        
        plt.savefig("packet_stats.png")

        plt.clf()

    def plot_message_stats(self):
        categories = ["Sent", "Received", "Lost"]
        values = [
            self.message_stats["sent"],
            self.message_stats["received"],
            self.message_stats["lost"]
        ]

        plt.bar(categories, values, color=["blue", "green", "red"])
        plt.title("Message Statistics")
        plt.xlabel("Message Type")
        plt.ylabel("Count")
        
        plt.savefig("message_stats.png")

        plt.clf() 


    def plot_latency(self):
        if self.message_stats["latency"]:
            self.message_stats["latency"].insert(0, 0)
            plt.plot(self.message_stats["latency"], color="purple")
            plt.title("message Latency Over Time")
            plt.xlabel("Message Number")
            plt.ylabel("Latency (seconds)")
            
            plt.savefig("latency.png")


            plt.clf() 