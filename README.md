# 网络流量监控系统

macOS 网络流量监控工具，包含数据采集和 Web 可视化界面。

## 📁 目录结构

```
network/
├── traffic_collector.py        # 流量采集脚本（每 5 分钟）
├── web_server.py               # Flask Web 服务
├── data/
│   └── traffic.db              # SQLite 数据库
├── templates/                  # Web 前端模板
│   └── index.html
├── logs/                       # 日志目录
│   ├── monitor.log            # 采集日志
│   ├── monitor.err            # 采集错误日志
│   ├── web_server.log         # Web 服务日志
│   ├── web_server.err         # Web 服务错误日志
│   └── last_alert.txt         # 最后告警记录
├── com.user.networkmonitor.plist  # 监控服务配置
├── com.user.networkweb.plist      # Web 服务配置
└── README.md                   # 本文档
```

## 🚀 安装和启动

### 1. 安装依赖

```bash
pip3 install flask
```

### 2. 启动服务

**方式一：使用 launchd（推荐，开机自启）**

```bash
cd /Users/rhuang/workspace/tools/network

# 加载监控服务（每 5 分钟采集数据）
launchctl load com.user.networkmonitor.plist

# 加载 Web 服务
launchctl load com.user.networkweb.plist
```

**方式二：手动运行**

```bash
cd /Users/rhuang/workspace/tools/network

# 运行一次数据采集
python3 traffic_collector.py

# 启动 Web 服务
python3 web_server.py
```

## 📊 访问界面

- **Web 界面**: http://localhost:5003/
- **数据 API**: http://localhost:5003/api/traffic
- **数据范围**: http://localhost:5003/api/data-range
- **统计信息**: http://localhost:5003/api/stats
- **告警配置**: http://localhost:5003/api/alerts
- **CSV 导出**: http://localhost:5003/api/export/csv

## 🔧 服务管理

### 查看服务状态

```bash
# 查看所有网络相关服务
launchctl list | grep network

# 查看监控服务
launchctl list | grep networkmonitor

# 查看 Web 服务
launchctl list | grep networkweb
```

### 停止服务

```bash
# 停止监控服务
launchctl unload com.user.networkmonitor.plist

# 停止 Web 服务
launchctl unload com.user.networkweb.plist
```

### 重启服务

```bash
# 重启监控服务
launchctl unload com.user.networkmonitor.plist
launchctl load com.user.networkmonitor.plist

# 重启 Web 服务
launchctl unload com.user.networkweb.plist
launchctl load com.user.networkweb.plist
```

### 查看日志

```bash
# 监控服务日志
tail -f logs/monitor.log

# Web 服务日志
tail -f logs/web_server.log

# 错误日志
tail -f logs/monitor.err
tail -f logs/web_server.err
```

## 📈 数据库操作

```bash
# 查看最新数据
sqlite3 data/traffic.db "SELECT * FROM traffic_data ORDER BY id DESC LIMIT 10;"

# 查看数据统计
sqlite3 data/traffic.db \
  "SELECT DATE(timestamp) as date, COUNT(*) as records FROM traffic_data GROUP BY DATE(date);"

# 导出数据
sqlite3 data/traffic.db \
  ".mode csv" ".output traffic_export.csv" "SELECT * FROM traffic_data;"
```

## 🌐 API 接口

### 获取流量数据
```
GET /api/traffic?start=YYYY-MM-DDTHH:MM&end=YYYY-MM-DDTHH:MM
```
返回：流量数据、速度数据、告警信息

### 获取数据范围
```
GET /api/data-range
```
返回：最早和最晚数据时间

### 获取统计信息
```
GET /api/stats
```
返回：总记录数、总流量、最新数据等

### 获取告警配置
```
GET /api/alerts
```
返回：告警阈值和状态

### 导出 CSV
```
GET /api/export/csv?start=YYYY-MM-DDTHH:MM&end=YYYY-MM-DDTHH:MM
```
返回：CSV 文件下载

## ⚙️ 配置说明

### 监控服务配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| StartInterval | 采集间隔（秒） | 300 (5 分钟) |
| WorkingDirectory | 工作目录 | /Users/rhuang/workspace/tools/network |
| StandardOutPath | 输出日志 | logs/monitor.log |
| StandardErrorPath | 错误日志 | logs/monitor.err |

### Web 服务配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| RunAtLoad | 加载时启动 | true |
| KeepAlive | 自动重启 | true |
| WorkingDirectory | 工作目录 | /Users/rhuang/workspace/tools/network |
| Port | 监听端口 | 5003 |

### 告警配置 (web_server.py)

```python
ALERT_CONFIG = {
    'enabled': True,                      # 是否启用告警
    'download_threshold_mb': 100,         # 下载流量阈值 (MB)
    'upload_threshold_mb': 50,            # 上传流量阈值 (MB)
    'speed_threshold_mbps': 10,           # 速度阈值 (Mbps)
    'last_alert_file': 'logs/last_alert.txt'
}
```

### 日志轮转配置

| 日志类型 | 文件大小限制 | 备份数量 |
|---------|-------------|---------|
| monitor.log | 5 MB | 3 |
| monitor.err | 5 MB | 3 |
| web_server.log | 10 MB | 5 |
| web_server.err | 10 MB | 5 |

## 🛠️ 自定义

### 修改采集间隔

编辑 `com.user.networkmonitor.plist`，修改 `StartInterval` 值（秒）：

```xml
<key>StartInterval</key>
<integer>60</integer>  <!-- 改为 1 分钟 -->
```

然后重启服务。

### 修改 Web 端口

编辑 `web_server.py`，修改最后一行：

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False)  # 修改 port 参数
```

### 修改告警阈值

编辑 `web_server.py` 或 `traffic_collector.py` 中的 `ALERT_CONFIG`：

```python
ALERT_CONFIG = {
    'enabled': True,
    'download_threshold_mb': 200,  # 改为 200 MB
    'upload_threshold_mb': 100,    # 改为 100 MB
    'speed_threshold_mbps': 50,    # 改为 50 Mbps
}
```

### 修改数据保留时间

编辑 `traffic_collector.py`，修改 `cleanup_old_data()` 函数中的天数：

```python
thirty_days_ago = datetime.now() - timedelta(days=60)  # 改为 60 天
```

## 🎨 功能特性

### Web 界面功能
- 📊 流量趋势图表（累计流量）
- 🚀 网络速度图表（MB/s）
- 🌓 暗色主题切换（自动保存偏好）
- 🔄 实时监控（10 秒自动刷新）
- 📥 CSV 数据导出
- ⚠️ 流量告警显示
- 📱 响应式设计（支持移动端）
- 🎯 自定义时间范围查询

### 告警功能
- 下载流量超限告警
- 上传流量超限告警
- 下载速度超限告警
- 上传速度超限告警
- 告警去重（避免重复通知）

### 日志轮转
- 自动限制日志文件大小
- 保留指定数量的备份文件
- 防止日志文件无限增长

## 📝 注意事项

1. 数据库会定期清理 30 天前的数据
2. Web 服务默认监听 5003 端口，确保未被占用
3. 首次运行会自动创建数据库
4. 所有日志文件会自动创建并轮转
5. 主题偏好会保存在 localStorage
6. 告警信息会记录在 logs/last_alert.txt

## 🔍 故障排查

### 服务无法启动

```bash
# 检查端口是否被占用
lsof -i :5003

# 检查 Python 是否可用
which python3

# 手动运行测试
cd /Users/rhuang/workspace/tools/network
python3 traffic_collector.py
python3 web_server.py
```

### 数据采集失败

```bash
# 检查 nettop 是否可用
nettop -L 1 -P

# 查看错误日志
cat logs/monitor.err
```

### Web 界面无法访问

```bash
# 检查服务是否运行
launchctl list | grep networkweb

# 测试 API
curl http://localhost:5003/api/data-range

# 查看 Web 日志
cat logs/web_server.log
```

### API 返回错误

```bash
# 测试参数验证
curl "http://localhost:5003/api/traffic?start=invalid"

# 正确格式
curl "http://localhost:5003/api/traffic?start=2026-02-23T10:00&end=2026-02-23T12:00"
```

## 📄 License

Personal Use
