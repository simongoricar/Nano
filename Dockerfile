# Basic info
FROM ubuntu:16.04
LABEL maintainer="DefaltSimon"
EXPOSE 80
VOLUME ["/files"]

RUN apt-get update && apt-get upgrade -y
WORKDIR /home/

# Install python and pip
RUN apt-get install wget python3.5 python3-dev build-essential git -y \
	&& wget -O get-pip.py "https://bootstrap.pypa.io/get-pip.py" \
	&& python3.5 get-pip.py \
	&& rm -f get-pip.py

ENV BINARIES /usr/local/bin/

# Download and install redis
RUN wget -O redis-4.0.6.tar.gz "http://download.redis.io/releases/redis-4.0.6.tar.gz" \
	&& tar xzf redis-4.0.6.tar.gz \
	&& cd redis-4.0.6/ && make
RUN cd redis-4.0.6/ \
	&& cp src/redis-server $BINARIES \
	&& cp src/redis-cli $BINARIES \
	&& cp src/redis-sentinel $BINARIES \
	&& cp src/redis-check-aof $BINARIES \
	&& cp src/redis-check-rdb $BINARIES

# Remove source
RUN rm -rf redis-4.0.6/ \
	&& rm -f redis-4.0.6.tar.gz

# Copy files	
ENV DATA /files
ENV HOME /home
ENV NANO /home/Nano/

COPY . $HOME/Nano
COPY data/ $DATA/data/
# Overwrite certain files
ADD docker/directories.json $NANO/core/
ADD docker/dockerautorun.sh $HOME

RUN rm -rf $NANO/data/ \
    && pip install -r $NANO/requirements.txt

# ujson needs build-essential!
# Uninstall unneeded stuff
RUN apt-get remove build-essential -y \
	&& apt-get purge -y --autoremove

# Set version and entrypoint
LABEL version="3.8"
ENTRYPOINT ["dockerautorun.sh"]
