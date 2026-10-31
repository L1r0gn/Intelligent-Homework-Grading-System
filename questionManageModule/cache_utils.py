# -*- coding: utf-8 -*-
"""
Redis 缓存工具 + 三种经典缓存问题的防护方案。

1. 缓存穿透 (penetration)：查询一个不存在的 key，每次都绕过缓存打到 DB。
   方案：布隆过滤器。先用布隆判断"这个 id 是否可能存在"，一定不存在就直接返回，
   绝不打 DB。布隆只可能误判"可能存在"(false positive，多打一次 DB 而已)，绝不会
   把存在的判成不存在，因此拦截是安全的。

2. 缓存击穿 (breakdown)：某个"热点 key"恰好过期，瞬间大量并发同时回源，压垮 DB。
   方案：互斥锁 / 单飞 (single-flight)。用一个原子占锁 (SETNX) 保证同一时刻只有
   一个线程去重建缓存，其它线程拿不到锁就短暂等待后重读缓存。

3. 缓存雪崩 (avalanche)：大量 key 在同一时刻集体过期，导致 DB 瞬间被压垮。
   方案：TTL 随机抖动。给每个 key 的基础过期时间加上随机偏移，让过期时间分散开。
"""
import random
import time

from django.core.cache import cache
from pybloom_live import BloomFilter

from .models import Problem

# ---------- 布隆过滤器（防穿透）----------
# pybloom_live 现成实现：capacity 容量、error_rate 误判率
_bloom = None


def _get_question_bloom():
    """懒加载：用所有【激活中】题目的 id 建立布隆过滤器。"""
    global _bloom
    if _bloom is None:
        ids = Problem.objects.filter(is_active=True).values_list('id', flat=True)
        bf = BloomFilter(capacity=max(len(ids), 1000), error_rate=0.001)
        for pid in ids:
            bf.add(str(pid))
        _bloom = bf
    return _bloom


def rebuild_question_bloom():
    """题目增删改/上下架后重建布隆（布隆无法删除元素，直接重建最稳）。"""
    global _bloom
    _bloom = None
    _get_question_bloom()


def question_may_exist(pid):
    """False => 一定不存在（穿透拦截）；True => 可能存在（false positive 无害）。"""
    return str(pid) in _get_question_bloom()


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
