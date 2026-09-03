import redis
from .config import settings

# Kết nối Redis để lưu Window Context (Lịch sử hội thoại ngắn hạn)
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def get_window_context(session_id: str) -> str:
    """Lấy ngữ cảnh hội thoại từ Redis"""
    return redis_client.get(f"chat_context:{session_id}") or "[]"

def set_window_context(session_id: str, context: str, ttl: int = 3600):
    """Lưu ngữ cảnh hội thoại vào Redis với thời gian sống (TTL)"""
    redis_client.setex(f"chat_context:{session_id}", ttl, context)
