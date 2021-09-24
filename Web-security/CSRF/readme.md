# CSRF 
**With DWVA (Damn Vulnerable Web App)**<br>
1. Download docker image:`docker pull vulnerables/web-dvwa`<br>
2. Run the command: `docker run --rm -it -p 80:80 vulnerables/web-dvwa` to start the docker container<br>
3. Enter `localhost/setup.php` on the browser address bar to fireup the websiste.<br>
4. Click on the `Create / Reset database` button and it will generate any additional configuration needed<br>
You can now login with credentials: `username: admin, password: password`<br>
5. Click DWVA on the left menu, then set the security level to `low`<br>
6. Fireup the simple http server. Now you are ready for the lab.
7. For lab detail please watch the video of the instructor.
