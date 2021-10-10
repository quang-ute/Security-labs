# Demonstration of backdoor
## About the docker images
Two images (one for the server, another for the attacker) are created based on Ubuntu 20.04 OS with minimal packages pre-installed.<br>

## Network configuration
The server and attacker containers will be created and attach to network 10.9.0.0/24 <br>
The server machine is named server-10.9.0.5, whereas attacker-10.9.0.6 is the name of the attacker machine.<br>
The local directory `/mapdir` inside the server mapped to directory `./containers` on the host machine.<br>
## Building up the network
1. Create a directory named Backdoor. Copy docker-compose.yml and directory containers to the newly created directory.
2. Inside Backdoor, issuing the command `$>docker-compose up` to build up the images, containers, network. When everything is up, the containers are ready.<br>

