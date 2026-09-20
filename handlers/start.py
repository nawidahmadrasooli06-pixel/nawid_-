from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from lang import t
from database import register_user_start, set_user_language, get_user_language, active_challenges, get_challenge, increment_deep_link_start, user_active_participations, owner_active_challenges, is_blocked


def main_menu_keyboard(lang, admin=False):
    rows = [
        [InlineKeyboardButton(t(lang, "btn_active"), callback_data="menu_active"), InlineKeyboardButton(t(lang, "btn_new"), callback_data="menu_new")],
        [InlineKeyboardButton("📊 آمار من" if lang == "fa" else "📊 My Stats", callback_data="menu_stats"), InlineKeyboardButton(t(lang, "btn_results"), callback_data="menu_results")],
        [InlineKeyboardButton(t(lang, "btn_settings"), callback_data="menu_settings"), InlineKeyboardButton(t(lang, "btn_about"), callback_data="menu_about")],
        [InlineKeyboardButton(t(lang, "btn_creator"), callback_data="menu_creator")],
    ]
    if admin: rows.insert(0, [InlineKeyboardButton("🛡️ مدیریت مرکزی", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


def start_reply_keyboard(lang):
    return ReplyKeyboardMarkup([[KeyboardButton(t(lang, "start_button"))]], resize_keyboard=True, is_persistent=True, input_field_placeholder="پیامت را بنویس…")


def _menu_markup(lang, user_id):
    from config import ADMIN_ID
    return main_menu_keyboard(lang, user_id == ADMIN_ID)

async def send_main_menu(target, context, lang, user_id):
    await _show_or_edit_menu(target, context, lang, user_id, edit=False)

async def _show_or_edit_menu(message, context, lang, user_id, edit=False):
    if edit:
        try:
            await message.edit_text(t(lang, "main_menu"), reply_markup=_menu_markup(lang, user_id))
            return
        except Exception:
            pass
    # Inline panel + persistent Start keyboard are intentionally separate Telegram UI layers.
    sent = await message.reply_text(t(lang, "main_menu"), reply_markup=_menu_markup(lang, user_id))
    context.user_data["menu_message_id"] = sent.message_id
    if not context.user_data.get("start_keyboard_sent"):
        await message.reply_text("▶️ برای باز کردن سریع پنل، از گزینه زیر استفاده کن.", reply_markup=start_reply_keyboard(lang))
        context.user_data["start_keyboard_sent"] = True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blocked(user.id): return
    lang = get_user_language(user.id)
    register_user_start(user.id, user.username or "", lang)
    context.user_data["lang"] = lang
    if update.message and update.message.text and update.message.text.startswith("▶️"):
        try: await update.message.delete()
        except Exception: pass
    if context.args:
        payload = context.args[0]
        if payload.startswith("CH"):
            challenge_id = payload[2:]; challenge = get_challenge(challenge_id)
            if challenge and challenge.get("active"):
                context.user_data.clear(); context.user_data["lang"] = lang; context.user_data["pending_challenge_id"] = challenge_id
                increment_deep_link_start(challenge_id)
                from handlers.participant import start_participation_from_challenge
                await start_participation_from_challenge(update, context, challenge_id); return
    context.user_data["state"] = None
    await update.message.reply_text(t(lang, "welcome"))
    await _show_or_edit_menu(update.message, context, lang, user.id, edit=False)

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.data.split("_", 1)[1]
    context.user_data["lang"] = lang; set_user_language(query.from_user.id, lang)
    await query.message.edit_text(t(lang, "main_menu"), reply_markup=_menu_markup(lang, query.from_user.id))
    await query.answer(t(lang, "language_saved"))

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data; lang = context.user_data.get("lang") or get_user_language(query.from_user.id)
    if data == "menu_back":
        await query.message.edit_text(t(lang, "main_menu"), reply_markup=_menu_markup(lang, query.from_user.id)); return
    if data == "menu_new":
        from handlers.owner import start_owner_flow
        await start_owner_flow(update, context); return
    if data == "menu_active":
        items = active_challenges()
        if not items:
            await query.message.edit_text(t(lang, "active_empty"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")]])); return
        rows = [[InlineKeyboardButton(f"🎯 {c.get('title','چالش')}", callback_data=f"challenge_view_{c['_id']}")] for c in items]
        rows.append([InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")])
        await query.message.edit_text(t(lang, "active_title"), reply_markup=InlineKeyboardMarkup(rows)); return
    if data == "menu_stats":
        items = user_active_participations(query.from_user.id)
        if not items:
            await query.message.edit_text(t(lang, "stats_none"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")]])); return
        if len(items) == 1:
            from handlers.participant import render_user_stats
            await render_user_stats(query, context, items[0][0], items[0][1]); return
        rows = [[InlineKeyboardButton(f"📢 {c.get('title','چالش')}", callback_data=f"stats_{c['_id']}")] for c, _ in items]
        rows.append([InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")])
        await query.message.edit_text("📊 چالش موردنظر را انتخاب کن:", reply_markup=InlineKeyboardMarkup(rows)); return
    if data == "menu_results":
        await query.message.edit_text(t(lang, "results"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")]])); return
    if data == "menu_settings":
        await query.message.edit_text("⚙️ تنظیمات\n\nاینجا می‌توانی زبان ربات را تغییر بدهی و راهنمای کوتاه استفاده را ببینی.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_fa"), callback_data="lang_fa"), InlineKeyboardButton(t(lang, "btn_en"), callback_data="lang_en")], [InlineKeyboardButton("📖 راهنمای استفاده", callback_data="settings_help")], [InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")]])); return
    if data == "settings_help":
        await query.message.edit_text("💡 راهنمای سریع\n\n➕ برای ساخت چالش، اطلاعات را مرحله‌به‌مرحله وارد کن.\n🎯 برای شرکت، از لینک ثبت‌نام همان چالش وارد شو.\n📊 برای دیدن آمار خودت، آمار من را باز کن.\n\nهرجا ورودی اشتباه باشد، ربات نمونه درست را به تو نشان می‌دهد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_settings")]])); return
    if data == "menu_about":
        await query.message.edit_text(t(lang, "about"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")]])); return
    if data == "menu_creator":
        from handlers.about import creator_callback
        await creator_callback(update, context); return
    if data == "admin_panel":
        from handlers.admin import admin_panel_callback
        await admin_panel_callback(update, context); return
    if data.startswith("challenge_view_"):
        challenge_id = data.split("_", 2)[2]; c = get_challenge(challenge_id)
        if not c or not c.get("active"):
            await query.message.edit_text(t(lang, "challenge_closed"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_active")]])); return
        from handlers.owner import format_local_day
        day, tm = format_local_day(c["start_time"], c.get("timezone", "Asia/Kabul"))
        text = f"🎯 {c.get('title','چالش لایکی')}\n\n🏆 {len(c.get('prizes', []))} جایزه\n📅 {day} | {tm}\n⏳ {c.get('duration_hours',24):g} ساعت\n📢 {c.get('channel_link') or '-'}\n\nاگر آماده‌ای، ثبت‌نام را شروع کن."
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "join"), callback_data=f"challenge_join_{challenge_id}")], [InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_active")]])); return
    if data.startswith("challenge_join_"):
        challenge_id = data.split("_", 2)[2]; context.user_data["pending_challenge_id"] = challenge_id
        from handlers.participant import start_participation_from_challenge
        await start_participation_from_challenge(update, context, challenge_id); return
    if data.startswith("stats_"):
        challenge_id = data.split("_", 1)[1]; items = user_active_participations(query.from_user.id); found = next(((c,p) for c,p in items if str(c["_id"]) == challenge_id), None)
        if not found:
            await query.message.edit_text(t(lang, "stats_none"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")]])); return
        from handlers.participant import render_user_stats
        await render_user_stats(query, context, found[0], found[1]); return
    if data.startswith("owner_stats_"):
        from handlers.owner import owner_stats
        await owner_stats(query, context, data.split("_", 2)[2]); return
    if data.startswith("owner_people_"):
        from handlers.owner import owner_people
        await owner_people(query, context, data.split("_", 2)[2]); return
    if data.startswith("owner_board_"):
        from handlers.owner import owner_board
        await owner_board(query, context, data.split("_", 2)[2]); return
    if data.startswith("report_open_"):
        from handlers.participant import open_report_flow
        await open_report_flow(query, context, data.split("_", 2)[2]); return
    if data.startswith("report_"):
        from handlers.participant import choose_report_reason
        await choose_report_reason(query, context, data); return
    if data.startswith("admin_"):
        from handlers.admin import dispatch_admin_callback
        await dispatch_admin_callback(update, context); return

def handle_text_start_button(update, context):
    # Kept async-compatible with the router.
    import asyncio
    async def _run():
        if update.message and update.message.text == t(context.user_data.get("lang", "fa"), "start_button"):
            await start_command(update, context); return True
        return False
    return _run()
