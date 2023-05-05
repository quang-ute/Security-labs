FROM alpine:3.12

# init ash file (for non-login shells)
ENV ENV '$HOME/.ashrc'

# default screen size
ENV XRES 1280x1024x24

# default tzdata settings
ENV TZ Etc/UTC

# update and install system software
RUN apk update \
	&& apk upgrade \
	#
	# main packages
	&& apk add setup-box sudo supervisor openssh-server openssh nano tcpdump lftp \
	&& apk add firefox wireshark xvfb x11vnc \
	#
	# keyboard and other utils
	xfce4-xkb-plugin mousepad \
	#
	# timezone support
	tzdata

# run setup-box to setup a desktop + xfce4 workstation
# but first, patch setup-box to not asking for new user's passwd
RUN sed -i  's/adduser -h/adduser -D -h/' /sbin/setup-box \
	&& echo Y | setup-box -v -d xfce -u alpine

# change root passwd and add users and groups 
# (user alpine alredy added by setup-box)
RUN	echo "root:alpine" | /usr/sbin/chpasswd \
    && echo "alpine:alpine" | /usr/sbin/chpasswd \
    && echo "alpine    ALL=(ALL) ALL" >> /etc/sudoers 	
#COPY transfer.php tricky.html /home/alpine 
COPY hosts /etc/hosts


# setup sshd
RUN mkdir /run/sshd \
	&& ssh-keygen -A

# add my sys config files
ADD etc /etc

# customizations

# ash personal config file for non-login shell mode (as default in xfce terminal)
# read by ash per ENV=~/.ashrc (see above)
RUN echo "alias ll='ls -l'" > /home/alpine/.ashrc \
	&& echo "alias lla='ls -al'" >> /home/alpine/.ashrc \
	&& echo "alias llh='ls -hl'" >> /home/alpine/.ashrc \
	&& echo "alias hh=history" >> /home/alpine/.ashrc \
	#
	# ash personal config file for login shell mode
	&& cp /home/alpine/.ashrc /home/alpine/.profile 


# personal xfce4 config
ADD config/xfce4/terminal/terminalrc /home/alpine/.config/xfce4/terminal/terminalrc

# set custom wallpaper
ADD config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml  \
	/home/alpine/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml

# RUN chown -R alpine:alpine /home/alpine/.config /home/alpine/.xscreensaver
RUN chown -R alpine:alpine /home/alpine/

# exposed ports
EXPOSE 22 5900

# default command
CMD ["/usr/bin/supervisord","-c","/etc/supervisord.conf"]
