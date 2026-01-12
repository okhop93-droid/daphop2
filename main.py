import asyncio, random, re, os, json
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events, Button, functions
from telethon.sessions import StringSession

# ===== CẤU HÌNH =====
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8028025981:AAG4pVK8CCHNh0Kbz0h4k5bqVvPRn_DhG_E"
BOT_GAME = "xocdia88_bot_uytin_bot"
LOG_GROUP = -1002984339626  # ID nhóm nhận code
SESSION_FILE = "sessions.txt"
CODES_FILE = "codes.json"

# ===== KEEP ALIVE =====
app = Flask(__name__)
@app.route("/")
def home(): return "BOT ONLINE"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()

ACCS = {}           
TOTAL_CODE = 0
CODES_DB = {}       
PENDING_LOGIN = {}  

# ===== QUẢN LÝ FILE =====
def save_session(sess):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        if sess not in f.read():
            f.write(sess + "\n")

def save_codes():
    with open(CODES_FILE, "w") as f:
        json.dump(CODES_DB, f, indent=2)

# ===== LUỒNG ĐẬP HỘP & TỰ GỬI VÀO NHÓM =====
async def grab_loop(acc):
    global TOTAL_CODE
    client = acc["client"] 

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if not ev.reply_markup: return
        btn = next((b for r in ev.reply_markup.rows for b in r.buttons 
                    if any(x in b.text.lower() for x in ["đập","hộp"])), None)
        if not btn: return

        try:
            # Click đập hộp
            await asyncio.sleep(random.uniform(0.1, 0.4))
            await ev.click()
            print(f"--- [TK {acc['stt']}] Đã nhấn đập hộp! ---")
            
            # Đợi tin nhắn code
            await asyncio.sleep(2.5) 
            msgs = await client.get_messages(BOT_GAME, limit=1)
            
            if msgs and msgs[0].message:
                raw_text = msgs[0].message
                # Tìm mã code
                match = re.search(r'là:\s*([A-Z0-9]+)', raw_text)
                
                if match or any(word in raw_text for word in ["Code", "Mã", "quà"]):
                    gift_code = match.group(1) if match else "Lượm được quà!"
                    
                    if gift_code != acc.get("last"):
                        acc["last"] = gift_code
                        TOTAL_CODE += 1
                        
                        # --- TÀI KHOẢN TỰ GỬI VÀO NHÓM ---
                        try:
                            msg_to_group = f"🎁 [TK {acc['stt']} - {acc['name']}] ĐẬP ĐƯỢC QUÀ:\n\n{raw_text}"
                            await client.send_message(LOG_GROUP, msg_to_group)
                            print(f"--- [TK {acc['stt']}] Đã gửi code vào nhóm ---")
                        except Exception as e:
                            # Nếu chưa vào nhóm thì tự Join rồi gửi lại
                            try:
                                await client(functions.channels.JoinChannelRequest(channel=LOG_GROUP))
                                await asyncio.sleep(1)
                                await client.send_message(LOG_GROUP, msg_to_group)
                            except: print(f"❌ TK {acc['stt']} không thể gửi tin vào nhóm.")
                        
                        CODES_DB[str(acc["id"])] = gift_code
                        save_codes()
        except Exception as e:
            print(f"❌ Lỗi TK {acc['stt']}: {e}")

# ===== ADMIN BOT (Dùng để quản lý và nạp thêm acc) =====
admin = TelegramClient("admin_bot", API_ID, API_HASH)

@admin.on(events.NewMessage(pattern="/start"))
async def start(e):
    if e.sender_id != 7816353760: return
    btns = [
        [Button.inline("📦 Danh Sách Acc", b"acc"), Button.inline("📊 Thống kê", b"stat")],
        [Button.inline("➕ Nạp Acc", b"add")]
    ]
    await e.respond(f"🤖 **HỆ THỐNG ĐẬP HỘP**\n📦 Đang chạy: `{len(ACCS)}` Acc\n🎁 Tổng mã: `{TOTAL_CODE}`", buttons=btns)

@admin.on(events.CallbackQuery)
async def cb(e):
    if e.data == b"acc":
        txt = "📑 **DANH SÁCH TÀI KHOẢN:**\n"
        for a in ACCS.values():
            txt += f"• **STT {a['stt']}**: {a['name']} (Online)\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])
    elif e.data == b"back":
        await start(e)

# ===== XỬ LÝ NẠP ACC MỚI =====
@admin.on(events.NewMessage(pattern="/login"))
async def login_handler(e):
    try:
        phone = e.text.split(" ", 1)[1]
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        await c.connect()
        sent = await c.send_code_request(phone)
        PENDING_LOGIN[e.sender_id] = {"c": c, "p": phone, "h": sent.phone_code_hash}
        await e.respond(f"📩 Nhập OTP cho `+{phone}` bằng lệnh: `/otp <mã>`")
    except: await e.respond("❌ Lỗi. Cú pháp: `/login 84xxx`")

@admin.on(events.NewMessage(pattern="/otp"))
async def otp_handler(e):
    data = PENDING_LOGIN.get(e.sender_id)
    if not data: return
    try:
        code = "".join(filter(str.isdigit, e.text))
        await data["c"].sign_in(data["p"], code, phone_code_hash=data["h"])
        save_session(data["c"].session.save())
        me = await data["c"].get_me()
        new_stt = len(ACCS) + 1
        ACCS[me.id] = {"id": me.id, "stt": new_stt, "client": data["c"], "name": me.first_name, "last": None}
        asyncio.create_task(grab_loop(ACCS[me.id]))
        await e.respond(f"✅ Đã nạp xong TK {new_stt}: {me.first_name}")
    except Exception as ex: await e.respond(f"❌ Lỗi: {ex}")

# ===== KHỞI CHẠY =====
async def main():
    if os.path.exists(CODES_FILE):
        global CODES_DB, TOTAL_CODE
        with open(CODES_FILE) as f: 
            CODES_DB = json.load(f)
            TOTAL_CODE = len(CODES_DB)

    await admin.start(bot_token=BOT_TOKEN)
    
    # Load lại các Session cũ (bao gồm cả 10 acc cứng nếu bạn đã nạp vào file)
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            for i, s in enumerate(f.read().splitlines(), 1):
                if not s.strip(): continue
                try:
                    c = TelegramClient(StringSession(s), API_ID, API_HASH)
                    await c.connect()
                    if await c.is_user_authorized():
                        me = await c.get_me()
                        ACCS[me.id] = {"id": me.id, "stt": i, "client": c, "name": me.first_name, "last": None}
                        asyncio.create_task(grab_loop(ACCS[me.id]))
                        print(f"✅ Tài khoản {i} ({me.first_name}) đã Online")
                except: continue
    
    await admin.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
    
