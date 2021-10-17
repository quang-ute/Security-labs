#!/usr/bin/python3
from scapy.all import *
pkt=sniff(iface='eth0',filter='icmp or udp',count=10)
pkt.summary()
