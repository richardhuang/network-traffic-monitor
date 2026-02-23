# 网络流量监控系统配置文件
# 复制此文件为 config.py 并修改配置

# Web 服务配置
WEB_HOST = '0.0.0.0'
WEB_PORT = 5003

# 数据库配置
DB_PATH = 'data/traffic.db'

# 日志配置
LOG_DIR = 'logs'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# 采集配置
COLLECTION_INTERVAL = 300  # 5 分钟

# 告警配置
ALERT_ENABLED = True
ALERT_DOWNLOAD_THRESHOLD_MB = 100
ALERT_UPLOAD_THRESHOLD_MB = 50
ALERT_SPEED_THRESHOLD_MBPS = 10
