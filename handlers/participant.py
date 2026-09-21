from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bson import ObjectId
from lang import t
from database import participants, add_participant, participant_for_user, set_participant_post, set_joined_status, save_report, get_challenge, user_active_participations


def participant_banner(challenge, participant):
    prizes = "\n".join(f"{m} نفر {i}: {p}" for i, (m, p) in enumerate(zip(["🥇", "🥈", "🥉"] + ["🏅"] * 17, challenge.get("prizes", [])), 1))
    rules = challenge.get("rules") or "پیش‌فرض"
    if str(rules).strip().lower() in {"default", "پیش‌فرض", "پیش فرض"}:
        rules = "🚫 از لایک‌های فیک و غیرواقعی استفاده نکنید؛ فعالیت‌های مشکوک بررسی می‌شود."
    return (
        "👤 کارت رسمی شرکت‌کننده\n\n"
        f"# {participant['number']}  |  {participant['name']}\n"
        f"🎂 {participant['age']} سال  |  📍 {participant['city']}\n\n"
        "━━━━━━━━━━━━━━\n"
        "🏆 جوایز چالش\n"
        f"{prizes or 'هنوز جایزه‌ای ثبت نشده است.'}\n\n"
        "━━━━━━━━━━━━━━\n"
        "📜 قوانین\n"
        f"{rules}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🔗 ثبت‌نام: {challenge.get('registration_link') or '-'}\n"
        f"📢 کانال: {challenge.get('channel_title') or challenge.get('channel_link') or '-'}\n"
        f"👑 برگزارکننده: {challenge.get('owner_username') or '-'}\n\n"
        "❤️ برای شرکت‌کننده موردنظرت لایک ثبت کن."
    )


def like_keyboard(challenge_id, participant_id, count=0):
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"❤️ لایک ({count})", callback_data=f"like_{challenge_id}_{participant_id}")]])


async def start_participation_from_challenge(update, context, challenge_id):
    context.user_data["pending_challenge_id"] = str(challenge_id)
    await enter_participant_flow(update, context)


async def enter_participant_flow(update, context):
    lang = context.user_data.get("lang", "fa")
    challenge_id = context.user_data.get("pending_challenge_id")
    challenge = get_challenge(challenge_id)
    target = update.message or update.callback_query.message
    if not challenge or not challenge.get("active"):
        await target.reply_text(t(lang, "challenge_closed")); return
    existing = participant_for_user(challenge_id, update.effective_user.id)
    if existing:
        await target.reply_text(t(lang, "already_registered", number=existing["number"])); return
    context.user_data["state"] = "await_name"
    await target.reply_text(t(lang, "enter_welcome", title=challenge.get("title", "چالش لایکی"), winners=len(challenge.get("prizes", []))))
    await target.reply_text(t(lang, "ask_name"))


async def receive_name(update, context):
    lang = context.user_data.get("lang", "fa")
    name = (update.message.text or "").strip()
    if not name or len(name) > 60:
        await update.message.reply_text(t(lang, "ask_name")); return
    context.user_data["p_name"] = name
    context.user_data["state"] = "await_age"
    await update.message.reply_text(t(lang, "ask_age"))


async def receive_age(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        age = int((update.message.text or "").strip())
    except Exception:
        age = 0
    if not 5 <= age <= 100:
        await update.message.reply_text(t(lang, "bad_age")); return
    context.user_data["p_age"] = age
    context.user_data["state"] = "await_city"
    await update.message.reply_text(t(lang, "ask_city"))


async def receive_city(update, context):
    lang = context.user_data.get("lang", "fa")
    city = (update.message.text or "").strip()
    if not city or len(city) > 80:
        await update.message.reply_text(t(lang, "ask_city")); return
    context.user_data["p_city"] = city
    context.user_data["state"] = "await_photo"
    await update.message.reply_text(t(lang, "ask_photo"))


async def receive_photo(update, context):
    lang = context.user_data.get("lang", "fa")
    if not update.message or not update.message.photo:
        await update.message.reply_text(t(lang, "ask_photo")); return
    challenge_id = context.user_data.get("pending_challenge_id")
    challenge = get_challenge(challenge_id)
    if not challenge or not challenge.get("active"):
        await update.message.reply_text(t(lang, "challenge_closed")); return
    user = update.effective_user
    existing = participant_for_user(challenge_id, user.id)
    if existing:
        await update.message.reply_text(t(lang, "already_registered", number=existing["number"])); return
    joined = False
    try:
        member = await context.bot.get_chat_member(challenge["channel_id"], user.id)
        joined = member.status in ("member", "administrator", "creator", "restricted")
    except Exception:
        pass
    photo_file_id = update.message.photo[-1].file_id
    participant, created = add_participant(challenge_id, user.id, context.user_data.get("p_name", "-"), context.user_data.get("p_age", 0), context.user_data.get("p_city", "-"), photo_file_id, challenge["channel_id"], joined)
    if not created:
        await update.message.reply_text(t(lang, "already_registered", number=participant["number"])); return
    try:
        sent = await context.bot.send_photo(chat_id=challenge["channel_id"], photo=photo_file_id, caption=participant_banner(challenge, participant), reply_markup=like_keyboard(challenge_id, str(participant["_id"])))
        set_participant_post(challenge_id, user.id, sent.message_id)
        set_joined_status(challenge_id, user.id, joined)
    except Exception:
        participants.delete_one({"_id": participant["_id"]})
        await update.message.reply_text("❌ ثبت‌نام کامل نشد چون ارسال کارت به کانال انجام نشد. مطمئن شو ربات در کانال ادمین است و دوباره عکس را بفرست.")
        return
    await update.message.reply_text(t(lang, "registered", number=participant["number"], city=participant["city"], name=participant["name"]))
    context.user_data.clear()
    context.user_data["lang"] = lang
    from handlers.start import send_main_menu
    await send_main_menu(update.message, context, lang, user.id)


def participant_edit_keyboard(challenge_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ نام", callback_data=f"pedit_name_{challenge_id}"), InlineKeyboardButton("🎂 سن", callback_data=f"pedit_age_{challenge_id}")],
        [InlineKeyboardButton("📍 شهر / ولایت", callback_data=f"pedit_city_{challenge_id}"), InlineKeyboardButton("🖼️ عکس", callback_data=f"pedit_photo_{challenge_id}")],
        [InlineKeyboardButton("↩️ برگشت", callback_data=f"stats_{challenge_id}")],
    ])

async def participant_edit_menu(query, context, challenge_id):
    lang=context.user_data.get("lang","fa"); p=participant_for_user(challenge_id,query.from_user.id); c=get_challenge(challenge_id)
    if not p or not c or not c.get("active"):
        await query.answer("این بخش دیگر قابل ویرایش نیست.",show_alert=True); return
    await query.answer(); await query.message.edit_text("✏️ ویرایش اطلاعات شرکت‌کننده\n\nهر بخشی را خواستی تغییر بده. بعد از تغییر، کارت کانال هم به‌روزرسانی می‌شود.",reply_markup=participant_edit_keyboard(challenge_id))

async def participant_edit_field(query, context, field, challenge_id):
    await query.answer(); p=participant_for_user(challenge_id,query.from_user.id); c=get_challenge(challenge_id)
    if not p or not c or not c.get("active"):
        await query.answer("این چالش دیگر فعال نیست.",show_alert=True); return
    context.user_data["participant_edit"]={"challenge_id":str(challenge_id),"field":field}; context.user_data["state"]="participant_edit"
    prompts={"name":"👤 نام جدیدت را بفرست.","age":"🎂 سن جدیدت را به عدد بفرست.\nنمونه: ۲۱","city":"📍 شهر یا ولایت جدیدت را بفرست.","photo":"🖼️ عکس جدیدت را به صورت عکس بفرست."}
    await query.message.edit_text(prompts.get(field,"مقدار جدید را بفرست."))

async def receive_participant_edit(update, context):
    info=context.user_data.get("participant_edit");
    if not info: return
    cid=info["challenge_id"]; field=info["field"]; p=participant_for_user(cid,update.effective_user.id); c=get_challenge(cid)
    if not p or not c or not c.get("active"):
        await update.message.reply_text("⛔ این چالش دیگر فعال نیست."); return
    if field=="photo":
        if not update.message.photo:
            await update.message.reply_text("🖼️ لطفاً عکس را به صورت عکس بفرست."); return
        participants.update_one({"_id":p["_id"]},{"$set":{"photo_file_id":update.message.photo[-1].file_id}})
    else:
        value=(update.message.text or "").strip()
        try:
            if field=="name":
                if not value or len(value)>60: raise ValueError
                participants.update_one({"_id":p["_id"]},{"$set":{"name":value}})
            elif field=="age":
                age=int(value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹","0123456789")))
                if not 5<=age<=100: raise ValueError
                participants.update_one({"_id":p["_id"]},{"$set":{"age":age}})
            elif field=="city":
                if not value or len(value)>80: raise ValueError
                participants.update_one({"_id":p["_id"]},{"$set":{"city":value}})
        except Exception:
            examples={"name":"نامت را بنویس.","age":"مثلاً: ۲۱","city":"مثلاً: هرات یا فرانکفورت"}
            await update.message.reply_text("⚠️ مقدار درست نیست.\n\n"+examples.get(field,"دوباره تلاش کن.")); return
    # refresh channel card
    newp=participant_for_user(cid,update.effective_user.id)
    try:
        if newp.get("post_message_id"):
            if field=="photo":
                await context.bot.edit_message_media(chat_id=c["channel_id"],message_id=newp["post_message_id"],media=__import__('telegram').InputMediaPhoto(newp["photo_file_id"],caption=participant_banner(c,newp)))
            else:
                await context.bot.edit_message_caption(chat_id=c["channel_id"],message_id=newp["post_message_id"],caption=participant_banner(c,newp),reply_markup=like_keyboard(cid,str(newp["_id"]),int(newp.get("likes",0))))
    except Exception: pass
    context.user_data.pop("participant_edit",None); context.user_data["state"]=None
    await update.message.reply_text("✅ اطلاعاتت با موفقیت ویرایش شد و کارتت هم به‌روزرسانی شد.")

def report_keyboard(challenge_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 جایزه پرداخت نشده", callback_data=f"report_reason|{challenge_id}|prize")],
        [InlineKeyboardButton("⚠️ مشکل در اجرای چالش", callback_data=f"report_reason|{challenge_id}|problem")],
        [InlineKeyboardButton("✏️ اطلاعات تغییر کرده", callback_data=f"report_reason|{challenge_id}|changed")],
        [InlineKeyboardButton("🔍 رفتار مشکوک", callback_data=f"report_reason|{challenge_id}|suspicious")],
        [InlineKeyboardButton("📝 مورد دیگر", callback_data=f"report_reason|{challenge_id}|other")],
    ])


async def open_report_flow(query, context, challenge_id):
    lang = context.user_data.get("lang", "fa")
    context.user_data["report_challenge_id"] = str(challenge_id)
    await query.message.edit_text(t(lang, "report_menu"), reply_markup=report_keyboard(challenge_id))


async def choose_report_reason(query, context, data):
    parts = data.split("|")
    if len(parts) != 3 or parts[0] != "report_reason":
        return
    _, challenge_id, reason = parts
    context.user_data["report_challenge_id"] = challenge_id
    context.user_data["report_reason"] = reason
    context.user_data["state"] = "await_report_text"
    await query.message.edit_text(t(context.user_data.get("lang", "fa"), "report_text"))


async def render_user_stats(query, context, challenge, participant):
    lang = context.user_data.get("lang", "fa")
    rate = int(challenge.get("stars_rate", 0)) if challenge.get("stars_enabled") else 0
    score = int(participant.get("likes", 0)) + int(participant.get("stars_received", 0)) * rate
    from handlers.owner import remaining_text
    text = t(lang, "stats_header", title=challenge.get("title", "-"), channel=challenge.get("channel_title") or challenge.get("channel_link") or "-", number=participant.get("number"), likes=participant.get("likes", 0), stars=participant.get("stars_received", 0), score=score, star_likes=int(participant.get("stars_received", 0))*rate, remaining=remaining_text(challenge["end_time"]))
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✏️ ویرایش اطلاعات من", callback_data=f"pedit_{challenge['_id']}" )], [InlineKeyboardButton("🚨 گزارش چالش", callback_data=f"report_open_{challenge['_id']}" )], [InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")]])
    await query.message.edit_text(text, reply_markup=kb)


async def receive_report_text(update, context):
    lang = context.user_data.get("lang", "fa")
    challenge_id = context.user_data.get("report_challenge_id")
    reason = context.user_data.get("report_reason", "other")
    details = (update.message.text or "").strip()
    if not challenge_id or not details:
        await update.message.reply_text(t(lang, "report_text")); return
    challenge = get_challenge(challenge_id)
    if not challenge:
        await update.message.reply_text(t(lang, "challenge_closed")); return
    report_id = save_report(challenge_id, update.effective_user.id, challenge.get("owner_id"), reason, details)
    from config import ADMIN_ID
    reporter = f"@{update.effective_user.username}" if update.effective_user.username else str(update.effective_user.id)
    admin_text = ("🚨 گزارش جدید چالش\n\n" f"🎯 چالش: {challenge.get('title','-')}\n" f"📢 کانال: {challenge.get('channel_link','-')}\n" f"👤 گزارش‌دهنده: {reporter}\n" f"📝 دلیل: {reason}\n" f"📄 توضیح: {details}\n" f"🆔 گزارش: {report_id}")
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ بستن گزارش", callback_data=f"admin_close_report_{report_id}")]]))
    except Exception:
        pass
    context.user_data.pop("report_challenge_id", None); context.user_data.pop("report_reason", None); context.user_data["state"] = None
    await update.message.reply_text(t(lang, "report_saved"))
