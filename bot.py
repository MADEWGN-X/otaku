import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import asyncio
from main import get_kfiles_links, download_all_files
from pyrogram import Client
import aiohttp
from moviepy.editor import VideoFileClip
from PIL import Image
import numpy as np
from list import get_episode_list

# Konfigurasi API
api_id = "2345226"
api_hash = "6cc6449dcef22f608af2cf7efb76c99d" 
bot_token = "7255389524:AAHzkOawoc5TPd9t_zEpIwS5Z_M7whhZfJo"

# Inisialisasi client Pyrogram
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Buat folder dls jika belum ada
if not os.path.exists('dls'):
    os.makedirs('dls')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengirim pesan saat command /start dijalankan."""
    await update.message.reply_text(
        'Selamat datang! Kirimkan link otakudesu untuk mendownload video.\n'
        'Format: https://otakudesu.cloud/episode/xxx'
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani URL yang dikirim user"""
    url = update.message.text
    
    # Check if URL is an anime list page
    if 'otakudesu.cloud/anime/' in url:
        await process_list(update, context)
        return
        
    # Check if URL is an episode page
    if not 'otakudesu.cloud/episode' in url:
        await update.message.reply_text('Link tidak valid! Gunakan link dari otakudesu.cloud')
        return
    
    # Handle episode download logic
    processing_msg = await update.message.reply_text('⏳ Sedang mengambil informasi video...')
    
    try:
        # Dapatkan link download
        kfiles_links = get_kfiles_links(url)
        print(kfiles_links)
        
        if not kfiles_links:
            await processing_msg.edit_text('❌ Tidak ditemukan link download yang valid!')
            return
        
        # Buat keyboard inline dengan pilihan kualitas
        keyboard = []
        # Tambahkan opsi download semua
        keyboard.append([
            InlineKeyboardButton(
                "Download Semua Kualitas", 
                callback_data="dl_all"
            )
        ])
        # Tambahkan pilihan kualitas individual
        for i, link in enumerate(kfiles_links):
            keyboard.append([
                InlineKeyboardButton(
                    f"{link['quality']} ({link['size']})", 
                    callback_data=f"dl_{i}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Simpan links di context untuk digunakan nanti
        context.user_data['kfiles_links'] = kfiles_links
        
        await processing_msg.edit_text(
            'Pilih kualitas video yang ingin didownload:',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await processing_msg.edit_text(f'❌ Terjadi kesalahan: {str(e)}')

async def generate_thumbnail(video_path):
    """Membuat thumbnail dari video menggunakan moviepy"""
    try:
        thumbnail_path = video_path.rsplit('.', 1)[0] + '_thumb.jpg'
        
        # Memuat video
        clip = VideoFileClip(video_path)
        
        # Coba ambil frame di menit ke-3 (180 detik)
        time = 180 if clip.duration > 180 else 30
        
        # Mendapatkan frame
        frame = clip.get_frame(time)
        
        # Konversi ke PIL Image dan resize
        image = Image.fromarray(frame)
        image = image.resize((1280, 725), Image.Resampling.LANCZOS)
        
        # Simpan thumbnail
        image.save(thumbnail_path, "JPEG", quality=90)
        
        # Tutup video
        clip.close()
        
        return thumbnail_path
            
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        if 'clip' in locals():
            clip.close()
        return None

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani callback saat user memilih kualitas video"""
    query = update.callback_query
    await query.answer()
    
    links = context.user_data.get('kfiles_links', [])
    if not links:
        await query.edit_message_text('❌ Data tidak valid!')
        return

    # Cek apakah user memilih download semua
    if query.data == "dl_all":
        status_msg = await query.edit_message_text("⏳ Mendownload semua kualitas...")
        try:
            async with app:  # Mulai sesi Pyrogram
                for i, link in enumerate(links):
                    await status_msg.edit_text(
                        f"⏳ Mendownload {link['quality']} ({i+1}/{len(links)})..."
                    )
                    
                    filename = os.path.join('dls', f"video_{link['quality'].replace(' ', '_')}.mp4")
                    await download_all_files([link], download_path='dls')
                    
                    # Generate thumbnail
                    thumbnail_path = await generate_thumbnail(filename)
                    
                    await status_msg.edit_text(
                        f"⏳ Mengupload {link['quality']} ({i+1}/{len(links)})..."
                    )
                    
                    # Upload menggunakan Pyrogram dengan thumbnail dan ukuran spesifik
                    await app.send_video(
                        chat_id=update.effective_chat.id,
                        video=filename,
                        caption=f"**{link['title']}**\n\n"
                                f"Resolusi: {link['quality']}\n"
                                f"Channel: @Anime_sub_indo_AR",
                        thumb=thumbnail_path if thumbnail_path else None,
                        width=1280,
                        height=725,
                        supports_streaming=True
                    )
                    
                    # Hapus file video dan thumbnail
                    if os.path.exists(filename):
                        os.remove(filename)
                    if thumbnail_path and os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
            
            await status_msg.edit_text("✅ Semua video berhasil didownload dan diupload!")
            await asyncio.sleep(5)
            await status_msg.delete()
            
        except Exception as e:
            await status_msg.edit_text(f'❌ Terjadi kesalahan: {str(e)}')
            cleanup_dls()
        return
    
    # Proses download single file
    selected_index = int(query.data.split('_')[1])
    if selected_index >= len(links):
        await query.edit_message_text('❌ Data tidak valid!')
        return
    
    selected_link = links[selected_index]
    status_msg = await query.edit_message_text(
        f"⏳ Mendownload {selected_link['quality']}..."
    )
    
    try:
        filename = os.path.join('dls', f"video_{selected_link['quality'].replace(' ', '_')}.mp4")
        await download_all_files([selected_link], download_path='dls')
        
        # Generate thumbnail
        thumbnail_path = await generate_thumbnail(filename)
        
        await status_msg.edit_text(f"⏳ Mengupload {selected_link['quality']}...")
        
        # Upload menggunakan Pyrogram dengan thumbnail dan ukuran spesifik
        async with app:
            await app.send_video(
                chat_id=update.effective_chat.id,
                video=filename,
                caption=f"**{selected_link['title']}**\n\n"
                        f"Resolusi: {selected_link['quality']}\n"
                        f"Channel: @Anime_sub_indo_AR",
                thumb=thumbnail_path if thumbnail_path else None,
                width=1280,
                height=725,
                supports_streaming=True
            )
        
        # Hapus file video dan thumbnail
        if os.path.exists(filename):
            os.remove(filename)
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f'❌ Terjadi kesalahan: {str(e)}')
        if os.exists(filename):
            os.remove(filename)
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

async def process_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle anime list URL"""
    url = update.message.text
    
    if not 'otakudesu.cloud/anime/' in url:
        await update.message.reply_text('Link tidak valid! Gunakan link daftar anime dari otakudesu.cloud')
        return
    
    status_msg = await update.message.reply_text('⏳ Mengambil daftar episode...')
    try:
        episodes = get_episode_list(url)
        print(episodes)
        if not episodes:
            await status_msg.edit_text('❌ Tidak ada episode yang ditemukan!')
            return
            
        await status_msg.edit_text(f'📑 Ditemukan {len(episodes)} episode\n⏳ Mulai memproses...')
        
        for i, episode in enumerate(episodes, 1):
            try:
                await status_msg.edit_text(f'⏳ Memproses episode {i}/{len(episodes)}\n{episode["title"]}')
                
                # Get download links for episode
                kfiles_links = get_kfiles_links(episode['url'])
                if not kfiles_links:
                    continue
                    
                # Filter for 720p quality
                selected_link = None
                for link in kfiles_links:
                    if '720p' in link['quality'].lower():
                        selected_link = link
                        break
                        
                if not selected_link:
                    await status_msg.edit_text(f'⚠️ Kualitas 720p tidak ditemukan untuk episode {i}')
                    continue
                
                # Download 720p version
                filename = os.path.join('dls', f"video_Mp4_720p.mp4")
                await download_all_files([selected_link], download_path='dls')
                thumbnail_path = await generate_thumbnail(filename)
                
                # Upload to Telegram
                async with app:
                    await app.send_video(
                        chat_id=update.effective_chat.id,
                        video=filename,
                        caption=f"**{selected_link['title']}**\n\n"
                                f"Resolusi: 720p\n"
                                f"Channel: @Anime_sub_indo_AR",
                        thumb=thumbnail_path if thumbnail_path else None,
                        width=1280,
                        height=725,
                        supports_streaming=True
                    )
# ...existing code...
                # Cleanup
                if os.path.exists(filename):
                    os.remove(filename)
                if thumbnail_path and os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
                    
            except Exception as e:
                print(f"Error processing episode {i}: {e}")
                continue
        
        await status_msg.edit_text("✅ Semua episode selesai diproses!")
        
    except Exception as e:
        await status_msg.edit_text(f'❌ Terjadi kesalahan: {str(e)}')
        cleanup_dls()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log Errors caused by Updates."""
    print(f'Update {update} caused error {context.error}')

def cleanup_dls():
    """Membersihkan folder dls dari file yang tersisa"""
    if os.path.exists('dls'):
        for file in os.listdir('dls'):
            file_path = os.path.join('dls', file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f'Error menghapus file {file_path}: {str(e)}')

def main():
    """Start the bot."""
    # Bersihkan folder dls saat startup
    cleanup_dls()
    
    # Buat aplikasi
    application = Application.builder().token(bot_token).build()

    # Tambahkan handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(download_callback, pattern='^dl_'))
    application.add_handler(MessageHandler(
        filters.Regex(r'https://otakudesu\.cloud/anime/.*') & ~filters.COMMAND, 
        process_list
    ))
    
    # Error handler
    application.add_error_handler(error_handler)

    # Jalankan bot
    print('Bot started...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()