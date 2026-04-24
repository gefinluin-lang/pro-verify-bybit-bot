import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import json
import os
from flask import Flask, request

# ========== ЗАГРУЗКА ТОКЕНОВ ИЗ .ENV ==========
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CRYPTOBOT_TOKEN = os.getenv('CRYPTOBOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
HELP_CONTACT = '@poderkaverif'

# ========== ПРОВЕРКА ==========
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден!")
if not CRYPTOBOT_TOKEN:
    raise ValueError("CRYPTOBOT_TOKEN не найден!")

# ========== CRYPTOBOT ==========
crypto_available = False
crypto_client = None

try:
    from cryptobot import CryptoBotClient
    from cryptobot.models import Asset
    crypto_client = CryptoBotClient(api_token=CRYPTOBOT_TOKEN, is_mainnet=True)
    crypto_available = True
    print("✅ CryptoBot подключён")
except Exception as e:
    print(f"❌ CryptoBot НЕ подключён: {e}")

bot = telebot.TeleBot(BOT_TOKEN)

# ========== FLASK ДЛЯ RENDER ==========
app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return "✅ Бот работает!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 400

# ========== УСТАНОВКА WEBHOOK ==========
WEBHOOK_URL = 'https://pro-verify-bybit-bot.onrender.com/webhook'
bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url=WEBHOOK_URL)
print(f"✅ Webhook установлен: {WEBHOOK_URL}")

# ========== ДАННЫЕ ==========
DATA_FILE = 'bot_data.json'
total_revenue_usdt = 0
total_orders = 0
BANNED_USERS = set()
user_carts = {}
pending_orders = {}
user_name = {}
user_bank = {}

def load_data():
    global total_revenue_usdt, total_orders, BANNED_USERS, user_carts, user_name, user_bank
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                total_revenue_usdt = data.get('total_revenue_usdt', 0)
                total_orders = data.get('total_orders', 0)
                BANNED_USERS = set(data.get('banned_users', []))
                user_carts = data.get('user_carts', {})
                user_name = data.get('user_name', {})
                user_bank = data.get('user_bank', {})
        except:
            pass

def save_data():
    if ADMIN_ID in BANNED_USERS:
        BANNED_USERS.discard(ADMIN_ID)
    data = {
        'total_revenue_usdt': total_revenue_usdt,
        'total_orders': total_orders,
        'banned_users': list(BANNED_USERS),
        'user_carts': user_carts,
        'user_name': user_name,
        'user_bank': user_bank
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

load_data()
save_data()

def is_banned(user_id):
    if user_id == ADMIN_ID:
        return False
    return user_id in BANNED_USERS

def ban_user(user_id):
    if user_id == ADMIN_ID:
        return
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

# ========== ТОВАРЫ ==========
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
    "sber": {"name": "🏦 Сбербанк", "price": 263}
}

COMBOS = {
    "combo1": {"name": "🔥 ПОЛНЫЙ ФАРШ", "price": 250},
    "combo2": {"name": "🚀 КРИПТО-СТАРТ", "price": 213},
    "combo3": {"name": "🎯 ОПЦИОНЩИК", "price": 200}
}

# ========== КЛАВИАТУРЫ ==========
def start_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Верификация", callback_data="verification"),
        InlineKeyboardButton("💳 Купить карту", callback_data="buy_card"),
        InlineKeyboardButton("🎁 Комбо", callback_data="combos"),
        InlineKeyboardButton("🛒 Корзина", callback_data="cart"),
        InlineKeyboardButton("⭐ Отзывы", callback_data="reviews"),
        InlineKeyboardButton("🆘 Поддержка", callback_data="support")
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
    kb.add(
        InlineKeyboardButton("💳 ОПЛАТИТЬ", url=pay_url),
        InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data="paid"),
        InlineKeyboardButton("◀ Назад", callback_data="back_to_start")
    )
    return kb

def admin_accept_keyboard(user_id, amount):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(f"✅ ПРИНЯТЬ {amount} USDT", callback_data=f"accept_{user_id}_{amount}"),
        InlineKeyboardButton(f"❌ ОТКЛОНИТЬ", callback_data=f"reject_{user_id}")
    )
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

def bank_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🏦 Сбербанк", callback_data="bank_sber"),
        InlineKeyboardButton("🏦 Т-Банк", callback_data="bank_tbank"),
        InlineKeyboardButton("🏦 Альфа-Банк", callback_data="bank_alfa")
    )
    return kb

# ========== ОБРАБОТЧИКИ ==========
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.chat.id
    if uid == ADMIN_ID:
        bot.send_message(uid, "🌟 ДОБРО ПОЖАЛОВАТЬ, АДМИНИСТРАТОР!\n\n👇 Выбери действие:", reply_markup=start_keyboard(uid))
        return
    if is_banned(uid):
        bot.send_message(uid, "🚫 ДОСТУП ЗАБЛОКИРОВАН")
        return
    if uid not in user_name:
        bot.send_message(uid, "🌟 ДОБРО ПОЖАЛОВАТЬ В МАГАЗИН!\n\n📝 Напишите ваше имя:")
        bot.register_next_step_handler(m, get_user_name)
        return
    bot.send_message(uid, f"🌟 С НОВЫМ ВИЗИТОМ, {user_name[uid]}!\n🏦 Ваш банк: {user_bank.get(uid, 'Не выбран')}\n\n👇 Выбери действие:", reply_markup=start_keyboard(uid))

def get_user_name(m):
    uid = m.chat.id
    user_name[uid] = m.text
    save_data()
    bot.send_message(uid, f"✅ Отлично, {user_name[uid]}!\n\n🏦 Теперь выберите ваш банк:", reply_markup=bank_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def handle(call):
    uid = call.from_user.id
    data = call.data

    if uid != ADMIN_ID and is_banned(uid):
        bot.answer_callback_query(call.id, "❌ Доступ заблокирован")
        return

    # РЕГИСТРАЦИЯ
    if uid != ADMIN_ID and data.startswith("bank_"):
        if data == "bank_sber":
            user_bank[uid] = "Сбербанк"
        elif data == "bank_tbank":
            user_bank[uid] = "Т-Банк"
        elif data == "bank_alfa":
            user_bank[uid] = "Альфа-Банк"
        save_data()
        bot.edit_message_text(f"🎉 РЕГИСТРАЦИЯ ЗАВЕРШЕНА!\n📝 Имя: {user_name[uid]}\n🏦 Банк: {user_bank[uid]}\n\n🌟 Добро пожаловать!", call.message.chat.id, call.message.message_id, reply_markup=start_keyboard(uid))
        bot.answer_callback_query(call.id, f"✅ Выбран {user_bank[uid]}")
        return

    # НАВИГАЦИЯ
    if data == "back_to_start":
        bot.edit_message_text("🌟 ГЛАВНОЕ МЕНЮ\n\n👇 Выбери действие:", call.message.chat.id, call.message.message_id, reply_markup=start_keyboard(uid))
        return

    # АДМИН
    if data == "stats" and uid == ADMIN_ID:
        bot.send_message(ADMIN_ID, f"💰 СТАТИСТИКА\n\n💵 Выручка: {total_revenue_usdt} USDT\n📦 Заказов: {total_orders}\n👥 Забанено: {len(BANNED_USERS)}\n👤 Пользователей: {len(user_name)}")
        bot.answer_callback_query(call.id)
        return
    if data == "banned_list" and uid == ADMIN_ID:
        bot.send_message(ADMIN_ID, get_banned_list_text(), reply_markup=back_keyboard())
        bot.answer_callback_query(call.id)
        return

    # ПОДДЕРЖКА
    if data == "support":
        bot.edit_message_text("🆘 ПОДДЕРЖКА\n\n📝 Напишите ваш вопрос, администратор ответит вам.", call.message.chat.id, call.message.message_id, reply_markup=back_keyboard())
        return

    # ПРОДУКТЫ
    if data == "verification":
        bot.edit_message_text("✅ ВЕРИФИКАЦИЯ\n\n🔐 Выберите платформу:", call.message.chat.id, call.message.message_id, reply_markup=verification_platform_keyboard())
    elif data == "buy_card":
        bot.edit_message_text("💳 ПОКУПКА КАРТЫ\n\n🏦 Выберите банк:", call.message.chat.id, call.message.message_id, reply_markup=cards_keyboard())
    elif data == "combos":
        bot.edit_message_text("🎁 КОМБО-ПАКЕТЫ\n\n🔥 Выберите пакет:", call.message.chat.id, call.message.message_id, reply_markup=combos_keyboard())
    elif data == "reviews":
        bot.edit_message_text("⭐ ОТЗЫВЫ\n\n👉 [КАНАЛ С ОТЗЫВАМИ](https://t.me/BYBIT100VERIF)", call.message.chat.id, call.message.message_id, reply_markup=back_keyboard(), disable_web_page_preview=True)
    elif data == "cart":
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif data == "clear_cart":
        user_carts[str(uid)] = []
        save_data()
        bot.answer_callback_query(call.id, "✅ Корзина очищена")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif data == "checkout":
        items, total = get_cart_text(uid)
        if not items or total == 0:
            bot.answer_callback_query(call.id, "❌ Корзина пуста!")
            return
        if not crypto_available:
            bot.send_message(uid, "❌ Оплата временно недоступна")
            return
        try:
            invoice = crypto_client.create_invoice(asset=Asset.USDT, amount=float(total), description=f"Order_{uid}")
            pending_orders[uid] = {"amount": total, "items": items}
            bot.send_message(uid, f"💳 ОПЛАТА\n\n📦 Заказ:\n{items}\n💰 Сумма: {total} USDT\n\n👇 ОПЛАТИТЕ ПО ССЫЛКЕ\n\n⚠️ ПОСЛЕ ОПЛАТЫ НАЖМИТЕ 'Я ОПЛАТИЛ'", reply_markup=payment_keyboard(invoice.bot_invoice_url))
            bot.answer_callback_query(call.id, "✅ Счёт создан!")
        except Exception as e:
            bot.send_message(uid, f"❌ Ошибка: {e}")
    elif data == "paid":
        bot.send_message(uid, "📸 ОТПРАВЬТЕ СКРИНШОТ ОПЛАТЫ В ЭТОТ ЧАТ")
        bot.answer_callback_query(call.id, "✅ Ждём скриншот")
    elif data == "back_to_verification":
        bot.edit_message_text("✅ ВЕРИФИКАЦИЯ\n\nВыбери платформу:", call.message.chat.id, call.message.message_id, reply_markup=verification_platform_keyboard())
    elif data == "platform_bybit":
        bot.edit_message_text("🏦 BYBIT\n\nВыбери страну:", call.message.chat.id, call.message.message_id, reply_markup=bybit_keyboard())
    elif data == "platform_pocket":
        bot.edit_message_text("🎯 POCKET OPTION\n\nВыбери страну:", call.message.chat.id, call.message.message_id, reply_markup=pocket_keyboard())

    # ДОБАВЛЕНИЕ В КОРЗИНУ
    elif data.startswith("add_bybit_"):
        code = data.split("_")[2]
        item = BYBIT_COUNTRIES[code]
        if str(uid) not in user_carts:
            user_carts[str(uid)] = []
        user_carts[str(uid)].append({"name": item["name"], "price": item["price"]})
        save_data()
        bot.answer_callback_query(call.id, f"✅ {item['name']} добавлен!")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif data.startswith("add_pocket_"):
        code = data.split("_")[2]
        item = POCKET_COUNTRIES[code]
        if str(uid) not in user_carts:
            user_carts[str(uid)] = []
        user_carts[str(uid)].append({"name": item["name"], "price": item["price"]})
        save_data()
        bot.answer_callback_query(call.id, f"✅ {item['name']} добавлен!")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif data.startswith("add_card_"):
        code = data.split("_")[2]
        item = CARDS[code]
        if str(uid) not in user_carts:
            user_carts[str(uid)] = []
        user_carts[str(uid)].append({"name": item["name"], "price": item["price"]})
        save_data()
        bot.answer_callback_query(call.id, f"✅ {item['name']} добавлен!")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())
    elif data.startswith("add_combo_"):
        code = data.split("_")[2]
        item = COMBOS[code]
        if str(uid) not in user_carts:
            user_carts[str(uid)] = []
        user_carts[str(uid)].append({"name": item["name"], "price": item["price"]})
        save_data()
        bot.answer_callback_query(call.id, f"✅ {item['name']} добавлен!")
        items, total = get_cart_text(uid)
        bot.edit_message_text(f"🛒 КОРЗИНА\n\n{items}\n💰 Сумма: {total} USDT", call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard())

    # ПРИНЯТЬ/ОТКЛОНИТЬ
    elif data.startswith("accept_"):
        parts = data.split("_")
        user_id = int(parts[1])
        amount = float(parts[2])
        add_revenue(amount)
        bot.send_message(user_id, f"✅ ПЛАТЁЖ НА {amount} USDT ПРИНЯТ!\n\nСпасибо за покупку!")
        bot.answer_callback_query(call.id, f"✅ +{amount} USDT")
    elif data.startswith("reject_"):
        parts = data.split("_")
        user_id = int(parts[1])
        bot.send_message(user_id, f"❌ ПЛАТЁЖ ОТКЛОНЁН!\n\nОтправьте чёткий скриншот оплаты.")
        bot.answer_callback_query(call.id, f"❌ Платёж отклонён")

# ========== СКРИНШОТЫ ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = m.chat.id
    if uid != ADMIN_ID and is_banned(uid):
        bot.send_message(uid, "🚫 ДОСТУП ЗАБЛОКИРОВАН")
        return
    if uid not in pending_orders:
        bot.send_message(uid, "❌ Сначала оформите заказ!")
        return
    order = pending_orders.pop(uid)
    amount = order["amount"]
    items = order["items"]
    caption = f"📸 СКРИНШОТ ОТ {user_name.get(uid, uid)} (ID: {uid})\n💰 {amount} USDT\n\n📦 {items}"
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=caption, reply_markup=admin_accept_keyboard(uid, amount))
    bot.send_message(uid, "✅ Скриншот отправлен! Администратор проверит оплату.")

# ========== УДАЛЕНИЕ ИЗ КОРЗИНЫ ==========
@bot.message_handler(func=lambda m: m.text and m.text.startswith('/del_'))
def delete_item(m):
    uid = m.chat.id
    try:
        idx = int(m.text.split('_')[1])
        if str(uid) in user_carts and idx < len(user_carts[str(uid)]):
            removed = user_carts[str(uid)].pop(idx)
            save_data()
            bot.send_message(uid, f"🗑 Удалён: {removed['name']}")
            items, total = get_cart_text(uid)
            bot.send_message(uid, f"🛒 КОРЗИНА\n\n{items}\n💰 Сумма: {total} USDT", reply_markup=cart_keyboard())
    except:
        pass

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🔥 БОТ PRO VERIFY BYBIT ЗАПУЩЕН!")
    print("=" * 50)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
