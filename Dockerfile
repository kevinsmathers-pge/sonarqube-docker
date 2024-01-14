ARG ARTIFACTORY

FROM ${ARTIFACTORY}/ubuntu:latest

RUN apt update && \
    apt install -y git bash curl gettext docker python3 python3-pip openssl jq wget unzip openjdk-21-jre-headless patch && \
    apt-get clean
RUN /usr/bin/pip3 install awscli 

WORKDIR /root
COPY ./src ./src

# Install firewall certificate
RUN cp src/CombinedCA.cer /usr/share/ca-certificates/CombinedCA.crt
RUN echo "CombinedCA.crt" >>/etc/ca-certificates.conf
RUN update-ca-certificates

# Enable legacy renegotiation for running from behind the corporate firewall
RUN patch -p0 -d/ <src/openssl_cnf.patch && \
    patch -p0 -d/ <src/wgetrc.patch

# Fetch & install sonarqube
RUN wget -q https://binaries.sonarsource.com/Distribution/sonarqube/sonarqube-10.3.0.82913.zip -P /opt
RUN unzip -q /opt/sonarqube*.zip -d /opt
#RUN mv /opt/sonar-scanner-4.6.2.2472-linux /opt/sonar-scanner-dir
#RUN rm -rf /opt/sonar-scanner-dir/jre
#RUN ln -s /usr/lib/jvm/java-11-openjdk/jre/ /opt/sonar-scanner-dir/jre