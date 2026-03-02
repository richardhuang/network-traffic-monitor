#!/usr/bin/env python3
"""
Network Traffic Monitor - 5-minute interval version
Collects network traffic data every 5 minutes and stores in SQLite database.
"""

import sqlite3
import time
import subprocess
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

# 配置
DB_PATH = 'data/traffic.db'
LOG_DIR = 'logs'
COLLECTION_INTERVAL = 300  # 5 分钟

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs('data', exist_ok=True)

# 配置日志轮转
monitor_handler = RotatingFileHandler(
    f'{LOG_DIR}/monitor.log',
    maxBytes=5*1024*1024,  # 5MB
    backupCount=3
)
monitor_handler.setLevel(logging.INFO)
monitor_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
monitor_handler.setFormatter(monitor_formatter)

error_handler = RotatingFileHandler(
    f'{LOG_DIR}/monitor.err',
    maxBytes=5*1024*1024,  # 5MB
    backupCount=3
)
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)

logger = logging.getLogger('network_monitor')
logger.setLevel(logging.INFO)
logger.addHandler(monitor_handler)
logger.addHandler(error_handler)

# 告警配置
ALERT_CONFIG = {
    'enabled': True,
    'download_threshold_mb': 100,
    'upload_threshold_mb': 50,
    'speed_threshold_mbps': 10,
    'last_alert_file': f'{LOG_DIR}/last_alert.txt'
}

def get_network_stats():
    """Get network statistics using netstat on macOS (no popup window)"""
    try:
        result = subprocess.run(
            ['/usr/sbin/netstat', '-ib'],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            logger.error(f"Error running netstat: {result.stderr}")
            return None, None

        total_received = 0
        total_sent = 0

        for line in result.stdout.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 10 and parts[0].startswith('en'):
                # Ibytes is column 6, Obytes is column 9
                try:
                    total_received += int(parts[6])
                    total_sent += int(parts[9])
                except ValueError:
                    continue

        return total_received, total_sent

    except Exception as e:
        logger.error(f"Error getting network stats: {e}")
        return None, None

def init_database():
    """Initialize the database if it doesn't exist"""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                bytes_received INTEGER,
                bytes_sent INTEGER,
                download_speed REAL,
                upload_speed REAL
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully!")

def get_previous_data():
    """获取上一次采集的数据用于计算速度"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, bytes_received, bytes_sent
            FROM traffic_data
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'timestamp': datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S'),
                'bytes_received': row[1],
                'bytes_sent': row[2]
            }
        return None
    except Exception as e:
        logger.error(f"Error getting previous data: {e}")
        return None

def calculate_speed(current, previous, interval_seconds):
    """计算速度 (bytes/s)"""
    if previous is None:
        return 0.0
    
    diff = current - previous
    if diff < 0:
        return 0.0  # 计数器重置
    
    return diff / interval_seconds

def check_traffic_alert(received, sent, interval_seconds=COLLECTION_INTERVAL):
    """检查流量是否触发告警"""
    if not ALERT_CONFIG['enabled']:
        return None
    
    received_mb = received / (1024 * 1024)
    sent_mb = sent / (1024 * 1024)
    
    download_speed_mbps = (received * 8) / (interval_seconds * 1000000)
    upload_speed_mbps = (sent * 8) / (interval_seconds * 1000000)
    
    alerts = []
    
    if received_mb > ALERT_CONFIG['download_threshold_mb']:
        alerts.append(f"下载流量告警：{received_mb:.2f} MB (阈值：{ALERT_CONFIG['download_threshold_mb']} MB)")
    
    if sent_mb > ALERT_CONFIG['upload_threshold_mb']:
        alerts.append(f"上传流量告警：{sent_mb:.2f} MB (阈值：{ALERT_CONFIG['upload_threshold_mb']} MB)")
    
    if download_speed_mbps > ALERT_CONFIG['speed_threshold_mbps']:
        alerts.append(f"下载速度告警：{download_speed_mbps:.2f} Mbps (阈值：{ALERT_CONFIG['speed_threshold_mbps']} Mbps)")
    
    if upload_speed_mbps > ALERT_CONFIG['speed_threshold_mbps']:
        alerts.append(f"上传速度告警：{upload_speed_mbps:.2f} Mbps (阈值：{ALERT_CONFIG['speed_threshold_mbps']} Mbps)")
    
    if alerts:
        alert_msg = "\n".join(alerts)
        last_alert = ""
        if os.path.exists(ALERT_CONFIG['last_alert_file']):
            with open(ALERT_CONFIG['last_alert_file'], 'r') as f:
                last_alert = f.read().strip()
        
        if alert_msg != last_alert:
            with open(ALERT_CONFIG['last_alert_file'], 'w') as f:
                f.write(alert_msg)
            logger.warning(f"🚨 TRAFFIC ALERT: {alert_msg}")
            return alert_msg
    
    return None

def save_traffic_data():
    """Save current network traffic data to database with speed calculation"""
    init_database()

    received, sent = get_network_stats()
    if received is None or sent is None:
        logger.error("Failed to get network statistics")
        return False

    # 获取上一次的数据用于计算速度
    prev_data = get_previous_data()
    current_time = datetime.now()
    
    # 计算时间间隔
    if prev_data:
        time_diff = (current_time - prev_data['timestamp']).total_seconds()
    else:
        time_diff = COLLECTION_INTERVAL
    
    # 计算速度 (bytes/s)
    download_speed = calculate_speed(received, prev_data['bytes_received'] if prev_data else None, time_diff)
    upload_speed = calculate_speed(sent, prev_data['bytes_sent'] if prev_data else None, time_diff)
    
    # 保存到数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO traffic_data (timestamp, bytes_received, bytes_sent, download_speed, upload_speed)
        VALUES (?, ?, ?, ?, ?)
    ''', (current_time.strftime('%Y-%m-%d %H:%M:%S'), received, sent, download_speed, upload_speed))
    conn.commit()
    conn.close()

    # 转换单位用于显示
    received_mb = received / (1024 * 1024)
    sent_mb = sent / (1024 * 1024)
    download_mbps = (download_speed * 8) / 1000000
    upload_mbps = (upload_speed * 8) / 1000000
    
    logger.info(f"Saved: {received_mb:.2f} MB ↓, {sent_mb:.2f} MB ↑ | Speed: {download_mbps:.2f} Mbps ↓, {upload_mbps:.2f} Mbps ↑")
    
    # 检查告警
    check_traffic_alert(received, sent, time_diff)
    
    return True

def cleanup_old_data():
    """Remove data older than 30 days"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    thirty_days_ago = datetime.now() - timedelta(days=30)
    cursor.execute('''
        DELETE FROM traffic_data
        WHERE timestamp < ?
    ''', (thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S'),))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old records")

def main():
    """Main function to collect and save data"""
    logger.info("Collecting network traffic data...")
    if save_traffic_data():
        cleanup_old_data()
        return True
    return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Network Traffic Monitor Started")
    logger.info(f"Collection interval: {COLLECTION_INTERVAL} seconds")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Alert config: {ALERT_CONFIG}")
    logger.info("=" * 50)
    
    success = main()
    sys.exit(0 if success else 1)
