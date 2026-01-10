import re, asyncio, random, datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8492633588:AAGSoL3wMHq8HOD2llLmbp6gdfaAwOqjJvo'
BOT_GAME = 'xocdia88_bot_uytin_bot'
GR_LOG = -1002984339626

app = Flask('')
@app.route('/')
def home(): return "AUTO_LOGIN_SYSTEM_ACTIVE"

# Lưu trữ tạm thời các phiên đăng nhập đang chờ OTP
waiting_otp = {}

async def start_admin():
    bot = TelegramClient('admin_bot', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 Bot Quản Trị đã sẵn sàng!")

    # BƯỚC 1: NHẬN SĐT ĐỂ ĐĂNG NHẬP
    @bot.on(events.NewMessage(chats=GR_LOG, pattern='/login'))
    async def login_handler(e):
        try:
            phone = e.text.split(" ", 1)[1].strip()
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            # Gửi mã OTP
            send_code = await client.send_code_request(phone)
            waiting_otp[e.sender_id] = {
                "client": client, 
                "phone": phone, 
                "hash": send_code.phone_code_hash
            }
            await e.respond(f"📩 Đã gửi OTP đến `{phone}`. Hãy nhắn: `/otp <mã>`")
        except Exception as ex:
            await e.respond(f"❌ Lỗi: {ex}")

    # BƯỚC 2: NHẬN OTP VÀ TỰ ĐỘNG CHẠY
    @bot.on(events.NewMessage(chats=GR_LOG, pattern='/otp'))
    async def otp_handler(e):
        user_data = waiting_otp.get(e.sender_id)
        if not user_data:
            return await e.respond("❌ Vui lòng dùng lệnh `/login` trước.")
        
        try:
            otp_code = e.text.split(" ", 1)[1].strip()
            client = user_data["client"]
            # Hoàn tất đăng nhập
            await client.sign_in(user_data["phone"], otp_code, phone_code_hash=user_data["hash"])
            
            # Lấy mã Session vừa tạo
            new_session = client.session.save()
            await e.respond(f"✅ ĐĂNG NHẬP THÀNH CÔNG!\nSession của bạn: `{new_session}`\n🚀 Acc đã bắt đầu đập hộp.")
            
            # Kích hoạt đập hộp cho Acc này ngay lập tức
            asyncio.create_task(run_daphop(client, bot))
            del waiting_otp[e.sender_id]
        except Exception as ex:
            await e.respond(f"❌ Lỗi OTP: {ex}")

    await bot.run_until_disconnected()

async def run_daphop(client, bot_admin):
    me = await client.get_me()
    @client.on(events.NewMessage(chats=BOT_GAME))
    async def work(e):
        if e.reply_markup:
            for row in e.reply_markup.rows:
                for btn in row.buttons:
                    if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                        await asyncio.sleep(random.uniform(1, 3))
                        try:
                            await e.click()
                            await bot_admin.send_message(GR_LOG, f"💰 **{me.first_name}** đã đập hộp!")
                        except: pass
    await client.run_until_disconnected()

async def main():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    await start_admin()

if __name__ == '__main__':
    asyncio.run(main())
    
