FROM ubuntu:24.04

# The "legitimate" authoritative DNS server for example.net.
# iproute2 provides `tc`, used to add simulated WAN latency so the
# on-LAN attacker reliably wins the cache-poisoning race.
RUN apt update \
  && DEBIAN_FRONTEND=noninteractive apt install -y \
  --no-install-recommends \
  bind9 bind9-utils bind9-dnsutils \
  iproute2 iputils-ping net-tools \
  && rm -rf /var/lib/apt/lists/*

# Copy the configuration and the example.net zone file
COPY named.conf           /etc/bind/
COPY named.conf.options   /etc/bind/
COPY zone_example.net     /etc/bind/

# Validate the configuration at build time
RUN named-checkconf /etc/bind/named.conf

EXPOSE 53/udp 53/tcp

# Compose overrides this with its own command (adds the tc delay first).
CMD service named start && tail -f /dev/null
