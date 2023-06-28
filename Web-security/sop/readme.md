##How to start the websites
1. Download all the files in this folder onto your computer.
2. Enter `$> docker-compose up -d`, then the websites are ready.
3. Add these lines in the `/etc/hosts` file
`10.9.0.5    www.sitea.com` <br>
`10.9.0.5    www.siteb.com` <br>
`10.9.0.5    www.parentsite.com` <br>
Now you can access websites from web-client docker container by name.
