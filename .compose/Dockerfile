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
RUN curl -fsSL https://github.com/thin-edge/thin-edge.io/releases/download/${THIN_EDGE_VERSION}/c8y_log_plugin_${THIN_EDGE_VERSION}_${THIN_EDGE_ARCH}.deb --output tedge_logfile_plugin.deb
RUN curl -fsSL https://github.com/thin-edge/thin-edge.io/releases/download/${THIN_EDGE_VERSION}/tedge_apama_plugin_${THIN_EDGE_VERSION}_${THIN_EDGE_ARCH}.deb --output tedge_apama_plugin.deb
RUN curl -fsSL https://github.com/thin-edge/thin-edge.io/releases/download/${THIN_EDGE_VERSION}/c8y_configuration_plugin_${THIN_EDGE_VERSION}_${THIN_EDGE_ARCH}.deb --output tedge_configuration_plugin.deb
RUN curl -fsSL https://github.com/thin-edge/thin-edge.io/releases/download/${THIN_EDGE_VERSION}/tedge_watchdog_${THIN_EDGE_VERSION}_${THIN_EDGE_ARCH}.deb --output tedge_watchdog_plugin.deb

# Note: order matters
RUN dpkg -i tedge.deb
RUN dpkg -i tedge_mapper.deb
RUN dpkg -i tedge_apt_plugin.deb
RUN dpkg -i tedge_agent.deb
RUN dpkg -i tedge_logfile_plugin.deb
RUN dpkg -i tedge_configuration_plugin.deb
RUN dpkg -i tedge_apama_plugin.deb
RUN dpkg -i tedge_watchdog_plugin.deb

#RUN adduser vscode tedge-users
ARG DEVICE_ID
RUN tedge cert create --device-id ${DEVICE_ID}

ARG C8Y_URL
RUN tedge config set c8y.url ${C8Y_URL}
# we need to configure mosquitto manually because of docker
COPY c8y-bridge.conf /etc/tedge/mosquitto-conf/c8y-bridge.conf
COPY tedge-mosquitto.conf /etc/tedge/mosquitto-conf/tedge-mosquitto.conf
COPY c8y-log-plugin.toml /etc/tedge/c8y/c8y-log-plugin.toml
COPY c8y-configuration-plugin.toml /etc/tedge/c8y/c8y-configuration-plugin.toml
ARG DEVICE_ID
RUN sed -i "s/<<DEVICE_ID>>/${DEVICE_ID}/g" /etc/tedge/mosquitto-conf/c8y-bridge.conf
ARG C8Y_URL
RUN sed -i "s/<<C8Y_URL>>/${C8Y_URL}/g" /etc/tedge/mosquitto-conf/c8y-bridge.conf

# setup collectd
COPY collectd.conf /etc/collectd/collectd.conf

# setup supervisor
COPY thin-edge-supervisor.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord"]
#CMD ["/usr/sbin/mosquitto", "-c", "/etc/mosquitto/mosquitto.conf"]