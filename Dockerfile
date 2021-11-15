FROM python:3.9

RUN mkdir -p /opt/http_server /opt/data

COPY simple_http_server.py /opt/http_server/

WORKDIR /opt/data

ENV PORT=8000
EXPOSE $PORT


CMD python /opt/http_server/simple_http_server.py ${PORT}