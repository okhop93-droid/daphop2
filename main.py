import re, asyncio, random, datetime, time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH GỐC ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8492633588:AAGSoL3wMHq8HOD2llLmbp6gdfaAwOqjJvo' 
BOT_GAME = 'xocdia88_bot_uytin_bot'
GR_LOG = -1002984339626

# HỆ THỐNG QUẢN LÝ BIẾN
active_sessions = {} # Lưu các client đang chạy
stats = {}           # Lưu thông tin hiển thị
start_time = time.time()

app = Flask('')
@app.route('/')
def home(): return "SYSTEM_MANAGER_ACTIVE"

# --- HÀM KHỞI CHẠY MỘT ACC MỚI ---
async def run_new_acc(session_str, bot_admin):
    acc_id = str(len(active_sessions) + 1)
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    
    try:
        await client.start()
        me = await client.get_me()
        active_sessions[acc_id] = client
        stats[acc_id] = {"name": me.first_name, "status": "🟢 Online", "count": 0}
        
        # Thông báo khi acc online thành công
        await bot_admin.send_message(GR_LOG, f"✅ **THÊM THÀNH CÔNG:** Acc {acc_id} ({me.first_name}) đã vào đội hình!")

        @client.on(events.NewMessage(chats=BOT_GAME))
        async def handle_game(e):
            # Tự động đập hộp
            if e.reply_markup:
                for row in e.reply_markup.rows:
                    for btn in row.buttons:
                        if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                            delay = int(acc_id) * random.uniform(0.3, 0.8)
                            await asyncio.sleep(delay)
                            try:
                                await e.click()
                                stats[acc_id]["count"] += 1
                                # Thông báo húp quà vui vẻ
                                await bot_admin.send_message(GR_LOG, f"💰 **{me.first_name}** vừa húp quà! (Tổng: {stats[acc_id]['count']} lần)")
                            except: pass
        await client.run_until_disconnected()
    except Exception as e:
        stats[acc_id]["status"] = "❌ Lỗi/Die"
        await bot_admin.send_message(GR_LOG, f"⚠️ **CẢNH BÁO:** Acc {acc_id} ({stats[acc_id].get('name', 'Unknown')}) đã bị văng!")

# --- BOT QUẢN TRỊ (TOKEN) ---
async def start_admin():
    bot = TelegramClient('admin_manager', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 Bot Quản Trị đã sẵn sàng!")

    # 1. Lệnh thêm tài khoản ngay trên Bot
    @bot.on(events.NewMessage(chats=GR_LOG, pattern='/add'))
    async def add_acc(e):
        try:
            session_str = e.text.split(" ", 1)[1]
            await e.respond("⏳ Đang kiểm tra Session và nạp vào hệ thống...")
            asyncio.create_task(run_new_acc(session_str, bot))
        except:
            await e.respond("❌ Sai cú pháp. Dùng: `/add <mã_session>`")

    # 2. Lệnh xem Dashboard
    @bot.on(events.NewMessage(chats=GR_LOG, pattern='/status'))
    async def show_dashboard(e):
        msg = "🚀 **DASHBOARD QUẢN LÝ BOT**\n"
        msg += "━━━━━━━━━━━━━━━━━━\n"
        if not stats:
            msg += "Chưa có tài khoản nào được nạp.\n"
        for aid, data in stats.items():
            msg += f"{data['status']} **{data['name']}** (ID: {aid})\n┗ Húp thành công: {data['count']}\n"
        
        uptime = str(datetime.timedelta(seconds=int(time.time() - start_time)))
        msg += f"━━━━━━━━━━━━━━━━━━\n⏳ Uptime: {uptime}\n💡 Dùng `/add` để thêm Acc."
        await e.respond(msg)

    # 3. Quét mã code như cũ
    @bot.on(events.NewMessage(chats=BOT_GAME))
    async def get_code(e):
        if "Mã code của bạn là:" in e.raw_text:
            match = re.search(r"Mã code của bạn là:\s*([A-Z0-9]+)", e.raw_text)
            if match:
                await bot.send_message(GR_LOG, f"📩 **CODE MỚI:** `{match.group(1)}`")

    await bot.run_until_disconnected()

async def main():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    await start_admin()

if __name__ == '__main__':
    asyncio.run(main())
    
