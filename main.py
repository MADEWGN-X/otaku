import requests
from bs4 import BeautifulSoup
import direct
import aiohttp
import asyncio
import os
from tqdm import tqdm
from pyrogram import Client
from pyrogram.types import Message
import math
from hashlib import sha256
from requests import Session
from os import path as ospath

# Tambahkan konfigurasi Pyrogram client
api_id = "2345226"  
api_hash = "6cc6449dcef22f608af2cf7efb76c99d"
bot_token = "7255389524:AAHzkOawoc5TPd9t_zEpIwS5Z_M7whhZfJo"

# Inisialisasi client
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

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

async def download_all_files(links, download_path='dls'):
    """Download semua file dari list links"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for link in links:
            # Dapatkan direct link berdasarkan server
            if link['server'] == 'KFiles':
                direct_url = direct.krakenfiles(link['url'])
            elif link['server'] == 'GoFile':
                direct_url, header = direct.gofile(link['url'])
            else:
                print(f"Server tidak didukung: {link['server']}")
                continue
                
            if isinstance(direct_url, str) and direct_url.startswith('ERROR'):
                print(f"Error getting direct link for {link['quality']}: {direct_url}")
                continue
            
            # Buat nama file dari kualitas
            filename = os.path.join(download_path, f"video_{link['quality'].replace(' ', '_')}.mp4")
            
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
    download_links = []
    
    # Ambil judul dari tag title
    title = soup.find('title')
    anime_title = title.text.split('|')[0].strip() if title else 'Unknown Title'
    
    download_div = soup.find('div', class_='download')
    
    if download_div:
        download_items = download_div.find_all('li')
        
        for item in download_items:
            quality = item.find('strong')
            if quality and 'Mp4' in quality.text:
                links = item.find_all('a')
                for link in links:
                    server_name = link.text.strip()
                    if server_name in ['KFiles', 'GoFile']:  # Tambahkan Gofile
                        download_url = link.get('href')
                        r = requests.get(download_url)
                        final_url = r.url
                        download_links.append({
                            'quality': quality.text,
                            'url': final_url,
                            'size': item.find('i').text if item.find('i') else 'Unknown',
                            'title': anime_title,
                            'server': server_name  # Tambahkan info server
                        })
    
    return download_links

async def progress(current, total, message):
    """Fungsi helper untuk menampilkan progress upload"""
    percent = current * 100 / total
    size = current / 1024 / 1024
    total_size = total / 1024 / 1024
    progress_str = f"{size:.2f}MB / {total_size:.2f}MB ({percent:.1f}%)"
    try:
        await message.edit_text(f"Mengupload file...\n{progress_str}")
    except:
        pass

async def upload_file(file_path, chat_id, message):
    """Upload file ke Telegram menggunakan Pyrogram"""
    try:
        await app.send_video(
            chat_id=chat_id,
            video=file_path,
            caption=f"Channel: @otakudesu_id",
            progress=progress,
            progress_args=(message,),
            supports_streaming=True  # Penting untuk file video besar
        )
        return True
    except Exception as e:
        print(f"Error uploading {file_path}: {str(e)}")
        return False

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
    
    # Setelah download selesai, upload ke Telegram
    async with app:
        chat_id = "TARGET_CHAT_ID"  # Ganti dengan chat ID tujuan
        status_msg = await app.send_message(chat_id, "Memulai upload...")
        
        for link in kfiles_links:
            filename = f"video_{link['quality'].replace(' ', '_')}.mp4"
            file_path = os.path.join('dls', filename)
            if os.path.exists(file_path):
                print(f"\nMengupload {filename}...")
                success = await upload_file(file_path, chat_id, status_msg)
                if success:
                    print(f"Berhasil mengupload {filename}")
                else:
                    print(f"Gagal mengupload {filename}")

if __name__ == "__main__":
    asyncio.run(main())