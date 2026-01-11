import asyncio, random, re, os, json
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ===== CONFIG =====
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8028025981:AAG4pVK8CCHNh0Kbz0h4k5bqVvPRn_DhG_E"
BOT_GAME = "xocdia88_bot_uytin_bot"
SESSION_FILE = "sessions.txt"
CODES_FILE = "codes.json"
LOG_GROUP = -1001234567890  # ID nhóm nhận log mã

# ===== FLASK KEEP ALIVE =====
app = Flask(__name__)
@app.route("/")
def home():
    return "BOT ONLINE"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# ===== STATE =====
ACCS = {}           # acc_id -> {"client","name","status","last"}
TOTAL_CODE = 0
CODES_DB = {}       # acc_id -> last code
PENDING_LOGIN = {}  # sender_id -> {"client","phone","hash"}

# ===== TIME VN =====
def now_vn():
    return datetime.utcnow() + timedelta(hours=7)

def in_time():
    h = now_vn().hour + now_vn().minute/60
    return 7 <= h <= 9.5 or 11 <= h <= 14.5 or 19 <= h <= 24

def sleeping_time():
    h = now_vn().hour
    return 2 <= h < 6

# ===== ADMIN BOT =====
admin = TelegramClient("admin", API_ID, API_HASH)

def menu():
    return [
        [Button.inline("📦 Acc", b"acc")],
        [Button.inline("➕ Nạp Acc", b"add")],
        [Button.inline("🧪 Test Acc", b"test")],
        [Button.inline("📊 Thống kê", b"stat")],
        [Button.inline("♻️ Restart", b"restart")]
    ]

# ===== HELPER =====
async def notify_admin(acc, msg=None):
    text = msg if msg else f"⚠️ ACC `{acc['name']}` hiện trạng thái: {acc['status']}"
    try:
        if LOG_GROUP:
            await admin.send_message(LOG_GROUP, text)
        await admin.send_message(admin.me.id, text)
    except Exception as e:
        print("❌ Lỗi notify:", e)

def save_session(sess):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        if sess not in f.read():
            f.write(sess + "\n")

def save_codes():
    with open(CODES_FILE, "w") as f:
        json.dump(CODES_DB, f, indent=2)

def load_codes():
    global CODES_DB
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE) as f:
            CODES_DB = json.load(f)

# ===== ADMIN MENU =====
@admin.on(events.NewMessage(pattern="/start"))
async def start(e):
    await e.respond(
        f"🤖 BOT ĐẬP HỘP\n📦 Acc: {len(ACCS)}\n🎁 Tổng mã: {TOTAL_CODE}",
        buttons=menu()
    )

@admin.on(events.CallbackQuery)
async def cb(e):
    if e.data == b"acc":
        txt = "📦 DANH SÁCH ACC\n"
        for a in ACCS.values():
            txt += f"- {a['name']} | {a['status']}\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"add":
        await e.edit(
            "➕ NẠP ACC\n"
            "- Gửi SESSION1|SESSION2\n"
            "- Hoặc /login SĐT để login thủ công",
            buttons=[[Button.inline("⬅️ Back", b"back")]]
        )

    elif e.data == b"test":
        txt = "🧪 KIỂM TRA ACC...\n"
        await e.edit(txt)
        for a in ACCS.values():
            client = a["client"]
            try:
                if await client.is_user_authorized():
                    a["status"] = "ONLINE"
                else:
                    a["status"] = "OFFLINE"
            except FloodWaitError:
                a["status"] = "FLOOD"
            except:
                a["status"] = "ERROR"
            txt += f"- {a['name']} | {a['status']}\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"stat":
        await e.edit(f"📊 THỐNG KÊ\n🎁 Tổng mã: {TOTAL_CODE}", buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"restart":
        await e.edit("♻️ Restart...")
        os._exit(0)

    elif e.data == b"back":
        await e.edit("🤖 MENU", buttons=menu())

# ===== GRAB HỘP =====
async def grab_loop(acc):
    global TOTAL_CODE
    client = acc["client"]

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if sleeping_time(): return
        if not in_time(): return
        if not ev.reply_markup: return

        btn = next(
            (b for r in ev.reply_markup.rows for b in r.buttons
             if any(x in b.text.lower() for x in ["đập","hộp","mở"])),
            None
        )
        if not btn: return

        try:
            await asyncio.sleep(random.uniform(0.3,1.2))
            await ev.click()
            await asyncio.sleep(1.2)

            msg = await client.get_messages(BOT_GAME, limit=1)
            if msg and msg[0].message:
                m = re.search(r"code.*?:\s*([A-Z0-9]+)", msg[0].message, re.I)
                if m:
                    code = m.group(1)
                    if code != acc.get("last"):
                        acc["last"] = code
                        TOTAL_CODE += 1
                        CODES_DB[str(acc["id"])] = code
                        save_codes()
                        await notify_admin(acc, f"💌 ACC: {acc['name']}\n🎁 CODE: `{code}`")
        except FloodWaitError:
            acc["status"] = "FLOOD"
        except:
            acc["status"] = "ERROR"

# ===== WATCHER ACC =====
async def acc_watcher():
    while True:
        for a in ACCS.values():
            client = a["client"]
            prev = a["status"]
            try:
                if not await client.is_user_authorized():
                    a["status"] = "OFFLINE"
                else:
                    a["status"] = "ONLINE"
            except FloodWaitError:
                a["status"] = "FLOOD"
            except:
                a["status"] = "ERROR"

            if a["status"] != prev:
                await notify_admin(a)
        await asyncio.sleep(60)

# ===== LOAD ACC =====
async def load_accounts():
    load_codes()
    if not os.path.exists(SESSION_FILE): return

    with open(SESSION_FILE) as f:
        for s in f:
            s = s.strip()
            if not s: continue
            try:
                c = TelegramClient(StringSession(s), API_ID, API_HASH)
                await c.connect()
                if not await c.is_user_authorized(): continue

                me = await c.get_me()
                ACCS[me.id] = {
                    "id": me.id,
                    "client": c,
                    "name": me.first_name,
                    "status": "ONLINE",
                    "last": CODES_DB.get(str(me.id))
                }
                asyncio.create_task(grab_loop(ACCS[me.id]))
            except:
                continue

# ===== LOGIN THỦ CÔNG =====
@admin.on(events.NewMessage(pattern="/login"))
async def login_handler(e):
    try:
        phone = "".join(filter(str.isdigit,e.text.split(" ",1)[1]))
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        await c.connect()
        sent = await c.send_code_request(phone)
        PENDING_LOGIN[e.sender_id] = {"client":c,"phone":phone,"hash":sent.phone_code_hash}
        await e.respond(f"📩 OTP đã gửi +{phone}, nhập /otp 12345 để xác thực")
    except:
        await e.respond("❌ Sai định dạng /login + SĐT")

@admin.on(events.NewMessage(pattern="/otp"))
async def otp_handler(e):
    if e.sender_id not in PENDING_LOGIN:
        await e.respond("❌ Không có yêu cầu login")
        return
    data = PENDING_LOGIN[e.sender_id]
    code = "".join(filter(str.isdigit, e.text))
    try:
        await data["client"].sign_in(data["phone"], code, phone_code_hash=data["hash"])
        sess_str = data["client"].session.save()
        save_session(sess_str)
        me = await data["client"].get_me()
        ACCS[me.id] = {
            "id": me.id,
            "client": data["client"],
            "name": me.first_name,
            "status": "ONLINE",
            "last": CODES_DB.get(str(me.id))
        }
        asyncio.create_task(grab_loop(ACCS[me.id]))
        del PENDING_LOGIN[e.sender_id]
        await e.respond(f"✅ Kích hoạt thành công: {me.first_name}")
    except Exception as ex:
        await e.respond(f"❌ Lỗi OTP: {ex}")

# ===== MAIN =====
async def main():
    await admin.start(bot_token=BOT_TOKEN)
    await load_accounts()
    asyncio.create_task(acc_watcher())
    await admin.run_until_disconnected()

# ===== RUN =====
if __name__ == "__main__":
    asyncio.run(main())
