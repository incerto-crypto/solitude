FROM debian:9-slim

# update and install required software from debian repositories
RUN apt-get update && apt-get install -y apt-utils
RUN apt-get install -y curl gnupg

# add node repository
RUN curl -sL https://deb.nodesource.com/setup_10.x | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 bash -
# RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 apt-key add -
# RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

# install python3, node, git
RUN apt-get update && apt-get install -y \
    nodejs \
    python3 python3-pip python3-venv \
    git
RUN apt-get clean

# create user "ci", create ~/bin and add to PATH
RUN useradd -ms /bin/bash ci
USER ci
WORKDIR /home/ci
ENV HOME=/home/ci

# create python virtual environment and add to PATH
RUN python3 -mvenv .pyenv
ENV PATH="${HOME}/.pyenv/bin:${PATH}"
RUN python -mpip install -U setuptools
RUN python -mpip install -U wheel
RUN python -mpip install -U pip

# copy solitude
RUN mkdir tests
COPY tests/*.py tests/
COPY dist dist

# install solitude and create default project
RUN python -mpip install dist/*.whl
RUN mkdir project && (cd project && solitude init && solitude install)
