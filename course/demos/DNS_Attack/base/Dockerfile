FROM ubuntu:24.04

# Shared base used by the router and attacker containers.
# Provides routing/firewall tools plus Scapy for the DNS attack scripts.
RUN apt update \
  && DEBIAN_FRONTEND=noninteractive apt install -y \
  --no-install-recommends \
  iproute2 iptables iputils-ping net-tools \
  tcpdump dnsutils curl \
  python3 python3-scapy python-is-python3 \
  && rm -rf /var/lib/apt/lists/*

# Keep the container running; compose overrides this with its own command.
CMD ["tail", "-f", "/dev/null"]
