import asyncio, random, re, os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# ====== CẤU HÌNH ======
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8492633588:AAGSoL3wMHq8HOD2llLmbp6gdfaAwOqjJvo'

GAME_BOT = 'xocdia88_bot_uytin_bot'
LOG_GROUP = -1002984339626
SESSION_FILE = 'sessions.txt'

# ====== WEB KEEP ALIVE ======
app = Flask(__name__)
@app.route('/')
def home():
    return "SYSTEM ONLINE"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()

# ====== BIẾN HỆ THỐNG ======
clients = {}
pending_login = {}
recent_codes = set()
total_codes = 0

# ====== LƯU SESSION ======
def save_session(s):
    if not os.path.exists(SESSION_FILE):
        open(SESSION_FILE, 'w').close()
    with open(SESSION_FILE, 'r+') as f:
        if s not in f.read():
            f.write(s + '\n')

# ====== LOGIC ĐẬP HỘP AN TOÀN ======
async def auto_grab(client, name, admin_bot):
    delay_min = random.randint(3, 6)
    delay_max = random.randint(10, 15)

    @client.on(events.NewMessage(chats=GAME_BOT))
    async def handler(e):
        if not e.reply_markup:
            return

        for row in e.reply_markup.rows:
            for btn in row.buttons:
                if any(x in btn.text.lower() for x in ['đập', 'hộp', 'mở']):
                    wait = random.uniform(delay_min, delay_max)
                    await asyncio.sleep(wait)

                    try:
                        await e.click(btn)
                        await asyncio.sleep(1)

                        msg = (await client.get_messages(GAME_BOT, limit=1))[0]
                        if not msg.message:
                            return

                        m = re.search(r'[A-Z0-9]{8,15}', msg.message)
                        if not m:
                            return

                        code = m.group()
                        if code in recent_codes:
                            return

                        recent_codes.add(code)
                        global total_codes
                        total_codes += 1

                        await admin_bot.send_message(
                            LOG_GROUP,
                            f"🎁 HÚP MÃ\n"
                            f"👤 Acc: {name}\n"
                            f"⏱ Delay: {round(wait,1)}s\n"
                            f"📩 Code: `{code}`"
                        )

                        await asyncio.sleep(60)
                        recent_codes.discard(code)

                    except:
                        pass

# ====== MAIN ======
async def main():
    admin = TelegramClient('admin', API_ID, API_HASH)
    await admin.start(bot_token=BOT_TOKEN)

    # HỒI SINH SESSION
    if os.path.exists(SESSION_FILE):
        for s in open(SESSION_FILE).read().splitlines():
            try:
                c = TelegramClient(StringSession(s), API_ID, API_HASH)
                await c.connect()
                if await c.is_user_authorized():
                    me = await c.get_me()
                    clients[me.id] = c
                    asyncio.create_task(auto_grab(c, me.first_name, admin))
            except:
                pass

    def menu():
        return [
            [Button.inline("➕ Thêm acc", b"add")],
            [Button.inline("📑 Acc đang chạy", b"list")],
            [Button.inline("📊 Thống kê", b"stat")]
        ]

    @admin.on(events.NewMessage(pattern='/start'))
    async def start(e):
        await e.respond(
            f"🤖 BOT ĐẬP HỘP\n"
            f"👥 Acc: {len(clients)}\n"
            f"🎁 Tổng mã: {total_codes}",
            buttons=menu()
        )

    @admin.on(events.CallbackQuery)
    async def cb(e):
        if e.data == b'list':
            text = "📑 ACC ONLINE:\n"
            for i, c in enumerate(clients.values(), 1):
                me = await c.get_me()
                text += f"{i}. {me.first_name}\n"
            await e.edit(text, buttons=menu())

        if e.data == b'stat':
            await e.edit(
                f"📊 THỐNG KÊ\n"
                f"👥 Acc: {len(clients)}\n"
                f"🎁 Mã: {total_codes}",
                buttons=menu()
            )

        if e.data == b'add':
            await e.edit(
                "📱 Thêm acc\n"
                "Gõ: `/login 84xxxx`",
                buttons=menu()
            )

    @admin.on(events.NewMessage(pattern='/login'))
    async def login(e):
        phone = ''.join(filter(str.isdigit, e.text))
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        await c.connect()
        sent = await c.send_code_request(phone)
        pending_login[e.sender_id] = (c, phone, sent.phone_code_hash)
        await e.reply("📩 Nhập OTP: `/otp 12345`")

    @admin.on(events.NewMessage(pattern='/otp'))
    async def otp(e):
        if e.sender_id not in pending_login:
            return
        c, phone, h = pending_login[e.sender_id]
        code = ''.join(filter(str.isdigit, e.text))
        await c.sign_in(phone, code, phone_code_hash=h)

        save_session(c.session.save())
        me = await c.get_me()
        clients[me.id] = c
        asyncio.create_task(auto_grab(c, me.first_name, admin))
        await e.reply(f"✅ Đã thêm acc {me.first_name}")

    await admin.run_until_disconnected()

asyncio.run(main())
