import requests
from bs4 import BeautifulSoup

url = "https://otakudesu.cloud/episode/llp-sptr-s3-episode-10-sub-indo/"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Cari div dengan class "download"
download_div = soup.find('div', class_='download')

if download_div:
    # Cari semua elemen li yang berisi link download
    download_items = download_div.find_all('li')
    
    for item in download_items:
        # Cari strong tag untuk mendapatkan kualitas video
        quality = item.find('strong')
        if quality and 'Mp4' in quality.text:
            print(f"\n{quality.text}:")
            
            # Cari semua link download
            links = item.find_all('a')
            for link in links:
                server_name = link.text.strip()
                # Hanya proses jika server adalah Mega atau Kfiles
                if server_name in ['Mega', 'KFiles']:
                    download_url = link.get('href')
                    r = requests.get(download_url)
                    final_url = r.url
                    print(f"Server: {server_name} - URL: {final_url}")
            
            # Ambil ukuran file
            size = item.find('i')
            if size:
                print(f"Ukuran: {size.text}")
else:
    print("Tidak dapat menemukan bagian download di halaman ini")