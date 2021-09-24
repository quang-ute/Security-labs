# CSRF 
**With DWVA (Damn Vulnerable Web App)**<br>
1. Download docker image:`docker pull vulnerables/web-dvwa`<br>
2. Run the command: `docker run --rm -it -p 80:80 vulnerables/web-dvwa` to start the docker container<br>
3. Enter `localhost/setup.php` on the browser address bar to fireup the websiste.<br>
4. Click on the `Create / Reset database` button and it will generate any aditional configuration needed<br>
You can now login with credentials: `username: admin, password: password`<br>
5. Click DWVA on the left menu, then set the security level to `low`<br>
**Attack**<br> 
1. Click CSFR to start the CSRF attack. Your goal is setting the admin password at will by inspecting the http GET request when user changes the admin password.<br>
2. Right click the "**Change your admin password**" pane, select `inspect` to display the web inspector pane at the bottom of the browser.<br>
3. Click `Network` tab on this pane to reveal the network packet inspector.<br> 
4. Enter the same password string in both `New password` and `Confirm new password` textbox, then click `Change` button.<br> 
5. A series of network packets will show up on the left in the bottom pane. Click the first packet which is the http GET request sent from browser to the server. The content of this packet reveal instantly on the right as shown in the picture below<br>  
<img width="548" alt="Screen Shot 2021-09-24 at 17 34 07" src="https://user-images.githubusercontent.com/57078914/134661071-897c91b7-ca77-440b-87ae-1f98296ef650.png">
