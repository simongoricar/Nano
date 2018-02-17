# Basic info
FROM ubuntu:16.04
LABEL maintainer="DefaltSimon"
EXPOSE 80

# Install python and pip, update stuff
ENV BUILD_DEPS "zlibc libxml2 libxml2-dev libxslt1-dev libjpeg8-dev zlib1g-dev libfreetype6-dev build-essential"
RUN apt-get update \
    && apt-get install wget python3.5 python3-dev git nano $BUILD_DEPS -y

RUN wget -O get-pip.py "https://bootstrap.pypa.io/get-pip.py" \
	&& python3.5 get-pip.py \
	&& rm -f get-pip.py

# Copy files
ENV HOME /home
ENV NANO /home/Nano

COPY . $HOME/Nano

# Overwrite certain files
COPY docker/directories.json $NANO/core/
# Docker configuration
COPY docker/dockerautorun.sh $HOME
RUN chmod +x $HOME/dockerautorun.sh

RUN rm -rf docker/ \
    && pip install -r $NANO/requirements.txt

# Uninstall dependencies after installing python modules
RUN apt-get remove $BUILD_DEPS -y \
	&& apt-get purge -y --autoremove

# Set version and entrypoint
ARG VERSION=unknown
LABEL version=$VERSION
CMD ["python", "./nano.py"]
