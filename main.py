import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage
import uvicorn
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from database import init_db, get_setting, set_setting, validate_promo, add_promocode, add_order, update_order_status, get_stats

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    web_app_url = f"{BASE_URL}/static/index.html"
    
    welcome_text = (
        "✨ **Abe Vayn rasmiy botiga xush kelibsiz!** ✨\n\n"
        "Siz bu yerda eksklyuziv **Labubu** o'yinchoqlarini "
        "to'g'ridan-to'g'ri **abe.vayn** nomidan xarid qilishingiz mumkin!\n\n"
        "👇 Pastdagi **Mini App** tugmasini bosing va buyurtma bering:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧸 Labubu Mini App-ni ochish", web_app=WebAppInfo(url=web_app_url))],
            [InlineKeyboardButton(text="📸 Instagram (abe.vayn)", url="https://instagram.com/abe.vayn")]
        ]
    )
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔️ Siz admin emassiz!")
        
    count, total_sum = get_stats()
    card = get_setting("card_number")
    
    admin_text = (
        "⚙️ **Admin Panel - Abe Vayn Shop**\n\n"
        f"📊 **Jami buyurtmalar:** {count} ta\n"
        f"💰 **Jami tushum:** {total_sum:,.0f} so'm\n"
        f"💳 **Hozirgi Karta:** `{card}`\n\n"
        "Buyruqlar:\n"
        "• `/setcard 8600...` - Karta raqamini o'zgartirish\n"
        "• `/addpromo ABE10 10` - Yangi promo-kod qo'shish"
    )
    await message.answer(admin_text, parse_mode="Markdown")

@dp.message(Command("setcard"))
async def cmd_setcard(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        set_setting("card_number", args[1])
        await message.answer(f"✅ Karta raqami o'zgartirildi: {args[1]}")
    else:
        await message.answer("Format: `/setcard 8600123456789012`", parse_mode="Markdown")

@dp.message(Command("addpromo"))
async def cmd_addpromo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) >= 2:
        code = args[1]
        percent = float(args[2]) if len(args) > 2 else 10.0
        if add_promocode(code, percent):
            await message.answer(f"✅ Promo-kod yaratildi: **{code}** ({percent}% skidka)", parse_mode="Markdown")
        else:
            await message.answer("❌ Bu promo-kod allaqachon mavjud!")
    else:
        await message.answer("Format: `/addpromo PROMO10 10`", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("status_"))
async def handle_status_change(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    _, order_id, status_code = callback.data.split("_")
    
    statuses = {
        "sent": "📦 BTS orqali yuborildi",
        "delivered": "✅ Etib bordi",
        "cancel": "❌ Bekor qilindi"
    }
    
    new_status = statuses.get(status_code, "Jarayonda")
    update_order_status(order_id, new_status)
    
    await callback.message.edit_text(callback.message.text + f"\n\nSTATUS: **{new_status}**", parse_mode="Markdown")
    await callback.answer("Status o'zgartirildi!")

@app.get("/api/info")
async def get_info():
    return {
        "card_number": get_setting("card_number"),
        "card_holder": get_setting("card_holder"),
        "product_name": "Labubu Collection Toy",
        "price": 20000
    }

@app.get("/api/check-promo")
async def check_promo(code: str):
    disc = validate_promo(code)
    if disc is not None:
        return {"valid": True, "discount_percent": disc}
    return {"valid": False, "discount_percent": 0}

@app.post("/api/order")
async def create_order(
    user_id: int = Form(...),
    user_name: str = Form(...),
    phone: str = Form(...),
    region: str = Form(...),
    promo: str = Form(""),
    check_photo: UploadFile = File(...)
):
    orig_price = 20000.0
    disc = validate_promo(promo) if promo else None
    final_price = orig_price * (1 - (disc / 100.0)) if disc else orig_price
    
    check_bytes = await check_photo.read()
    
    admin_msg = (
        "🆕 **YANGI BUYURTMA (Abe Vayn Shop)!**\n\n"
        f"👤 **Mijoz:** {user_name} (ID: {user_id})\n"
        f"📞 **Tel:** {phone}\n"
        f"📍 **Manzil (BTS):** {region}\n"
        f"🧸 **Mahsulot:** Labubu Toy[span_0](start_span)[span_0](end_span)\n"
        f"💵 **Asl narxi:** {orig_price:,.0f} so'm\n"
        f"🎟 **Promo-kod:** {promo if promo else 'Yo\\'q'}\n"
        f"💰 **To'langan narx:** {final_price:,.0f} so'm\n"
    )
    
    photo_file = types.BufferedInputFile(check_bytes, filename="check.jpg")
    order_id = add_order(user_id, user_name, phone, region, "Labubu Toy", orig_price, final_price, promo, "file")
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 Yuborildi (BTS)", callback_data=f"status_{order_id}_sent"),
                InlineKeyboardButton(text="✅ Etib bordi", callback_data=f"status_{order_id}_delivered")
            ]
        ]
    )
    
    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_file, caption=admin_msg, reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error sending order to admin: {e}")

    return {"status": "ok", "order_id": order_id}

@app.on_event("startup")
async def on_startup():
    init_db()
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
