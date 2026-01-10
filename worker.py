import asyncio, random, re, time
from telethon import events

# Hàm kiểm tra khung giờ
from datetime import datetime
def trong_khung_gio():
    giờ = datetime.now().hour + datetime.now().minute/60
    return (
        7 <= giờ <= 9.5 or
        11 <= giờ <= 14.5 or
        19 <= giờ <= 24
    )

async def worker_loop(acc):
    client = acc["client"]

    while acc["enable"]:
        if not trong_khung_gio():
            await asyncio.sleep(60)
            continue

        try:
            # --- Lắng nghe tin nhắn mới từ bot game ---
            # Nếu muốn gắn code cũ: copy logic click nút vào đây
            msgs = await client.get_messages(acc["bot_game"], limit=1)
            if msgs and hasattr(msgs[0], "reply_markup") and msgs[0].reply_markup:
                # tìm nút "Đập / Hộp / Mở"
                btn = next(
                    (b for r in msgs[0].reply_markup.rows for b in r.buttons
                     if any(x in b.text.lower() for x in ["đập", "hộp", "mở"])),
                    None
                )
                if btn:
                    await asyncio.sleep(random.uniform(0.1, 0.6))
                    await msgs[0].click()
                    await asyncio.sleep(1.2)
                    # Lấy mã quà (ví dụ code A-Z0-9)
                    new_msg = await client.get_messages(acc["bot_game"], limit=1)
                    match = re.search(r"[A-Z0-9]{8,15}", new_msg[0].message)
                    if match:
                        acc["last_code"] = match.group()
                        print(f"[{acc['name']}] Húp quà thành công: {match.group()}")

        except Exception as e:
            print(f"[{acc['name']}] Lỗi worker: {e}")

        await asyncio.sleep(random.randint(5, 15))  # delay ngẫu nhiên
