FROM ubuntu:20.04
LABEL maintainer="DefaultSimon"

##
# Install python
##
ENV BUILD_DEPS "gcc python3-dev"

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install software-properties-common git curl -y  \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install python3.8 python3.8-distutils $BUILD_DEPS -y

##
# Copy files
##
ENV HOMEDIR /home
ENV NANODIR /home/Nano

COPY . $HOMEDIR/Nano

# Copy docker-specific files
COPY docker/directories.json $NANODIR/core/
COPY docker/nano-entrypoint.sh $HOMEDIR
RUN chmod +x $HOMEDIR/nano-entrypoint.sh

# Install dependencies
RUN chmod +x $HOMEDIR/nano-entrypoint.sh \
    && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python3.8 get-pip.py \
    && python3.8 -m pip install -r $NANODIR/requirements.txt

# Uninstall python and compile dependencies after installing python modules to make the container smaller
RUN apt-get remove $BUILD_DEPS -y \
	&& apt-get purge -y --autoremove

# Set version and entrypoint
# TODO what does this arg do?
ARG VERSION=unknown
LABEL version=$VERSION
ENTRYPOINT ["/bin/bash", "/home/nano-entrypoint.sh"]
