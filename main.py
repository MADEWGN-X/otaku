import requests
from bs4 import BeautifulSoup
import direct
import aiohttp
import asyncio
import os
from tqdm import tqdm

async def download_file(session, url, filename, total_size=None):
    """Download file dengan progress bar menggunakan aiohttp"""
    try:
        async with session.get(url) as response:
            # Dapatkan total ukuran file jika belum diketahui
            if not total_size:
                total_size = int(response.headers.get('content-length', 0))
            
            # Buat progress bar
            progress = tqdm(
                total=total_size,
                unit='iB',
                unit_scale=True,
                desc=filename
            )
            
            # Buat file dan tulis chunk by chunk
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    with open(filename, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024):
                            size = f.write(chunk)
                            progress.update(size)
            
            progress.close()
            return True
            
    except Exception as e:
        print(f"Error downloading {filename}: {str(e)}")
        # Hapus file yang tidak selesai didownload
        if os.path.exists(filename):
            os.remove(filename)
        return False

async def download_all_files(links):
    """Download semua file dari list links"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for link in links:
            # Dapatkan direct link
            direct_url = direct.krakenfiles(link['url'])
            if direct_url.startswith('ERROR'):
                print(f"Error getting direct link for {link['quality']}: {direct_url}")
                continue
                
            # Buat nama file dari kualitas
            filename = f"video_{link['quality'].replace(' ', '_')}.mp4"
            
            # Convert size string ke bytes jika tersedia
            size = None
            if link['size'] != 'Unknown':
                try:
                    size_num = float(link['size'].split()[0])
                    size_unit = link['size'].split()[1].lower()
                    
                    # Konversi ke bytes
                    multiplier = {
                        'kb': 1024,
                        'mb': 1024**2,
                        'gb': 1024**3
                    }.get(size_unit, 1)
                    
                    size = int(size_num * multiplier)
                except:
                    pass
            
            # Tambahkan task download        
            task = asyncio.create_task(
                download_file(session, direct_url, filename, size)
            )
            tasks.append(task)
            
        # Jalankan semua download secara concurrent
        results = await asyncio.gather(*tasks)
        return results

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

async def main():
    # Dapatkan links
    url = "https://otakudesu.cloud/episode/llp-sptr-s3-episode-10-sub-indo/"
    kfiles_links = get_kfiles_links(url)
    
    # Print info links
    for link in kfiles_links:
        print(f"\nKualitas: {link['quality']}")
        print(f"URL: {link['url']}")
        print(f"Ukuran: {link['size']}")
    
    # Download semua file
    print("\nMemulai download...")
    results = await download_all_files(kfiles_links)
    
    # Print hasil download
    success = results.count(True)
    print(f"\nDownload selesai: {success}/{len(results)} file berhasil didownload")

if __name__ == "__main__":
    asyncio.run(main())