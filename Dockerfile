FROM centos:8

RUN dnf install -y git python3 && \
    dnf -y clean all --enablerepo='*'

RUN git clone https://gitlab.gnome.org/GNOME/releng.git /opt/releng

RUN groupadd releng -g 1000450000 && \ 
    useradd releng -g 1000450000 -u 1000450000 -r -l -m

RUN chown -R releng:releng /opt/releng

ENTRYPOINT ["/usr/bin/python3"]
