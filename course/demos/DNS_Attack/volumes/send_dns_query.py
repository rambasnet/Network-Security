#! /usr/bin/env python3
"""
Craft and send a DNS query with Scapy, then print the response.

By default this queries the lab's OWN DNS server (10.9.0.53) over the internal
10.9.0.0 bridge. That path works from the attacker container because it does
NOT traverse Docker Desktop's userspace NAT (gvproxy).

Why not query a public resolver (e.g. 8.8.8.8) from here?
  On Docker Desktop (macOS/Windows) the attacker runs with network_mode: host,
  i.e. inside the Docker VM. That VM keeps its default route in a POLICY
  routing table (table 2), which Scapy does not read, so Scapy falls back to
  the loopback interface and the packet never leaves the machine. Even when
  forced onto eth0, gvproxy does not return Scapy's raw-socket UDP. A kernel
  socket (e.g. `dig @8.8.8.8`) works, but Scapy raw sockets to the Internet do
  not. On a native Linux host the external query below works fine.

Usage:
    python3 send_dns_query.py                      # ask lab DNS for default domain
    python3 send_dns_query.py www.example.net      # ask lab DNS for a domain
    python3 send_dns_query.py www.example.net 10.9.0.54   # ask a specific server
    DNS_EXTERNAL=1 python3 send_dns_query.py www.coloradomesa.edu 8.8.8.8
                                                   # external mode (native Linux only)
"""

import os
import sys

from scapy.all import DNS, DNSQR, IP, UDP, sr1, get_if_addr, get_if_list

# Defaults: resolve a lab domain against the lab's local DNS server.
DNS_SERVER_IP = "10.9.0.53"
QUERY_DOMAIN = "www.example.net"

# Address of the Docker bridge that backs net-10.9.0.0 (used to auto-detect
# the interface Scapy should send on when talking to a 10.9.0.0/24 host).
LAB_BRIDGE_IP = "10.9.0.1"


def find_lab_iface(bridge_ip=LAB_BRIDGE_IP):
    """Return the host interface attached to the 10.9.0.0/24 lab network.

    The attacker runs with network_mode: host, so it sees the Docker bridge
    (br-<id>) whose own address is 10.9.0.1. We locate it by address rather
    than hard-coding a br-<id> name that changes when the network is recreated.
    Returns None if not found (e.g. when querying an off-LAN / external server).
    """
    for iface in get_if_list():
        try:
            if get_if_addr(iface) == bridge_ip:
                return iface
        except Exception:
            continue
    return None


def send_dns_query(domain, server_ip):
    # Pick the sending interface. For a lab (10.9.0.x) target, send over the
    # internal bridge; otherwise let Scapy route it (external mode).
    iface = find_lab_iface() if server_ip.startswith("10.9.0.") else None

    # Build IP / UDP / DNS layers. A random-ish source port avoids clashes.
    request = (
        IP(dst=server_ip)
        / UDP(sport=40000, dport=53)
        / DNS(id=100, rd=1, qd=DNSQR(qname=domain))
    )

    print(f"Sending query for {domain!r} to {server_ip} "
          f"(iface={iface or 'auto/route'})")
    response = sr1(request, iface=iface, timeout=5, verbose=0)

    if response is None:
        print("No response (timed out).")
        if not server_ip.startswith("10.9.0."):
            print("  External queries via Scapy do not work on Docker Desktop; "
                  "run on a native Linux host, or query the lab DNS (10.9.0.53).")
        return

    if response.haslayer(DNS) and response[DNS].ancount:
        print(f"Answer(s) for {domain}:")
        for i in range(response[DNS].ancount):
            rr = response[DNS].an[i]
            print(f"  {rr.rrname.decode(errors='replace')} -> {rr.rdata}")
    else:
        print("Response received, but no answer records:")
        response.show()


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else QUERY_DOMAIN
    server = sys.argv[2] if len(sys.argv) > 2 else DNS_SERVER_IP
    # DNS_EXTERNAL=1 is only a reminder flag; external mode works on native Linux.
    if os.environ.get("DNS_EXTERNAL") and server.startswith("10.9.0."):
        print("DNS_EXTERNAL set but server is a lab address; querying it anyway.")
    send_dns_query(domain, server)
