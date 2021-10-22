#!/usr/bin/python3
from scapy.all import *
def process_packet(pkt):
    pkt.show()
    print("----------------")
f = 'udp and dst portrange 50-55 or icmp'
pkt=sniff(iface='ens3', filter=f, prn=process_packet)
pkt.summary()
