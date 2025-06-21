
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re

from config import api_id, api_hash, bot_token

bot = Client("cds_otp_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

user_data = {}

batch_ids = {
    "1": {"name": "XRAY – NDA 2025", "id": 1121},
    "2": {"name": "ZULU – CDS", "id": 1140},
    "3": {"name": "YAQEEN – AFCAT", "id": 1160},
    "4": {"name": "ZULU OTA – CDS 2 2025", "id": 1188},
    "5": {"name": "FOXTROT – NDA Target", "id": 1195},
    "6": {"name": "YANKEE – CDS 2025", "id": 1202},
    "7": {"name": "DELTA – NDA (Hindi Medium)", "id": 1215}
}

@bot.on_message(filters.command("extract"))
async def extract_command(client, message: Message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_email"}
    await message.reply("📩 ENTER YOUR CDS JOURNEY EMAIL ID.")

@bot.on_message(filters.text & ~filters.command("extract"))
async def handle_input(client, message: Message):
    chat_id = message.chat.id
    text = message.text.strip()
    step = user_data.get(chat_id, {}).get("step")

    if step == "awaiting_email" and re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", text):
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.cdsjourney.in/api/v1/auth/otp", json={"email": text}) as r:
                if r.status == 200:
                    user_data[chat_id] = {"step": "awaiting_otp", "email": text}
                    await message.reply("🔐 ENTER YOUR OTP SENT ON YOUR EMAIL ID.")
                else:
                    await message.reply("❌ Failed to send OTP. Try again.")
    elif step == "awaiting_otp":
        email = user_data[chat_id]["email"]
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.cdsjourney.in/api/v1/auth/login", json={"email": email, "otp": text}) as r:
                res = await r.json()
                token = res.get("accessToken")
                if token:
                    user_data[chat_id]["token"] = token
                    user_data[chat_id]["step"] = "logged_in"
                    batch_list = "\n".join([f"{key}. {val['name']}" for key, val in batch_ids.items()])
                    await message.reply(f"✅ Login successful!\n\n📚 Available Batches:\n{batch_list}\n\nSend the batch number to extract Zoom links.")
                else:
                    await message.reply("❌ Invalid OTP or login failed.")
    elif step == "logged_in" and text in batch_ids:
        token = user_data[chat_id]["token"]
        batch = batch_ids[text]
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://api.cdsjourney.in/api/v1/batches/{batch['id']}/contents"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:
                res = await r.json()
                links = [c["url"] for c in res.get("data", []) if "zoom" in c.get("url", "")]
                if links:
                    file_path = f"/mnt/data/{batch['name'].replace(' ', '_')}.txt"
                    with open(file_path, "w") as f:
                        f.write("\n".join(links))
                    await message.reply_document(file_path, caption=f"✅ Zoom links for {batch['name']}")
                else:
                    await message.reply(f"⚠️ No Zoom links found for {batch['name']}.")
    else:
        await message.reply("❌ Invalid input. Use /extract to begin.")

bot.run()
