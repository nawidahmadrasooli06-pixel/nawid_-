from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bson import ObjectId
from lang import t
from database import participants, challenges, add_like, remove_like, remove_like_on_leave, set_joined_status, get_challenge

async def like_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = context.user_data.get("lang", "fa")
    parts = query.data.split("_", 2)
    if len(parts) != 3:
        await query.answer("Invalid", show_alert=True); return
    _, challenge_id, participant_id = parts
    try:
        p = participants.find_one({"_id": ObjectId(participant_id), "challenge_id": challenge_id})
    except Exception:
        p = None
    if not p:
        await query.answer("❌ پیدا نشد", show_alert=True); return
    challenge = get_challenge(challenge_id)
    if not challenge or not challenge.get("active"):
        await query.answer(t(lang, "challenge_closed"), show_alert=True); return
    if p.get("user_id") == query.from_user.id:
        await query.answer(t(lang, "cannot_like_self"), show_alert=True); return
    try:
        member = await context.bot.get_chat_member(challenge["channel_id"], query.from_user.id)
        is_member = member.status in ("member", "administrator", "creator", "restricted")
    except Exception:
        is_member = False
    if not is_member:
        set_joined_status(challenge_id, query.from_user.id, False)
        await query.answer(t(lang, "channel_required"), show_alert=True)
        return
    set_joined_status(challenge_id, query.from_user.id, True)

    # Clicking the same participant's button a second time withdraws the like.
    already_on_this_post = participants.find_one(
        {"_id": p["_id"], "liked_by": query.from_user.id}, {"_id": 1}
    )
    if already_on_this_post:
        success, reason = remove_like(p["_id"], query.from_user.id)
        if not success:
            await query.answer("ℹ️ این پست دیگر لایک ثبت‌شده‌ای از شما ندارد.", show_alert=False)
            return
        updated = participants.find_one({"_id": p["_id"]})
        await query.answer("💔 لایک خود را پس گرفتید.")
        try:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                    f"❤️ لایک ({updated.get('likes', 0)})", callback_data=query.data
                )]])
            )
        except Exception:
            pass
        return

    success, reason = add_like(p["_id"], query.from_user.id)
    if not success:
        message = "ℹ️ قبلاً در همین چالش به شرکت‌کننده دیگری لایک داده‌ای؛ اول لایک قبلی را پس بگیر." if reason == "duplicate" else "❌ خطا"
        await query.answer(message, show_alert=(reason != "duplicate"))
        return
    updated = participants.find_one({"_id": p["_id"]})
    await query.answer(t(lang, "like_added"))
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"❤️ لایک ({updated.get('likes', 0)})", callback_data=query.data)]]))
    except Exception:
        pass

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.chat_member
    if not cm:
        return
    old_status = cm.old_chat_member.status
    new_status = cm.new_chat_member.status
    user_id = cm.new_chat_member.user.id
    channel_id = cm.chat.id
    member_statuses = ("member", "administrator", "creator", "restricted")
    if new_status in ("left", "kicked") and old_status in member_statuses:
        remove_like_on_leave(channel_id, user_id)
    elif new_status in member_statuses:
        participants.update_many({"channel_id": channel_id, "user_id": user_id}, {"$set": {"joined_channel": True}})
