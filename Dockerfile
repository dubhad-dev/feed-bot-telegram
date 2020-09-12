FROM python:3.8.5
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . ./

ENV API_ID=
ENV API_HASH=
ENV BOT_TOKEN=
ENV USER_ID=
ENV MARK_UNREAD=false

CMD python bot.py