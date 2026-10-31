# -*- coding: utf-8 -*-
"""
Redis 缓存工具 + 三种经典缓存问题的防护方案。

1. 缓存穿透 (penetration)：查询一个不存在的 key，每次都绕过缓存打到 DB。
   方案：先判断"这个 id 是否是激活题目"，不是就直接返回，绝不打 DB。

   注意：这里**没有用进程内布隆过滤器**。布隆对象存在每个进程的内存里，
   gunicorn 起多个 worker 时，新增题目只有处理该请求的 worker 会更新自己的那份，
   其他 worker 仍认为题目不存在，表现为"随机 404"。
   改为 Redis SET（键 question:active_ids），多个 worker 共享同一份索引。

2. 缓存击穿 (breakdown)：某个"热点 key"恰好过期，瞬间大量并发同时回源，压垮 DB。
   方案：互斥锁 / 单飞 (single-flight)。用一个原子占锁 (SETNX) 保证同一时刻只有
   一个线程去重建缓存，其它线程拿不到锁就短暂等待后重读缓存。

3. 缓存雪崩 (avalanche)：大量 key 在同一时刻集体过期，导致 DB 瞬间被压垮。
   方案：TTL 随机抖动。给每个 key 的基础过期时间加上随机偏移，让过期时间分散开。
"""
import logging
import random
import time

import redis
from django.conf import settings
from django.core.cache import cache

from .models import Problem

logger = logging.getLogger(__name__)

# ---------- 激活题目索引（防穿透，多进程共享）----------
ACTIVE_IDS_KEY = 'question:active_ids'
_redis_client = None


def _redis():
    """取 Redis 客户端（复用 CACHES 里的地址）。

    拿不到或连接异常时返回 None，调用方退化为直查数据库 —— 宁可慢，也不能判错。
    """
    global _redis_client
    if _redis_client is None:
        location = settings.CACHES.get('default', {}).get('LOCATION')
        if not location or not str(location).startswith('redis'):
            return None
        try:
            _redis_client = redis.Redis.from_url(str(location), decode_responses=True)
            _redis_client.ping()
        except redis.RedisError as e:
            logger.warning('Redis 不可用，题目存在性判断将退化为直查数据库: %s', e)
            _redis_client = None
    return _redis_client


def rebuild_question_index():
    """重建「激活题目 id」集合，题目增删改/上下架后调用。"""
    client = _redis()
    if client is None:
        return False
    ids = list(Problem.objects.filter(is_active=True).values_list('id', flat=True))
    try:
        pipe = client.pipeline()
        pipe.delete(ACTIVE_IDS_KEY)
        if ids:
            pipe.sadd(ACTIVE_IDS_KEY, *ids)
        pipe.execute()
        return True
    except redis.RedisError as e:
        logger.warning('重建题目索引失败: %s', e)
        return False


def question_may_exist(pid):
    """判断题目 id 是否可能是激活题目（False 表示一定不存在，可直接拦截）。"""
    client = _redis()
    if client is None:
        return Problem.objects.filter(id=pid, is_active=True).exists()
    try:
        # 索引丢失（Redis 重启 / 被清空）时自愈一次
        if not client.exists(ACTIVE_IDS_KEY):
            rebuild_question_index()
        return bool(client.sismember(ACTIVE_IDS_KEY, int(pid)))
    except (redis.RedisError, TypeError, ValueError) as e:
        logger.warning('查询题目索引失败，退化为直查数据库: %s', e)
        return Problem.objects.filter(id=pid, is_active=True).exists()


# ---------- 击穿 / 雪崩 ----------
def _lock_key(key):
    return key + ':lock'


def _rand_ttl(base_ttl, jitter_ratio=0.2):
    # 雪崩防护：TTL 加随机抖动，避免大量 key 同一时刻过期
    j = int(base_ttl * jitter_ratio)
    return base_ttl + random.randint(-j, j)


def get_cached(key, base_ttl, loader, *, mutex_timeout=5):
    """读缓存，未命中则用 loader 回源并写缓存；内置击穿/雪崩防护。"""
    # 1) 读缓存
    val = cache.get(key)
    if val is not None:
        return val
    # 2) 击穿防护：cache.add 原子占锁(SETNX)，抢不到则短暂等待后重读一次
    if not cache.add(_lock_key(key), '1', timeout=mutex_timeout):
        time.sleep(0.05)
        val = cache.get(key)
        if val is not None:
            return val
    try:
        val = loader()  # 3) 回源 DB
        if val is not None:
            cache.set(key, val, timeout=_rand_ttl(base_ttl))  # 雪崩防护
        return val
    finally:
        cache.delete(_lock_key(key))


def delete_question_detail_cache(question_id):
    cache.delete(f'question:detail:{question_id}')
