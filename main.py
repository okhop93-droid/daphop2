import asyncio, random, re, os
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# ================== CONFIG ==================
API_ID = int(os.getenv("API_ID", "36437338"))
API_HASH = os.getenv("API_HASH", "API_HASH_HERE")
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKEN_HERE")

BOT_GAME = "xocdia88_bot_uytin_bot"
GR_LOG = -1002984339626
SESSION_FILE = "database_sessions.txt"
# ============================================

# ================== WEB KEEP ALIVE ==================
app = Flask(__name__)
@app.route("/")
def home():
    return "SYSTEM ONLINE"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# ================== GLOBAL ==================
active_clients = {}
pending_auth = {}
recent_codes = set()
stat_counter = 0

# ================== UTILS ==================
def is_sleep_time():
    h = datetime.now().hour
    return 2 <= h < 6

def save_session(sess):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        if sess not in f.read():
            f.write(sess + "\n")

# ================== AUTO GRAB ==================
async def start_grabbing(client, acc_name, admin_bot):
    global stat_counter

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def grab(ev):
        if is_sleep_time():
            return

        if not ev.reply_markup:
            return

        btn = next(
            (
                b for r in ev.reply_markup.rows
                for b in r.buttons
                if any(x in (b.text or "").lower() for x in ["đập", "hộp", "mở"])
            ),
            None
        )

        if not btn:
            return

        await asyncio.sleep(random.uniform(3, 8))

        try:
            await ev.click()
            await asyncio.sleep(1.5)

            msg = (await client.get_messages(BOT_GAME, limit=1))[0]
            if not msg.message:
                return

            m = re.search(r"[A-Z0-9]{8,15}", msg.message)
            if not m:
                return

            code = m.group()
            if code in recent_codes:
                return

            recent_codes.add(code)
            stat_counter += 1

            await admin_bot.send_message(
                GR_LOG,
                f"🎁 **MỞ HỘP THÀNH CÔNG**\n"
                f"👤 Acc: `{acc_name}`\n"
                f"📩 Mã: `{code}`\n"
                f"📊 Tổng: `{stat_counter}`"
            )

            await asyncio.sleep(60)
            recent_codes.discard(code)

        except:
            pass

# ================== MAIN ==================
async def main():
    admin_bot = TelegramClient("admin", API_ID, API_HASH)
    await admin_bot.start(bot_token=BOT_TOKEN)

    # Hồi sinh acc
    if os.path.exists(SESSION_FILE):
        for s in open(SESSION_FILE).read().splitlines():
            try:
                c = TelegramClient(StringSession(s), API_ID, API_HASH)
                await c.connect()
                if await c.is_user_authorized():
                    me = await c.get_me()
                    active_clients[me.id] = c
                    asyncio.create_task(start_grabbing(c, me.first_name, admin_bot))
            except:
                pass

    # ================== UI ==================
    def menu():
        return [
            [Button.inline("➕ Nạp Acc", b"add"), Button.inline("📑 Acc Online", b"list")],
            [Button.inline("📊 Thống kê", b"stats")]
        ]

    @admin_bot.on(events.NewMessage(pattern="/start"))
    async def start(e):
        await e.respond(
            f"💎 **BOT MỞ HỘP**\n"
            f"📦 Acc online: `{len(active_clients)}`\n"
            f"🎁 Tổng mã: `{stat_counter}`",
            buttons=menu()
        )

    @admin_bot.on(events.CallbackQuery)
    async def cb(e):
        if e.data == b"list":
            txt = "📑 **ACC ONLINE**\n"
            for i, c in enumerate(active_clients.values(), 1):
                me = await c.get_me()
                txt += f"{i}. `{me.first_name}`\n"
            await e.edit(txt, buttons=menu())

        elif e.data == b"stats":
            await e.edit(
                f"📊 **THỐNG KÊ**\n"
                f"🎁 Mã: `{stat_counter}`\n"
                f"📦 Acc: `{len(active_clients)}`",
                buttons=menu()
            )

        elif e.data == b"add":
            await e.edit("Gửi: `/login 84xxxxxxxxx`")

    # ================== LOGIN ==================
    @admin_bot.on(events.NewMessage(pattern="/login"))
    async def login(e):
        phone = "".join(filter(str.isdigit, e.text))
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        await c.connect()
        r = await c.send_code_request(phone)
        pending_auth[e.sender_id] = (c, phone, r.phone_code_hash)
        await e.respond("📩 Nhập: `/otp 12345`")

    @admin_bot.on(events.NewMessage(pattern="/otp"))
    async def otp(e):
        if e.sender_id not in pending_auth:
            return
        c, phone, h = pending_auth.pop(e.sender_id)
        code = "".join(filter(str.isdigit, e.text))
        await c.sign_in(phone, code, phone_code_hash=h)
        save_session(c.session.save())
        me = await c.get_me()
        active_clients[me.id] = c
        asyncio.create_task(start_grabbing(c, me.first_name, admin_bot))
        await e.respond(f"✅ `{me.first_name}` đã online")

    await admin_bot.run_until_disconnected()

# ================== RUN ==================
if __name__ == "__main__":
    Thread(target=run_web).start()
    asyncio.run(main())
