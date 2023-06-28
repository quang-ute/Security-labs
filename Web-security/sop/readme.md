How to start the websites
Download all the files in this folder onto your computer.
Enter $> docker-compose up -d, then the websites are ready.
Add these lines in the /etc/hosts file
10.9.0.5    www.sitea.com
10.9.0.5    www.siteb.com
10.9.0.5    www.parentsite.com
Now you can access websites from web-client docker container by name.
