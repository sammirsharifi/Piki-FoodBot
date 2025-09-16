import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import db
from config import USER_BOT_TOKEN

bot = Bot(token=USER_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ------------------------------ #
# FSM for registering/changing name
# ------------------------------ #
class NameForm(StatesGroup):
    waiting_for_name = State()

# ------------------------------ #
# Show main menu
# ------------------------------ #
async def show_main_menu(message_or_cb, order_id, edit=False):
    conn = sqlite3.connect("foodbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price FROM menus WHERE order_id = ?", (order_id,))
    menus = cursor.fetchall()

    cursor.execute("SELECT menu_id, quantity FROM cart WHERE user_id = ? AND order_id = ?",
                   (getattr(message_or_cb.from_user, 'id', message_or_cb.from_user.id), order_id))
    cart_items = dict(cursor.fetchall())
    conn.close()

    if not menus:
        text = "🍽 No menu yet."
        if isinstance(message_or_cb, CallbackQuery):
            await message_or_cb.message.edit_text(text)
        else:
            await message_or_cb.answer(text)
        return

    # عنوان منو
    cursor = sqlite3.connect("foodbot.db").cursor()
    cursor.execute("SELECT title FROM orders_table WHERE id = ?", (order_id,))
    title_row = cursor.fetchone()
    menu_title = title_row[0] if title_row else "Menu"
    text = f"📋 *{menu_title}*\n\n"

    builder = InlineKeyboardBuilder()
    for mid, name, price in menus:
        qty = cart_items.get(mid, 0)
        text += f'"{name}" - {price}\n'
        builder.button(text=f"{name}({qty})", callback_data=f"item_{order_id}_{mid}")
    builder.adjust(1)

    builder.button(text="🛒 View Cart", callback_data=f"viewcart_{order_id}")
    builder.button(text="📤 Send Order to Admin", callback_data=f"send_{order_id}")
    builder.adjust(2)

    kb = builder.as_markup()
    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.message.edit_text(text, reply_markup=kb)
    else:
        await message_or_cb.answer(text, reply_markup=kb)

# ------------------------------ #
# Show item menu
# ------------------------------ #
async def show_item_menu(callback: CallbackQuery, order_id, menu_id):
    conn = sqlite3.connect("foodbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM menus WHERE id = ?", (menu_id,))
    item = cursor.fetchone()
    cursor.execute("SELECT quantity FROM cart WHERE user_id = ? AND order_id = ? AND menu_id = ?",
                   (callback.from_user.id, order_id, menu_id))
    qty_row = cursor.fetchone()
    qty = qty_row[0] if qty_row else 0
    conn.close()



    text = f'"{item[0]}" - {item[1]} Toman\n\nQuantity Ordered: {qty}\n'

    builder = InlineKeyboardBuilder()
    builder.button(text="➖", callback_data=f"dec_{order_id}_{menu_id}")
    builder.button(text=str(qty), callback_data="noop")
    builder.button(text="➕", callback_data=f"inc_{order_id}_{menu_id}")
    builder.adjust(3)

    builder.button(text="🔙 Back to Menu", callback_data=f"back_{order_id}")
    builder.adjust(1)

    kb = builder.as_markup()
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

# ------------------------------ #
# Show cart
# ------------------------------ #
async def show_cart(callback: CallbackQuery, order_id):
    conn = sqlite3.connect("foodbot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.name, m.price, c.quantity
        FROM cart c
        JOIN menus m ON c.menu_id = m.id
        WHERE c.user_id = ? AND c.order_id = ?
    """, (callback.from_user.id, order_id))
    items = cursor.fetchall()
    conn.close()

    if not items:
        await callback.answer("❌ Cart is empty.", show_alert=True)
        return

    text = "🛒 *Your Cart:*\n\n"
    total = 0
    for name, price, qty in items:
        subtotal = price * qty
        text += f'"{name}({qty})" --> "{subtotal} Toman"\n'
        total += subtotal
    text += f"\n💰 Total: {total} Toman"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Back to Menu", callback_data=f"back_{order_id}")
    builder.adjust(1)

    kb = builder.as_markup()
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

# ------------------------------ #
# Start command
# ------------------------------ #
@dp.message(F.text.startswith("/start"))
async def start_handler(message: Message, state: FSMContext):
    conn = sqlite3.connect("foodbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT fullname FROM users WHERE id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()

    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        order_id = int(args[1])
    else:
        await message.answer("👋 Welcome! Click a link from admin to start ordering.")
        return

    if row and row[0]:
        # اسم کاربر موجود است
        user_name = row[0]
        await message.answer(f"{user_name}, welcome back!")
    else:
        # FSM برای گرفتن اسم
        await message.answer("Welcome! Please send your name to register:")
        await state.set_state(NameForm.waiting_for_name)
        await state.update_data(order_id=order_id)
        return

    # بعد خوش آمد و ثبت نام، منو
    await show_main_menu(message, order_id)

# ------------------------------ #
# Handle name input
# ------------------------------ #
@dp.message(NameForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    user_name = message.text.strip()
    data = await state.get_data()
    order_id = data.get("order_id")

    # ذخیره در دیتابیس
    db.add_user(message.from_user.id, user_name, getattr(message.from_user, "username", None))

    await message.answer(f"Thanks {user_name}! You are registered.")
    await state.clear()
    await show_main_menu(message, order_id)

# ------------------------------ #
# Change name command
# ------------------------------ #
@dp.message(F.text.startswith("/change_name"))
async def change_name(message: Message, state: FSMContext):
    await message.answer("Please send your new name:")
    await state.set_state(NameForm.waiting_for_name)

# ------------------------------ #
# Callback handlers
# ------------------------------ #
@dp.callback_query(F.data.startswith("item_"))
async def item_selected(callback: CallbackQuery):
    _, order_id, menu_id = callback.data.split("_")
    await show_item_menu(callback, int(order_id), int(menu_id))

@dp.callback_query(F.data.startswith("inc_"))
async def inc_item(callback: CallbackQuery):
    _, order_id, menu_id = callback.data.split("_")
    db.update_cart(callback.from_user.id, int(order_id), int(menu_id), 1)
    await show_item_menu(callback, int(order_id), int(menu_id))

@dp.callback_query(F.data.startswith("dec_"))
async def dec_item(callback: CallbackQuery):
    _, order_id, menu_id = callback.data.split("_")
    db.update_cart(callback.from_user.id, int(order_id), int(menu_id), -1)
    await show_item_menu(callback, int(order_id), int(menu_id))

@dp.callback_query(F.data.startswith("back_"))
async def back_to_menu(callback: CallbackQuery):
    _, order_id = callback.data.split("_")
    await show_main_menu(callback, int(order_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("viewcart_"))
async def view_cart(callback: CallbackQuery):
    _, order_id = callback.data.split("_")
    await show_cart(callback, int(order_id))

@dp.callback_query(F.data.startswith("send_"))
async def send_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    cart = db.get_cart(callback.from_user.id, order_id)
    if not cart:
        return await callback.answer("❌ Cart is empty.")

    await callback.message.edit_text("Thank you!\nYour Order Sent To Admin\nEnjoy it :)")
    await callback.answer("Order finalized!")

# ------------------------------ #
# Main
# ------------------------------ #
async def main():
    db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Started UserBot")
    asyncio.run(main())
