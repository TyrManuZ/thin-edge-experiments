ARG VARIANT
FROM mcr.microsoft.com/vscode/devcontainers/base:${VARIANT}

RUN apt update
RUN apt install -y software-properties-common
RUN add-apt-repository ppa:mosquitto-dev/mosquitto-ppa
RUN apt update
RUN apt install -y mosquitto
RUN apt install -y mosquitto-clients
RUN apt install -y supervisor
RUN apt install -y python3-pip
RUN apt install -y python3-paho-mqtt
RUN apt install -y collectd-core

RUN pip install pyjwt
RUN pip install pyyaml
RUN pip install toml

# install and configure thin-edge
ARG THIN_EDGE_VERSION THIN_EDGE_ARCH
#RUN curl -fsSL https://raw.githubusercontent.com/thin-edge/thin-edge.io/main/get-thin-edge_io.sh | sudo sh -s ${THIN_EDGE_VERSION}
RUN curl -fsSL https://github.com/thin-edge/thin-edge.io/releases/download/${THIN_EDGE_VERSION}/tedge_mapper_${THIN_EDGE_VERSION}_${THIN_EDGE_ARCH}.deb --output tedge_mapper.deb
RUN curl -fsSL https://github.com/thin-edge/thin-edge.io/releases/download/${THIN_EDGE_VERSION}/tedge_${THIN_EDGE_VERSION}_${THIN_EDGE_ARCH}.deb --output tedge.deb
RUN curl -fsSL https://github.com/thin-edge/thin-edge.io/releases/download/${THIN_EDGE_VERSION}/tedge_agent_${THIN_EDGE_VERSION}_${THIN_EDGE_ARCH}.deb --output tedge_agent.deb
RUN curl -fsSL https://github.com/thin-edge/thin-edge.io/releases/download/${THIN_EDGE_VERSION}/tedge_apt_plugin_${THIN_EDGE_VERSION}_${THIN_EDGE_ARCH}.deb --output tedge_apt_plugin.deb
# The following plugin is only available for version 0.5.3 and higher
RUN curl -fsSL https://github.com/thin-edge/thin-edge.io/releases/download/${THIN_EDGE_VERSION}/tedge_logfile_request_plugin_${THIN_EDGE_VERSION}_${THIN_EDGE_ARCH}.deb --output tedge_logfile_plugin.deb

# Note: order matters
RUN dpkg -i tedge.deb
RUN dpkg -i tedge_mapper.deb
RUN dpkg -i tedge_apt_plugin.deb
RUN dpkg -i tedge_agent.deb
RUN dpkg -i tedge_logfile_plugin.deb

RUN adduser vscode tedge-users

# The certificates
ARG DEVICE_ID
COPY .compose/device_${DEVICE_ID}/deviceKeyNoPW.pem /etc/tedge/device-certs/tedge-private-key.pem
ARG DEVICE_ID
COPY .compose/device_${DEVICE_ID}/deviceCertChain.pem /etc/tedge/device-certs/tedge-certificate.pem

RUN chmod +r /etc/tedge/device-certs/tedge-private-key.pem
RUN chmod +r /etc/tedge/device-certs/tedge-certificate.pem
RUN chown mosquitto:mosquitto /etc/tedge/device-certs/tedge-private-key.pem
RUN chown mosquitto:mosquitto /etc/tedge/device-certs/tedge-certificate.pem
RUN chown mosquitto:mosquitto /etc/tedge/device-certs

ARG C8Y_URL
RUN tedge config set c8y.url ${C8Y_URL}
# we need to configure mosquitto manually because of docker
COPY .devcontainer/c8y-bridge.conf /etc/tedge/mosquitto-conf/c8y-bridge.conf
COPY .devcontainer/tedge-mosquitto.conf /etc/tedge/mosquitto-conf/tedge-mosquitto.conf
ARG DEVICE_ID
RUN sed -i "s/<<DEVICE_ID>>/${DEVICE_ID}/g" /etc/tedge/mosquitto-conf/c8y-bridge.conf
ARG C8Y_URL
RUN sed -i "s/<<C8Y_URL>>/${C8Y_URL}/g" /etc/tedge/mosquitto-conf/c8y-bridge.conf

# setup collectd
COPY .devcontainer/collectd.conf /etc/collectd/collectd.conf

# setup supervisor
COPY .devcontainer/thin-edge-supervisor.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord"]
#CMD ["/usr/sbin/mosquitto", "-c", "/etc/mosquitto/mosquitto.conf"]