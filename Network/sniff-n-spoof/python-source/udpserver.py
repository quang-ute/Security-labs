#!/usr/bin/python3
import socket

ip = "0.0.0.0"
port = 9090
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ip,port))
while True:
	data, (ip,port) = sock.recvfrom(1024)
	print("Sender: {}, port: {}".format(ip,port))
	print("Received message: {}".format(data))

	sock.sendto(b"Thank you!",(ip,port))
