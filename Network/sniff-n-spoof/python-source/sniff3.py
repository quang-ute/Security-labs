#!/usr/bin/python3
from scapy.all import *
def process_packet(pkt):
	if pkt.haslayer(IP):
		ip = pkt[IP]
		print("IP: {} --> {}".format(ip.src, ip.dst))
	if pkt.haslayer(TCP):
		tcp = pkt[TCP]
		print(" Flag:{}".format(tcp.flags),end="")
		print("	TCP port: {} --> {}".format(tcp.sport, tcp.dport))
	elif pkt.haslayer(UDP):
		udp = pkt[UDP]
		print(" UDP port: {} --> {}".format(udp.sport, udp.dport))
	elif pkt.haslayer(ICMP):
		icmp = pkt[ICMP]
		print(" ICMP type: {}".format(icmp.type))
	else:
		print("	Other protocol")

sniff(iface='br-bf52093ff2f2', filter='ip', prn=process_packet)
