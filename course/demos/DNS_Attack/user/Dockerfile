FROM ubuntu:24.04

# Networking/DNS tools for testing name resolution from inside the container
RUN apt update \
  && DEBIAN_FRONTEND=noninteractive apt install -y \
  --no-install-recommends \
  bind9-dnsutils iproute2 iputils-ping net-tools curl \
  && rm -rf /var/lib/apt/lists/*

# We cannot directly set /etc/resolv.conf, because the file
# will be overwritten when the container starts.
COPY resolv.conf /etc/resolv.conf.override

COPY start.sh /
RUN  chmod +x /start.sh

# Copying to /etc/resolv.conf is done inside start.sh
CMD [ "/start.sh"]
