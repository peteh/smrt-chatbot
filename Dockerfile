FROM python:3.12-bookworm
VOLUME /storage
RUN mkdir -p /root/.cache && ln -s /storage /root/.cache/huggingface && mkdir -p /root/.local && ln -s /storage /root/.local/share
RUN apt-get update && apt-get install -y opus-tools vorbis-tools ffmpeg espeak
WORKDIR /app
COPY app/ .
ENV STORAGE_PATH=/storage
ENV SERVER_PORT 9000

RUN pip3 install -U -r requirements.txt
CMD ["python3", "-u", "smrt.py"]
EXPOSE 9000/tcp
