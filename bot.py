import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import asyncio
from main import get_kfiles_links, download_all_files
from pyrogram import Client
import aiohttp
import subprocess

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

async def progress(current, total, message, text):
    """Fungsi untuk menampilkan progress upload"""
    try:
        percent = current * 100 / total
        progress_str = f"{text}\n" \
                      f"Progress: {current * 100 / total:.1f}%\n" \
                      f"[{'=' * int(percent/5)}{'.' * (20-int(percent/5))}]"
        await message.edit_text(progress_str)
    except Exception:
        pass

async def extract_thumbnail(video_path):
    """Mengekstrak thumbnail dari video"""
    try:
        thumbnail_path = video_path.rsplit('.', 1)[0] + '_thumb.jpg'
        
        # Menggunakan ffmpeg untuk mengambil frame dari video
        command = [
            'ffmpeg', '-i', video_path,
            '-ss', '00:00:01',  # ambil frame pada detik pertama
            '-vframes', '1',
            '-vf', 'scale=320:-1',  # resize thumbnail
            thumbnail_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if os.path.exists(thumbnail_path):
            return thumbnail_path
        return None
    except Exception as e:
        print(f"Error creating thumbnail: {str(e)}")
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
            async with app:
                for i, link in enumerate(links):
                    await status_msg.edit_text(
                        f"⏳ Mendownload {link['quality']} ({i+1}/{len(links)})..."
                    )
                    
                    filename = os.path.join('dls', f"video_{link['quality'].replace(' ', '_')}.mp4")
                    await download_all_files([link], download_path='dls')
                    
                    # Generate thumbnail
                    thumbnail = await extract_thumbnail(filename)
                    
                    await status_msg.edit_text(
                        f"⏳ Mengupload {link['quality']} ({i+1}/{len(links)})..."
                    )
                    
                    # Upload dengan thumbnail
                    await app.send_video(
                        chat_id=update.effective_chat.id,
                        video=filename,
                        caption=f"**{link['title']}**\n\n"
                                f"Resolusi: {link['quality']}\n"
                                f"Channel: @otakudesu_id",
                        thumb=thumbnail if thumbnail else None,
                        supports_streaming=True,
                        progress=progress,
                        progress_args=(status_msg, f"⏳ Mengupload {link['quality']} ({i+1}/{len(links)})")
                    )
                    await asyncio.sleep(2)
                    
                    # Hapus file video dan thumbnail
                    if os.path.exists(filename):
                        os.remove(filename)
                    if thumbnail and os.path.exists(thumbnail):
                        os.remove(thumbnail)
            
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
        thumbnail = await extract_thumbnail(filename)
        
        file_size = os.path.getsize(filename)
        file_size_mb = file_size / (1024 * 1024)
        
        await status_msg.edit_text(f"📊 Ukuran file: {file_size_mb:.2f} MB\n⏳ Mengupload {selected_link['quality']}...")
        
        if file_size_mb > 50:
            await status_msg.edit_text(f"❌ File terlalu besar ({file_size_mb:.2f} MB). Telegram membatasi upload maksimal 50MB untuk bot.")
            if os.path.exists(filename):
                os.remove(filename)
            if thumbnail and os.path.exists(thumbnail):
                os.remove(thumbnail)
            return
            
        # Upload dengan thumbnail
        async with app:
            await app.send_video(
                chat_id=update.effective_chat.id,
                video=filename,
                caption=f"{selected_link['title']}\n\n"
                        f"Resolusi: {selected_link['quality']}\n"
                        f"Channel: @otakudesu_id",
                thumb=thumbnail if thumbnail else None,
                supports_streaming=True,
                progress=progress,
                progress_args=(status_msg, f"⏳ Mengupload {selected_link['quality']}")
            )
        
        # Hapus file video dan thumbnail
        if os.path.exists(filename):
            os.remove(filename)
        if thumbnail and os.path.exists(thumbnail):
            os.remove(thumbnail)
            
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f'❌ Terjadi kesalahan: {str(e)}')
        if os.path.exists(filename):
            os.remove(filename)
        if thumbnail and os.path.exists(thumbnail):
            os.remove(thumbnail)

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