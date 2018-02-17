# Basic info
FROM ubuntu:16.04
LABEL maintainer="DefaltSimon"
EXPOSE 80

WORKDIR /home/

# Install python and pip, update stuff
RUN apt-get update \
    && apt-get install wget python3.5 python3-dev build-essential git nano \
    ## Pillow, lxml, ....
    zlibc libxml2 libxml2-dev libxslt1-dev \
    libjpeg8-dev zlib1g-dev libfreetype6-dev -y

RUN wget -O get-pip.py "https://bootstrap.pypa.io/get-pip.py" \
	&& python3.5 get-pip.py \
	&& rm -f get-pip.py

# Remove source
RUN rm -rf redis-4.0.6/ \
	&& rm -f redis-4.0.6.tar.gz

# Copy files	
# ENV DATA /files
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

# ujson needs build-essential!
# Uninstall unneeded stuff
RUN apt-get remove build-essential -y \
	&& apt-get purge -y --autoremove

# Set version and entrypoint
LABEL version="3.8"

# VOLUME $DATA
ENTRYPOINT ["/home/dockerautorun.sh"]
