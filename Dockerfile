FROM python:3.7.3

RUN echo '---> Setting up build environment' \
    && apt-get update -y \
	&& apt-get install -y git gcc make libssl-dev libffi-dev libsqlite3-dev libpq-dev locales telnet

RUN echo '---> Setting up user environment' \
    && mkdir /app

COPY . /app
WORKDIR /app

RUN localedef -c -f UTF-8 -i en_US en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV TERM=xterm-256color

RUN echo '---> Installing package dependencies' \
	&& pip install --upgrade pip \
	&& pip install -r /app/requirements.txt \
	&& pip install -e .

RUN echo '---> Clean up build environment' \
	&& apt-get autoremove -y \
	&& apt-get clean -y \
    && rm -rf ~/.cache \
    && rm -rf /var/cache/apt \
    && sh -c 'find . | grep -E "(_pycache_|\.pyc|\.pyo$)" | xargs rm -rf'

CMD ["pili", "--config=production", "uwsgi", "--section=production"]
