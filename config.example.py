# -*- coding: utf-8 -*-
"""
配置模板。复制为 config.py 后填入真实值：

    cp config.example.py config.py

config.py 已被 .gitignore 排除，请不要把真实密钥提交到仓库。
"""

# MySQL 密码（settings.py 里数据库用户固定为 root，库名 ihgs）
DATABASES_PASSWORD = 'your-mysql-password'

# 大模型 API Key
# 注意：变量名沿用历史命名 OPENROUTER_API_KEY，实际调用的是阿里云百炼（DashScope 兼容模式），
# 见 gradingModule/tasks.py 中的 base_url。
OPENROUTER_API_KEY = 'sk-your-api-key'

# 微信小程序凭证
WECHAT_APPID = 'wx-your-appid'
WECHAT_SECRET = 'your-wechat-secret'

# 服务器地址
DOMAIN_ID = '127.0.0.1'
DOMAIN_NAME = 'localhost'
