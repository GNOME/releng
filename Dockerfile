FROM python:3.8-slim

RUN apt update && apt install git -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    git clone https://gitlab.gnome.org/GNOME/releng.git /opt/releng

ENTRYPOINT ["/usr/bin/python3"]
