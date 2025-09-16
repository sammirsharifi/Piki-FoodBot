# admin_bot.py
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import db
from config import ADMIN_BOT_TOKEN, USER_BOT_USERNAME, ADMIN_IDS
from utils import export_report_to_excel
import os

import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher()

# ------------------------------
# FSM states for creating order and menu
# ------------------------------
class OrderStates(StatesGroup):
    waiting_for_title = State()

class MenuStates(StatesGroup):
    waiting_for_item_name = State()
    waiting_for_item_price = State()

# ------------------------------
# Start command
# ------------------------------
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("👋 Welcome Admin! Use /neworder to create a new order.")
    else:
        await message.answer("⛔ You are not authorized to use this bot.")

# ------------------------------
# Create new order
# ------------------------------
@dp.message(F.text == "/neworder")
async def start_new_order(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Not authorized.")
    await message.answer("📌 Please send the title for the new order:")
    await state.set_state(OrderStates.waiting_for_title)

@dp.message(OrderStates.waiting_for_title)
async def process_order_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        return await message.answer("❌ Title cannot be empty.")
    order_id = db.create_order(title, message.from_user.id)

    # لینک دعوت به UserBot
    link = f"https://t.me/{USER_BOT_USERNAME}?start={order_id}"

    await message.answer(
        f"✅ Order created: {title}\n"
        f"🔗 Invite link for users: {link}\n\n"
        f"Use /addmenu_{order_id} to add menu items."
    )
    await state.clear()

# ------------------------------
# Add menu items with FSM
# ------------------------------
@dp.message(F.text.startswith("/addmenu_"))
async def start_add_menu(message: Message, state: FSMContext):
    if message.from_user.id not in  ADMIN_IDS:
        return await message.answer("⛔ Not authorized.")
    order_id = int(message.text.split("_")[1])
    await state.update_data(order_id=order_id)
    await message.answer("📌 Please send the name of the menu item:")
    await state.set_state(MenuStates.waiting_for_item_name)

@dp.message(MenuStates.waiting_for_item_name)
async def process_item_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if name.lower() == "/done":
        await message.answer("✅ Finished adding menu items.")
        return await state.clear()
    if not name:
        return await message.answer("❌ Name cannot be empty.")
    await state.update_data(item_name=name)
    await message.answer("💰 Now send the price of this item:")
    await state.set_state(MenuStates.waiting_for_item_price)

@dp.message(MenuStates.waiting_for_item_price)
async def process_item_price(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data['order_id']
    name = data['item_name']
    try:
        price = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Price must be a number.")
    db.add_menu(order_id, name, price)
    await message.answer(f"✅ Added {name} ({price} تومان). Send another item name or type /done to finish.")
    await state.set_state(MenuStates.waiting_for_item_name)

# ------------------------------
# Report
# ------------------------------
# ------------------------------
# Report - show buttons for orders
# ------------------------------
@dp.message(F.text.startswith("/report"))
async def report_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Not authorized.")
    
    conn = sqlite3.connect("foodbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM orders_table")
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        return await message.answer("📭 No orders yet.")
    
    builder = InlineKeyboardBuilder()
    for order_id, title in orders:
        builder.button(text=f"{title}", callback_data=f"order_{order_id}")
    builder.adjust(1)
    
    await message.answer("📋 Select an order to view:", reply_markup=builder.as_markup())

# ------------------------------
# Callback: show order menu
# ------------------------------
@dp.callback_query(F.data.startswith("order_"))
async def order_menu_callback(callback: CallbackQuery):
    _, order_id = callback.data.split("_")
    order_id = int(order_id)
    
    conn = sqlite3.connect("foodbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM orders_table WHERE id = ?", (order_id,))
    title_row = cursor.fetchone()
    order_title = title_row[0] if title_row else "Menu"
    conn.close()
    
    text = f"📋 *{order_title}*"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Order Overview", callback_data=f"overview_{order_id}")
    builder.button(text="💰 Invoice / Bill", callback_data=f"bill_{order_id}")
    builder.button(text="🔙 Back to Main", callback_data="back_main")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ------------------------------
# Callback: Order Overview
# ------------------------------
@dp.callback_query(F.data.startswith("overview_"))
async def overview_callback(callback: CallbackQuery):
    _, order_id = callback.data.split("_")
    order_id = int(order_id)

    # گرفتن گزارش کامل با جزئیات هر کاربر و مجموع کل
    report = db.get_cart_report_summary(order_id)
    if not report["users"]:
        return await callback.answer("📭 No orders yet.")

    text = f"📝 *Order Overview*\n\n"

    # جزئیات هر کاربر
    for user, items in report["users"].items():
        text += f"👤 {user}:\n"
        for item_name, qty in items.items():
            text += f"   - {item_name}: {qty} \n"
        text += "\n"

    # مجموع کل آیتم‌ها
    text += "📊 *Total per item:*\n"
    for item_name, total_qty in report["totals"].items():
        text += f"   - {item_name}: {total_qty} \n"

    # دکمه‌ها
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Back to Order Menu", callback_data=f"order_{order_id}")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# ------------------------------
# Callback: Invoice / Bill
# ------------------------------
@dp.callback_query(F.data.startswith("bill_"))
async def bill_callback(callback: CallbackQuery):
    _, order_id = callback.data.split("_")
    order_id = int(order_id)

    # گرفتن گزارش با قیمت‌ها از تابع جدید
    report = db.get_cart_report_with_prices(order_id)
    if not report or not report["users"]:
        return await callback.answer("📭 No orders yet.")

    text = f"💰 *Invoice / Bill*\n\n"

    # نمایش جزئیات هر کاربر
    for user, items in report["users"].items():
        text += f"👤 *{user}*\n"
        user_total = 0  # مجموع قیمت سفارش‌های هر کاربر
        for item_name, data in items.items():
            qty = data["quantity"]
            price = data["total_price"]
            text += f"  - {item_name}: {qty}  --> {price} Toman\n"
            user_total += price
        text += f" \n ➤ Total for {user}: {user_total} Toman\n\n"



    # جمع کل نهایی
    text += f"\n💵 *Grand Total: {report['grand_total']} Toman*"

    # دکمه بازگشت
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Back to Order Menu", callback_data=f"order_{order_id}")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()



# ------------------------------
# Callback: Back to Main Menu
# ------------------------------
@dp.callback_query(F.data == "back_main")
async def back_main_callback(callback: CallbackQuery):
    conn = sqlite3.connect("foodbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM orders_table")
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        return await callback.message.edit_text("📭 No orders yet.")
    
    builder = InlineKeyboardBuilder()
    for order_id, title in orders:
        builder.button(text=f"{title}", callback_data=f"order_{order_id}")
    builder.adjust(1)
    
    await callback.message.edit_text("📋 Select an order to view:", reply_markup=builder.as_markup())
    await callback.answer()

# ------------------------------
# Export report to Excel
# ------------------------------
@dp.message(F.text.startswith("/export"))
async def export_handler(message: Message):
    if message.from_user.id not in  ADMIN_IDS:
        return await message.answer("⛔ Not authorized.")
    try:
        _, order_id = message.text.split(" ", 1)
        order_id = int(order_id)
        report = db.get_report(order_id)
        if not report:
            return await message.answer("📭 No orders yet.")
        filename = f"report_{order_id}.xlsx"
        export_report_to_excel(report, filename)
        await message.answer_document(open(filename, "rb"))
        os.remove(filename)
    except:
        await message.answer("❌ Format: /export order_id")

# ------------------------------
# Main
# ------------------------------
async def main():
    db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Started AdminBot")
    asyncio.run(main())
