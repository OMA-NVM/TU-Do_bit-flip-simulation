# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.241.1/containers/ubuntu/.devcontainer/base.Dockerfile

# [Choice] Ubuntu version (use ubuntu-22.04 or ubuntu-18.04 on local arm64/Apple Silicon): ubuntu-22.04, ubuntu-20.04, ubuntu-18.04
ARG VARIANT="jammy"
FROM mcr.microsoft.com/vscode/devcontainers/base:0-${VARIANT}

SHELL ["/bin/bash", "-c"]

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
        && apt-get -y install --no-install-recommends build-essential \
        m4 zlib1g zlib1g-dev libprotobuf-dev protobuf-compiler \
        python-pip python2-dev libz-dev clangd \
        gcc make gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
        libncurses-dev bison flex libboost-all-dev

RUN update-alternatives --install /usr/bin/python python /usr/bin/python2 1
RUN pip2 install scons
#RUN cd gem5 ; scons -j 12 EXTRAS=../nvmain ./build/ARM/gem5.fast

#Unikraft deps
#RUN apt install apt-transport-https ca-certificates software-properties-common \
#    curl gnupg2
#RUN curl -fsSL https://releases.unikraft.org/linux/gpg | apt-key add -
#RUN add-apt-repository \
#    "deb [arch=amd64] http://releases.unikraft.org/linux/ubuntu \
#    $(lsb_release -cs) \
#    stable"
#RUN apt-get update ; apt-get install unikraft-tools

# Set environment variables

RUN echo "set completion-ignore-case on" >> /etc/inputrc
