# nawid_chalesh — Render Web Service (free-plan compatible)

این نسخه برای Web Service رایگان Render آماده شده است: ربات همچنان با Telegram long polling کار می‌کند و هم‌زمان یک HTTP health endpoint روی پورت `PORT` خود Render پاسخ می‌دهد. این تغییر برای رفع علت محتمل `Timed Out` در لاگ‌های قبلی است؛ استقرار زنده با حساب‌های کاربر از اینجا قابل تأیید نیست.

## Render settings
- Service type: Web Service (همان سرویس فعلی را می‌توانی نگه داری)
- Runtime: Python؛ فایل `.python-version` نسخه 3.11.11 را مشخص می‌کند
- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`
- Root Directory: خالی، مگر اینکه مخزن ساختار متفاوتی داشته باشد
- Health Check Path (اگر فیلدش موجود است): `/health`

## Environment Variables
این کد نام‌های اصلی و نام‌های جایگزین زیر را می‌پذیرد:
- `BOT_TOKEN` (ضروری)
- `MONGO_URI` یا `MONGODB_URI` (ضروری)
- `ADMIN_ID` یا `ADMIN_CHAT_ID` (ضروری؛ شناسه عددی تلگرام)

متغیرها را در Render وارد کن؛ توکن یا URI را در GitHub یا چت قرار نده. چون مقادیر قبلی در چت/لاگ قابل مشاهده شده‌اند، توکن BotFather و رمز کاربر MongoDB را عوض کن.

## Deploy and test
1. این ZIP را باز کن و محتویات پوشه را در ریشه مخزن GitHub قرار بده؛ ساختار `main.py`, `config.py`, `database.py`, `handlers/`, `requirements.txt` باید در ریشه باشد.
2. بهتر است قبل از جایگزینی، از مخزن یک نسخه پشتیبان بگیری.
3. در Render از همان Web Service استفاده کن و تنظیمات بالا را ثبت کن.
4. Deploy را اجرا کن. لاگ باید شامل `HTTP health server listening on port ...` و `Challenge bot started` باشد.
5. آدرس سرویس و سپس `/health` را باز کن؛ باید `ok` نشان دهد. بعد در تلگرام `/start` را آزمایش کن.

## Important
این اصلاح مشکل محتملِ نداشتن HTTP listener را هدف می‌گیرد. اگر بعد از آن خطای MongoDB، Telegram conflict (چند نمونه هم‌زمان polling می‌کنند)، یا متغیر محیطی دیده شود، باید بر اساس لاگ جدید بررسی شود. یک ربات تلگرام با polling را هم‌زمان روی دو سرویس اجرا نکن. Free Web Services ممکن است پس از مدتی بی‌ترافیکی بخوابند و تضمین uptime دائمی ندارند.
