from telegram import Update
from telegram.ext import ContextTypes
from bson import ObjectId
from database import participants, challenges, set_stars_received

async def message_reaction_count_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mrc = update.message_reaction_count
    if not mrc:
        return
    p = participants.find_one({"post_message_id": mrc.message_id, "channel_id": mrc.chat.id})
    if not p:
        return
    try:
        challenge = challenges.find_one({"_id": ObjectId(str(p["challenge_id"]))})
    except Exception:
        return
    if not challenge or not challenge.get("stars_enabled"):
        return
    paid_count = 0
    for reaction in (mrc.reactions or []):
        try:
            reaction_type = getattr(reaction.type, "type", "")
            # PTB models paid reactions as a reaction type whose discriminator is "paid".
            if reaction_type == "paid" or reaction_type.__class__.__name__.lower() in {"reactiontypepaid", "paidreactiontype"}:
                paid_count = int(reaction.total_count)
                break
        except Exception:
            continue
    set_stars_received(p["_id"], paid_count)
