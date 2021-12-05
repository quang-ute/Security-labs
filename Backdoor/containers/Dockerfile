FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update  \
    && apt-get -y install  \
    sudo \
        binutils \
	netcat \
#        curl   \
	python \
        iputils-ping \
        nano   \
        net-tools \
     && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash exam && \
	echo "root:exam" | chpasswd && \
	echo "exam:exam" | chpasswd && \
	usermod -aG sudo exam

USER exam
WORKDIR /home/exam
COPY server /home/exam
COPY stack /home/exam
CMD /bin/bash
