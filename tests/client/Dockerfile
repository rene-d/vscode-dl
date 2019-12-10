FROM ubuntu:disco


ENV DEBIAN_FRONTEND=noninteractive
RUN ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime

RUN apt-get update -y \
&&  apt-get install -y \
        curl lftp python3 python3-pip \
        vim golang-1.12 git \
        sudo apt-file apt-utils net-tools iputils-ping iproute2 \
        x11-common libgtk-3-0 libnotify4 libnss3 libxkbfile1 libsecret-1-0 libxss1 libx11-xcb1 libasound2 \
\
&&  dpkg-reconfigure --frontend noninteractive tzdata \
&&  update-alternatives --install /usr/bin/go go /usr/lib/go-1.12/bin/go 12 \
&&  apt-file update \
\
&&  python3 -mpip install python-dateutil PyYAML requests requests_cache \
\
&&  useradd --create-home --shell /bin/bash user \
&&  echo "user ALL = (ALL) NOPASSWD:ALL" >> /etc/sudoers

USER user
WORKDIR /home/user

ENV HOME=/home/user
ENV PATH=$PATH:$HOME/.local/bin
ENV TMPDIR=/tmp

COPY . .

CMD ["bash", "-l"]
