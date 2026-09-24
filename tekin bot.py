import os
from threading import Thread
from flask import Flask
import telebot
from telebot import types
from supabase import create_client, Client

# --- 1. RENDER UCHUN BEPUL WEB SERVICE PORT SERVERI ---
app = Flask(__name__)

@app.route('/')
def home():
    return "AutoCare Hub Bot is running 24/7!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# Serverni orqa fonda ishga tushirish (Render port xatoligi bermasligi uchun)
keep_alive()

# --- 2. TELEGRAM BOT VA SUPABASE SOZLAMALARI ---
BOT_TOKEN = "8810746481:AAGzigosaPG6SC7ijhpzGRKesuX8f44dg3E"

SUPABASE_URL = "https://lpxiiyahrttqdnkcfwcj.supabase.co"
SUPABASE_KEY = "sb_publishable_3zbJwx_WnVIXXe0Vo6M1mw_Qe344aj6"

bot = telebot.TeleBot(BOT_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

user_data = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    welcome_text = (
        f"Salom, {message.from_user.first_name}!\n\n"
        "🚗 **AutoCare Hub** — Avtomobilga xizmat ko'rsatish va navbat olish botiga xush kelibsiz!\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:"
    )
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("📅 Navbat olish")
    btn2 = types.KeyboardButton("📩 Adminga ma'lumot yuborish")
    btn3 = types.KeyboardButton("👨‍🔧 Ustalarimiz")
    btn4 = types.KeyboardButton("💰 Narxlar va Xizmatlar")
    markup.add(btn1, btn2, btn3, btn4)

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- 3. NAVBAT OLISH BO'LIMI ---
@bot.message_handler(func=lambda msg: msg.text == "📅 Navbat olish")
def start_booking(message):
    msg = bot.send_message(
        message.chat.id,
        "Navbat olish uchun avtomobil rusumi va raqamini kiriting:\n<i>(Masalan: Gentra 01A777AA)</i>",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_booking_car)

def process_booking_car(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'car': message.text}
    msg = bot.send_message(chat_id, "Qaysi xizmat turi bo'yicha navbatga yozilmoqchisiz?")
    bot.register_next_step_handler(msg, process_booking_finish)

def process_booking_finish(message):
    chat_id = message.chat.id
    service_type = message.text
    car_info = user_data.get(chat_id, {}).get('car', "Noma'lum")
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {chat_id}"

    try:
        data = {
            "telegram_user": username,
            "car_details": car_info,
            "service_type": f"[NAVBAT] {service_type}",
            "status": "pending"
        }
        supabase.table("service_requests").insert(data).execute()
        bot.send_message(chat_id, "✅ **Navbatingiz qabul qilindi!** Saytdagi Admin panelda ko'rinadi.", parse_mode="Markdown")
    except Exception as e:
        print(f"Xato: {e}")
        bot.send_message(chat_id, "⚠️ Bazaga yozishda xatolik bo'ldi. Qaytadan urinib ko'ring.")

# --- 4. NOMLANGAN MA'LUMOT YUBORISH BO'LIMI ---
@bot.message_handler(func=lambda msg: msg.text == "📩 Adminga ma'lumot yuborish")
def start_info_send(message):
    msg = bot.send_message(message.chat.id, "Yuborilayotgan ma'lumot nomini (sarlavhasini) kiriting:")
    bot.register_next_step_handler(msg, process_info_title)

def process_info_title(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'title': message.text}
    msg = bot.send_message(chat_id, "Endi batafsil ma'lumot yoki izohingizni yozib qoldiring:")
    bot.register_next_step_handler(msg, process_info_finish)

def process_info_finish(message):
    chat_id = message.chat.id
    description = message.text
    title = user_data.get(chat_id, {}).get('title', "Sarlavhasiz")
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {chat_id}"

    try:
        data = {
            "telegram_user": username,
            "car_details": f"Sarlavha: {title}",
            "service_type": f"[MA'LUMOT] {description}",
            "status": "pending"
        }
        supabase.table("service_requests").insert(data).execute()
        bot.send_message(chat_id, "✅ **Ma'lumotingiz nomlanib adminga yuborildi!** Saytda ko'rinadi.", parse_mode="Markdown")
    except Exception as e:
        print(f"Xato: {e}")
        bot.send_message(chat_id, "⚠️ Bazaga yozishda xatolik bo'ldi. Qaytadan urinib ko'ring.")

# --- 5. USTALAR VA XIZMATLAR RO'YXATI ---
@bot.message_handler(func=lambda msg: msg.text == "👨‍🔧 Ustalarimiz")
def show_mechanics(message):
    try:
        res = supabase.table("mechanics").select("*").execute()
        if not res.data:
            bot.send_message(message.chat.id, "Hozircha ustalar ro'yxati bo'sh.")
            return

        text = "<b>🛠️ AutoCare Hub Ustalarimiz:</b>\n\n"
        for m in res.data:
            text += f"👤 <b>{m.get('name', 'Usta')}</b> - {m.get('specialty', 'Avto usta')}\n📞 Tel: {m.get('phone', 'Mavjud emas')}\n-------------------------\n"
        bot.send_message(message.chat.id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Xato: {e}")
        bot.reply_to(message, "Ustalar ro'yxatini yuklab bo'lmadi.")

@bot.message_handler(func=lambda msg: msg.text == "💰 Narxlar va Xizmatlar")
def show_services(message):
    try:
        res = supabase.table("services").select("*").execute()
        if not res.data:
            bot.send_message(message.chat.id, "Hozircha xizmatlar ro'yxati bo'sh.")
            return

        text = "<b>💳 Xizmatlar va Narxlar:</b>\n\n"
        for s in res.data:
            text += f"🔧 <b>{s.get('title', 'Xizmat')}</b>\n💵 Narxi: {s.get('price', 'Kelishilgan')} so'm\n-------------------------\n"
        bot.send_message(message.chat.id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Xato: {e}")
        bot.reply_to(message, "Xizmatlarni yuklab bo'lmadi.")

if __name__ == "__main__":
    print("Bot va Flask veb-serveri muvaffaqiyatli ishga tushirildi...")
    bot.polling(none_stop=True, interval=0)
