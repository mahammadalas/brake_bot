import asyncio
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ====================
# ⚙️ KONFİQURASİYA
# ====================

TOKEN = "8283943387:AAHfl3iyDx0UEz4yM8x0hScugEG3MBwyw8Q"  # BOT TOKEN
CHANNEL_ID = -1003287048408  # Brake Logs kanal ID-si 
BRAKE_DURATION = 10 * 60       # 10 dəqiqəlik brake
MIN_WAIT_TIME = 2 * 60 * 60    # 2 saat gözləmə limiti

STATS_FILE = "data.json"
BRAKE_STATE_FILE = "brake_state.json"

queue = []
last_brake_times = {}
brake_lock = asyncio.Lock()


# ====================
# 📁 FAYL FONKSİYALARI
# ====================

def set_current_brake_user(user_id=None):
    """Hazır brake userini faylda saxlayır"""
    state = {"current_brake_user": user_id}
    with open(BRAKE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

def get_current_brake_user():
    """Hazır brake userini fayldan oxuyur"""
    if not os.path.exists(BRAKE_STATE_FILE):
        return None
    with open(BRAKE_STATE_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data.get("current_brake_user")
        except:
            return None

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

def save_brake_stat(user_id, username):
    stats = load_stats()
    if str(user_id) not in stats:
        stats[str(user_id)] = {"username": username, "times": []}
    stats[str(user_id)]["times"].append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    save_stats(stats)


# ====================
# 🔘 ƏMRLƏR
# ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🧘 Brake çıx", callback_data="brake")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Salam!\nBrake götürmək üçün aşağıdakı düyməyə bas 👇",
        reply_markup=reply_markup
    )


async def handle_brake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name

    async with brake_lock:
        current_user = get_current_brake_user()

        # 🔒 2 saat limiti yoxla (aktiv və ya sıradakı userlər üçün)
        last_time = last_brake_times.get(user_id)
        if last_time and (datetime.now() - last_time).total_seconds() < MIN_WAIT_TIME:
            diff = MIN_WAIT_TIME - (datetime.now() - last_time).total_seconds()
            mins = int(diff // 60)
            await query.message.reply_text(
                f"⏳ Son brake vaxtından {mins} dəqiqə keçməyib. Gözləməli olacaqsan."
            )
            return

        # 🟢 Brake boşdursa, useri işə sal
        if not current_user:
            set_current_brake_user(user_id)
            last_brake_times[user_id] = datetime.now()
            save_brake_stat(user_id, username)

            await query.message.reply_text("🔔 Brake çıxmağa hazırlaş, offline ol.")
            await asyncio.sleep(60)
            await query.message.reply_text("😌 Brake başladı, xoş istirahətlər!")

            # 🔔 Kanal logu
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=(
                    f"📢 <b>Yeni Brake Götürüldü</b>\n\n"
                    f"👤 <b>User:</b> @{username}\n"
                    f"🕐 <b>Başlama:</b> {datetime.now().strftime('%H:%M:%S')}\n"
                    f"🕒 <b>Bitmə:</b> {(datetime.now() + timedelta(seconds=BRAKE_DURATION)).strftime('%H:%M:%S')}\n"
                    f"📅 <b>Tarix:</b> {datetime.now().strftime('%d.%m.%Y')}"
                ),
                parse_mode="HTML"
            )

            await asyncio.sleep(BRAKE_DURATION - 60)
            await query.message.reply_text("⚠️ Brake bitməsinə 1 dəqiqə qaldı, hazırlaş!")
            await asyncio.sleep(60)
            await query.message.reply_text("✅ Brake-dən qayıt və online ol!")

            # ✅ Brake bitdi, növbətini yoxla
            set_current_brake_user(None)

            if queue:
                next_user = queue.pop(0)
                await context.bot.send_message(
                    next_user,
                    "🚀 Sənin vaxtın çatdı! 1 dəqiqə sonra brake başlayacaq."
                )

        # 🚫 Əgər başqa user brake-dədirsə
        else:
            if user_id == current_user:
                await query.message.reply_text("ℹ️ Sən artıq brake-dəsən.")
            else:
                # 🔁 Təkrar brake əmri verdikdə sıraya düşməsin, 2 saat xəbərdarlığı getsin
                if last_time and (datetime.now() - last_time).total_seconds() < MIN_WAIT_TIME:
                    diff = MIN_WAIT_TIME - (datetime.now() - last_time).total_seconds()
                    mins = int(diff // 60)
                    await query.message.reply_text(
                        f"⏳ Son brake vaxtından {mins} dəqiqə keçməyib. Gözləməli olacaqsan."
                    )
                else:
                    await query.message.reply_text(
                        "🧘 Hazırda brake doludur, gözləməli olacaqsan."
                    )


# ====================
# 🚀 BOTU BAŞLAT
# ====================

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_brake, pattern="brake"))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())