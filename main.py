import requests
from bs4 import BeautifulSoup


import direct

def get_kfiles_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    kfiles_links = []
    
    download_div = soup.find('div', class_='download')
    
    if download_div:
        download_items = download_div.find_all('li')
        
        for item in download_items:
            quality = item.find('strong')
            if quality and 'Mp4' in quality.text:
                links = item.find_all('a')
                for link in links:
                    server_name = link.text.strip()
                    if server_name == 'KFiles':
                        download_url = link.get('href')
                        r = requests.get(download_url)
                        final_url = r.url
                        kfiles_links.append({
                            'quality': quality.text,
                            'url': final_url,
                            'size': item.find('i').text if item.find('i') else 'Unknown'
                        })
    
    return kfiles_links

# Contoh penggunaan:
url = "https://otakudesu.cloud/episode/llp-sptr-s3-episode-10-sub-indo/"
kfiles_links = get_kfiles_links(url)




for link in kfiles_links:
    print(f"\nKualitas: {link['quality']}")
    print(f"URL: {link['url']}")
    print(direct.krakenfiles(link['url']))
    
    print(f"Ukuran: {link['size']}")