FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update  \
    && apt-get -y install  \
        apache2 \
        curl   \
        nano   \
        libapache2-mod-php7.4 \
        php7.4-cli \
        php7.4-gd \
        php7.4-pdo \
        php7.4-json \
        php7.4-xml \
        php7.4-mbstring \
        php7.4-mysql \
    && a2enmod rewrite \
    && a2enmod ssl \
    && a2enmod cgi \
    && a2enmod headers

CMD service apache2 start && tail -f /dev/null

COPY my_server.conf server_name.conf /etc/apache2/sites-available/

RUN mkdir /var/www/mysite 
RUN mkdir /var/www/darksite 
RUN chmod 755 /var/www/mysite
RUN chmod 755 /var/www/darksite


RUN  a2ensite server_name.conf   \
     && a2ensite my_server.conf 
