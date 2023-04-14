FROM python:3.10-bullseye
RUN apt-get update & apt-get install -y opus-tools
RUN mkdir /models
WORKDIR /app
COPY app/ .
RUN pip3 install -U -r requirements.txt
CMD ["python3", "-u", "smrt.py"]

ENV SERVER_PORT 9000
EXPOSE 9000/tcp
