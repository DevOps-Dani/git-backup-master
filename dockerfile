FROM eu.gcr.io/px-utilities-20190329/python:3.10.4-slim
LABEL maintainer="dani.westlake@brainlabsdigital.com"

RUN apt-get update

WORKDIR /git_backup
ADD requirements.txt ./
ADD git_backup.py ./
ADD client_secret.json ./
ADD config.ini ./
ADD --chown=root:root entrypoint.sh ./

RUN pip install -r requirements.txt

CMD [ "python", "/git_backup/git_backup.py" ]