import asyncio, random, re, os, json
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# ===== CẤU HÌNH =====
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8028025981:AAG4pVK8CCHNh0Kbz0h4k5bqVvPRn_DhG_E"

ADMIN_ID = 7816353760
BOT_GAME = "xocdia88_bot_uytin_bot"

SESSION_FILE = "sessions.txt"
CODES_FILE = "codes.json"

# ===== KEEP ALIVE =====
app = Flask(__name__)
@app.route("/")
def home(): return "BOT ONLINE"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# ===== BIẾN =====
ACCS = {}
CODES_DB = {}
TOTAL_CODE = 0
PENDING_LOGIN = {}

# ===== FILE =====
def save_session(sess):
    with open(SESSION_FILE, "a+", encoding="utf-8") as f:
        f.seek(0)
        if sess not in f.read():
            f.write(sess + "\n")

def save_codes():
    with open(CODES_FILE, "w", encoding="utf-8") as f:
        json.dump(CODES_DB, f, indent=2)

# ===== ADMIN BOT =====
admin = TelegramClient("admin", API_ID, API_HASH)

def only_admin(e): 
    return e.sender_id == ADMIN_ID

def menu():
    return [
        [Button.inline("📦 Acc", b"acc"), Button.inline("📊 Thống kê", b"stat")],
        [Button.inline("➕ Nạp Acc", b"add")]
    ]

@admin.on(events.NewMessage(pattern="/start"))
async def start(e):
    if not only_admin(e): return
    await e.respond(
        f"🤖 BOT ĐẬP HỘP\nAcc: {len(ACCS)}\nCode: {TOTAL_CODE}",
        buttons=menu()
    )

@admin.on(events.CallbackQuery)
async def cb(e):
    if not only_admin(e): return

    if e.data == b"acc":
        t = "📦 ACC:\n"
        for a in ACCS.values():
            t += f"- {a['stt']} | {a['name']}\n"
        await e.edit(t, buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"stat":
        t = f"🎁 TỔNG CODE: {TOTAL_CODE}\n\n"
        for a in ACCS.values():
            codes = CODES_DB.get(str(a["id"]), [])
            t += f"- Acc {a['stt']}: {len(codes)}\n"
        await e.edit(t, buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"add":
        await e.edit("➕ /login <sdt>", buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"back":
        await e.edit("MENU", buttons=menu())

# ===== LOGIN =====
@admin.on(events.NewMessage(pattern="/login"))
async def login(e):
    if not only_admin(e): return
    phone = "".join(filter(str.isdigit, e.text))
    c = TelegramClient(StringSession(), API_ID, API_HASH)
    await c.connect()
    sent = await c.send_code_request(phone)
    PENDING_LOGIN[e.sender_id] = {"c": c, "p": phone, "h": sent.phone_code_hash}
    await e.respond("📩 Nhập /otp <mã>")

@admin.on(events.NewMessage(pattern="/otp"))
async def otp(e):
    if not only_admin(e): return
    d = PENDING_LOGIN.get(e.sender_id)
    if not d: return

    code = "".join(filter(str.isdigit, e.text))
    await d["c"].sign_in(d["p"], code, phone_code_hash=d["h"])
    save_session(d["c"].session.save())

    me = await d["c"].get_me()
    acc = {
        "id": me.id,
        "stt": len(ACCS) + 1,
        "client": d["c"],
        "name": me.first_name,
        "last": None
    }
    ACCS[me.id] = acc
    setup_grabber(acc)

    await e.respond("✅ Acc OK")
    del PENDING_LOGIN[e.sender_id]

# ===== ĐẬP HỘP – FIX CHUẨN =====
def setup_grabber(acc):
    client = acc["client"]

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if not ev.reply_markup:
            return

        btn = None
        for r in ev.reply_markup.rows:
            for b in r.buttons:
                if b.text and any(x in b.text.lower() for x in ["đập", "hộp"]):
                    btn = b
                    break
        if not btn:
            return

        await asyncio.sleep(random.uniform(0.2, 0.5))
        await ev.click()
        await asyncio.sleep(2)

        msgs = await client.get_messages(BOT_GAME, limit=1)
        if not msgs or not msgs[0].message:
            return

        m = re.search(r"([A-Z0-9]{6,})", msgs[0].message)
        if not m:
            return

        code = m.group(1)
        uid = str(acc["id"])
        CODES_DB.setdefault(uid, [])
        if code in CODES_DB[uid]:
            return

        CODES_DB[uid].append(code)
        save_codes()

        global TOTAL_CODE
        TOTAL_CODE += 1

        await admin.send_message(
            ADMIN_ID,
            f"🎁 CODE MỚI\nAcc {acc['stt']} ({acc['name']})\nCode: {code}"
        )

# ===== MAIN =====
async def main():
    global CODES_DB, TOTAL_CODE

    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, encoding="utf-8") as f:
            CODES_DB = json.load(f)
            TOTAL_CODE = sum(len(v) for v in CODES_DB.values())

    await admin.start(bot_token=BOT_TOKEN)

    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, encoding="utf-8") as f:
            for i, s in enumerate(f.read().splitlines(), 1):
                if not s.strip(): continue
                c = TelegramClient(StringSession(s), API_ID, API_HASH)
                await c.connect()
                if await c.is_user_authorized():
                    me = await c.get_me()
                    acc = {
                        "id": me.id,
                        "stt": i,
                        "client": c,
                        "name": me.first_name,
                        "last": None
                    }
                    ACCS[me.id] = acc
                    setup_grabber(acc)

    await admin.run_until_disconnected()

asyncio.run(main())
