
FROM registry.access.redhat.com/ubi8/ubi-minimal
USER root
RUN  microdnf install python3 && \
     microdnf update -y && \
     microdnf clean all && \
     rm -rf /var/cache/yum

RUN  microdnf install python3-devel python3-pip gcc
COPY requirements.txt requirements.txt
RUN  pip3 install --upgrade pip --no-cache-dir
RUN  pip3 install -r requirements.txt --no-cache-dir

COPY . /usr/src/app
WORKDIR /usr/src/app

EXPOSE 4000

CMD python3 app.py
