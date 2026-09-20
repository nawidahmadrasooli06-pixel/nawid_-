from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, timezone
from pymongo import ReturnDocument
from database import challenges, get_leaderboard
from lang import t


def now_utc_naive(): return datetime.now(timezone.utc).replace(tzinfo=None)


def reminder_text(ch):
    if ch.get("stars_enabled"):
        stars = f"⭐️ هر استارز شما {int(ch.get('stars_rate', 0))} لایک حساب می‌شود."
    else:
        stars = "⭐️ استارز در این چالش فعال نیست."
    return t("fa", "reminder", stars=stars)


def ended_notice():
    return t("fa", "ended_notice")


def result_caption(p, prize, rank, rate):
    likes = int(p.get("likes", 0)); stars = int(p.get("stars_received", 0)); star_likes = stars * int(rate or 0); score = likes + star_likes
    return t("fa", "result_caption", rank=rank, name=p.get("name", "-"), city=p.get("city", "-"), prize=prize, likes=likes, stars=stars, star_likes=star_likes, score=score)


async def publish_results(bot, ch):
    board = get_leaderboard(str(ch["_id"]), ch.get("stars_rate", 0))
    count = int(ch.get("winners_count", 0)); prizes = ch.get("prizes", []); rate = ch.get("stars_rate", 0) if ch.get("stars_enabled") else 0
    winners = board[:count]
    for rank, p in enumerate(winners, 1):
        prize = prizes[rank - 1] if rank - 1 < len(prizes) else "-"
        try:
            if p.get("photo_file_id"):
                await bot.send_photo(chat_id=ch["channel_id"], photo=p["photo_file_id"], caption=result_caption(p, prize, rank, rate))
            else:
                await bot.send_message(chat_id=ch["channel_id"], text=result_caption(p, prize, rank, rate))
        except Exception:
            try: await bot.send_message(chat_id=ch["channel_id"], text=result_caption(p, prize, rank, rate))
            except Exception: pass
    try: await bot.send_message(chat_id=ch["channel_id"], text=t("fa", "results_done"))
    except Exception: pass


async def check_challenges(bot):
    now = now_utc_naive()
    for ch in challenges.find({"active": True}):
        end_time = ch.get("end_time")
        if not end_time: continue
        if not ch.get("reminded") and end_time - timedelta(hours=1) <= now < end_time:
            try: await bot.send_message(chat_id=ch["channel_id"], text=reminder_text(ch))
            except Exception: pass
            challenges.update_one({"_id": ch["_id"], "reminded": {"$ne": True}}, {"$set": {"reminded": True}})
        if now >= end_time:
            claimed = challenges.find_one_and_update({"_id": ch["_id"], "active": True}, {"$set": {"active": False, "ended_at": now, "results_at": now + timedelta(minutes=2), "results_published": False}}, return_document=ReturnDocument.BEFORE)
            if not claimed: continue
            try: await bot.send_message(chat_id=ch["channel_id"], text=ended_notice())
            except Exception: pass
    for ch in challenges.find({"active": False, "results_published": {"$ne": True}, "results_at": {"$lte": now}}):
        claimed = challenges.find_one_and_update({"_id": ch["_id"], "results_published": {"$ne": True}}, {"$set": {"results_published": True}}, return_document=ReturnDocument.BEFORE)
        if not claimed: continue
        await publish_results(bot, ch)


def start_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_challenges, "interval", seconds=10, args=[bot], id="challenge_checker", replace_existing=True, max_instances=1, coalesce=True)
    scheduler.start()
    return scheduler
