from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio, random
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT = 'xocdia88_bot_uytin_bot'

# Session duy nhất của ACC 8 (Nguyễn Thanh)
SESSION_ACC8 = '1BVtsOGcBu5WplDJSVRn8EYslTyiYpN7-V12ICXB1BTgp7nFs5n6-AQC-Xq7hBPi1D4Q1oZJlaCzxfSSqfe2xYRt24KGquwMu4sr1UwA9--QNaG9jjvEbt-T1MnrjfifVK_1fSn8kB08l-5DegwyTxMFLQ9SehsYU_cTG4wHfE_OGgQzU5VSELO7Vi7V1PRG0v2VmZ6pu-ec96jRTeFROrQOIN0VZIyVrjIIp68oBWiXidNnWrV8RMKO9dVRdnj6vQtl5E7_Pa6pR51RyM2IN-BSn78lDVlpT2vkOS4yV6kF8Y3pE-MtgJv56amDM4kl3Ib-5tf4-4uy4fCcc8SBXsmbccTnngks='

app = Flask('')
@app.route('/')
def home(): return "ACC_8_ONLINE"

async def main():
    # Chạy Web Server giữ app sống trên Koyeb
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    
    print("🚀 ĐANG KHỞI CHẠY DUY NHẤT ACC 8 (NGUYỄN THANH)...", flush=True)
    
    try:
        client = TelegramClient(StringSession(SESSION_ACC8), API_ID, API_HASH)
        await client.start()
        print("✅ ACC 8 ĐÃ ONLINE - ĐANG CHỜ BOT PHÁT QUÀ!", flush=True)

        @client.on(events.NewMessage(chats=BOT))
        async def work(e):
            if e.reply_markup:
                for row in e.reply_markup.rows:
                    for btn in row.buttons:
                        if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                            # Delay ngẫu nhiên để tránh bị bot quét
                            await asyncio.sleep(random.uniform(0.1, 0.4))
                            try:
                                await e.click()
                                print("💰 ACC 8 VỪA ĐẬP HỘP THÀNH CÔNG!", flush=True)
                            except: pass

        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ LỖI ACC 8: {e}", flush=True)

if __name__ == '__main__':
    asyncio.run(main())
    
