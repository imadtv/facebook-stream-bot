import os
import subprocess
import asyncio
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8327108993:AAE_hCDGuubnkURHMj3fj838YZhekyteoXw"

# ---------------- بيانات المستخدمين والبثوص ----------------
user_streams = {}  # chat_id: {stream_id: {"stream_key":..., "m3u8":..., "proc":...}}
RESTART_DELAY = 10  # ثواني لإعادة تشغيل البث بعد توقفه

# ---------------- وظائف البث ----------------
async def start_stream(chat_id: int, stream_id: str, stream_key: str, m3u8_url: str, context: ContextTypes.DEFAULT_TYPE):
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
        proc = subprocess.Popen(ffmpeg_cmd)
        user_streams[chat_id][stream_id]["proc"] = proc
        await context.bot.send_message(chat_id, f"✅ تم بدء البث [{stream_id}] بنجاح!")
        # مراقبة البث لإعادة التشغيل
        asyncio.create_task(monitor_stream(chat_id, stream_id, stream_key, m3u8_url, context))
    except Exception as e:
        await context.bot.send_message(chat_id, f"❌ خطأ أثناء تشغيل البث [{stream_id}]:\n{e}")

async def monitor_stream(chat_id: int, stream_id: str, stream_key: str, m3u8_url: str, context: ContextTypes.DEFAULT_TYPE):
    proc = user_streams[chat_id][stream_id].get("proc")
    if not proc:
        return
    proc.wait()
    await context.bot.send_message(chat_id, f"⚠️ البث [{stream_id}] توقف! جاري إعادة التشغيل...")
    await asyncio.sleep(RESTART_DELAY)
    await start_stream(chat_id, stream_id, stream_key, m3u8_url, context)

async def stop_stream(chat_id: int, stream_id: str, context: ContextTypes.DEFAULT_TYPE):
    proc = user_streams[chat_id][stream_id].get("proc")
    if proc:
        proc.terminate()
        await context.bot.send_message(chat_id, f"🛑 تم إيقاف البث [{stream_id}] بنجاح!")
    user_streams[chat_id].pop(stream_id, None)

async def stop_all_streams(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    if chat_id in user_streams:
        for stream_id in list(user_streams[chat_id].keys()):
            await stop_stream(chat_id, stream_id, context)
        await context.bot.send_message(chat_id, "🛑 تم إيقاف جميع البثوص الخاصة بك.")
    else:
        await context.bot.send_message(chat_id, "⚠️ لا يوجد بثوص جاريه.")

# ---------------- أوامر Telegram ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton("➕ بدء بث جديد", callback_data="new_stream")],
        [InlineKeyboardButton("⏹ إيقاف بث فردي", callback_data="stop_stream")],
        [InlineKeyboardButton("⛔ إيقاف كل البثوص", callback_data="stop_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 مرحباً! استخدم الأزرار لإدارة البثوص:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    if query.data == "new_stream":
        await query.message.reply_text("📥 أرسل Stream Key ثم رابط m3u8 مفصول بمسافة:")
        context.user_data["awaiting_new"] = True
    elif query.data == "stop_stream":
        if chat_id in user_streams and user_streams[chat_id]:
            keys = list(user_streams[chat_id].keys())
            keyboard = [[InlineKeyboardButton(sid, callback_data=f"stop_{sid}")] for sid in keys]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("اختر البث لإيقافه:", reply_markup=reply_markup)
        else:
            await query.message.reply_text("⚠️ لا يوجد بثوص جاريه.")
    elif query.data == "stop_all":
        await stop_all_streams(chat_id, context)
    elif query.data.startswith("stop_"):
        stream_id = query.data.replace("stop_", "")
        await stop_stream(chat_id, stream_id, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if context.user_data.get("awaiting_new"):
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ يجب إرسال Stream Key ثم رابط m3u8 مفصول بمسافة.")
            return
        stream_key, m3u8_url = parts
        stream_id = str(uuid.uuid4())[:8]  # معرف فريد قصير للبث
        if chat_id not in user_streams:
            user_streams[chat_id] = {}
        user_streams[chat_id][stream_id] = {"stream_key": stream_key, "m3u8": m3u8_url}
        context.user_data["awaiting_new"] = False
        await update.message.reply_text(f"🚀 جاري بدء البث [{stream_id}]...")
        await start_stream(chat_id, stream_id, stream_key, m3u8_url, context)

async def send_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ استخدم: /text <stream_id> <النص>")
        return
    stream_id = args[0]
    text_msg = " ".join(args[1:])
    if chat_id in user_streams and stream_id in user_streams[chat_id]:
        await update.message.reply_text(f"📝 أرسل النص للبث [{stream_id}]: {text_msg}")
    else:
        await update.message.reply_text(f"⚠️ البث [{stream_id}] غير موجود.")

async def send_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ استخدم: /image <stream_id> <رابط الصورة>")
        return
    stream_id = args[0]
    image_url = args[1]
    if chat_id in user_streams and stream_id in user_streams[chat_id]:
        await update.message.reply_text(f"🖼️ أرسل الصورة للبث [{stream_id}]: {image_url}")
    else:
        await update.message.reply_text(f"⚠️ البث [{stream_id}] غير موجود.")

# ---------------- تشغيل البوت ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("text", send_text))
    app.add_handler(CommandHandler("image", send_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button))
    print("✅ Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
