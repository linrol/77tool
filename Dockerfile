FROM ubuntu:16.04

MAINTAINER jhao104 "linrolgmail@gmail.com"

RUN apt-get update -y && \
apt-get install -y python3-pip python3-dev

COPY ./requirements.txt /requirements.txt

WORKDIR /

RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

COPY . /

ENTRYPOINT [ "python3" ]

CMD [ "api/app.py" ]