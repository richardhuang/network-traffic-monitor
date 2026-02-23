# 网络流量监控 - 配置说明

## 📁 配置文件

### 1. 复制配置文件模板

```bash
cd /Users/rhuang/workspace/tools/network
cp config.example.py config.py
```

### 2. 编辑 `config.py`

```python
# Web 服务配置
WEB_HOST = '0.0.0.0'  # 监听地址
WEB_PORT = 5003       # 监听端口（可修改）

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
```

## 🔧 配置项说明

### Web 服务配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `WEB_HOST` | `'0.0.0.0'` | 监听地址，`'0.0.0.0'` 表示监听所有网卡 |
| `WEB_PORT` | `5003` | Web 服务端口，可修改为其他端口（如 8080） |

**示例：修改端口为 8080**
```python
WEB_PORT = 8080
```

然后访问：http://localhost:8080/

### 数据库配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DB_PATH` | `'data/traffic.db'` | SQLite 数据库文件路径 |

### 日志配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LOG_DIR` | `'logs'` | 日志文件目录 |
| `LOG_MAX_BYTES` | `10MB` | 单个日志文件最大大小 |
| `LOG_BACKUP_COUNT` | `5` | 日志备份文件数量 |

### 采集配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `COLLECTION_INTERVAL` | `300` (5 分钟) | 数据采集间隔（秒） |

**注意：** 修改采集间隔需要同时修改 launchd 配置文件

### 告警配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ALERT_ENABLED` | `True` | 是否启用告警 |
| `ALERT_DOWNLOAD_THRESHOLD_MB` | `100` | 下载流量告警阈值（MB） |
| `ALERT_UPLOAD_THRESHOLD_MB` | `50` | 上传流量告警阈值（MB） |
| `ALERT_SPEED_THRESHOLD_MBPS` | `10` | 速度告警阈值（Mbps） |

## 🚀 修改配置后重启服务

```bash
# 停止服务
launchctl unload com.user.networkweb.plist

# 启动服务
launchctl load com.user.networkweb.plist
```

或者强制重启：

```bash
pkill -f "web_server.py"
sleep 1
launchctl load com.user.networkweb.plist
```

## 📝 环境变量（可选）

也可以通过环境变量覆盖配置：

```bash
export NETWORK_MONITOR_PORT=8080
python3 web_server.py
```

## 🔍 验证配置

```bash
# 查看 Web 服务日志
tail -f logs/web_server.log

# 应该看到类似输出：
# Host: 0.0.0.0, Port: 5003
# Alert config: {...}
```

## ⚠️ 注意事项

1. **端口占用**：确保修改的端口未被其他程序占用
2. **防火墙**：如果修改端口，确保防火墙允许该端口
3. **launchd 配置**：修改端口后，launchd 配置仍然有效
4. **浏览器缓存**：修改配置后清除浏览器缓存
