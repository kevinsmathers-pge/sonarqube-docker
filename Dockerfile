ARG ARTIFACTORY=

FROM ${ARTIFACTORY}ubuntu:latest

RUN apt update && \
    apt install -y git bash curl gettext docker python3 python3-pip openssl jq wget unzip openjdk-17-jre-headless patch && \
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
RUN unzip -q /opt/sonarqube*.zip -d /opt && \
    rm -f /opt/sonarqube*.zip && \
    ln -sf /opt/sonarqube-* /opt/sonarqube && \
    patch -p0 -d/ <src/sonarqube_cnf.patch

# Fetch & install sonar-scanner-cli
RUN wget -q https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip -P /opt
RUN unzip -q /opt/sonar-scanner-cli*zip -d /opt && \
    rm -f /opt/sonar-scanner-cli*zip && \
    ln -sf /opt/sonar-scanner-* /opt/sonar-scanner && \
    cp src/sonar_scanner_cf.patch.template /tmp && \
    cp src/fill-template.py /tmp && \
    cp src/scanner-setup.sh /opt

# Create sonarqube user
RUN useradd sonarqube -s /usr/bin/bash -d /opt/sonarqube && \
    chown -R sonarqube.sonarqube /opt/sonarqube-* && \
    chown -R sonarqube.sonarqube /opt/sonar-scanner-*

# Install manual debugging utilities
RUN apt install -y sudo vim rcs && \
    apt-get clean && \
    echo "sonarqube ALL=NOPASSWD: ALL" >>/etc/sudoers

# Install python libraries
COPY dist dist
RUN pip install dist/*whl

USER sonarqube
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/CombinedCA.pem
WORKDIR /opt
RUN 
#RUN mv /opt/sonar-scanner-4.6.2.2472-linux /opt/sonar-scanner-dir
#RUN rm -rf /opt/sonar-scanner-dir/jre
#RUN ln -s /usr/lib/jvm/java-11-openjdk/jre/ /opt/sonar-scanner-dir/jre