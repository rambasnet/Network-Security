# DNS Attacks Lab

A self-contained Docker lab for demonstrating DNS attacks: a **rogue/compromised
local DNS server**, **local DNS sniff-and-spoof**, and **DNS cache poisoning**.
The lab runs entirely on your machine and does **not** depend on real Internet
DNS, so the attack demos are deterministic and repeatable in class.

> Educational use only. Run these attacks only inside this lab.

---

## 1. Topology

```
                         net-10.8.0.0/24 (the "outside")
                                  │
                          ┌───────┴────────┐
                          │   router-11    │  10.8.0.11  ── NAT ──▶ Internet
                          │ (gateway/NAT)  │
                          └───────┬────────┘
                                  │ 10.9.0.11
  ════════════════════════ net-10.9.0.0/24 (the lab LAN) ════════════════════════
     │             │              │                │                 │
 user-5        dns-server-53   legit-dns-54   attacker-dns-153     firefox
 10.9.0.5       10.9.0.53       10.9.0.54       10.9.0.153        10.9.0.100
 (victim       (local caching  (honest         (attacker's        (GUI browser,
  client,       resolver)       example.net     rogue name         DNS=10.9.0.53)
 (DNS=...0.53)                   authority)      server)

 attacker  ── network_mode: host ──▶ sees the whole 10.9.0.0 LAN (sniff + spoof)
```

The **attacker** container shares the host network namespace, so it can sniff
and inject packets on the `10.9.0.0/24` bridge — this is what makes the
on-path attacks possible.

---

## 2. Services

| Service        | Container          | IP                    | Role                                                                                                                                                   |
| -------------- | ------------------ | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `router`       | `router-11`        | 10.9.0.11 / 10.8.0.11 | Gateway + NAT between the lab LAN and the outside.                                                                                                     |
| `dns-server`   | `dns-server-53`    | 10.9.0.53             | The **victim** local caching resolver. This is what `user-5` and `firefox` use.                                                                        |
| `user`         | `user-5`           | 10.9.0.5              | The **victim client**. Uses `10.9.0.53` for DNS. Where you run `dig`/`ping`.                                                                           |
| `legit-dns`    | `legit-dns-54`     | 10.9.0.54             | The **honest** authoritative server for `example.net` (serves the real records). Has an 80 ms simulated WAN delay so the local attacker wins the race. |
| `attacker-dns` | `attacker-dns-153` | 10.9.0.153            | The **attacker's rogue** authoritative server (`attacker32.com`, `example.com`, rogue `example.net`, and the reverse zone).                            |
| `attacker`     | `attacker`         | host network          | The **attacker** box. Runs the Scapy scripts in `volumes/`. Sniffs/injects on the LAN.                                                                 |
| `firefox`      | `firefox`          | 10.9.0.100            | Optional GUI browser (open `http://localhost:5800`) to _see_ a hijack in a browser.                                                                    |

### How the resolver (`dns-server-53`) is configured

`dns_server/named.conf` makes the victim resolver answer these zones from lab
servers instead of the real Internet:

| Zone                     | Resolved via                          | Purpose                                                       |
| ------------------------ | ------------------------------------- | ------------------------------------------------------------- |
| `example.com`            | forward → `10.9.0.153` (attacker-dns) | Rogue-forwarder demo                                          |
| `attacker32.com`         | forward → `10.9.0.153` (attacker-dns) | Rogue-forwarder demo                                          |
| `0.168.192.in-addr.arpa` | forward → `10.9.0.153` (attacker-dns) | Reverse (PTR) demo                                            |
| `example.net`            | forward → `10.9.0.54` (legit-dns)     | **Cache-poisoning target** (honest server the attacker races) |
| everything else          | `forwarders { 8.8.8.8; 1.1.1.1; }`    | Real sites resolve (so `ping google.com` works)               |

---

## 3. Prerequisites

- Docker Desktop (macOS/Windows) or Docker Engine (Linux) with Docker Compose v2.
- The lab is tuned to work on **Docker Desktop for macOS**; see
  [Platform notes](#9-platform-notes--troubleshooting).

---

## 4. Build & start

```bash
cd course/demos/DNS_Attack
docker compose build          # first time, or after changing a Dockerfile/zone/config
docker compose up -d          # start all services
docker compose ps             # all containers should be "Up"
```

Open a shell on the containers you use most:

```bash
docker exec -it user-5 bash       # victim client
docker exec -it attacker bash     # attacker (scripts are in /volumes)
```

---

## 5. Verify the lab is healthy

```bash
# Victim client can resolve the lab zones (via the resolver 10.9.0.53):
docker exec user-5 dig +short www.example.com     @10.9.0.53   # 8.8.8.8  (rogue record)
docker exec user-5 dig +short www.attacker32.com  @10.9.0.53   # 192.168.0.101
docker exec user-5 dig +short -x 192.168.0.101    @10.9.0.53   # www.attacker32.com.
docker exec user-5 dig +short www.example.net     @10.9.0.53   # 93.184.216.34  (HONEST)

# Real Internet names resolve too (via forwarders), and connectivity works:
docker exec user-5 dig +short google.com @10.9.0.53
docker exec user-5 ping -c1 google.com
```

If `www.example.net` returns `93.184.216.34`, the honest path is working and
you are ready to attack it.

---

## 6. Demo 1 — Rogue / compromised local DNS (forwarder hijack)

**Idea:** if the local resolver is misconfigured or compromised to forward a
domain to an attacker-controlled name server, every client silently gets
attacker-chosen answers — no packet spoofing required.

```bash
# The resolver forwards example.com / attacker32.com to the attacker's server:
docker exec user-5 dig +short www.example.com    @10.9.0.53   # 8.8.8.8      (attacker's record)
docker exec user-5 dig +short attacker32.com      @10.9.0.53   # 192.168.0.101
docker exec user-5 dig +short abc.attacker32.com  @10.9.0.53   # 192.168.0.102
docker exec user-5 dig +short -x 192.168.0.101    @10.9.0.53   # reverse lookup, too
```

Compare with the _truth_ served by the attacker's zone files in
`attacker_dns/zone_*` — the client has no way to tell these are rogue.

**Talking point:** this is the baseline threat. The next two demos show how an
attacker who is only _on the network_ (not controlling the resolver) can achieve
the same thing.

---

## 7. Demo 2 — DNS cache poisoning (the main attack)

**Idea:** the attacker sniffs the resolver's outbound query for
`www.example.net` and injects a **forged reply** that arrives before the honest
answer from `legit-dns`. The forged record is cached by the resolver (long TTL),
so **every** client is poisoned until the cache expires or is flushed.

Script: `volumes/poison_dns_cache.py`
(sniffs `src host 10.9.0.53 and dst port 53`, spoofs `www.example.net → 192.168.0.100`).

```bash
# --- Terminal A: start the attacker ---
docker exec -it attacker python3 /volumes/poison_dns_cache.py
#   prints "Sending spoofed packet" when it fires

# --- Terminal B: trigger a lookup from the victim ---
docker exec dns-server-53 rndc flush                       # clear cached truth first
docker exec user-5 dig +short www.example.net @10.9.0.53   # 192.168.0.100  (POISONED)

# Show the poisoned entry sitting in the resolver's cache (TTL ~3 days):
docker exec dns-server-53 rndc dumpdb -cache
docker exec dns-server-53 grep example.net /var/cache/bind/dump.db
```

**Why it wins reliably:** `legit-dns` has an 80 ms `tc netem` delay (simulating a
remote authoritative server), while the attacker is on the local LAN. Show it:

```bash
docker exec legit-dns-54 tc qdisc show dev eth0            # ... netem delay 80ms
```

**Reset between runs:**

```bash
docker exec attacker pkill -f poison_dns_cache
docker exec dns-server-53 rndc flush
docker exec user-5 dig +short www.example.net @10.9.0.53   # back to 93.184.216.34
```

**Browser view (optional):** open `http://localhost:5800` (the `firefox`
service, DNS = `10.9.0.53`). Because it uses the poisoned resolver, visiting
`www.example.net` is redirected to the spoofed IP. For a convincing visual
payoff, point `SPOOFED_IP` in `poison_dns_cache.py` at a web server running in
the lab (e.g. an attacker-hosted phishing page); otherwise the browser simply
fails to connect to `192.168.0.100`, which still demonstrates the redirect.

---

## 8. Demo 3 — Local DNS sniff-and-spoof

**Idea:** instead of poisoning the cache, the attacker forges a reply to _any_
DNS query it sees for the target name, racing the legitimate responder. This
spoofs the answer for the immediate query (and can poison the resolver too).

Script: `volumes/dns_sniff_spoof.py`
(sniffs `udp and dst port 53`, spoofs `www.example.net → 208.67.220.220`).

```bash
# --- Terminal A ---
docker exec -it attacker python3 /volumes/dns_sniff_spoof.py

# --- Terminal B ---
docker exec dns-server-53 rndc flush
docker exec user-5 dig +short www.example.net @10.9.0.53   # 208.67.220.220  (spoofed)
```

**Difference from Demo 2:** this script spoofs replies broadly (any querier),
while `poison_dns_cache.py` specifically targets the resolver's outbound query
and injects an authority (NS) record aimed at a full-domain hijack.

---

## 9. Helper: craft a DNS query by hand (`send_dns_query.py`)

A teaching script that builds a DNS query packet with Scapy.

```bash
docker exec attacker python3 /volumes/send_dns_query.py                    # www.example.net @ 10.9.0.53
docker exec attacker python3 /volumes/send_dns_query.py mail.example.net 10.9.0.54
docker exec attacker python3 /volumes/send_dns_query.py www.example.com 10.9.0.53
```

It auto-detects the lab bridge interface and defaults to the lab DNS. Querying a
public resolver directly with Scapy (e.g. `... 8.8.8.8`) does **not** work on
Docker Desktop (see below); it fails gracefully with an explanation.

---

## 10. Reset / stop / clean up

```bash
docker exec dns-server-53 rndc flush          # drop poisoned entries, keep lab running
docker compose restart dns-server             # or restart the resolver for a clean cache

docker compose down                           # stop & remove containers (keeps images)
docker compose down --rmi local -v            # also remove built images + volumes
```

---

## 11. Platform notes & troubleshooting

This lab is tuned for **Docker Desktop on macOS**, whose user-space network stack
(gvproxy) behaves differently from a native Linux bridge. Key points:

- **Scapy scripts auto-detect the capture interface** by finding the NIC that
  holds `10.9.0.1` (the lab bridge). You do **not** need to hard-code a
  `br-xxxxxxxx` name — it changes whenever the Docker network is recreated.
- **The resolver uses a public forwarder** (`forwarders { 8.8.8.8; 1.1.1.1; }`)
  for non-lab domains instead of full root recursion, which Docker Desktop's NAT
  cannot complete.
- **Do not set a fixed `query-source port`** (e.g. `query-source port 33333;`)
  on Docker Desktop. Its user-space NAT (gvproxy) does not reliably return
  replies to a long-lived fixed port, so Internet resolution breaks — often
  only _after_ a Docker restart. `named` is left to use ephemeral ports. The
  "predictable source port" idea can still be discussed, or re-enabled on a
  native Linux SEED VM; the attack demos never depend on it. Symptom when this
  regresses: `ping <IP>` works but `ping <name>` fails, and
  `dig <anything> @10.9.0.53` times out while the lab zones still resolve.
- **`ping <name>` failing but `ping <IP>` working** means DNS, not connectivity.
  Check that `dns-server-53` is up and that the name is covered by a lab zone or
  the forwarder.
- **The attack won't fire?** Make sure the `attacker` container is up with
  `network_mode: host`, flush the resolver cache (`rndc flush`) before each run,
  and confirm the script prints `Sending spoofed packet`.

---

## 12. Known limitation — full-domain (Kaminsky) NS hijack

Because `example.net` is a **forward** zone (to keep the lab Internet-free), the
resolver forwards every `example.net` query to the honest server and ignores the
injected `NS` record. So Demo 2 poisons the **specific name** (`www.example.net`)
reliably, but the full-zone hijack (`mail.example.net`, etc. → attacker) does
**not** take effect — `mail.example.net` still returns the legit `93.184.216.35`
during the attack.

Demonstrating the NS hijack requires **iterative** resolution (the resolver
walking root → TLD → authoritative), which means standing up a small lab
root/TLD "mini-Internet." That is a possible extension to this lab.

---

## 13. File layout

```
DNS_Attack/
├── docker-compose.yml
├── base/            # shared image for router + attacker (scapy, tcpdump, iptables)
├── dns_server/      # victim resolver (named.conf = forward zones + forwarders)
├── user/            # victim client (resolv.conf -> 10.9.0.53)
├── legit_dns/       # honest example.net authority (+ tc netem delay)
├── attacker_dns/    # attacker's rogue authoritative zones
│   ├── zone_attacker32.com
│   ├── zone_example.com
│   ├── zone_example.net
│   └── zone_192.168.0        # reverse (PTR) zone
└── volumes/         # Scapy attack scripts (mounted at /volumes in attacker)
    ├── poison_dns_cache.py   # Demo 2: cache poisoning
    ├── dns_sniff_spoof.py    # Demo 3: sniff-and-spoof
    └── send_dns_query.py     # helper: craft a DNS query
```
