from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING, ReturnDocument
from config import MONGO_URI

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
db = client["challenge_bot"]
users = db["users"]
challenges = db["challenges"]
participants = db["participants"]
reports = db["reports"]
audit_logs = db["audit_logs"]
counters = db["counters"]
blocked_users = db["blocked_users"]

users.create_index([("user_id", ASCENDING)], unique=True)
challenges.create_index([("active", ASCENDING), ("end_time", ASCENDING)])
challenges.create_index([("owner_id", ASCENDING), ("active", ASCENDING)])
participants.create_index([("challenge_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
participants.create_index([("challenge_id", ASCENDING), ("number", ASCENDING)], unique=True)
participants.create_index([("channel_id", ASCENDING), ("post_message_id", ASCENDING)])
reports.create_index([("status", ASCENDING), ("created_at", DESCENDING)])


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def register_user_start(user_id, username="", language=None):
    update = {"username": username or ""}
    if language:
        update["language"] = language
    users.update_one(
        {"user_id": int(user_id)},
        {"$set": update, "$setOnInsert": {"user_id": int(user_id), "started_at": utcnow()}},
        upsert=True,
    )
    return users.find_one({"user_id": int(user_id)})


def set_user_language(user_id, language):
    users.update_one({"user_id": int(user_id)}, {"$set": {"language": language}}, upsert=True)


def get_user_language(user_id):
    doc = users.find_one({"user_id": int(user_id)}, {"language": 1})
    return doc.get("language", "fa") if doc else "fa"


def get_total_starts():
    return users.count_documents({})


def is_blocked(user_id):
    return bool(blocked_users.find_one({"user_id": int(user_id), "blocked": True}))


def block_user(user_id):
    blocked_users.update_one({"user_id": int(user_id)}, {"$set": {"user_id": int(user_id), "blocked": True, "blocked_at": utcnow()}}, upsert=True)


def create_challenge(owner_id, data):
    doc = {
        "owner_id": int(owner_id),
        "owner_username": data.get("owner_username", ""),
        "channel_id": int(data["channel_id"]),
        "channel_username": data.get("channel_username", ""),
        "channel_link": data.get("channel_link", ""),
        "channel_title": data.get("channel_title", ""),
        "title": data.get("title", "چالش لایکی"),
        "start_time": data["start_time"],
        "end_time": data["end_time"],
        "timezone": data.get("timezone", "Asia/Kabul"),
        "duration_hours": float(data.get("duration_hours", 24)),
        "winners_count": int(data["winners_count"]),
        "prizes": list(data.get("prizes", [])),
        "rules": data.get("rules", "پیش‌فرض"),
        "stars_enabled": bool(data.get("stars_enabled", False)),
        "stars_rate": int(data.get("stars_rate", 0)),
        "active": True,
        "reminded": False,
        "created_at": utcnow(),
        "deep_link_starts": 0,
        "banner_message_id": None,
        "registration_link": "",
    }
    result = challenges.insert_one(doc)
    return str(result.inserted_id)


def set_registration_link(challenge_id, link):
    challenges.update_one({"_id": ObjectId(str(challenge_id))}, {"$set": {"registration_link": link}})


def increment_deep_link_start(challenge_id):
    challenges.update_one({"_id": ObjectId(str(challenge_id))}, {"$inc": {"deep_link_starts": 1}})


def get_challenge(challenge_id):
    try:
        return challenges.find_one({"_id": ObjectId(str(challenge_id))})
    except Exception:
        return None


def active_challenges(limit=50):
    return list(challenges.find({"active": True}).sort("created_at", DESCENDING).limit(limit))


def owner_active_challenges(owner_id, limit=50):
    return list(challenges.find({"owner_id": int(owner_id), "active": True, "deleted_by_owner": {"$ne": True}}).sort("created_at", DESCENDING).limit(limit))


def owner_challenges(owner_id, limit=100):
    return list(challenges.find({"owner_id": int(owner_id), "deleted_by_owner": {"$ne": True}}).sort("created_at", DESCENDING).limit(limit))


def delete_challenge_for_owner(challenge_id, owner_id):
    result = challenges.update_one({"_id": ObjectId(str(challenge_id)), "owner_id": int(owner_id)}, {"$set": {"deleted_by_owner": True, "deleted_at": utcnow()}})
    return result.modified_count > 0


def participant_for_user(challenge_id, user_id):
    return participants.find_one({"challenge_id": str(challenge_id), "user_id": int(user_id)})


def add_participant(challenge_id, user_id, name, age, city, photo_file_id, channel_id, joined_channel=False):
    challenge_id = str(challenge_id)
    user_id = int(user_id)
    existing = participant_for_user(challenge_id, user_id)
    if existing:
        return existing, False
    counter = counters.find_one_and_update(
        {"_id": f"participants:{challenge_id}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    number = int(counter["seq"])
    participant = {
        "challenge_id": challenge_id,
        "channel_id": int(channel_id),
        "user_id": user_id,
        "number": number,
        "name": name,
        "age": int(age),
        "city": city,
        "photo_file_id": photo_file_id,
        "likes": 0,
        "stars_received": 0,
        "liked_by": [],
        "joined_channel": bool(joined_channel),
        "registered_at": utcnow(),
        "post_message_id": None,
    }
    try:
        participants.insert_one(participant)
    except Exception:
        existing = participant_for_user(challenge_id, user_id)
        if existing:
            return existing, False
        raise
    return participant, True


def set_participant_post(challenge_id, user_id, message_id):
    participants.update_one({"challenge_id": str(challenge_id), "user_id": int(user_id)}, {"$set": {"post_message_id": int(message_id)}})


def set_joined_status(challenge_id, user_id, joined):
    participants.update_one({"challenge_id": str(challenge_id), "user_id": int(user_id)}, {"$set": {"joined_channel": bool(joined)}})


def add_like(participant_id, liker_user_id):
    p = participants.find_one({"_id": participant_id})
    if not p:
        return False, "missing"
    if int(p.get("user_id")) == int(liker_user_id):
        return False, "self"
    result = participants.update_one(
        {"_id": participant_id, "liked_by": {"$ne": int(liker_user_id)}},
        {"$inc": {"likes": 1}, "$push": {"liked_by": int(liker_user_id)}},
    )
    return (True, "ok") if result.modified_count else (False, "duplicate")


def remove_like_on_leave(channel_id, left_user_id):
    channel_id = int(channel_id); left_user_id = int(left_user_id)
    affected = participants.find({"channel_id": channel_id, "liked_by": left_user_id})
    for p in affected:
        participants.update_one({"_id": p["_id"], "likes": {"$gt": 0}}, {"$inc": {"likes": -1}, "$pull": {"liked_by": left_user_id}})
        participants.update_one({"_id": p["_id"], "likes": {"$lte": 0}}, {"$set": {"likes": 0}, "$pull": {"liked_by": left_user_id}})
    participants.update_many({"channel_id": channel_id, "user_id": left_user_id}, {"$set": {"joined_channel": False}})


def set_stars_received(participant_id, paid_count):
    participants.update_one({"_id": participant_id}, {"$set": {"stars_received": max(0, int(paid_count))}})


def get_leaderboard(challenge_id, stars_rate=0):
    docs = list(participants.find({"challenge_id": str(challenge_id)}))
    rate = max(0, int(stars_rate or 0))
    for d in docs:
        d["total_score"] = int(d.get("likes", 0)) + int(d.get("stars_received", 0)) * rate
    docs.sort(key=lambda x: (x["total_score"], x.get("likes", 0), x.get("stars_received", 0), -int(x.get("number", 0))), reverse=True)
    return docs


def user_active_participations(user_id):
    ids = [str(c["_id"]) for c in challenges.find({"active": True}, {"_id": 1})]
    if not ids:
        return []
    docs = list(participants.find({"user_id": int(user_id), "challenge_id": {"$in": ids}}))
    by_id = {str(c["_id"]): c for c in challenges.find({"_id": {"$in": [ObjectId(x) for x in ids]}})}
    result = [(by_id[p["challenge_id"]], p) for p in docs if p["challenge_id"] in by_id]
    result.sort(key=lambda x: x[0].get("end_time", datetime.max))
    return result


def challenge_stats(challenge_id):
    ps = list(participants.find({"challenge_id": str(challenge_id)}, {"likes": 1, "stars_received": 1, "joined_channel": 1}))
    return {
        "participants": len(ps),
        "joined": sum(1 for p in ps if p.get("joined_channel")),
        "likes": sum(int(p.get("likes", 0)) for p in ps),
        "stars": sum(int(p.get("stars_received", 0)) for p in ps),
    }


def save_report(challenge_id, reporter_id, owner_id, reason, details):
    result = reports.insert_one({
        "challenge_id": str(challenge_id), "reporter_id": int(reporter_id), "owner_id": int(owner_id),
        "reason": reason, "details": details, "status": "open", "created_at": utcnow(),
    })
    return str(result.inserted_id)


def get_open_reports(limit=30):
    return list(reports.find({"status": "open"}).sort("created_at", DESCENDING).limit(limit))


def get_report(report_id):
    try:
        return reports.find_one({"_id": ObjectId(str(report_id))})
    except Exception:
        return None


def close_report(report_id):
    reports.update_one({"_id": ObjectId(str(report_id))}, {"$set": {"status": "closed", "closed_at": utcnow()}})


def audit(actor_id, action, challenge_id=None, target_user_id=None, details=None):
    audit_logs.insert_one({
        "actor_id": int(actor_id), "action": action, "challenge_id": str(challenge_id) if challenge_id else None,
        "target_user_id": int(target_user_id) if target_user_id else None, "details": details or {}, "created_at": utcnow(),
    })
