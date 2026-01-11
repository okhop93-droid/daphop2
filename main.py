import asyncio, random, re, os, json
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ===== CONFIG (THAY TẠI ĐÂY) =====
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8028025981:AAG4pVK8CCHNh0Kbz0h4k5bqVvPRn_DhG_E"
BOT_GAME = "xocdia88_bot_uytin_bot"
SESSION_FILE = "sessions.txt"
CODES_FILE = "codes.json"
LOG_GROUP = -1002234567890  # <--- THAY ID NHÓM CỦA BẠN VÀO ĐÂY

# ===== FLASK KEEP ALIVE =====
app = Flask(__name__)
@app.route("/")
def home(): return "BOT ONLINE"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# ===== STATE =====
ACCS = {}           
TOTAL_CODE = 0
CODES_DB = {}       
PENDING_LOGIN = {}  

# ===== ADMIN BOT =====
admin = TelegramClient("admin", API_ID, API_HASH)

def menu():
    return [
        [Button.inline("📦 Danh Sách TK", b"acc")],
        [Button.inline("➕ Nạp Acc", b"add")],
        [Button.inline("🧪 Test Acc", b"test")],
        [Button.inline("📊 Thống kê", b"stat")],
        [Button.inline("♻️ Restart", b"restart")]
    ]

# ===== LƯU TRỮ =====
def save_session(sess):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        if sess not in f.read():
            f.write(sess + "\n")

def save_codes():
    with open(CODES_FILE, "w") as f:
        json.dump(CODES_DB, f, indent=2)

async def notify_admin(acc, msg=None):
    text = msg if msg else f"⚠️ **Tài khoản {acc['stt']}** ({acc['name']}): {acc['status']}"
    try:
        await admin.send_message(admin.me.id, text)
    except: pass

# ===== GRAB HỘP (ACC TỰ GỬI VÀO NHÓM) =====
async def grab_loop(acc):
    global TOTAL_CODE
    client = acc["client"]

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if not ev.reply_markup: return

        # Tìm nút đập hộp
        btn = next((b for r in ev.reply_markup.rows for b in r.buttons 
                    if any(x in b.text.lower() for x in ["đập","hộp"])), None)
        if not btn: return

        try:
            await asyncio.sleep(random.uniform(0.1, 0.4))
            await ev.click()
            await asyncio.sleep(2) # Chờ Bot Game nhả mã

            msgs = await client.get_messages(BOT_GAME, limit=1)
            if msgs and msgs[0].message:
                raw_text = msgs[0].message
                # Regex lấy mã đứng sau chữ "là:"
                match = re.search(r'là:\s*([A-Z0-9]+)', raw_text)
                
                if match:
                    gift_code = match.group(1)
                    if gift_code != acc.get("last"):
                        acc["last"] = gift_code
                        TOTAL_CODE += 1
                        
                        # --- GỬI VÀO NHÓM VỚI TÊN: TK 1, TK 2... ---
                        if LOG_GROUP:
                            msg_nhom = f"🎁 **Tài khoản {acc['stt']}** đã húp: `{gift_code}`"
                            try:
                                await client.send_message(LOG_GROUP, msg_nhom)
                            except: pass
                        
                        await notify_admin(acc, f"✅ **TK {acc['stt']}** vừa húp mã: `{gift_code}`")
                        CODES_DB[str(acc["id"])] = gift_code
                        save_codes()
        except Exception as e:
            print(f"❌ Lỗi TK {acc['stt']}: {e}")

# ===== LOAD ACC & ĐÁNH SỐ =====
async def load_accounts():
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE) as f:
            global CODES_DB
            CODES_DB = json.load(f)
            
    if not os.path.exists(SESSION_FILE): return

    with open(SESSION_FILE) as f:
        sessions = f.read().splitlines()
        
    for index, s in enumerate(sessions, start=1):
        s = s.strip()
        if not s: continue
        try:
            c = TelegramClient(StringSession(s), API_ID, API_HASH)
            await c.connect()
            if not await c.is_user_authorized(): continue

            me = await c.get_me()
            ACCS[me.id] = {
                "id": me.id,
                "stt": index, # Đánh số 1, 2, 3...
                "client": c,
                "name": me.first_name,
                "status": "ONLINE",
                "last": CODES_DB.get(str(me.id))
            }
            asyncio.create_task(grab_loop(ACCS[me.id]))
        except: continue

# ===== GIAO DIỆN ADMIN =====
@admin.on(events.NewMessage(pattern="/start"))
async def start(e):
    await e.respond(f"🤖 **BOT QUẢN LÝ ĐẬP HỘP**\n📦 Acc đang chạy: {len(ACCS)}\n🎁 Tổng húp: {TOTAL_CODE}", buttons=menu())

@admin.on(events.CallbackQuery)
async def cb(e):
    if e.data == b"acc":
        txt = "📦 **DANH SÁCH TÀI KHOẢN:**\n"
        for a in ACCS.values():
            txt += f"- **TK {a['stt']}**: {a['name']} (🟢 Online)\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])
    elif e.data == b"back":
        await e.edit("🤖 **MENU QUẢN LÝ**", buttons=menu())
    elif e.data == b"restart":
        await e.edit("♻️ Đang khởi động lại...")
        os._exit(0)

# ===== LOGIN THỦ CÔNG =====
@admin.on(events.NewMessage(pattern="/login"))
async def login_handler(e):
    try:
        phone = "".join(filter(str.isdigit,e.text.split(" ",1)[1]))
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        await c.connect()
        sent = await c.send_code_request(phone)
        PENDING_LOGIN[e.sender_id] = {"client":c,"phone":phone,"hash":sent.phone_code_hash}
        await e.respond(f"📩 OTP gửi tới `+{phone}`, nhập `/otp <mã>`")
    except: await e.respond("❌ Sai định dạng /login + SĐT")

@admin.on(events.NewMessage(pattern="/otp"))
async def otp_handler(e):
    data = PENDING_LOGIN.get(e.sender_id)
    if not data: return
    try:
        code = "".join(filter(str.isdigit, e.text))
        await data["client"].sign_in(data["phone"], code, phone_code_hash=data["hash"])
        save_session(data["client"].session.save())
        await e.respond("✅ Nạp thành công! Hãy nhấn `/restart` để bot nhận diện số thứ tự mới.")
    except Exception as ex: await e.respond(f"❌ Lỗi: {ex}")

async def main():
    await admin.start(bot_token=BOT_TOKEN)
    await load_accounts()
    await admin.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
            
