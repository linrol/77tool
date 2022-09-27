FROM ubuntu:18.04

MAINTAINER jhao104 "linrolgmail@gmail.com"

RUN sed -i s@/archive.ubuntu.com/@/mirrors.aliyun.com/@g /etc/apt/sources.list

RUN apt-get update -y && \
    apt-get install -y software-properties-common &&  \
    add-apt-repository ppa:deadsnakes/ppa &&  \
    apt-get install -y python3.7

COPY ./requirements.txt /requirements.txt

WORKDIR /

RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

COPY . /

ENTRYPOINT [ "python3" ]

CMD [ "api/app.py" ]