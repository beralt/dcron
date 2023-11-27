FROM python:3.12.0-alpine3.18

WORKDIR /usr/src/app

COPY . .

RUN pip install .

CMD [ "dcrond" ]