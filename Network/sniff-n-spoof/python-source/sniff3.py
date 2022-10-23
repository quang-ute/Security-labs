#!/usr/bin/python3
from scapy.all import *
def process_packet(pkt):
	if pkt.haslayer(IP):
		ip = pkt[IP]
		print("IP:{} --> {}".format(ip.src, ip.dst),end="/")
	if pkt.haslayer(TCP):
		tcp = pkt[TCP]
		print("TCP:{} --> {} {}".format(tcp.sport, tcp.dport,tcp.flags))
	elif pkt.haslayer(UDP):
		udp = pkt[UDP]
		print("UDP:{} --> {}".format(udp.sport, udp.dport))
	elif pkt.haslayer(ICMP):
		icmp = pkt[ICMP]
		type,code = icmp.type,icmp.code
		typemsg = "Echo request" if (type==8) else "Echo reply"
		print("ICMP {},{}".format(typemsg,icmp.code))
	else:
		print("	Other protocol")
# replace iface with NIC name of your computer
sniff(iface='br-5311b69d8d78', filter='ip', prn=process_packet)
