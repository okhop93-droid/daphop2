from telethon import TelegramClient, events
from telethon.sessions import StringSession
import sqlite3, datetime, asyncio
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8492633588:AAGSoL3wMHq8HOD2llLmbp6gdfaAwOqjJvo'

# --- KHỞI TẠO DATABASE LƯU TRỮ ---
def init_db():
    conn = sqlite3.connect('manager.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts 
                      (phone TEXT PRIMARY KEY, session TEXT, status TEXT, last_update TEXT)''')
    conn.commit()
    conn.close()

init_db()

bot = TelegramClient('bot_manager', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
login_data = {}

# Web server để Render không bị tắt
app = Flask('')
@app.route('/')
def home(): return "BOT_MANAGER_ACTIVE"

@bot.on(events.NewMessage(pattern='/start'))
async def start(e):
    await e.reply("🗄️ **HỆ THỐNG QUẢN LÝ ACC VĨNH VIỄN**\n\nCommands:\n- `/login [SĐT]`: Thêm/Reset Acc\n- `/list`: Xem danh sách Acc đang lưu\n- `/status`: Kiểm tra tình trạng lỗi")

@bot.on(events.NewMessage(pattern='/login'))
async def login(e):
    parts = e.text.split(' ')
    if len(parts) < 2: return await e.reply("Sai cú pháp. VD: `/login +84123...`")
    
    phone = parts[1]
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    
    sent = await client.send_code_request(phone)
    login_data[e.sender_id] = {'phone': phone, 'hash': sent.phone_code_hash, 'client': client}
    await e.reply(f"📩 Mã OTP đã gửi tới `{phone}`. Hãy nhập OTP để lưu Session.")

@bot.on(events.NewMessage)
async def handle_otp(e):
    if e.sender_id in login_data and e.text.isdigit():
        data = login_data[e.sender_id]
        client = data['client']
        try:
            await client.sign_in(data['phone'], e.text, phone_code_hash=data['hash'])
            new_session = client.session.save()
            
            # Lưu vào Database vĩnh viễn
            conn = sqlite3.connect('manager.db')
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO accounts VALUES (?, ?, ?, ?)",
                           (data['phone'], new_session, 'LIVE', str(datetime.datetime.now())))
            conn.commit()
            conn.close()
            
            await e.reply(f"✅ **ĐÃ LƯU TRỮ VĨNH VIỄN!**\nAcc: `{data['phone']}`\nSession: `{new_session}`")
            del login_data[e.sender_id]
        except Exception as ex:
            await e.reply(f"❌ Lỗi login: {ex}")

@bot.on(events.NewMessage(pattern='/list'))
async def list_acc(e):
    conn = sqlite3.connect('manager.db')
    cursor = conn.cursor()
    cursor.execute("SELECT phone, status, last_update FROM accounts")
    rows = cursor.fetchall()
    msg = "📊 **DANH SÁCH ACC TRÊN HỆ THỐNG:**\n\n"
    for r in rows:
        msg += f"📱 `{r[0]}` | {r[1]} | {r[2]}\n"
    await e.reply(msg if rows else "Chưa có acc nào được lưu.")
    conn.close()

def run_web(): app.run(host='0.0.0.0', port=8080)

print("🚀 Bot quản lý đang khởi động...")
Thread(target=run_web).start()
bot.run_until_disconnected()
