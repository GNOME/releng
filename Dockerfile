FROM centos:7

RUN yum install -y epel-release git && \
    yum -y clean all --enablerepo='*'

RUN git clone https://gitlab.gnome.org/GNOME/releng.git /opt/releng

RUN groupadd releng -g 1000450000 
    useradd releng -g 1000450000 -u 1000450000 -r -l -m

RUN chown -R releng:releng /opt/releng

ENTRYPOINT ["/usr/bin/python2"]
