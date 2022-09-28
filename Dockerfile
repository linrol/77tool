FROM ubuntu:18.04

MAINTAINER jhao104 "linrolgmail@gmail.com"

RUN sed -i s@/archive.ubuntu.com/@/mirrors.cloud.tencent.com/@g /etc/apt/sources.list

# Update apt packages
RUN apt update
RUN apt upgrade -y

# Install python 3.7
RUN apt install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt install python3.7 -y

# Install pip
RUN apt install python3-pip -y
RUN python3 -m pip install --upgrade pip

# Install git
RUN add-apt-repository ppa:git-core/ppa
RUN apt update
RUN apt install git -y

# git clone sourcecode
WORKDIR /data/
COPY ./download.sh ./download.sh
RUN ./download.sh

# Install pip packages
WORKDIR /data/backend/branch-manage/
COPY . ./
RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

# run
# ENTRYPOINT ["python3"]
WORKDIR /data/backend/branch-manage/api/
CMD python3 app.py -p=8076 -i="wwcba5faed367cdeee" -s="d8x9pOUynLxggWIrxWecj9oupX59EwFH9teCkC9J1H4" -t="UNn2blWtjouEPUSeMsVS5A9eTjy5Z" -k="VpPjRfzYsddGOlSVJRVvUQeOaS6hjrAVYb3bobmWapw" -gd="gitlab.q7link.com" -gi="cdd8afbfd433d3b15a06f0b313fdf6060a5a04d63d9871ac0f366a3bffa44214" -gs="b6960421995e1272d286258a06df48021f0c37761907e59c62798a75d0631b11"
# CMD sleep 99999999