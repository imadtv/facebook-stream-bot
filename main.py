import os
import subprocess
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# 🔹 توكن البوت
BOT_TOKEN = "8327108993:AAE_hCDGuubnkURHMj3fj838YZhekyteoXw"

# 🔹 قاعدة بيانات بسيطة في الذاكرة لكل مستخدم
user_data = {}

# 🟢 أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أرسل لي Stream Key الخاص ببث فيسبوك:")

# 🟣 استقبال الرسائل (Stream Key ثم رابط M3U8)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # الخطوة الأولى: حفظ Stream Key
    if chat_id not in user_data:
        user_data[chat_id] = {"stream_key": text}
        await update.message.reply_text("✅ تم حفظ Stream Key.\nالآن أرسل لي رابط m3u8:")
        return

    # الخطوة الثانية: استقبال رابط M3U8 وبدء البث
    stream_key = user_data[chat_id]["stream_key"]
    m3u8_url = text
    await update.message.reply_text("🚀 جاري بدء البث على فيسبوك...")

    facebook_rtmp = f"rtmps://live-api-s.facebook.com:443/rtmp/{stream_key}"

    ffmpeg_cmd = [
        "ffmpeg",
        "-re",
        "-i", m3u8_url,
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        facebook_rtmp
    ]

    try:
        subprocess.Popen(ffmpeg_cmd)
        await update.message.reply_text("✅ تم بدء البث بنجاح!\nاستخدم /stop لإيقاف البث.")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء تشغيل البث:\n{e}")

# 🔴 أمر /stop لإيقاف كل عمليات ffmpeg
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subprocess.call(["pkill", "-f", "ffmpeg"])
        await update.message.reply_text("🛑 تم إيقاف جميع عمليات البث.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ لم أستطع إيقاف ffmpeg:\n{e}")

# 🚀 التشغيل الرئيسي
def main():
    # التحقق من وجود التوكن
    if not BOT_TOKEN:
        print("❌ لم يتم العثور على التوكن! تأكد من إضافته.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
