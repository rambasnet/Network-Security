FROM ubuntu:24.04

# Install the BIND DNS server and basic networking tools
RUN apt update \
  && DEBIAN_FRONTEND=noninteractive apt install -y \
  --no-install-recommends \
  bind9 bind9-utils bind9-dnsutils \
  iproute2 iputils-ping net-tools \
  && rm -rf /var/lib/apt/lists/*

# Copy the configuration and zone files
COPY named.conf  zone_attacker32.com  zone_example.com  /etc/bind/
COPY zone_192.168.0 /etc/bind/

# Validate the configuration at build time
RUN named-checkconf /etc/bind/named.conf

EXPOSE 53/udp 53/tcp

# Start the BIND named service and keep it running
CMD service named start && tail -f /dev/null
