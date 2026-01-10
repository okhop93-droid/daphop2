import asyncio, os
from telethon import TelegramClient, Button
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread
from worker import worker_loop

# ===== CONFIG =====
API_ID = 36437338
API_HASH = "API_HASH"
BOT_TOKEN = "BOT_TOKEN"
SESSION_FILE = "sessions.txt"
BOT_GAME = "xocdia88_bot_uytin_bot"

# ===== STATE =====
ACCOUNTS = []  # mỗi item: {"id", "client", "name", "enable", "task", "bot_game"}

# ===== FLASK =====
app = Flask(__name__)
@app.route("/")
def home():
    return "SERVICE ONLINE"

# ===== UTIL =====
def save_session(sess):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        if sess not in f.read():
            f.write(sess + "\n")

# ===== ADMIN BOT =====
bot = TelegramClient("admin", API_ID, API_HASH)

def menu():
    return [
        [Button.inline("➕ Nạp Acc", b"add")],
        [Button.inline("📦 Danh sách Acc", b"list")],
        [Button.inline("♻️ Restart", b"restart")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    await e.respond(f"🤖 BOT DỊCH VỤ\n📦 Acc: {len(ACCOUNTS)}", buttons=menu())

# ===== CALLBACK =====
@bot.on(events.CallbackQuery)
async def cb(e):
    uid = e.sender_id

    if e.data == b"add":
        await e.edit("➕ NẠP ACC\nGửi SESSION", buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"list":
        txt = "📦 DANH SÁCH ACC\n"
        for acc in ACCOUNTS:
            txt += f"- {acc['name']} | enable: {acc['enable']}\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"restart":
        await e.edit("♻️ Restarting...")
        os._exit(0)

    elif e.data == b"back":
        await e.edit("🤖 MENU", buttons=menu())

# ===== NẠP ACC =====
@bot.on(events.NewMessage)
async def on_message(e):
    if not e.is_private: return
    lines = e.text.strip().splitlines()
    ok = 0

    for line in lines:
        parts = line.split("|") if "|" in line else [line]
        for sess in parts:
            try:
                client = TelegramClient(StringSession(sess.strip()), API_ID, API_HASH)
                await client.connect()
                if not await client.is_user_authorized():
                    continue
                me = await client.get_me()
                acc = {
                    "id": me.id,
                    "name": me.first_name,
                    "client": client,
                    "enable": True,
                    "task": None,
                    "bot_game": BOT_GAME,
                    "last_code": None
                }
                acc["task"] = asyncio.create_task(worker_loop(acc))
                ACCOUNTS.append(acc)
                save_session(sess.strip())
                ok += 1
            except:
                continue

    await e.respond(f"✅ Đã nạp {ok} acc")

# ===== START =====
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            for s in f:
                s = s.strip()
                if not s: continue
                client = TelegramClient(StringSession(s), API_ID, API_HASH)
                await client.connect()
                if not await client.is_user_authorized(): continue
                me = await client.get_me()
                acc = {
                    "id": me.id,
                    "name": me.first_name,
                    "client": client,
                    "enable": True,
                    "task": asyncio.create_task(worker_loop({
                        "client": client,
                        "name": me.first_name,
                        "enable": True,
                        "bot_game": BOT_GAME,
                        "last_code": None
                    })),
                    "bot_game": BOT_GAME,
                    "last_code": None
                }
                ACCOUNTS.append(acc)

    await bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()
    asyncio.run(main())
