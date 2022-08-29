## About bWapp
bWAPP, or a buggy web application, is a free and open source deliberately insecure web application.
It helps security enthusiasts, developers and students to discover and to prevent web vulnerabilities.
bWAPP prepares one to conduct successful penetration testing and ethical hacking projects.

What makes bWAPP so unique? Well, it has over 100 web vulnerabilities!
It covers all major known web bugs, including all risks from the OWASP Top 10 project
## How to install
Download docker image: `docker pull raesene/bwapp`

Run the command: `docker run --rm -it -p 8025:80 raesene/bwapp` to start the docker container. 

Enter `localhost:8025/install.php` on the browser address bar to initialize the database.

You can now login with credential: username: bee, password: bug

Now you are ready for the Web security labs.
