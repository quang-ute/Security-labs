#!/usr/bin/python3
from scapy.all import *
print("Triggering UDP ping pong . . .")

ip = IP(src="10.9.0.5", dst="10.9.0.6")
udp = UDP(sport=9090, dport=9090)
data = "Let the ping pong game start!\n"
pkt = ip/udp/data
send(pkt,verbose=0) 
