import json
import os
from datetime import datetime, timedelta
import requests
import telebot
from telebot import types
from config import BOT_TOKEN, ADMIN_ID, GITHUB_BASE_URL, PUBG_ID, TELEGRAM_USERNAME

bot = telebot.TeleBot(BOT_TOKEN)
SUBS_FILE = "subscriptions.json"
PENDING_FILE = "pending_requests.json"

# ============ تخزين مؤقت لنوايا المستخدمين ============
user_intention = {}

# ============ دوال مساعدة لملفات JSON ============

def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = f.read().strip()
                return json.loads(data) if data else {}
        except:
            return {}
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ============ دوال إدارة الطلبات ============

def add_pending_request(user_id, plan_type, photo_file_id):
    pending = load_json(PENDING_FILE)
    pending[str(user_id)] = {
        "user_id": user_id,
        "plan_type": plan_type,
        "photo_file_id": photo_file_id,
        "timestamp": datetime.now().isoformat()
    }
    save_json(PENDING_FILE, pending)

def remove_pending_request(user_id):
    pending = load_json(PENDING_FILE)
    user_str = str(user_id)
    if user_str in pending:
        del pending[user_str]
        save_json(PENDING_FILE, pending)

# ============ دوال الاشتراكات ============

def is_active(user_id):
    subs = load_json(SUBS_FILE)
    user_str = str(user_id)
    if user_str not in subs:
        return False
    try:
        expiry = datetime.fromisoformat(subs[user_str]["expiry"])
        return datetime.now() < expiry
    except:
        return False

# ============ روابط GitHub ============

def list_github_files(folder):
    try:
        # استخراج اسم المستودع من GITHUB_BASE_URL
        repo_name = "/".join(GITHUB_BASE_URL.split("/")[-2:])
        list_url = f"https://raw.githubusercontent.com/{repo_name}/main/{folder}/filelist.txt"
        response = requests.get(list_url, timeout=5)
        if response.status_code == 200:
            flist = response.text.strip().split("\n")
            return [f for f in flist if f and not f.startswith("#")]
    except Exception as e:
        print(f"[ERROR] فشل عرض ملفات {folder}: {e}")
    return []

# ============ إشعار آمن للمشرف ============

def try_notify_admin(text):
    if not ADMIN_ID:
        return
    try:
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except Exception as e:
        print(f"[إشعار] لا يمكن إرسال تنبيه للمشرف: {e}")

# ============ واجهة المستخدم ============

def show_plan_selection(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(".NORMAL", callback_data="select_plan:NORMAL"),
        types.InlineKeyboardButton("VIP", callback_data="select_plan:VIP")
    )
    bot.send_message(message.chat.id, "🎯 اختر نوع الاشتراك:", reply_markup=markup)

def show_payment_methods(message, plan_type):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if plan_type == "NORMAL":
        markup.add(
            types.InlineKeyboardButton("🎮 شحن UC (عادي)", callback_data="offer:NORMAL:uc"),
            types.InlineKeyboardButton("💎 نجوم/هدية (عادي)", callback_data="offer:NORMAL:stars")
        )
        bot.send_message(message.chat.id, "اختر طريقة الدفع للخطة العادية:", reply_markup=markup)
    else:
        markup.add(
            types.InlineKeyboardButton("🎮 شحن UC (مميز)", callback_data="offer:VIP:uc"),
            types.InlineKeyboardButton("💎 نجوم/هدية (مميز)", callback_data="offer:VIP:stars")
        )
        bot.send_message(message.chat.id, "اختر طريقة الدفع للخطة المميزة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_plan:"))
def handle_plan_selection(call):
    plan_type = call.data.split(":")[1]
    user_intention[call.from_user.id] = plan_type
    show_payment_methods(call.message, plan_type)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("offer:"))
def show_offers(call):
    _, plan_type, method = call.data.split(":")
    if method == "uc":
        if plan_type == "NORMAL":
            msg = (
                f"🎮 *شحن UC - خطة عادية*\n\n"
                f"الحساب: `{PUBG_ID}`\n\n"
                " - 300 UC = 7 أيام\n"
                " - 660 UC = 15 يوم\n\n"
                "📸 أرسل لقطة شاشة للشحن الآن."
            )
        else:
            msg = (
                f"🎮 *شحن UC - خطة مميزة*\n\n"
                f"الحساب: `{PUBG_ID}`\n\n"
                " - 1500 UC = 10 أيام\n"
                " - 3850 UC = 30 يوم\n\n"
                "📸 أرسل لقطة شاشة للشحن الآن."
            )
    else:
        if plan_type == "NORMAL":
            msg = (
                "💎 *نجوم/هدية - خطة عادية*\n\n"
                " - 50 نجمة = 7 أيام\n"
                " - 100 نجمة = 15 يوم\n\n"
                f"📩 أرسل النجوم إلى: `@{TELEGRAM_USERNAME}`\n"
                "📸 ثم أرسل لقطة الإيصال الآن."
            )
        else:
            msg = (
                "💎 *نجوم/هدية - خطة مميزة*\n\n"
                " - 150 نجمة = 10 أيام\n"
                " - 300 نجمة = 30 يوم\n\n"
                f"📩 أرسل النجوم إلى: `@{TELEGRAM_USERNAME}`\n"
                "📸 ثم أرسل لقطة الإيصال الآن."
            )
    bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# ============ استقبال الصور ============

@bot.message_handler(content_types=['photo'])
def handle_receipt_photo(message):
    user_id = message.from_user.id
    plan_type = user_intention.get(user_id, "NORMAL")
    add_pending_request(user_id, plan_type, message.photo[-1].file_id)

    username = f"@{message.from_user.username}" if message.from_user.username else f"ID{user_id}"
    try_notify_admin(
        f"📥 طلب جديد ({plan_type}) من {username}\n"
        f"لعرض جميع الطلبات: /requests"
    )
    bot.send_message(
        message.chat.id,
        "✅ تم استلام صورة الدفع! سيتم التحقق منها قريبًا."
    )

# ============ أوامر المشرف ============

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "👤 لوحة تحكم المشرف:\n"
            "/activate <user_id> <days> <VIP/NORMAL>\n"
            "/unactivate <user_id>\n"
            "/listsubs\n"
            "/requests"
        )
        return

    if is_active(user_id):
        show_files(message)
    else:
        show_plan_selection(message)

@bot.message_handler(commands=['requests'])
def show_requests_menu(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("عادي (NORMAL)", callback_data="view:NORMAL"),
        types.InlineKeyboardButton("مميز (VIP)", callback_data="view:VIP")
    )
    bot.send_message(message.chat.id, "اختر نوع الطلبات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view:"))
def list_requests(call):
    req_type = call.data.split(":")[1]
    pending = load_json(PENDING_FILE)
    filtered = {uid: data for uid, data in pending.items() if data.get("plan_type") == req_type}

    if not filtered:
        bot.answer_callback_query(call.id, f"📭 لا توجد طلبات {req_type}.", show_alert=True)
        return

    markup = types.InlineKeyboardMarkup()
    for uid in filtered:
        markup.add(types.InlineKeyboardButton(f"ID: {uid}", callback_data=f"photo:{uid}"))
    bot.send_message(call.message.chat.id, f"📋 طلبات {req_type}:", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("photo:"))
def show_photo(call):
    user_id = call.data.split(":")[1]
    pending = load_json(PENDING_FILE)
    if user_id in pending and pending[user_id]["photo_file_id"]:
        bot.send_photo(call.message.chat.id, pending[user_id]["photo_file_id"])
    else:
        bot.send_message(call.message.chat.id, "❌ لا توجد صورة لهذا الطلب.")
    bot.answer_callback_query(call.id)

# ============ تفعيل / إلغاء الاشتراك ============

@bot.message_handler(commands=['activate'])
def activate_sub(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) != 4:
            bot.reply_to(message, "UsageId: /activate <user_id> <days> <VIP/NORMAL>")
            return
        user_id = int(parts[1])
        days = int(parts[2])
        plan_type = parts[3].upper()
        if plan_type not in ["VIP", "NORMAL"]:
            bot.reply_to(message, "النوع يجب أن يكون VIP أو NORMAL")
            return

        subs = load_json(SUBS_FILE)
        subs[str(user_id)] = {
            "type": plan_type,
            "expiry": (datetime.now() + timedelta(days=days)).isoformat()
        }
        save_json(SUBS_FILE, subs)
        remove_pending_request(user_id)

        try:
            bot.send_message(user_id, "🎉 تم تفعيل اشتراكك! استخدم /start لعرض الملفات.")
        except:
            pass
        bot.reply_to(message, f"✅ تم التفعيل لـ {user_id} كـ {plan_type} لمدة {days} يوم.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['unactivate'])
def deactivate_sub(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "UsageId: /unactivate <user_id>")
            return
        user_id = int(parts[1])
        subs = load_json(SUBS_FILE)
        user_str = str(user_id)
        if user_str in subs:
            del subs[user_str]
            save_json(SUBS_FILE, subs)
            bot.reply_to(message, f"✅ تم إلغاء الاشتراك لـ {user_id}")
            try:
                bot.send_message(user_id, "⚠️ تم إلغاء اشتراكك من قبل المشرف.")
            except:
                pass
        else:
            bot.reply_to(message, f"❌ المستخدم {user_id} ليس لديه اشتراك نشط.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.message_handler(commands=['listsubs'])
def list_subscribers(message):
    if message.from_user.id != ADMIN_ID:
        return
    subs = load_json(SUBS_FILE)
    if not subs:
        bot.reply_to(message, "📭 لا يوجد مشتركين نشطين.")
        return

    lines = ["📋 المشتركين النشطين:"]
    for uid, data in subs.items():
        try:
            expiry = datetime.fromisoformat(data["expiry"])
            status = "✅ نشط" if datetime.now() < expiry else "❌ منتهي"
            plan = data.get("type", "NORMAL")
            lines.append(f"ID: `{uid}` | نوع: {plan} | حالة: {status}")
        except:
            lines.append(f"ID: `{uid}` | نوع: {data.get('type', 'UNKNOWN')} | حالة: ❓ غير معروف")

    bot.reply_to(message, "\n".join(lines), parse_mode="Markdown")

# ============ عرض الملفات ============

def show_files(message):
    subs_data = load_json(SUBS_FILE)
    user_str = str(message.from_user.id)
    user_type = "VIP" if is_active(message.from_user.id) and subs_data.get(user_str, {}).get("type") == "VIP" else "NORMAL"
    
    folders = ["NORMAL"]
    if user_type == "VIP":
        folders.append("VIP")

    markup = types.InlineKeyboardMarkup()
    for folder in folders:
        files = list_github_files(folder)
        if not files:
            continue
        markup.add(types.InlineKeyboardButton(f"📁 {folder}", callback_data="dummy"))
        for file in files:
            markup.add(types.InlineKeyboardButton(f"📄 {file}", callback_data=f"send:{folder}:{file}"))

    if markup.keyboard:
        bot.send_message(message.chat.id, "📂 اختر ملفًا:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ لا توجد ملفات متاحة حاليًا.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("send:"))
def send_file(call):
    if not is_active(call.from_user.id):
        bot.answer_callback_query(call.id, "⏳ اشتراكك منتهٍ!", show_alert=True)
        return
    try:
        _, folder, filename = call.data.split(":", 2)
        # بناء رابط مباشر باستخدام raw.githubusercontent.com
        repo_parts = GITHUB_BASE_URL.split("/")[-2:]  # ['user', 'repo']
        file_url = f"https://raw.githubusercontent.com/{'/'.join(repo_parts)}/main/{folder}/{filename}"
        
        response = requests.get(file_url, timeout=15)
        if response.status_code != 200:
            raise Exception(f"الملف غير موجود أو لا يمكن الوصول إليه (HTTP {response.status_code})")

        bot.send_document(call.message.chat.id, response.content, visible_file_name=filename)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطأ: {str(e)}", show_alert=True)

# ============ التشغيل ============

if __name__ == "__main__":
    print("🚀 البوت يعمل...")
    bot.infinity_polling()