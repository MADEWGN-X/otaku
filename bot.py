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
        download_links = get_kfiles_links(url)
        
        if not download_links:
            await processing_msg.edit_text('❌ Tidak ditemukan link download yang valid!')
            return
        
        # Pisahkan link berdasarkan server
        kfiles_links = [link for link in download_links if link['server'] == 'KFiles']
        gofile_links = [link for link in download_links if link['server'] == 'GoFile']
        
        # Buat keyboard inline untuk pilihan server
        server_keyboard = [
            [InlineKeyboardButton("KFiles", callback_data="server_kfiles")],
            [InlineKeyboardButton("GoFile", callback_data="server_gofile")]
        ]
        
        server_markup = InlineKeyboardMarkup(server_keyboard)
        
        # Simpan links di context untuk digunakan nanti
        context.user_data['kfiles_links'] = kfiles_links
        context.user_data['gofile_links'] = gofile_links
        
        await processing_msg.edit_text(
            'Pilih server download:',
            reply_markup=server_markup
        )
        
    except Exception as e:
        await processing_msg.edit_text(f'❌ Terjadi kesalahan: {str(e)}')

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani callback saat user memilih kualitas video"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data
    data_parts = query.data.split('_')
    
    # Cek format callback data yang lama
    if len(data_parts) == 2:  # Format lama: 'dl_0' atau 'dl_all'
        # Gunakan KFiles sebagai default untuk kompatibilitas
        data_parts.append('kfiles')
    
    action = data_parts[1]
    server = data_parts[2]
    
    # Pilih links berdasarkan server
    links = []
    if server == 'kfiles':
        links = context.user_data.get('kfiles_links', [])
    else:
        links = context.user_data.get('gofile_links', [])
    
    if not links:
        await query.edit_message_text('❌ Data tidak valid!')
        return

    # Cek apakah user memilih download semua
    if action == "all":
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
                                f"Server: {link['server']}\n"
                                f"Channel: @otakudesu_id",
                        parse_mode='Markdown',
                        supports_streaming=True
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
    
    # Proses download single file
    try:
        selected_index = int(action)  # Menggunakan action sebagai index
        if selected_index >= len(links):
            await query.edit_message_text('❌ Data tidak valid!')
            return
        
        selected_link = links[selected_index]
        status_msg = await query.edit_message_text(
            f"⏳ Mendownload {selected_link['quality']}..."
        )
        
        # Download file ke folder dls
        filename = os.path.join('dls', f"video_{selected_link['quality'].replace(' ', '_')}.mp4")
        await download_all_files([selected_link], download_path='dls')
        
        # Upload ke Telegram
        await status_msg.edit_text(f"⏳ Mengupload {selected_link['quality']}...")
        
        # Kirim video
        with open(filename, 'rb') as video:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video,
                caption=f"**{selected_link['title']}**\n\n"
                        f"Resolusi: {selected_link['quality']}\n"
                        f"Server: {selected_link['server']}\n"
                        f"Channel: @otakudesu_id",
                parse_mode='Markdown',
                supports_streaming=True
            )
        
        # Hapus file setelah upload
        if os.path.exists(filename):
            os.remove(filename)
            
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f'❌ Terjadi kesalahan: {str(e)}')
        if 'filename' in locals() and os.path.exists(filename):
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