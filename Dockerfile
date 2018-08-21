# Basic info
FROM ubuntu:16.04
LABEL maintainer="DefaltSimon"
EXPOSE 80

# Install dependencies
ENV BUILD_DEPS "zlibc libxml2 libxml2-dev libssl-dev libxslt1-dev libjpeg8-dev zlib1g-dev libfreetype6-dev libssl-dev tk-dev libc6-dev build-essential libreadline-gplv2-dev libncursesw5-dev libsqlite3-dev libgdbm-dev libbz2-dev"
RUN apt-get update \
    && apt-get install wget python3-dev git $BUILD_DEPS -y

# Install python
ENV PYTHON_VERSION "3.6.6"
ENV PYTHON_SOURCE "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"

# Download and compile from source
RUN wget $PYTHON_SOURCE \
    && tar xzf "Python-${PYTHON_VERSION}.tgz" \
    && rm "Python-${PYTHON_VERSION}.tgz" \
    # Compile and install
    && cd "Python-${PYTHON_VERSION}" && ./configure --enable-optimizations \
    && make && make install \
    # Clean up
    && cd .. && rm -r "Python-${PYTHON_VERSION}/"

RUN wget -O get-pip.py "https://bootstrap.pypa.io/get-pip.py" \
	&& python3.6 get-pip.py \
	&& rm get-pip.py

# Copy files
ENV HOME /home
ENV NANO /home/Nano

COPY . $HOME/Nano

# Copy necessary files
RUN cp docker/directories.json $NANO/core/ \
    && cp docker/dockerautorun.sh $HOME \
    && chmod +x $HOME/dockerautorun.sh

# Remove old folders
RUN rm -r docker/ \
    && pip install -r $NANO/requirements.txt

# Uninstall dependencies after installing python modules
RUN apt-get remove $BUILD_DEPS -y \
	&& apt-get purge -y --autoremove

# Set version and entrypoint
ARG VERSION=unknown
LABEL version=$VERSION
ENTRYPOINT ["/home/dockerautorun.sh"]
