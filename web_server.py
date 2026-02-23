from flask import Flask, render_template, jsonify, request, send_file
import sqlite3
import json
import os
import csv
import io
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

app = Flask(__name__)

# 加载配置
try:
    import config
    WEB_HOST = config.WEB_HOST
    WEB_PORT = config.WEB_PORT
    DB_PATH = config.DB_PATH
    LOG_DIR = config.LOG_DIR
    LOG_MAX_BYTES = config.LOG_MAX_BYTES
    LOG_BACKUP_COUNT = config.LOG_BACKUP_COUNT
    ALERT_ENABLED = config.ALERT_ENABLED
    ALERT_DOWNLOAD_THRESHOLD_MB = config.ALERT_DOWNLOAD_THRESHOLD_MB
    ALERT_UPLOAD_THRESHOLD_MB = config.ALERT_UPLOAD_THRESHOLD_MB
    ALERT_SPEED_THRESHOLD_MBPS = config.ALERT_SPEED_THRESHOLD_MBPS
except ImportError:
    # 默认配置（如果 config.py 不存在）
    WEB_HOST = '0.0.0.0'
    WEB_PORT = 5003
    DB_PATH = 'data/traffic.db'
    LOG_DIR = 'logs'
    LOG_MAX_BYTES = 10 * 1024 * 1024
    LOG_BACKUP_COUNT = 5
    ALERT_ENABLED = True
    ALERT_DOWNLOAD_THRESHOLD_MB = 100
    ALERT_UPLOAD_THRESHOLD_MB = 50
    ALERT_SPEED_THRESHOLD_MBPS = 10

# 配置日志轮转
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Web 服务日志轮转配置
web_handler = RotatingFileHandler(
    f'{LOG_DIR}/web_server.log',
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT
)
web_handler.setLevel(logging.INFO)
web_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
web_handler.setFormatter(web_formatter)
app.logger.addHandler(web_handler)
app.logger.setLevel(logging.INFO)

# 错误日志轮转配置
error_handler = RotatingFileHandler(
    f'{LOG_DIR}/web_server.err',
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT
)
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)
app.logger.addHandler(error_handler)

# 告警配置
ALERT_CONFIG = {
    'enabled': ALERT_ENABLED,
    'download_threshold_mb': ALERT_DOWNLOAD_THRESHOLD_MB,
    'upload_threshold_mb': ALERT_UPLOAD_THRESHOLD_MB,
    'speed_threshold_mbps': ALERT_SPEED_THRESHOLD_MBPS,
    'last_alert_file': f'{LOG_DIR}/last_alert.txt'
}

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def validate_datetime(dt_string):
    """验证日期时间格式"""
    formats = [
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d %H:%M:%S'
    ]
    for fmt in formats:
        try:
            return datetime.strptime(dt_string, fmt)
        except ValueError:
            continue
    return None

def check_traffic_alert(received, sent, interval_seconds=300):
    """检查流量是否触发告警"""
    if not ALERT_CONFIG['enabled']:
        return None
    
    received_mb = received / (1024 * 1024)
    sent_mb = sent / (1024 * 1024)
    
    # 计算速度 (Mbps)
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
        # 检查是否已经发送过相同告警（避免重复）
        last_alert = ""
        if os.path.exists(ALERT_CONFIG['last_alert_file']):
            with open(ALERT_CONFIG['last_alert_file'], 'r') as f:
                last_alert = f.read().strip()
        
        if alert_msg != last_alert:
            with open(ALERT_CONFIG['last_alert_file'], 'w') as f:
                f.write(alert_msg)
            return alert_msg
    
    return None

@app.route('/')
def index():
    app.logger.info('Index page requested')
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT MIN(timestamp) as min_time, MAX(timestamp) as max_time FROM traffic_data')
    range_row = cursor.fetchone()

    if range_row and range_row['min_time'] and range_row['max_time']:
        min_time = datetime.strptime(range_row['min_time'], '%Y-%m-%d %H:%M:%S')
        max_time = datetime.strptime(range_row['max_time'], '%Y-%m-%d %H:%M:%S')

        now = datetime.now()
        default_end = max_time.strftime('%Y-%m-%dT%H:%M')
        twenty_four_hours_ago = now - timedelta(hours=24)
        if min_time > twenty_four_hours_ago:
            default_start = min_time.strftime('%Y-%m-%dT%H:%M')
        else:
            default_start = twenty_four_hours_ago.strftime('%Y-%m-%dT%H:%M')
    else:
        now = datetime.now()
        default_end = now.strftime('%Y-%m-%dT%H:%M')
        default_start = (now - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M')

    conn.close()
    return render_template('index.html', default_start_time=default_start, default_end_time=default_end)

@app.route('/api/traffic')
def get_traffic_data():
    """获取流量数据，支持时间范围查询"""
    try:
        start_time = request.args.get('start', None)
        end_time = request.args.get('end', None)
        
        # 参数验证
        if start_time or end_time:
            if start_time and not validate_datetime(start_time):
                app.logger.error(f'Invalid start time format: {start_time}')
                return jsonify({
                    'error': f'无效的开始时间格式：{start_time}。请使用格式：YYYY-MM-DDTHH:MM'
                }), 400
            
            if end_time and not validate_datetime(end_time):
                app.logger.error(f'Invalid end time format: {end_time}')
                return jsonify({
                    'error': f'无效的结束时间格式：{end_time}。请使用格式：YYYY-MM-DDTHH:MM'
                }), 400
            
            # 验证时间范围合理性
            if start_time and end_time:
                start_dt = validate_datetime(start_time)
                end_dt = validate_datetime(end_time)
                if start_dt > end_dt:
                    return jsonify({
                        'error': '开始时间不能晚于结束时间'
                    }), 400
                
                # 限制查询范围最大为 31 天
                if (end_dt - start_dt).days > 31:
                    return jsonify({
                        'error': '查询范围不能超过 31 天'
                    }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        if start_time and end_time:
            start_db = start_time.replace('T', ' ') + ':00'
            end_db = end_time.replace('T', ' ') + ':00'

            cursor.execute('''
                SELECT timestamp, bytes_received, bytes_sent
                FROM traffic_data
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (start_db, end_db))
            app.logger.info(f'Query traffic data from {start_db} to {end_db}')
        else:
            twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                SELECT timestamp, bytes_received, bytes_sent
                FROM traffic_data
                WHERE timestamp >= ?
                ORDER BY timestamp
            ''', (twenty_four_hours_ago,))
            app.logger.info('Query last 24 hours traffic data')

        rows = cursor.fetchall()
        conn.close()

        timestamps = []
        received = []  # 累计值
        sent = []      # 累计值
        incremental_received = []  # 增量值（每 5 分钟）
        incremental_sent = []      # 增量值（每 5 分钟）
        download_speeds = []
        upload_speeds = []
        total_received = 0
        total_sent = 0
        
        prev_received = None
        prev_sent = None
        prev_timestamp = None

        for row in rows:
            timestamps.append(row['timestamp'])
            received.append(row['bytes_received'])
            sent.append(row['bytes_sent'])
            total_received = row['bytes_received']
            total_sent = row['bytes_sent']
            
            # 计算增量流量（bytes）
            if prev_received is not None:
                inc_received = row['bytes_received'] - prev_received
                inc_sent = row['bytes_sent'] - prev_sent
                # 如果差值为负，说明计数器重置了，使用当前值作为增量
                incremental_received.append(max(0, inc_received))
                incremental_sent.append(max(0, inc_sent))
            else:
                incremental_received.append(0)
                incremental_sent.append(0)
            
            # 计算速度 (bytes/s)
            if prev_received is not None and prev_timestamp:
                current_ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                time_diff = (current_ts - prev_timestamp).total_seconds()
                if time_diff > 0:
                    download_speed = (row['bytes_received'] - prev_received) / time_diff
                    upload_speed = (row['bytes_sent'] - prev_sent) / time_diff
                    download_speeds.append(max(0, download_speed))
                    upload_speeds.append(max(0, upload_speed))
                else:
                    download_speeds.append(0)
                    upload_speeds.append(0)
            else:
                download_speeds.append(0)
                upload_speeds.append(0)
            
            prev_received = row['bytes_received']
            prev_sent = row['bytes_sent']
            prev_timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')

        # 检查告警
        alerts = None
        if rows:
            latest_row = rows[-1]
            alert_msg = check_traffic_alert(latest_row['bytes_received'], latest_row['bytes_sent'])
            if alert_msg:
                alerts = alert_msg
                app.logger.warning(f'Traffic alert: {alert_msg}')

        return jsonify({
            'timestamps': timestamps,
            'received': received,
            'sent': sent,
            'incremental_received': incremental_received,
            'incremental_sent': incremental_sent,
            'download_speeds': download_speeds,
            'upload_speeds': upload_speeds,
            'total_received': total_received,
            'total_sent': total_sent,
            'alerts': alerts
        })

    except Exception as e:
        app.logger.error(f'Error in get_traffic_data: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/data-range')
def get_data_range():
    """获取数据时间范围"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT MIN(timestamp) as min_time, MAX(timestamp) as max_time FROM traffic_data')
        row = cursor.fetchone()
        conn.close()

        if row and row['min_time'] and row['max_time']:
            return jsonify({
                'min_time': row['min_time'],
                'max_time': row['max_time']
            })
        else:
            return jsonify({'error': '暂无数据'}), 404

    except Exception as e:
        app.logger.error(f'Error in get_data_range: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts')
def get_alerts():
    """获取告警配置和状态"""
    try:
        return jsonify({
            'enabled': ALERT_CONFIG['enabled'],
            'download_threshold_mb': ALERT_CONFIG['download_threshold_mb'],
            'upload_threshold_mb': ALERT_CONFIG['upload_threshold_mb'],
            'speed_threshold_mbps': ALERT_CONFIG['speed_threshold_mbps']
        })
    except Exception as e:
        app.logger.error(f'Error in get_alerts: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/csv')
def export_csv():
    """导出流量数据为 CSV 文件"""
    try:
        start_time = request.args.get('start', None)
        end_time = request.args.get('end', None)
        
        conn = get_db_connection()
        cursor = conn.cursor()

        if start_time and end_time:
            start_db = start_time.replace('T', ' ') + ':00'
            end_db = end_time.replace('T', ' ') + ':00'
            cursor.execute('''
                SELECT timestamp, bytes_received, bytes_sent
                FROM traffic_data
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (start_db, end_db))
        else:
            cursor.execute('''
                SELECT timestamp, bytes_received, bytes_sent
                FROM traffic_data
                ORDER BY timestamp
            ''')

        rows = cursor.fetchall()
        conn.close()

        # 创建 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['时间戳', '接收流量 (Bytes)', '发送流量 (Bytes)', '接收流量 (MB)', '发送流量 (MB)'])
        
        for row in rows:
            writer.writerow([
                row['timestamp'],
                row['bytes_received'],
                row['bytes_sent'],
                round(row['bytes_received'] / (1024 * 1024), 2),
                round(row['bytes_sent'] / (1024 * 1024), 2)
            ])

        output.seek(0)
        
        filename = f'traffic_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        app.logger.error(f'Error in export_csv: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """获取统计数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute('SELECT COUNT(*) as count FROM traffic_data')
        total_records = cursor.fetchone()['count']
        
        # 数据范围
        cursor.execute('SELECT MIN(timestamp) as min_time, MAX(timestamp) as max_time FROM traffic_data')
        range_row = cursor.fetchone()
        
        # 最新数据
        cursor.execute('''
            SELECT bytes_received, bytes_sent, timestamp 
            FROM traffic_data 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        latest = cursor.fetchone()
        
        # 计算总流量
        cursor.execute('SELECT SUM(bytes_received) as total_in, SUM(bytes_sent) as total_out FROM traffic_data')
        sum_row = cursor.fetchone()
        
        conn.close()
        
        stats = {
            'total_records': total_records,
            'min_time': range_row['min_time'] if range_row else None,
            'max_time': range_row['max_time'] if range_row else None,
            'latest_received': latest['bytes_received'] if latest else 0,
            'latest_sent': latest['bytes_sent'] if latest else 0,
            'latest_timestamp': latest['timestamp'] if latest else None,
            'total_received_sum': sum_row['total_in'] if sum_row and sum_row['total_in'] else 0,
            'total_sent_sum': sum_row['total_out'] if sum_row and sum_row['total_out'] else 0
        }
        
        return jsonify(stats)
        
    except Exception as e:
        app.logger.error(f'Error in get_stats: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.logger.info('Starting Network Traffic Web Server...')
    app.logger.info(f'Host: {WEB_HOST}, Port: {WEB_PORT}')
    app.logger.info(f'Alert config: {ALERT_CONFIG}')
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)
