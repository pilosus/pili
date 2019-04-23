FROM python:3.7.3

RUN echo '---> Setting up build environment' \
    && apt update -y \
	&& apt install -y git gcc make libssl-dev libffi-dev libsqlite3-dev libpq-dev locales


RUN echo ' ---> Setting up user environment' \
    && adduser -u 1000 pili \
    && mkdir /app \
    && chown pili /app

RUN localedef -c -f UTF-8 -i en_US en_US.UTF-8
ENV LANG=en_US.UTF-8

COPY requirements.txt /app/requirements.txt

RUN echo ' ---> Installing package dependencies' \
	&& pip install --upgrade pip \
	&& pip install -r /app/requirements.txt

COPY . /app

WORKDIR /app

RUN echo ' ---> Clean up build environment' \
	&& apt autoremove -y \
	&& apt clean -y \
    && rm -rf ~/.cache \
    && rm -rf /var/cache/apt \
    && sh -c 'find . | grep -E "(_pycache_|\.pyc|\.pyo$)" | xargs rm -rf'

USER pili

CMD ["python", "manage.py", "runserver", "--host=0.0.0.0"]
