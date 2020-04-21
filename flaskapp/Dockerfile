FROM python:3.6

WORKDIR /flaskapp

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python3.6", "app.py" ]