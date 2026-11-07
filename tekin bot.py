import asyncio
import logging
import uuid
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove
from supabase import create_client, Client

# --- SOZLAMALAR ---
BOT_TOKEN = "9173847420:AAFqibB74gbbOtbauRs3HKV89xNw_46KENg"
SUPABASE_URL = "https://xddtaatcwgphtwxvfcce.supabase.co"
SUPABASE_KEY = "sb_publishable_SgS2z53-9bjFh56EBKCIIg_G2Uqx4Ih"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)


class BookingState(StatesGroup):
    client_name = State()
    car_number = State()
    car_photo = State()
    booking_time = State()


@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"Assalomu alaykum, {user_name}!\n\n"
        "AvtoServis & Ehtiyot qismlar botiga xush kelibsiz.\n\n"
        "Buyruqlar:\n"
        "/navbatlar - Faol navbatlarni ko'rish\n"
        "/yozilish - Yangi navbatga yozilish\n"
        "/ustalar - Ustalar ro'yxati\n"
        "/zapchast - Ehtiyot qismlar",
        parse_mode="Markdown"
    )


# --- NAVBATGA YOZILISH ---
@dp.message(Command("yozilish"))
async def start_booking(message: types.Message, state: FSMContext):
    await message.answer("Iltimos, ism va familiyangizni kiriting:")
    await state.set_state(BookingState.client_name)


@dp.message(BookingState.client_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    await message.answer("Endi mashinangiz raqamini kiriting (masalan: 01A777AA):")
    await state.set_state(BookingState.car_number)


@dp.message(BookingState.car_number)
async def process_car(message: types.Message, state: FSMContext):
    await state.update_data(car_number=message.text)
    await message.answer(
        "Iltimos, mashinangiz rasmini yuboring (agar rasm yubormasangiz, istalgan matn yoki 'yo'q' deb yozib yuboring):")
    await state.set_state(BookingState.car_photo)


@dp.message(BookingState.car_photo)
async def process_photo(message: types.Message, state: FSMContext):
    car_image_url = None

    if message.photo:
        try:
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)

            # To'g'rilangan yuklab olish usuli
            file_bytes_io = await bot.download_file(file_info.file_path)
            file_bytes = file_bytes_io.read()

            file_name = f"car_{uuid.uuid4().hex}.jpg"

            # Supabase storagega yuklash
            supabase.storage.from_("images").upload(
                path=file_name,
                file=file_bytes,
                file_options={"content-type": "image/jpeg"}
            )

            # Ommaviy havolani olish
            car_image_url = supabase.storage.from_("images").get_public_url(file_name)
        except Exception as e:
            logging.error(f"Rasm yuklashda xatolik: {e}")

    await state.update_data(car_image_url=car_image_url)
    await message.answer("Qaysi vaqtga yozilmoqchisiz? (Masalan: Bugun 14:00):")
    await state.set_state(BookingState.booking_time)


@dp.message(BookingState.booking_time)
async def process_time(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_name = data.get("client_name")
    car_number = data.get("car_number")
    car_image_url = data.get("car_image_url")
    booking_time = message.text

    try:
        supabase.table("appointments").insert({
            "client_name": client_name,
            "car_number": car_number,
            "car_image_url": car_image_url,
            "booking_time": booking_time
        }).execute()

        text = (
            "Muvaffaqiyatli navbatga yozildingiz!\n\n"
            f"Ism: {client_name}\n"
            f"Mashina: {car_number}\n"
            f"Vaqt: {booking_time}\n\n"
            "Ma'lumot bazaga va saytga qo'shildi!"
        )

        if car_image_url:
            await message.answer_photo(
                photo=car_image_url,
                caption=text,
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await message.answer(
                text,
                reply_markup=ReplyKeyboardRemove()
            )
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

    await state.clear()


@dp.message(Command("navbatlar"))
async def get_appointments(message: types.Message):
    try:
        response = supabase.table("appointments").select("*").execute()
        data = response.data

        if not data:
            await message.answer("Hozircha faol navbatlar yo'q.")
            return

        for item in data[-5:]:
            client_name = item.get('client_name', 'Noma\'lum')
            car_number = item.get('car_number', '-')
            booking_time = item.get('booking_time', '-')
            car_image_url = item.get('car_image_url')

            text = f"👤 Ism: {client_name}\n🚗 Mashina: {car_number}\n⏰ Vaqt: {booking_time}"

            if car_image_url:
                try:
                    await message.answer_photo(photo=car_image_url, caption=text)
                except Exception:
                    await message.answer(text)
            else:
                await message.answer(text)
    except Exception as e:
        await message.answer(f"Xatolik: {e}")


# --- USTALAR ---
@dp.message(Command("ustalar"))
async def get_masters(message: types.Message):
    try:
        response = supabase.table("masters").select("*").execute()
        data = response.data

        if not data:
            await message.answer("Hozircha ustalar ro'yxati bo'sh.")
            return

        for item in data:
            name = item.get('name', 'Noma\'lum')
            speciality = item.get('speciality', 'Ko\'rsatilmagan')
            is_available = item.get('available')
            status = "🟢 Bo'sh" if is_available else "🔴 Band"
            image_url = item.get('image_url')

            caption = (
                f"👨‍🔧 **Ism:** {name}\n"
                f"🛠 **Mutaxassisligi:** {speciality}\n"
                f"📌 **Holati:** {status}"
            )

            if image_url:
                try:
                    await message.answer_photo(photo=image_url, caption=caption, parse_mode="Markdown")
                except Exception:
                    await message.answer(caption, parse_mode="Markdown")
            else:
                await message.answer(caption, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")


# --- EHTIYOT QISMLAR ---
@dp.message(Command("zapchast"))
async def get_spare_parts(message: types.Message):
    try:
        response = supabase.table("spare_parts").select("*").execute()
        data = response.data

        if not data:
            await message.answer("Hozircha ehtiyot qismlar yo'q.")
            return

        for item in data:
            name = item.get('name', 'Noma\'lum')
            price = item.get('price', 'Ko\'rsatilmagan')
            image_url = item.get('image_url')

            caption = (
                f"⚙️ **Nomi:** {name}\n"
                f"💰 **Narxi:** {price}"
            )

            if image_url:
                try:
                    await message.answer_photo(photo=image_url, caption=caption, parse_mode="Markdown")
                except Exception:
                    await message.answer(caption, parse_mode="Markdown")
            else:
                await message.answer(caption, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Xatolik: {e}")


async def main():
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
