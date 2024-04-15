FROM python:3.9

ENV TZ=Asia/Tehran

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY . /code/

RUN pip install --upgrade pip && pip install -r requirements.txt

EXPOSE 8001

CMD ["python", "third_party_service.py"]
