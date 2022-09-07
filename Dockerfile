FROM python:3.9


COPY ./requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r /src/requirements.txt

COPY . ./src

WORKDIR /src
