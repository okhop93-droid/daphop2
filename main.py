import asyncio, random, re, os, json
from datetime import datetime
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
LOG_GROUP = -1001234567890   # nhóm nhận log code
SESSION_FILE = "sessions.txt"
CODES_FILE = "codes.json"

CHECK_INTERVAL = 60  # check acc mỗi phút

# ===== FLASK KEEP ALIVE =====
app = Flask(__name__)
@app.route("/")
def home():
    return "BOT ONLINE"

# ===== STATE =====
ACCS = {}       # acc_id -> info
TOTAL_CODE = 0

# ===== LOAD CODES CŨ =====
if os.path.exists(CODES_FILE):
    with open(CODES_FILE, "r") as f:
        CODES_DB = json.load(f)
else:
    CODES_DB = {}  # acc_id -> list of codes

def save_codes():
    with open(CODES_FILE, "w") as f:
        json.dump(CODES_DB, f, indent=2)

# ===== TIME CHECK =====
def in_time():
    h = datetime.now().hour + datetime.now().minute / 60
    return (
        7 <= h <= 9.5 or
        11 <= h <= 14.5 or
        19 <= h <= 24
    )

def sleeping_time():
    h = datetime.now().hour
    return 2 <= h < 6

# ===== ADMIN BOT =====
admin = TelegramClient("admin", API_ID, API_HASH)

def menu():
    return [
        [Button.inline("📦 Acc", b"acc")],
        [Button.inline("➕ Nạp Acc", b"nạp_acc")],
        [Button.inline("📊 Thống kê", b"stat")],
        [Button.inline("♻️ Restart", b"restart")]
    ]

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

    elif e.data == b"stat":
        await e.edit(
            f"📊 THỐNG KÊ\n🎁 Tổng mã: {TOTAL_CODE}",
            buttons=[[Button.inline("⬅️ Back", b"back")]]
        )

    elif e.data == b"restart":
        await e.edit("♻️ Restart...")
        os._exit(0)

    elif e.data == b"nạp_acc":
        await e.edit("📩 Gửi StringSession của acc để nạp:", buttons=[[Button.inline("⬅️ Back", b"back")]])
        @admin.on(events.NewMessage(from_users=e.sender_id))
        async def add_acc_msg(ev2):
            s = ev2.message.strip()
            try:
                c = TelegramClient(StringSession(s), API_ID, API_HASH)
                await c.connect()
                if not await c.is_user_authorized():
                    await ev2.reply("❌ Acc chưa login hoặc session sai!")
                    return
                me = await c.get_me()
                # lưu session vào file
                with open(SESSION_FILE, "a") as f:
                    f.write(s + "\n")
                # thêm vào ACCS
                ACCS[me.id] = {
                    "client": c,
                    "name": me.first_name,
                    "id": me.id,
                    "status": "ONLINE",
                    "last": None
                }
                asyncio.create_task(grab_loop(ACCS[me.id]))
                await ev2.reply(f"✅ Thêm acc {me.first_name} thành công!")
            except Exception as ex:
                await ev2.reply(f"❌ Lỗi: {ex}")

    elif e.data == b"back":
        await e.edit("🤖 MENU", buttons=menu())

# ===== HELPER NOTIFY =====
async def notify_admin(acc):
    if admin.is_connected:
        await admin.send_message(
            LOG_GROUP,
            f"⚠️ ACC `{acc['name']}` hiện trạng thái: {acc['status']}"
        )

# ===== GRAB HỘP =====
async def grab_loop(acc):
    global TOTAL_CODE
    client = acc["client"]

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if sleeping_time(): return
        if not in_time(): return
        if not ev.message: return

        btn = None
        if ev.reply_markup:
            btn = next(
                (b for r in ev.reply_markup.rows for b in r.buttons
                 if any(x in b.text.lower() for x in ["đập", "hộp", "mở"])),
                None
            )
        if btn:
            try:
                await asyncio.sleep(random.uniform(0.3, 1.2))
                await ev.click()  # nhấn 1 lần
                await asyncio.sleep(1.2)

                msg = await client.get_messages(BOT_GAME, limit=1)
                if msg and msg[0].message:
                    m = re.search(r"Mã code của bạn là:\s*([A-Z0-9]+)", msg[0].message, re.I)
                    if m:
                        code = m.group(1)
                        acc_id = str(acc["id"])

                        if acc_id not in CODES_DB:
                            CODES_DB[acc_id] = []

                        if code not in CODES_DB[acc_id]:
                            CODES_DB[acc_id].append(code)
                            save_codes()
                            TOTAL_CODE += 1

                            if LOG_GROUP:
                                await admin.send_message(
                                    LOG_GROUP,
                                    f"💌 ACC: {acc['name']}\n🎁 CODE: `{code}`"
                                )
                            acc["last"] = code

                acc["status"] = "ONLINE"

            except FloodWaitError:
                acc["status"] = "FLOOD"
            except:
                acc["status"] = "ERROR"

# ===== WATCHER ACC =====
async def acc_watcher():
    while True:
        for acc in ACCS.values():
            client = acc["client"]
            prev_status = acc["status"]
            try:
                if not await client.is_user_authorized():
                    acc["status"] = "OFFLINE"
                else:
                    acc["status"] = "ONLINE"
            except FloodWaitError:
                acc["status"] = "FLOOD"
            except:
                acc["status"] = "ERROR"

            if acc["status"] != prev_status:
                await notify_admin(acc)

        await asyncio.sleep(CHECK_INTERVAL)

# ===== LOAD ACC =====
async def load_accounts():
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
                    "client": c,
                    "name": me.first_name,
                    "id": me.id,
                    "status": "ONLINE",
                    "last": None
                }
                asyncio.create_task(grab_loop(ACCS[me.id]))
            except:
                continue

# ===== MAIN =====
async def main():
    await admin.start(bot_token=BOT_TOKEN)
    await load_accounts()
    asyncio.create_task(acc_watcher())
    await admin.run_until_disconnected()

# ===== RUN =====
if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()
    asyncio.run(main())
