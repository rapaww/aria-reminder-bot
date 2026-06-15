# 🤖 ARIA WhatsApp Reminder Bot — Setup Guide

## Overview
Bot WhatsApp yang bisa nerima reminder dalam bahasa natural, kirim notifikasi otomatis, snooze, repeat, dan daily summary tiap pagi.

---

## STEP 1 — Bikin Akun (semua gratis)

### A. Twilio
1. Daftar di https://www.twilio.com/try-twilio
2. Verify email & nomor HP
3. Masuk ke Console → catat **Account SID** dan **Auth Token**
4. Di sidebar kiri → **Messaging** → **Try it out** → **Send a WhatsApp message**
5. Ikutin instruksi — kamu bakal kirim WA ke nomor Twilio sandbox (+1 415 523 8886)
6. Setelah connected, catat nomor sandbox itu (format: `whatsapp:+14155238886`)

### B. Supabase
1. Daftar di https://supabase.com
2. Buat **New Project** (nama bebas, password bebas, pilih region Singapore)
3. Tunggu project ready (~1 menit)
4. Masuk ke **SQL Editor** (sidebar kiri)
5. Copy-paste isi file `schema.sql`, lalu klik **Run**
6. Ke **Settings** → **API** → catat **Project URL** dan **anon public key**

### C. Railway (hosting gratis)
1. Daftar di https://railway.app pakai GitHub
2. Nanti dipakai di Step 3

### D. Anthropic API
1. Masuk ke https://console.anthropic.com
2. **API Keys** → **Create Key** → catat keynya

---

## STEP 2 — Setup Project di GitHub

1. Buat repo baru di GitHub (nama: `aria-reminder-bot`)
2. Upload semua file dari folder `wareminder` ini ke repo tersebut
3. Struktur file harus begini:
```
aria-reminder-bot/
├── app/
│   └── main.py
├── requirements.txt
├── Procfile
├── schema.sql (optional, gak perlu diupload)
└── .env.example
```

---

## STEP 3 — Deploy ke Railway

1. Masuk ke https://railway.app
2. Klik **New Project** → **Deploy from GitHub repo**
3. Pilih repo `aria-reminder-bot` kamu
4. Railway akan auto-detect Python dan start deploy
5. Setelah deploy, klik project → **Settings** → **Environment** → tambah semua variable berikut:

```
TWILIO_ACCOUNT_SID        = [dari Twilio Console]
TWILIO_AUTH_TOKEN         = [dari Twilio Console]
TWILIO_WHATSAPP_FROM      = whatsapp:+14155238886
YOUR_WHATSAPP_NUMBER      = whatsapp:+628xxxxxxxxx
SUPABASE_URL              = [dari Supabase Settings → API]
SUPABASE_KEY              = [anon public key dari Supabase]
ANTHROPIC_API_KEY         = [dari Anthropic Console]
TIMEZONE                  = Asia/Jakarta
```

6. Setelah semua variable diisi → Railway otomatis redeploy
7. Klik **Settings** → **Networking** → **Generate Domain** → catat URL kamu (contoh: `https://aria-bot.up.railway.app`)

---

## STEP 4 — Connect Twilio ke Railway

1. Balik ke Twilio Console
2. **Messaging** → **Settings** → **WhatsApp Sandbox Settings**
3. Di field **"When a message comes in"** → isi dengan:
   ```
   https://aria-bot.up.railway.app/webhook
   ```
4. Method: **HTTP POST**
5. Klik **Save**

---

## STEP 5 — Test Bot!

Kirim WA ke nomor Twilio sandbox kamu:

```
ingetin aku beli bensin jam 5 sore
```

Bot bakal balas konfirmasi reminder tersimpan, dan jam 5 sore kamu dapat WA otomatis!

---

## Cara Pakai Bot

| Command | Fungsi |
|---------|--------|
| Ketik reminder bebas | Simpan reminder baru |
| `list` | Lihat semua reminder aktif |
| `done` | Tandai reminder selesai |
| `snooze 30` | Tunda 30 menit |
| `hapus [id]` | Hapus reminder spesifik |
| `help` | Tampilkan bantuan |

### Contoh Input Natural Language:
- "taruh kunci di laci, ingetin jam 5 sore"
- "meeting besok jam 2 siang, urgent"
- "minum obat tiap hari jam 8 pagi"
- "bayar listrik tanggal 20 bulan ini"

---

## Catatan Penting

- **Twilio free trial** punya kredit $15 — cukup buat ratusan pesan
- **Railway free tier** 500 jam/bulan — cukup buat 1 app jalan terus
- **Supabase free tier** 500MB database — lebih dari cukup
- **Anthropic API** — ada free tier terbatas, atau isi kredit $5 cukup lama banget

---

## Troubleshooting

**Bot gak bales?**
→ Cek Railway logs di dashboard → tab **Deployments** → klik deployment → **View Logs**

**Reminder gak terkirim?**
→ Pastikan format `remind_at` di database sesuai `YYYY-MM-DD HH:MM`
→ Cek timezone sudah `Asia/Jakarta`

**Error 401 dari Twilio?**
→ Cek ulang TWILIO_ACCOUNT_SID dan TWILIO_AUTH_TOKEN
