FROM centos:7

RUN echo '---> Setting up build environment' \
	&& yum install -y git gcc make openssl-devel bzip2-devel libffi-devel sqlite-devel postgresql-devel wget

RUN echo '---> Setting up Python' \
    && cd /usr/src \
    && wget https://www.python.org/ftp/python/3.7.2/Python-3.7.2.tgz \
    && tar xzf Python-3.7.2.tgz \
    && cd Python-3.7.2 \
    && ./configure --enable-optimizations \
    && make altinstall


RUN echo ' ---> Setting up user environment' \
    && adduser -u 1000 pili \
    && mkdir /app \
    && chown pili /app

RUN localedef -c -f UTF-8 -i ru_RU ru_RU.UTF-8
ENV LC_ALL=ru_RU.UTF-8
ENV LANG=ru_RU.UTF-8

COPY requirements.txt /app/requirements.txt

RUN echo ' ---> Installing package dependencies' \
	&& pip3.7 install --upgrade pip \
	&& pip3.7 install -r /app/requirements.txt

COPY . /app

WORKDIR /app

RUN echo ' ---> Clean up build environment' \
	&& yum autoremove -y \
	&& yum clean all \
    && rm -rf ~/.cache \
    && rm -rf /var/cache/yum \
    && sh -c 'find . | grep -E "(_pycache_|\.pyc|\.pyo$)" | xargs rm -rf'

USER pili

CMD ["python3.7", "manage.py", "runserver", "--host=0.0.0.0"]
