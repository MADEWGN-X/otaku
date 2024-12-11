import requests
from bs4 import BeautifulSoup

url = "https://otakudesu.cloud/anime/love-superstar-s3-sub-indo/"

response = requests.get(url)
# Buat objek BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')

# Cari semua elemen yang mengandung teks "Love Live"
love_live_elements = soup.find_all(string=lambda text: "Love Live" in text if text else False)

# Tampilkan hasil
if love_live_elements:
    print("Teks 'Love Live' ditemukan dalam elemen berikut:")
    for element in love_live_elements:
        print(f"- {element.strip()}")
else:
    print("Teks 'Love Live' tidak ditemukan di halaman ini")
