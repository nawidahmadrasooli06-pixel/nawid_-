from telegram import Update
from telegram.ext import ContextTypes
from handlers.owner import receive_title, receive_channel, receive_owner_username, receive_custom_date, receive_time, receive_duration, receive_winners, receive_prize, receive_rules, receive_stars_rate, receive_custom_emojis, owner_stats_entry
from handlers.participant import receive_name, receive_age, receive_city, receive_photo, receive_report_text
from handlers.start import handle_text_start_button

TEXT_STATE_HANDLERS = {
    "await_title": receive_title, "await_channel": receive_channel, "await_owner_username": receive_owner_username,
    "await_custom_date": receive_custom_date, "await_time": receive_time, "await_duration": receive_duration,
    "await_winners": receive_winners, "await_prize": receive_prize, "await_rules": receive_rules,
    "await_stars_rate": receive_stars_rate, "await_custom_emojis": receive_custom_emojis,
    "await_name": receive_name, "await_age": receive_age, "await_city": receive_city, "await_report_text": receive_report_text,
}

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type != "private": return
    if await handle_text_start_button(update, context): return
    text = (update.message.text or "").strip()
    if text.lower() in {"آمار چالش", "آمار چالش من", "challenge stats", "my challenge stats"}:
        context.user_data["state"] = None; await owner_stats_entry(update, context); return
    handler = TEXT_STATE_HANDLERS.get(context.user_data.get("state"))
    if handler:
        await handler(update, context); return
    low = text.lower()
    if any(k in low for k in ["چطور", "چگونه", "ساخت چالش", "چالش بساز"]):
        await update.message.reply_text("🤖 برای ساخت چالش، از ➕ ساخت چالش در پنل استفاده کن.\n\nمن مرحله‌به‌مرحله ازت اطلاعات می‌گیرم و برای هر مرحله نمونه هم می‌دهم.")
    elif any(k in low for k in ["ثبت نام", "ثبت‌نام", "شرکت کنم", "شرکت در چالش"]):
        await update.message.reply_text("🎯 برای شرکت در چالش، لینک ثبت‌نام همان چالش را باز کن.\n\nاگر لینک را داری، از همان لینک وارد شو تا ثبت‌نام مخصوص همان چالش باز شود.")
    elif any(k in low for k in ["آمار", "نتیجه", "لایک", "استارز"]):
        await update.message.reply_text("📊 برای آمار، از 📊 آمار من استفاده کن.\n\nاگر مالک چالش هستی، می‌توانی «آمار چالش» را برای ربات بفرستی.")
    else:
        await update.message.reply_text("👋 سلام! من دستیار ربات چالش هستم.\n\nاگر درباره ساخت چالش، ثبت‌نام، لایک، استارز یا آمار سؤال داری، بپرس.\n\nیا از ▶️ استارت استفاده کن تا پنل را باز کنم.")

async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.chat.type == "private" and context.user_data.get("state") == "await_photo":
        await receive_photo(update, context)

async def general_nontext_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type != "private": return
    state = context.user_data.get("state")
    if state == "await_photo":
        await update.message.reply_text("🖼️ لطفاً عکس را به صورت عکس بفرست، نه استیکر، فایل یا پیام."); return
    if state == "await_custom_emojis":
        await update.message.reply_text("🎨 لطفاً ایموجی‌های سفارشی تلگرام را در یک پیام بفرست.\n\nحداکثر ۶ ایموجی کافی است."); return
    await update.message.reply_text("👋 من اینجام. اگر کمکی می‌خواهی، از ▶️ استارت استفاده کن یا سؤال خودت را بپرس.")
