# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /scraper

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 6969

CMD [ "python3", "-m" , "flask", "--app", "main.py", "run", "--host=0.0.0.0", "--port", "6969"]
