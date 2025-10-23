import os
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8327108993:AAE_hCDGuubnkURHMj3fj838YZhekyteoXw"

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أرسل لي Stream Key الخاص ببث فيسبوك:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if chat_id not in user_data:
        user_data[chat_id] = {"stream_key": text}
        await update.message.reply_text("✅ تم حفظ Stream Key.\nالآن أرسل لي رابط m3u8:")
        return

    stream_key = user_data[chat_id]["stream_key"]
    m3u8_url = text
    await update.message.reply_text("🚀 جاري بدء البث على فيسبوك...")

    facebook_rtmp = f"rtmps://live-api-s.facebook.com:443/rtmp/{stream_key}"

    ffmpeg_cmd = [
        "ffmpeg",
        "-re", "-i", m3u8_url,
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        facebook_rtmp
    ]

    try:
        subprocess.Popen(ffmpeg_cmd)
        await update.message.reply_text("✅ تم بدء البث بنجاح!\nاستخدم /stop لإيقاف البث.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ أثناء تشغيل ffmpeg:\n{e}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subprocess.call(["pkill", "-f", "ffmpeg"])
    await update.message.reply_text("🛑 تم إيقاف جميع عمليات البث.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
