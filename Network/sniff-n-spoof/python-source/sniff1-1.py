#!/usr/bin/python3
#import scapy.all as scapy
from scapy.all import *
def process_pkt(pkt):
    dst_mac=pkt[0][0].dst
    src_mac=pkt[0][0].src
    print("TCP flag:",pkt[0][2].flags)
    print("Source port:",pkt[0][2].sport)
    print("Dest port:",pkt[0][2].dport)  
    print("  IP:")
    print("     Source:",pkt[0][1].src)
    print("     Dest:",pkt[0][1].dst)      
    print("     Ethernet:")
    print("         src:",src_mac)
    print("         dest:",dst_mac)
  
pkt=sniff(iface='br-55a796522682',prn=process_pkt)

