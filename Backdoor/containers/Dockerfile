FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update  \
    && apt-get -y install  \
        binutils \
	netcat \
        curl   \
        iproute2  \
        iputils-ping \
        mtr-tiny \
        nano   \
        net-tools \
        unzip \
     && rm -rf /var/lib/apt/lists/*



CMD /bin/bash
