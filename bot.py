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
    
    # Validasi URL
    if not url.startswith('https://otakudesu.cloud/episode/'):
        await update.message.reply_text('Link tidak valid! Gunakan link dari otakudesu.cloud')
        return
    
    # Kirim pesan sedang memproses
    processing_msg = await update.message.reply_text('⏳ Sedang mengambil informasi video...')
    
    try:
        # Dapatkan link download
        kfiles_links = get_kfiles_links(url)
        
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
                                f"Channel: @otakudesu_id",
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
                        f"Channel: @otakudesu_id",
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
        if os.path.exists(filename):
            os.remove(filename)
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

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
    
    # Error handler
    application.add_error_handler(error_handler)

    # Jalankan bot
    print('Bot started...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 