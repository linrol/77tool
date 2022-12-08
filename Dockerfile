FROM ubuntu:18.04

MAINTAINER jhao104 "linrolgmail@gmail.com"

RUN sed -i s@/archive.ubuntu.com/@/mirrors.cloud.tencent.com/@g /etc/apt/sources.list

# Update apt packages
RUN apt update && apt upgrade -y

# Install python 3.7
RUN apt install software-properties-common -y && \
    add-apt-repository ppa:deadsnakes/ppa &&  \
    apt install python3.9 -y

# Install pip
RUN apt install python3-pip -y &&  \
    python3 -m pip install --upgrade pip

# Install git
RUN add-apt-repository ppa:git-core/ppa && \
    apt update &&  \
    apt install git -y

# git clone sourcecode
ARG GIT_PASSWORD
ENV GIT_PASSWORD ${GIT_PASSWORD}
WORKDIR /data/
COPY ./download.sh ./download.sh
RUN ./download.sh

# Install pg and conifg pg
RUN apt install postgresql -y &&  \
    apt install libpq-dev -y
USER postgres
RUN /etc/init.d/postgresql start &&  \
    psql --command "alter user postgres with password '123';"

# Install pip packages
USER root
WORKDIR /data/backend/branch-manage/
COPY . ./
RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

# set utf-8
RUN apt install language-pack-zh-hans -y &&  \
    echo "export LC_ALL=zh_CN.utf8" > /etc/locale.conf &&  \
    echo "export LANG=zh_CN.utf8" > /etc/locale.conf &&  \
    echo "export LANGUAGE=zh_CN.utf8" > /etc/locale.conf
ENV LANG zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8

# run
RUN mkdir -p /data/logs
WORKDIR /data/backend/branch-manage/api/
CMD git config --global user.email "backend-ci@77hub.com" && git config --global user.name "backend-ci" && service postgresql start && python3 app.py -p=8076 -i="wwcba5faed367cdeee" -s="d8x9pOUynLxggWIrxWecj9oupX59EwFH9teCkC9J1H4" -t="UNn2blWtjouEPUSeMsVS5A9eTjy5Z" -k="VpPjRfzYsddGOlSVJRVvUQeOaS6hjrAVYb3bobmWapw"