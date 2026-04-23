import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import json
import os

BOT_TOKEN = '8757128298:AAHYxj8CC81aiX8UTX_U3YZCQoBtQsqdiYc'
ADMIN_ID = 8591124711
HELP_CONTACT = '@poderkaverif'
DATA_FILE = 'bot_data.json'

CRYPTOBOT_TOKEN = '565357:AAJPkqSRrhNbBGbhx33ivrm7AgnNmnM0SFg'

try:
    from cryptobot import CryptoBotClient
    from cryptobot.models import Asset
    crypto_client = CryptoBotClient(api_token=CRYPTOBOT_TOKEN, is_mainnet=True)
    crypto_available = True
    print("✅ CryptoBot подключён")
except:
    print("❌ CryptoBot не подключён")
    crypto_available = False

bot = telebot.TeleBot(BOT_TOKEN)

total_revenue_usdt = 0
total_orders = 0
BANNED_USERS = set()
user_carts = {}
pending_orders = {}

def load_data():
    global total_revenue_usdt, total_orders, BANNED_USERS, user_carts
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                total_revenue_usdt = data.get('total_revenue_usdt', 0)
                total_orders = data.get('total_orders', 0)
                BANNED_USERS = set(data.get('banned_users', []))
                user_carts = data.get('user_carts', {})
        except:
            pass
    else:
        user_carts = {}

def save_data():
    data = {
        'total_revenue_usdt': total_revenue_usdt,
        'total_orders': total_orders,
        'banned_users': list(BANNED_USERS),
        'user_carts': user_carts
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

load_data()

def is_banned(user_id):
    return user_id in BANNED_USERS

def ban_user(user_id):
    BANNED_USERS.add(user_id)
    save_data()

def add_revenue(usdt):
    global total_revenue_usdt, total_orders
    total_revenue_usdt += usdt
    total_orders += 1
    save_data()

def get_cart_text(user_id):
    cart = user_carts.get(str(user_id), [])
    if not cart:
        return "📭 Корзина пуста", 0
    items = ""
    total = 0
    for i, item in enumerate(cart):
        items += f"• {item['name']} - {item['price']} USDT\n   👉 /del_{i}\n\n"
        total += item["price"]
    return items, total

def is_item_in_cart(user_id, item_name):
    cart = user_carts.get(str(user_id), [])
    for item in cart:
        if item['name'] == item_name:
            return True
    return False

def get_banned_list_text():
    if not BANNED_USERS:
        return "📭 Список забаненных пуст"
    text = "🚫 ЗАБАНЕННЫЕ ПОЛЬЗОВАТЕЛИ:\n\n"
    for i, user_id in enumerate(BANNED_USERS, 1):
        text += f"{i}. ID: {user_id}\n"
    return text

BYBIT_COUNTRIES = {
    "id": {"name": "🇮🇩 Индонезия (Bybit)", "price": 6},
    "ng": {"name": "🇳🇬 Нигерия (Bybit)", "price": 6},
    "pk": {"name": "🇵🇰 Пакистан (Bybit)", "price": 9},
    "eg": {"name": "🇪🇬 Египет (Bybit)", "price": 11},
    "ph": {"name": "🇵🇭 Филиппины (Bybit)", "price": 14},
    "bd": {"name": "🇧🇩 Бангладеш (Bybit)", "price": 19}
}

POCKET_COUNTRIES = {
    "id": {"name": "🇮🇩 Индонезия (Pocket)", "price": 6},
    "ng": {"name": "🇳🇬 Нигерия (Pocket)", "price": 6},
    "pk": {"name": "🇵🇰 Пакистан (Pocket)", "price": 9},
    "eg": {"name": "🇪🇬 Египет (Pocket)", "price": 11},
    "ph": {"name": "🇵🇭 Филиппины (Pocket)", "price": 14},
    "bd": {"name": "🇧🇩 Бангладеш (Pocket)", "price": 19}
}

CARDS = {
    "alfa": {"name": "🏦 Альфа-Банк", "price": 188},
    "tbank": {"name": "🏦 Т-Банк", "price": 225},
    "sber": {"name": "🏦 Сбер", "price": 263}
}

COMBOS = {
    "combo1": {"name": "🔥 ПОЛНЫЙ ФАРШ", "price": 250},
    "combo2": {"name": "🚀 КРИПТО-СТАРТ", "price": 213},
    "combo3": {"name": "🎯 ОПЦИОНЩИК", "price": 200}
}

def start_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Верификация", callback_data="verification"),
        InlineKeyboardButton("💳 Купить карту", callback_data="buy_card"),
        InlineKeyboardButton("🎁 Комбо", callback_data="combos"),
        InlineKeyboardButton("🛒 Корзина", callback_data="cart"),
        InlineKeyboardButton("⭐ Отзывы", callback_data="reviews"),
        InlineKeyboardButton("🆘 Помощь", callback_data="help")
    )
    if user_id == ADMIN_ID:
        kb.add(
            InlineKeyboardButton("💰 Статистика", callback_data="stats"),
            InlineKeyboardButton("🚫 Забаненные", callback_data="banned_list")
        )
    return kb

def cart_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Оформить", callback_data="checkout"),
        InlineKeyboardButton("🗑 Очистить", callback_data="clear_cart"),
        InlineKeyboardButton("◀ Назад", callback_data="back_to_start")
    )
    return kb

def payment_keyboard(pay_url):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💳 ОПЛАТИТЬ", url=pay_url))
    kb.add(InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data="paid"))
    kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_to_start"))
    return kb

def admin_accept_keyboard(user_id, amount):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"💰 Принять {amount} USDT и Забанить", callback_data=f"accept_ban_{user_id}_{amount}"))
    return kb

def verification_platform_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🏦 BYBIT", callback_data="platform_bybit"),
        InlineKeyboardButton("🎯 Pocket Option", callback_data="platform_pocket"),
        InlineKeyboardButton("◀ Назад", callback_data="back_to_start")
    )
    return kb

def bybit_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for code, c in BYBIT_COUNTRIES.items():
        kb.add(InlineKeyboardButton(f"➕ {c['name']} - {c['price']} USDT", callback_data=f"add_bybit_{code}"))
    kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_to_verification"))
    return kb

def pocket_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for code, c in POCKET_COUNTRIES.items():
        kb.add(InlineKeyboardButton(f"➕ {c['name']} - {c['price']} USDT", callback_data=f"add_pocket_{code}"))
    kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_to_verification"))
    return kb

def cards_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for code, c in CARDS.items():
        kb.add(InlineKeyboardButton(f"➕ {c['name']} - {c['price']} USDT", callback_data=f"add_card_{code}"))
    kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_to_start"))
    return kb

def combos_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for code, c in COMBOS.items():
        kb.add(InlineKeyboardButton(f"➕ {c['name']} - {c['price']} USDT", callback_data=f"add_combo_{code}"))
    kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_to_start"))
    return kb

def back_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_to_start"))
    return kb

admin_name = ""
admin_bank = ""
admin_ready = False

@bot.message_handler(commands=['start'])
def start(m):
    global admin_name, admin_bank, admin_ready
    uid = m.chat.id
    if uid == ADMIN_ID and not admin_ready:
        bot.send_message(uid, "🔧 ПРИВЕТ, АДМИНИСТРАТОР!\n\n📝 Введите ваше имя:")
        bot.register_next_step_handler(m, get_admin_name)
        return
    if is_banned(uid):
        bot.send_message(uid, "🚫 ДОСТУП ЗАБЛОКИРОВАН\n\n🆘 Поддержка: " + HELP_CONTACT)
        return
    bot.send_message(uid, "🌟 ДОБРО ПОЖАЛОВАТЬ!\n\n👇 Выбери действие:\n\n━━━━━━━━━━━━━━━━━━━━\n🆘 Поддержка: " + HELP_CONTACT, reply_markup=start_keyboard(uid))

def get_admin_name(m):
    global admin_name, admin_bank, admin_ready
    admin_name = m.text
    bot.send_message(ADMIN_ID, f"✅ Имя сохранено: {admin_name}\n\n🏦 Теперь введите ваш банк:")
    bot.register_next_step_handler(m, get_admin_bank)

def get_admin_bank(m):
    global admin_bank, admin_ready
    admin_bank = m.text
    admin_ready = True
    bot.send_message(ADMIN_ID, f"✅ ДАННЫЕ СОХРАНЕНЫ!\n\n📝 Имя: {admin_name}\n🏦 Банк: {admin_bank}\n\n🌟 Добро пожаловать!", reply_markup=start_keyboard(ADMIN_ID))

@bot.callback_query_handler(func=lambda call: True)
def handle(call):
    uid = call.from_user.id
    if is_banned(uid) and uid != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Доступ заблокирован")
        return
    if call.data == "back_to_start":
        bot.edit_message_text("🌟 ГЛАВНОЕ МЕНЮ\n\n👇 Выбери действие:", call.message.chat.id, call.message.message_id, reply_markup=start_keyboard(uid))
        return
    if call.data == "stats" and uid == ADMIN_ID:
        bot.send_message(ADMIN_ID, f"💰 СТАТИСТИКА\n\n💵 Выручка: {total_revenue_usdt} USDT\n📦 Заказов: {total_orders}\n👥 Забанено: {len(BANNED_USERS)}\n\n🆘 Поддержка: {HELP_CONTACT}")
        return
    if call.data == "banned_list" and uid == ADMIN_ID:
        bot.send_message(ADMIN_ID, get_banned_list_text(), reply_markup=back_keyboard())
        return
    if call.data == "verification":
        bot.edit_message_text("✅ ВЕРИФИКАЦИЯ\n\nВыбери платформу:", call.message.chat.id, call.message.message_id, reply_markup=verification_platform_keyboard())
    elif call.data == "buy_card":
        bot.edit_message_text("💳 ПОКУПКА КАРТЫ\n\nВыбери банк:", call.message.chat.id, call.message.message_id, reply_markup=cards_keyboard())
    elif call.data == "combos":
        bot.edit_message_text("🎁 КОМБО-ПАКЕТЫ\n\nВыбери пакет:", call.message.chat.id, call.message.message_id, reply_markup=combos_keyboard())
    elif call.data == "reviews":
        bot.edit_message_text("⭐ ОТЗЫВЫ\n\n👉 [ПЕРЕЙТИ В КАНАЛ](https://t.me/BYBIT100VERIF)\n\n🆘 Поддержка: " + HELP_CONTACT, call.message.chat.id, call.message.message_id, reply_markup=back_keyboard(), disable_web_page_preview=True)
    elif call.data == "help":
        bot.edit_message_text("🆘 ПОМОЩЬ\n\n📞 Поддержка: " + HELP_CONTACT + "\n\n❓ Частые вопросы:\n• Как долго длится верификация? — 5-15 минут\n• Что делать после оплаты? — Нажать 'Я оплатил' и отправить скриншот", call.message.chat.id, call.message.message_id, reply_markup=back_keyboard())
    elif call.data == "cart":
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: {total} USDT\n\n🆘 Поддержка: {HELP_CONTACT}", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif call.data == "clear_cart":
        user_carts[str(uid)] = []
        save_data()
        bot.answer_callback_query(call.id, "✅ Корзина очищена")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: {total} USDT\n\n🆘 Поддержка: {HELP_CONTACT}", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif call.data == "checkout":
        items, total = get_cart_text(uid)
        if not items or total == 0:
            bot.answer_callback_query(call.id, "❌ Корзина пуста!")
            return
        if not crypto_available:
            bot.send_message(uid, "❌ Оплата временно недоступна\n\n🆘 Поддержка: " + HELP_CONTACT)
            return
        try:
            invoice = crypto_client.create_invoice(asset=Asset.USDT, amount=float(total), description=f"Order {uid}")
            pending_orders[uid] = {"amount": total, "items": items}
            bot.send_message(uid, f"💳 ОПЛАТА ЗАКАЗА\n\n📦 Заказ:\n{items}\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: {total} USDT\n\n👇 ОПЛАТИТЕ ПО ССЫЛКЕ\n\n⚠️ ПОСЛЕ ОПЛАТЫ НАЖМИТЕ 'Я ОПЛАТИЛ' И ОТПРАВЬТЕ СКРИНШОТ!\n\n🆘 Поддержка: {HELP_CONTACT}", reply_markup=payment_keyboard(invoice.bot_invoice_url))
        except Exception as e:
            bot.send_message(uid, f"❌ Ошибка: {e}\n\n🆘 Поддержка: {HELP_CONTACT}")
    elif call.data == "paid":
        bot.send_message(uid, "📸 ПОЖАЛУЙСТА, ОТПРАВЬТЕ СКРИНШОТ ОПЛАТЫ В ЭТОТ ЧАТ\n\nПоддержка: " + HELP_CONTACT)
        bot.answer_callback_query(call.id, "✅ Отправьте скриншот оплаты")
    elif call.data == "back_to_verification":
        bot.edit_message_text("✅ ВЕРИФИКАЦИЯ\n\nВыбери платформу:", call.message.chat.id, call.message.message_id, reply_markup=verification_platform_keyboard())
    elif call.data == "platform_bybit":
        bot.edit_message_text("🏦 BYBIT\n\nВыбери страну:", call.message.chat.id, call.message.message_id, reply_markup=bybit_keyboard())
    elif call.data == "platform_pocket":
        bot.edit_message_text("🎯 POCKET OPTION\n\nВыбери страну:", call.message.chat.id, call.message.message_id, reply_markup=pocket_keyboard())
    elif call.data.startswith("add_bybit_"):
        code = call.data.split("_")[2]
        item = BYBIT_COUNTRIES[code]
        if is_item_in_cart(uid, item['name']):
            bot.answer_callback_query(call.id, f"❌ {item['name']} уже есть в корзине!")
            return
        if str(uid) not in user_carts:
            user_carts[str(uid)] = []
        user_carts[str(uid)].append({"name": item["name"], "price": item["price"]})
        save_data()
        bot.answer_callback_query(call.id, f"✅ {item['name']} добавлен!")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif call.data.startswith("add_pocket_"):
        code = call.data.split("_")[2]
        item = POCKET_COUNTRIES[code]
        if is_item_in_cart(uid, item['name']):
            bot.answer_callback_query(call.id, f"❌ {item['name']} уже есть в корзине!")
            return
        if str(uid) not in user_carts:
            user_carts[str(uid)] = []
        user_carts[str(uid)].append({"name": item["name"], "price": item["price"]})
        save_data()
        bot.answer_callback_query(call.id, f"✅ {item['name']} добавлен!")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif call.data.startswith("add_card_"):
        code = call.data.split("_")[2]
        item = CARDS[code]
        if is_item_in_cart(uid, item['name']):
            bot.answer_callback_query(call.id, f"❌ {item['name']} уже есть в корзине!")
            return
        if str(uid) not in user_carts:
            user_carts[str(uid)] = []
        user_carts[str(uid)].append({"name": item["name"], "price": item["price"]})
        save_data()
        bot.answer_callback_query(call.id, f"✅ {item['name']} добавлен!")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif call.data.startswith("add_combo_"):
        code = call.data.split("_")[2]
        item = COMBOS[code]
        if is_item_in_cart(uid, item['name']):
            bot.answer_callback_query(call.id, f"❌ {item['name']} уже есть в корзине!")
            return
        if str(uid) not in user_carts:
            user_carts[str(uid)] = []
        user_carts[str(uid)].append({"name": item["name"], "price": item["price"]})
        save_data()
        bot.answer_callback_query(call.id, f"✅ {item['name']} добавлен!")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif call.data.startswith("accept_ban_"):
        parts = call.data.split("_")
        user_id = int(parts[2])
        amount = float(parts[3])
        add_revenue(amount)
        ban_user(user_id)
        bot.answer_callback_query(call.id, f"✅ Добавлено {amount} USDT\n🚫 Пользователь {user_id} забанен")

@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = m.chat.id
    if is_banned(uid):
        bot.send_message(uid, "🚫 ДОСТУП ЗАБЛОКИРОВАН")
        return
    if uid not in pending_orders:
        bot.send_message(uid, "❌ Сначала оформите заказ через корзину!")
        return
    order = pending_orders.pop(uid)
    amount = order["amount"]
    items = order["items"]
    caption = f"📸 НОВЫЙ СКРИНШОТ ОПЛАТЫ\n\n👤 Пользователь: {uid}\n💰 Сумма: {amount} USDT\n\n📦 Заказ:\n{items}"
    try:
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=caption, reply_markup=admin_accept_keyboard(uid, amount))
        bot.send_message(uid, "✅ СКРИНШОТ ОТПРАВЛЕН!\n\nАдминистратор проверит его в ближайшее время.")
    except Exception as e:
        bot.send_message(uid, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/del_'))
def delete_item(m):
    uid = m.chat.id
    try:
        idx = int(m.text.split('_')[1])
        if str(uid) in user_carts and idx < len(user_carts[str(uid)]):
            removed = user_carts[str(uid)].pop(idx)
            save_data()
            bot.send_message(uid, f"🗑 Товар удалён: {removed['name']}")
            items, total = get_cart_text(uid)
            bot.send_message(uid, f"🛒 КОРЗИНА\n\n{items}\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: {total} USDT", reply_markup=cart_keyboard())
    except:
        pass

if __name__ == "__main__":
    print("✅ Бот запущен")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=30)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(10)