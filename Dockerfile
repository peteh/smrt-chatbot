FROM python:3.13-bookworm
VOLUME /storage
RUN mkdir -p /root/.cache && ln -s /storage /root/.cache/huggingface && mkdir -p /root/.local && ln -s /storage /root/.local/share
RUN apt-get update && apt-get install -y opus-tools vorbis-tools ffmpeg espeak
WORKDIR /app
COPY scripts/ ./scripts/
COPY smrt/ ./smrt/
COPY requirements.txt .
ENV STORAGE_PATH=/storage

RUN pip3 install -U -r requirements.txt
ENV PYTHONPATH=/app
CMD ["python3", "-u", "scripts/main.py"]
# use SERVER_PORT as the port for the message server
ENV SERVER_PORT=5000

EXPOSE ${SERVER_PORT}/tcp
