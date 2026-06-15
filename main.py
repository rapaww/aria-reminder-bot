from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from supabase import create_client
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from groq import Groq
import os
import pytz
import re

app = Flask(__name__)

# Config dari environment variables
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WA_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")  # format: whatsapp:+14155238886
YOUR_WA_NUMBER = os.environ.get("YOUR_WHATSAPP_NUMBER")  # format: whatsapp:+628xxx
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Jakarta")

# Init clients
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = Groq(api_key=GROQ_KEY)
tz = pytz.timezone(TIMEZONE)

scheduler = BackgroundScheduler(timezone=tz)
scheduler.start()


def parse_reminder_with_ai(text):
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    response = ai_client.chat.completions.create(
    model="llama-3.1-8b-instant",
    max_tokens=300,
    messages=[{
        "role": "user",
        "content": f"""Sekarang waktu: {now} WIB.
Parse input reminder berikut dan return JSON dengan format:
{{
  "message": "isi reminder dalam bahasa natural",
  "remind_at": "YYYY-MM-DD HH:MM",
  "repeat": "none/daily/weekly",
  "priority": "normal/urgent"
}}

Kalau user bilang "besok", "nanti", "sore", "malam", dll — parse ke waktu yang masuk akal.
Kalau gak ada waktu spesifik, set remind_at 1 jam dari sekarang.
Return JSON only, no explanation.

Input: {text}"""
        }]
    )
    
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'```json|```', '', raw).strip()
    import json
    return json.loads(raw)


def send_whatsapp(to, message):
    """Kirim pesan WhatsApp via Twilio"""
    twilio_client.messages.create(
        from_=TWILIO_WA_FROM,
        to=to,
        body=message
    )


def check_and_send_reminders():
    """Cek database tiap menit, kirim reminder yang udah waktunya"""
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    
    result = supabase.table("reminders").select("*").eq("status", "active").eq("remind_at", now).execute()
    
    for reminder in result.data:
        msg = f"⏰ *Reminder!*\n\n{reminder['message']}"
        if reminder['priority'] == 'urgent':
            msg = f"🚨 *URGENT REMINDER!*\n\n{reminder['message']}"
        
        send_whatsapp(reminder['user_number'], msg + "\n\nReply *done* untuk mark selesai, atau *snooze X* untuk tunda X menit.")
        
        if reminder['repeat'] == 'none':
            supabase.table("reminders").update({"status": "sent"}).eq("id", reminder['id']).execute()
        elif reminder['repeat'] == 'daily':
            next_time = (datetime.now(tz) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
            supabase.table("reminders").update({"remind_at": next_time}).eq("id", reminder['id']).execute()
        elif reminder['repeat'] == 'weekly':
            next_time = (datetime.now(tz) + timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M")
            supabase.table("reminders").update({"remind_at": next_time}).eq("id", reminder['id']).execute()


def send_daily_summary():
    """Kirim summary reminder hari ini tiap pagi jam 8"""
    today = datetime.now(tz).strftime("%Y-%m-%d")
    
    result = supabase.table("reminders").select("*").eq("status", "active").like("remind_at", f"{today}%").execute()
    
    if not result.data:
        return
    
    msg = "🌅 *Good morning! Reminder kamu hari ini:*\n\n"
    for i, r in enumerate(result.data, 1):
        time_only = r['remind_at'].split(' ')[1]
        priority_icon = "🚨" if r['priority'] == 'urgent' else "📌"
        msg += f"{i}. {priority_icon} {time_only} — {r['message']}\n"
    
    msg += f"\nTotal: {len(result.data)} reminder aktif"
    send_whatsapp(YOUR_WA_NUMBER, msg)


# Schedule jobs
scheduler.add_job(check_and_send_reminders, 'cron', minute='*')
scheduler.add_job(send_daily_summary, 'cron', hour=8, minute=0)


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming WhatsApp messages"""
    incoming_msg = request.form.get("Body", "").strip()
    from_number = request.form.get("From", "")
    
    resp = MessagingResponse()
    
    # Handle commands
    lower = incoming_msg.lower()
    
    if lower == "list":
        result = supabase.table("reminders").select("*").eq("status", "active").eq("user_number", from_number).execute()
        if not result.data:
            resp.message("📭 Kamu gak punya reminder aktif.")
        else:
            msg = "📋 *Reminder aktif kamu:*\n\n"
            for i, r in enumerate(result.data, 1):
                msg += f"{i}. [{r['id'][:6]}] {r['remind_at']} — {r['message']}\n"
            resp.message(msg)
        return str(resp)
    
    if lower == "done" or lower.startswith("done "):
        supabase.table("reminders").update({"status": "done"}).eq("status", "sent").eq("user_number", from_number).execute()
        resp.message("✅ Reminder ditandai selesai!")
        return str(resp)
    
    if lower.startswith("snooze"):
        minutes = 30
        parts = lower.split()
        if len(parts) > 1 and parts[1].isdigit():
            minutes = int(parts[1])
        new_time = (datetime.now(tz) + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
        supabase.table("reminders").update({"remind_at": new_time, "status": "active"}).eq("status", "sent").eq("user_number", from_number).execute()
        resp.message(f"⏸️ Reminder di-snooze {minutes} menit. Akan diingetin jam {new_time.split()[1]}!")
        return str(resp)
    
    if lower.startswith("hapus "):
        reminder_id_prefix = lower.replace("hapus ", "").strip()
        result = supabase.table("reminders").select("id").eq("user_number", from_number).execute()
        for r in result.data:
            if r['id'].startswith(reminder_id_prefix):
                supabase.table("reminders").delete().eq("id", r['id']).execute()
                resp.message(f"🗑️ Reminder dihapus!")
                return str(resp)
        resp.message("❌ Reminder tidak ditemukan.")
        return str(resp)
    
    if lower == "help":
        help_msg = """🤖 *ARIA Reminder Bot*

*Cara pakai:*
Ketik reminder kamu dengan bebas, contoh:
• "taruh kunci di laci, ingetin jam 5 sore"
• "meeting besok jam 2 siang, urgent"
• "minum obat tiap hari jam 8 pagi"

*Commands:*
• *list* — lihat semua reminder aktif
• *done* — tandai reminder terakhir selesai
• *snooze 30* — tunda 30 menit
• *hapus [id]* — hapus reminder
• *help* — tampilkan bantuan ini"""
        resp.message(help_msg)
        return str(resp)
    
    # Parse sebagai reminder baru
    try:
        parsed = parse_reminder_with_ai(incoming_msg)
        
        supabase.table("reminders").insert({
            "user_number": from_number,
            "message": parsed["message"],
            "remind_at": parsed["remind_at"],
            "repeat": parsed.get("repeat", "none"),
            "priority": parsed.get("priority", "normal"),
            "status": "active"
        }).execute()
        
        priority_note = " 🚨 *URGENT*" if parsed.get("priority") == "urgent" else ""
        repeat_note = f" (repeat: {parsed['repeat']})" if parsed.get("repeat", "none") != "none" else ""
        
        resp.message(f"✅ Reminder disimpan!{priority_note}\n\n📌 *{parsed['message']}*\n⏰ {parsed['remind_at']}{repeat_note}\n\nKetik *list* untuk lihat semua reminder.")
    except Exception as e:
        resp.message("❌ Gagal parse reminder. Coba lebih spesifik, contoh: 'ingetin aku beli bensin jam 5 sore'")
    
    return str(resp)


@app.route("/", methods=["GET"])
def index():
    return "ARIA Reminder Bot is running! 🤖"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
