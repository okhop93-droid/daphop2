import asyncio, random, re, os, json
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ===== CẤU HÌNH HỆ THỐNG =====
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8028025981:AAG4pVK8CCHNh0Kbz0h4k5bqVvPRn_DhG_E"
BOT_GAME = "xocdia88_bot_uytin_bot"
SESSION_FILE = "sessions.txt"
CODES_FILE = "codes.json"
LOG_GROUP = -1002234567890  # <--- THAY ID NHÓM CỦA BẠN VÀO ĐÂY

# ===== GIỮ BOT ONLINE (FLASK) =====
app = Flask(__name__)
@app.route("/")
def home(): return "🤖 SYSTEM ONLINE"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# ===== BIẾN HỆ THỐNG =====
ACCS = {}           
TOTAL_CODE = 0
CODES_DB = {}       
PENDING_LOGIN = {}  

# ===== QUẢN LÝ DỮ LIỆU =====
def save_session(sess):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        if sess not in f.read():
            f.write(sess + "\n")

def save_codes():
    with open(CODES_FILE, "w") as f:
        json.dump(CODES_DB, f, indent=2)

# ===== ADMIN BOT =====
admin = TelegramClient("admin", API_ID, API_HASH)

def menu():
    return [
        [Button.inline("📦 Danh Sách Acc", b"acc"), Button.inline("🧪 Test Acc", b"test")],
        [Button.inline("➕ Nạp Acc", b"add"), Button.inline("📊 Thống Kê", b"stat")],
        [Button.inline("📄 Xem Code", b"view_codes"), Button.inline("♻️ Restart", b"restart")]
    ]

async def notify_admin(msg):
    try:
        me = await admin.get_me()
        await admin.send_message(me.id, msg)
    except: pass

# ===== LOGIC GRAB HỘP (ACC TỰ GỬI VÀO NHÓM) =====
async def grab_loop(acc):
    global TOTAL_CODE
    client = acc["client"]

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if not ev.reply_markup: return

        # Tìm nút đập hộp dựa trên ảnh
        btn = next((b for r in ev.reply_markup.rows for b in r.buttons 
                    if any(x in b.text.lower() for x in ["đập","hộp"])), None)
        if not btn: return

        try:
            await asyncio.sleep(random.uniform(0.1, 0.5))
            await ev.click()
            await asyncio.sleep(2.5) # Chờ Bot Game nhả mã

            msgs = await client.get_messages(BOT_GAME, limit=1)
            if msgs and msgs[0].message:
                raw_text = msgs[0].message
                # Regex lấy mã chuẩn sau chữ "là:"
                match = re.search(r'là:\s*([A-Z0-9]+)', raw_text)
                
                if match:
                    gift_code = match.group(1)
                    if gift_code != acc.get("last"):
                        acc["last"] = gift_code
                        TOTAL_CODE += 1
                        
                        # --- ACC TỰ NHẮN VÀO NHÓM ---
                        if LOG_GROUP:
                            msg_nhom = f"🎁 **Tài khoản {acc['stt']}** húp được: `{gift_code}`"
                            try:
                                await client.send_message(LOG_GROUP, msg_nhom)
                            except: pass
                        
                        # Báo riêng cho chủ bot
                        await notify_admin(f"✅ **TK {acc['stt']}** đã húp mã: `{gift_code}`")
                        
                        # Lưu dữ liệu
                        CODES_DB[str(acc["id"])] = gift_code
                        save_codes()
        except Exception as e:
            print(f"❌ Lỗi TK {acc['stt']}: {e}")

# ===== TỰ ĐỘNG LOAD & ĐÁNH SỐ TÀI KHOẢN =====
async def load_accounts():
    global TOTAL_CODE, CODES_DB
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE) as f:
            CODES_DB = json.load(f)
            TOTAL_CODE = len(set(CODES_DB.values()))
            
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
                "stt": index, # Gán số thứ tự TK 1, TK 2...
                "client": c,
                "name": me.first_name,
                "status": "ONLINE 🟢",
                "last": CODES_DB.get(str(me.id))
            }
            asyncio.create_task(grab_loop(ACCS[me.id]))
        except: continue

# ===== XỬ LÝ GIAO DIỆN ADMIN =====
@admin.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    await e.respond(f"🤖 **HỆ THỐNG ĐANG TRỰC**\n━━━━━━━━━━━━━━\n📦 Đang chạy: `{len(ACCS)}` Acc\n🎁 Tổng mã: `{TOTAL_CODE}`", buttons=menu())

@admin.on(events.CallbackQuery)
async def cb_handler(e):
    if e.data == b"acc":
        txt = "📑 **DANH SÁCH TÀI KHOẢN:**\n"
        for a in ACCS.values():
            txt += f"• **TK {a['stt']}**: {a['name']} | {a['status']}\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])

    elif e.data == b"test":
        await e.edit("🧪 **ĐANG KIỂM TRA DÀN ACC...**")
        res = "🧪 **KẾT QUẢ TEST:**\n"
        for a in ACCS.values():
            try:
                if await a['client'].is_user_authorized(): a['status'] = "ONLINE 🟢"
                else: a['status'] = "OFFLINE 🔴"
            except: a['status'] = "LỖI ⚠️"
            res += f"• **TK {a['stt']}**: {a['status']}\n"
            await asyncio.sleep(0.5)
        await e.edit(res, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])

    elif e.data == b"stat":
        res = f"📊 **THỐNG KÊ CHI TIẾT**\n━━━━━━━━━━━━━━\n📦 Tổng Acc: `{len(ACCS)}`\n🎁 Tổng mã húp: `{TOTAL_CODE}`\n\n"
        for a in ACCS.values():
            res += f"• **TK {a['stt']}**: `{a.get('last') or 'Chưa có'}`\n"
        await e.edit(res, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])

    elif e.data == b"add":
        await e.edit("➕ **NẠP ACC MỚI**\n━━━━━━━━━━━━━━\nNhập lệnh: `/login SĐT` (Ví dụ: `/login 84123456789`)", buttons=[[Button.inline("⬅️ Quay lại", b"back")]])

    elif e.data == b"restart":
        await e.edit("♻️ **Hệ thống đang khởi động lại...**")
        os._exit(0)

    elif e.data == b"back":
        await e.edit(f"🤖 **MENU QUẢN LÝ**", buttons=menu())

# ===== LOGIC LOGIN =====
@admin.on(events.NewMessage(pattern="/login"))
async def login_handler(e):
    try:
        phone = "".join(filter(str.isdigit, e.text.split(" ", 1)[1]))
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        await c.connect()
        sent = await c.send_code_request(phone)
        PENDING_LOGIN[e.sender_id] = {"c": c, "p": phone, "h": sent.phone_code_hash}
        await e.respond(f"📩 OTP đã gửi tới `+{phone}`. Nhập `/otp <mã>`")
    except: await e.respond("❌ Định dạng: `/login 84...`")

@admin.on(events.NewMessage(pattern="/otp"))
async def otp_handler(e):
    data = PENDING_LOGIN.get(e.sender_id)
    if not data: return
    try:
        code = "".join(filter(str.isdigit, e.text))
        await data["c"].sign_in(data["p"], code, phone_code_hash=data["h"])
        save_session(data["c"].session.save())
        await e.respond("✅ **Thành công!** Hãy nhấn **♻️ Restart** để cập nhật số thứ tự.")
    except Exception as ex: await e.respond(f"❌ Lỗi: {ex}")

async def main():
    await admin.start(bot_token=BOT_TOKEN)
    await load_accounts()
    await admin.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
            
