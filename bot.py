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
    
    # Dapatkan index dari link yang dipilih
    selected_index = int(query.data.split('_')[1])
    links = context.user_data.get('kfiles_links', [])
    
    if not links or selected_index >= len(links):
        await query.edit_message_text('❌ Data tidak valid!')
        return
    
    selected_link = links[selected_index]
    
    # Update pesan
    status_msg = await query.edit_message_text(
        f"⏳ Mendownload {selected_link['quality']}..."
    )
    
    try:
        # Download file ke folder dls
        filename = os.path.join('dls', f"video_{selected_link['quality'].replace(' ', '_')}.mp4")
        links_to_download = [selected_link]
        
        await download_all_files(links_to_download, download_path='dls')
        
        # Upload ke Telegram
        await status_msg.edit_text(f"⏳ Mengupload {selected_link['quality']}...")
        
        # Kirim video
        with open(filename, 'rb') as video:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video,
                caption=f"✅ {selected_link['quality']} - {selected_link['size']}",
                supports_streaming=True
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