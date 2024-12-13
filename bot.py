import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import asyncio
from main import get_kfiles_links, download_all_files
import aiohttp

# Ganti dengan token bot Telegram Anda
TOKEN = "7255389524:AAHzkOawoc5TPd9t_zEpIwS5Z_M7whhZfJo"

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
            for i, link in enumerate(links):
                # Update status untuk setiap file
                await status_msg.edit_text(
                    f"⏳ Mendownload {link['quality']} ({i+1}/{len(links)})..."
                )
                
                # Download file
                filename = os.path.join('dls', f"video_{link['quality'].replace(' ', '_')}.mp4")
                await download_all_files([link], download_path='dls')
                
                # Upload ke Telegram
                await status_msg.edit_text(
                    f"⏳ Mengupload {link['quality']} ({i+1}/{len(links)})..."
                )
                
                with open(filename, 'rb') as video:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=video,
                        caption=f"**{link['title']}**\n\n"
                                f"Resolusi: {link['quality']}\n"
                                f"Channel: @otakudesu_id",
                        supports_streaming=True,
                        read_timeout=120,
                        write_timeout=120,
                        connect_timeout=120
                    )
                
                # Hapus file setelah upload
                if os.path.exists(filename):
                    os.remove(filename)
            
            await status_msg.edit_text("✅ Semua video berhasil didownload dan diupload!")
            await asyncio.sleep(5)  # Tunggu 5 detik
            await status_msg.delete()
            
        except Exception as e:
            await status_msg.edit_text(f'❌ Terjadi kesalahan: {str(e)}')
            # Bersihkan semua file di folder dls
            cleanup_dls()
        return
    
    # Proses download single file seperti sebelumnya
    selected_index = int(query.data.split('_')[1])
    if selected_index >= len(links):
        await query.edit_message_text('❌ Data tidak valid!')
        return
    
    selected_link = links[selected_index]
    status_msg = await query.edit_message_text(
        f"⏳ Mendownload {selected_link['quality']}..."
    )
    
    try:
        # Download file ke folder dls
        filename = os.path.join('dls', f"video_{selected_link['quality'].replace(' ', '_')}.mp4")
        await download_all_files([selected_link], download_path='dls')
        
        # Cek dan print ukuran file
        file_size = os.path.getsize(filename)
        file_size_mb = file_size / (1024 * 1024)  # Konversi ke MB
        await status_msg.edit_text(f"📊 Ukuran file: {file_size_mb:.2f} MB\n⏳ Mengupload {selected_link['quality']}...")
        
        # Jika file lebih besar dari 50MB, tampilkan peringatan
        if file_size_mb > 50:
            await status_msg.edit_text(f"❌ File terlalu besar ({file_size_mb:.2f} MB). Telegram membatasi upload maksimal 50MB untuk bot.")
            if os.path.exists(filename):
                os.remove(filename)
            return
            
        # Lanjutkan dengan upload jika ukuran sesuai
        with open(filename, 'rb') as video:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video,
                caption=f"{selected_link['title']}\n\n"
                        f"Resolusi: {selected_link['quality']}\n"
                        f"Channel: @otakudesu_id",
                supports_streaming=True,
                read_timeout=120,
                write_timeout=120,
                connect_timeout=120
            )
        
        # Hapus file setelah upload
        if os.path.exists(filename):
            os.remove(filename)
            
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f'❌ Terjadi kesalahan: {str(e)}')
        # Hapus file jika ada error
        if os.path.exists(filename):
            os.remove(filename)

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
    application = Application.builder().token(TOKEN).build()

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