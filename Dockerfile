FROM ubuntu:20.04

MAINTAINER linrol "linrolgmail@gmail.com"

RUN sed -i s@/archive.ubuntu.com/@/mirrors.cloud.tencent.com/@g /etc/apt/sources.list && \
    # Update apt packages
    apt update && apt upgrade -y && \
    apt install lsb-release wget -y && \
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt update && apt upgrade -y && \
    # add ppa
    apt install software-properties-common -y && \
    add-apt-repository ppa:deadsnakes/ppa && \
    # Install python 3.9
    apt install python3.9 -y && \
    # Install pip
    apt install python3-pip -y && \
    python3 -m pip install --upgrade pip && \
    # Install git
    add-apt-repository ppa:git-core/ppa && \
    apt update && \
    apt install git -y && \
    # Install pg
    apt install postgresql -y && \
    apt install libpq-dev -y && \
    # Install language utf-8
    apt install language-pack-zh-hans -y && \
    echo "export LC_ALL=zh_CN.utf8" > /etc/locale.conf && \
    echo "export LANG=zh_CN.utf8" > /etc/locale.conf && \
    echo "export LANGUAGE=zh_CN.utf8" > /etc/locale.conf

# conifg pg
USER postgres
RUN /etc/init.d/postgresql start &&  \
    psql --command "alter user postgres with password '123';"
USER root

# git clone sourcecode
ARG GIT_PASSWORD
ENV GIT_PASSWORD ${GIT_PASSWORD}
WORKDIR /data/
COPY ./download.sh ./download.sh
RUN ./download.sh

# Install pip packages
WORKDIR /data/backend/branch-manage/
COPY . ./
RUN pip3 install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt
# RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

# set utf-8
ENV LANG zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8

# run
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN mkdir -p /data/logs
WORKDIR /data/backend/branch-manage/api/
CMD git config --global user.email "backend-ci@77hub.com" && git config --global user.name "backend-ci" && service postgresql start && python3 app.py -p=8049 -i="wwcba5faed367cdeee" -s="d8x9pOUynLxggWIrxWecj9oupX59EwFH9teCkC9J1H4" -t="UNn2blWtjouEPUSeMsVS5A9eTjy5Z" -k="VpPjRfzYsddGOlSVJRVvUQeOaS6hjrAVYb3bobmWapw"