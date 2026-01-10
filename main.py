from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8492633588:AAGSoL3wMHq8HOD2llLmbp6gdfaAwOqjJvo' # Token bot của bạn

# Bot chính dùng Token để nhận lệnh
bot = TelegramClient('bot_manager', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Bộ nhớ tạm lưu các bước đăng nhập
login_steps = {}

@bot.on(events.NewMessage(pattern='/start'))
async def start(e):
    await e.reply("👋 Tôi là Bot Quản Lý Session Vĩnh Viễn.\nSử dụng lệnh: `/login [số_điện_thoại]` để bắt đầu.")

@bot.on(events.NewMessage(pattern='/login'))
async def login(e):
    phone = e.text.split(' ')[1]
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    
    # Gửi mã xác nhận về Telegram của số điện thoại đó
    sent = await client.send_code_request(phone)
    login_steps[e.sender_id] = {'phone': phone, 'hash': sent.phone_code_hash, 'client': client}
    
    await e.reply(f"📩 Đã gửi mã xác nhận đến `{phone}`. Hãy phản hồi tin nhắn này bằng mã OTP (ví dụ: 12345).")

@bot.on(events.NewMessage)
async def handle_otp(e):
    if e.sender_id in login_steps and e.text.isdigit():
        data = login_steps[e.sender_id]
        client = data['client']
        try:
            # Thực hiện đăng nhập
            await client.sign_in(data['phone'], e.text, phone_code_hash=data['hash'])
            
            # LẤY SESSION VĨNH VIỄN
            session_str = client.session.save()
            
            await e.reply(f"✅ Đăng nhập thành công!\n\n**Mã Session mới của bạn:**\n`{session_str}`\n\nLưu mã này vào code đập hộp để chạy.")
            del login_steps[e.sender_id]
        except Exception as ex:
            await e.reply(f"❌ Lỗi: {str(ex)}")

print("🤖 Bot quản lý đang chạy...")
bot.run_until_disconnected()
