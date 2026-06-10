# ICT Scanner Bot — راهنمای نصب

## فایل‌های مورد نیاز
- bot.py
- requirements.txt
- railway.toml

---

## مرحله ۱: ساخت حساب GitHub
1. برو به github.com
2. Sign up کن (رایگان)
3. ایمیل رو تأیید کن

## مرحله ۲: آپلود فایل‌ها در GitHub
1. بعد از لاگین، روی "+" کلیک کن → "New repository"
2. اسم: ict-bot
3. Public انتخاب کن
4. "Create repository" بزن
5. روی "uploading an existing file" کلیک کن
6. هر ۳ فایل رو آپلود کن
7. "Commit changes" بزن

## مرحله ۳: Deploy در Railway
1. برو به railway.app
2. "Login with GitHub" بزن
3. "New Project" → "Deploy from GitHub repo"
4. ict-bot رو انتخاب کن
5. روی پروژه کلیک کن → "Variables" تب

## مرحله ۴: تنظیم متغیرها در Railway
این ۳ متغیر رو اضافه کن:

BOT_TOKEN = 8973095839:AAECsZego97Ord_LlJrYnZsvXcisRqv0qKE
CHAT_ID = 246256619
GEMINI_KEY = AIzaSyAQ.Ab8RN6Izs1PdLjVzg_2BRlqWgkeFh4gE-_16wygrG59PNL0_rQ

## مرحله ۵: Deploy
- بعد از تنظیم متغیرها Railway خودکار deploy میکنه
- در تلگرام به @Altman07_bot پیام بده /start

---
## دستورات ربات
- /start — شروع
- /scan — اسکن فوری
- /status — وضعیت
- /help — راهنما
