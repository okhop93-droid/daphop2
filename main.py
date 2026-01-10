import asyncio, os, random, json
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# ---------------- CONFIG ----------------
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8028025981:AAGJNsyU1NoN1YFTeSHmPA0aXEFDeOnCN4M'
TARGET_BOT = 'xocdia88_bot_uytin_bot'
GR_LOG = -1001234567890  # group log admin

SESSIONS_FILE = "sessions.json"
MAX_BOX_PER_DAY = 50
CHECK_INTERVAL = 600      # 10 phút
BACKUP_INTERVAL = 3600    # 1 giờ
TEST_INTERVAL = 3600      # 1 giờ

ACTIVE_HOURS = [(7, 9.5), (11, 14.5), (19, 24)]
SLEEP_HOURS = (2, 6)
# ----------------------------------------

os.makedirs("data", exist_ok=True)
clients = []
acc_box_count = {}
bot_active = True
box_active = True

# ---------------- UTILS -----------------
def now_hour(): 
    return datetime.now().hour + datetime.now().minute/60

def in_active_time(): 
    h = now_hour()
    return any(start <= h <= end for start,end in ACTIVE_HOURS)

def in_sleep_time():
    h = now_hour()
    return SLEEP_HOURS[0] <= h < SLEEP_HOURS[1]

def save_code(code):
    with open("data/codes.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | {code}\n")

def log_event(acc_name, event_type, extra=""):
    with open("data/log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | {acc_name} | {event_type} | {extra}\n")

async def send_group_log(bot_admin, message):
    try:
        await bot_admin.send_message(GR_LOG, message)
    except:
        pass

# ---------------- SESSIONS -----------------
def load_accounts():
    if not os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            f.write("[]")
        return []
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = f.read().strip()
            if not data:
                return []
            return json.loads(data)
    except json.JSONDecodeError:
        print("❌ Lỗi JSON, reset file sessions.json")
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            f.write("[]")
        return []

def save_accounts(data):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def can_open_box(acc_id):
    today = datetime.now().strftime("%Y-%m-%d")
    if acc_id not in acc_box_count or acc_box_count[acc_id]["date"] != today:
        acc_box_count[acc_id] = {"date": today, "count": 0}
    return acc_box_count[acc_id]["count"] < MAX_BOX_PER_DAY

def add_box_count(acc_id):
    acc_box_count[acc_id]["count"] += 1

# ---------------- ACCOUNT BOT -----------------
async def start_account(session_name, bot_admin):
    client = TelegramClient(StringSession(session_name), API_ID, API_HASH)
    await client.start()
    clients.append(client)

    try:
        me = await client.get_me()
        await send_group_log(bot_admin, f"✅ Acc ONLINE: {me.first_name}")
    except:
        await send_group_log(bot_admin, f"❌ Acc OFFLINE: {session_name}")
        return

    @client.on(events.NewMessage(from_users=TARGET_BOT))
    async def grabber(ev):
        try:
            me = await client.get_me()
            text = ev.raw_text.lower()
        except: return

        if ("hộp" in text or "đập" in text or "mở" in text) and bot_active and box_active:
            if in_sleep_time() or not in_active_time():
                log_event(me.first_name,"SKIP_OUT_OF_TIME",text)
                await send_group_log(bot_admin,f"{me.first_name} SKIP_OUT_OF_TIME")
                return
            if not can_open_box(me.id):
                log_event(me.first_name,"SKIP_MAX_BOX",text)
                await send_group_log(bot_admin,f"{me.first_name} SKIP_MAX_BOX")
                return
            delay = random.uniform(0.5,2)
            await asyncio.sleep(delay)
            try:
                await ev.click()
                add_box_count(me.id)
                log_event(me.first_name,"OPEN_BOX",text)
                save_code(text)
                await send_group_log(bot_admin,f"🎁 {me.first_name} mở hộp")
                await asyncio.sleep(1)
            except Exception as ex:
                log_event(me.first_name,"ERROR_CLICK",text)
                await send_group_log(bot_admin,f"❌ {me.first_name} ERROR_CLICK: {ex}")

# ---------------- ADMIN BOT -----------------
async def admin_bot():
    bot = TelegramClient('admin_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    def menu():
        return [
            [Button.inline("📑 Danh sách acc", b"list_acc"),
             Button.inline("📊 Thống kê", b"stats")],
            [Button.inline("⏸️ Pause bot", b"pause"),
             Button.inline("▶️ Resume bot", b"resume")],
            [Button.inline("🔘 Toggle hộp", b"toggle_box"),
             Button.inline("🧪 Test acc", b"test_acc")]
        ]

    @bot.on(events.NewMessage(pattern='/start'))
    async def start_cmd(e):
        await e.respond("💎 HỆ THỐNG QUẢN TRỊ BOT 💎", buttons=menu())

    @bot.on(events.CallbackQuery)
    async def cb_handler(e):
        global bot_active, box_active
        data = e.data.decode('utf-8')

        if data == "list_acc":
            text = "📑 **DANH SÁCH ACC**\n"
            if not clients:
                text += "(Trống)"
            else:
                for i,c in enumerate(clients,1):
                    me = await c.get_me()
                    text += f"{i}. {me.first_name}\n"
            await e.edit(text, buttons=[Button.inline("⬅️ Quay lại", b"back")])

        elif data == "stats":
            text = f"📊 **THỐNG KÊ**\n- Acc online: {len(clients)}\n"
            total = sum(v["count"] for v in acc_box_count.values())
            text += f"- Tổng hộp hôm nay: {total}"
            await e.edit(text, buttons=[Button.inline("⬅️ Quay lại", b"back")])

        elif data == "pause":
            bot_active = False
            await e.answer("⏸️ Bot tạm dừng toàn bộ")

        elif data == "resume":
            bot_active = True
            await e.answer("▶️ Bot chạy lại")

        elif data == "toggle_box":
            box_active = not box_active
            await e.answer(f"🔘 Chức năng bấm hộp {'BẬT' if box_active else 'TẮT'}")

        elif data == "test_acc":
            text = "🧪 Kết quả test acc:\n"
            for c in clients[:]:
                try:
                    me = await c.get_me()
                    text += f"✅ {me.first_name} ONLINE\n"
                except Exception as ex:
                    text += f"❌ Acc OFFLINE | {ex}\n"
            await e.edit(text, buttons=[Button.inline("⬅️ Quay lại", b"back")])

        elif data == "back":
            await e.edit("💎 HỆ THỐNG QUẢN TRỊ BOT 💎", buttons=menu())

    return bot

# ---------------- CHECK ACC & BACKUP -----------------
async def check_acc(bot_admin):
    while True:
        for c in clients[:]:
            try:
                await c.get_me()
            except Exception as ex:
                me_name = getattr(c, "first_name", "Unknown")
                log_event("SYSTEM","ACC_FAIL",str(c))
                await send_group_log(bot_admin,f"❌ Acc OFFLINE: {me_name} | {ex}")
                clients.remove(c)
        await asyncio.sleep(CHECK_INTERVAL)

async def test_all_acc(bot_admin):
    while True:
        for c in clients[:]:
            try:
                me = await c.get_me()
                await send_group_log(bot_admin, f"🧪 Test ONLINE: {me.first_name}")
            except Exception as ex:
                await send_group_log(bot_admin, f"🧪 Test OFFLINE: {ex}")
        await asyncio.sleep(TEST_INTERVAL)

async def backup_sessions():
    while True:
        for c in clients:
            try:
                s = c.session.save()
                with open("data/sessions_backup.txt","a",encoding="utf-8") as f:
                    f.write(s+"\n")
            except: pass
        await asyncio.sleep(BACKUP_INTERVAL)

# ---------------- MAIN -----------------
async def main():
    bot_admin = await admin_bot()
    accs = load_accounts()
    for s in accs:
        await start_account(s, bot_admin)

    asyncio.create_task(check_acc(bot_admin))
    asyncio.create_task(backup_sessions())
    asyncio.create_task(test_all_acc(bot_admin))

    print("BOT RUNNING")
    await asyncio.gather(*[c.run_until_disconnected() for c in clients], bot_admin.run_until_disconnected())

if __name__ == "__main__":
    asyncio.run(main())
