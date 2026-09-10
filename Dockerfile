
FROM python:3.10-slim

#konteyner icinde /app adinda bir klasor ac ve bundan sonraki her seyi orda yap
WORKDIR /app

# kutuphane listesini konteyner atiyoruz
COPY requirements.txt .

# konteynera bu kutuphaneleri yukluyoruz
RUN pip install --no-cache-dir -r requirements.txt

#projeninin tum kodlarini konteynera   kopyaliyoruz
COPY . .

#django 8000 portundan calisacak dis dunyadan erisime izin ver
EXPOSE 8000

# konteyner calistiginda djanangoyu baslatacak komut
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]