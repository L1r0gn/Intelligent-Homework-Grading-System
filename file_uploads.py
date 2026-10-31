# -*- coding: utf-8 -*-
"""
图片上传的公共校验与保存逻辑。

小程序端有多处上传（头像、作业内容配图），校验规则必须一致，
所以抽到这里，避免各视图各写一套导致限制不一致。
"""
import os
from uuid import uuid4

from django.core.files.storage import default_storage

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}


def save_image(upload, subdir):
    """
    校验并保存图片，返回相对路径（如 avatars/12/ab12.jpg）。

    校验不通过时抛 ValueError，由调用方转成 400 响应。
    """
    if upload is None:
        raise ValueError('缺少上传文件')

    if upload.size > MAX_IMAGE_SIZE:
        raise ValueError('图片不能超过 5MB')

    ext = os.path.splitext(upload.name or '')[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise ValueError('仅支持 jpg/png/gif/webp/bmp 格式')

    return default_storage.save(f'{subdir}/{uuid4().hex}{ext}', upload)
