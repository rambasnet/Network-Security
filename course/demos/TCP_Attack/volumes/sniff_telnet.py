#! /usr/bin/env python3

"""
Sniff Telnet packets

find the interface name by running ifconfig;
pick the one with docker-compose network settings
change IFACE to the correct interface name
"""

from scapy.all import IP, TCP, sniff

# FIXME: Change this to the correct interface
IFACE = 'br-e1f94e37dcc4'


def telnet_sniffer(packet):
    # Print the packet
    print(f'src={packet[IP].src} dst={packet[IP].dst} \
          src_p={packet[TCP].sport} dst_p={packet[TCP].dport} \
            seq={packet[TCP].seq} ack={packet[TCP].ack} \
          tcp_flags={packet[TCP].flags}')


if __name__ == "__main__":
    print('sniffing telnet packets...')
    sniff(iface=IFACE, filter="tcp and src port 23", prn=telnet_sniffer)
    # Usage: python3 sniff_telnet.py
    # Example: python3 sniff_telnet.py
