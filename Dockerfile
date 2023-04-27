FROM python:3.10-bullseye
VOLUME /storage
RUN mkdir -p /root/.cache && ln -s /storage /root/.cache/huggingface && /root/.local && ln -s /storage /root/.local/share
RUN apt-get update && apt-get install -y opus-tools espeak
WORKDIR /app
COPY app/ .
RUN pip3 install -U -r requirements.txt
CMD ["python3", "-u", "smrt.py"]

ENV SERVER_PORT 9000
EXPOSE 9000/tcp
