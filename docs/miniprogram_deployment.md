# Kairos 微信小程序部署指南

## 准备工作

| 项目 | 说明 | 费用 |
| ---- | ---- | ---- |
| 微信小程序账号 | 个人版免费，但类目受限 | 免费 |
| 域名 | 如 `kairos-api.com` | ¥30-60/年 |
| 云服务器 | 腾讯云轻量 2核2G | ¥35/月 |
| SSL 证书 | Let's Encrypt | 免费 |

## 一、申请微信小程序账号

### 1.1 注册流程

1. 访问 [微信公众平台](https://mp.weixin.qq.com/) → 立即注册 → 小程序
2. 填写邮箱、密码，验证邮箱
3. 选择主体类型：**个人**（免费，但不能选金融类目）
4. 绑定管理员微信（扫码验证）

### 1.2 获取 AppID

登录后：开发 → 开发管理 → 开发设置 → 记录 **AppID**

### 1.3 选择服务类目

设置 → 基本设置 → 服务类目 → 添加：**工具 → 信息查询**

> ⚠️ 个人开发者无法选择「金融」类目，建议定位为「数据展示工具」

## 二、部署后端 API（腾讯云轻量服务器）

### 2.1 购买服务器

1. 访问 [腾讯云轻量服务器](https://cloud.tencent.com/product/lighthouse)
2. 选择：Ubuntu 22.04、2核2G、上海/广州
3. 记录**公网 IP**

### 2.2 服务器初始化

```bash
# SSH 连接
ssh ubuntu@你的服务器IP

# 安装依赖
sudo apt update && sudo apt install -y curl git nginx
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 克隆并安装
cd ~ && git clone https://github.com/Ficere/kairos.git
cd kairos && uv sync
```

### 2.3 创建系统服务

```bash
sudo tee /etc/systemd/system/kairos-api.service << 'EOF'
[Unit]
Description=Kairos API Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/kairos
Environment="PATH=/home/ubuntu/.cargo/bin:/usr/bin"
ExecStart=/home/ubuntu/.cargo/bin/uv run kairos-api --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now kairos-api
```

## 三、域名和 HTTPS 配置

### 3.1 购买域名并解析

1. [腾讯云域名](https://dnspod.cloud.tencent.com/) 购买域名
2. DNS 解析添加 A 记录：`api` → 服务器 IP

### 3.2 申请 SSL 证书

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

### 3.3 配置 Nginx

```bash
sudo tee /etc/nginx/sites-available/kairos-api << 'EOF'
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/kairos-api /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3.4 验证

```bash
curl https://api.yourdomain.com/api/dates
```

## 四、配置微信小程序

### 4.1 添加服务器域名白名单

微信公众平台 → 开发 → 开发设置 → 服务器域名 → `request合法域名` 添加：`https://api.yourdomain.com`

### 4.2 更新小程序代码

```javascript
// miniprogram/app.js
globalData: { apiBase: 'https://api.yourdomain.com' }
```

```json
// miniprogram/project.config.json
{ "appid": "你的真实AppID", ... }
```

## 五、上传和发布

### 5.1 使用开发者工具

1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 导入 `miniprogram/` 目录，填写 AppID
3. 测试无误后点击「上传」，填写版本号 `1.0.0`

### 5.2 提交审核

微信公众平台 → 版本管理 → 开发版本 → 提交审核

**审核要点**：
- 避免「投资建议」「荐股」等敏感词
- 确保页面有数据，无空白
- 功能描述与类目一致

### 5.3 发布

审核通过后：版本管理 → 审核版本 → 发布 → 全量发布

## 六、定时数据更新

```bash
crontab -e
# 添加（工作日 9:00 和 14:00 运行）
0 9,14 * * 1-5 cd /home/ubuntu/kairos && uv run kairos-analyze --all >> /tmp/kairos.log 2>&1
```

## 七、本地开发测试

```bash
uv run kairos-api  # 启动 API，访问 http://localhost:8000
```

开发者工具：设置 → 项目设置 → 勾选「不校验合法域名」

## API 接口

| 接口 | 说明 |
| ---- | ---- |
| `GET /api/results?date=&direction=` | 分析结果列表 |
| `GET /api/summary?date=` | 汇总信息 |
| `GET /api/dates` | 可用日期列表 |
| `GET /api/detail/{contract}?date=` | 品种详情 |
| `GET /api/perplexity?date=` | Perplexity 分析 |

## 常见问题

| 问题 | 解决方案 |
| ---- | ---- |
| 网络请求失败 | 检查 API、域名白名单、防火墙 `sudo ufw allow 443` |
| 线上无数据 | 服务器运行 `cd ~/kairos && uv run kairos-analyze --all` |
| 审核被拒 | 避免金融敏感词，确保页面无空白 |
| 证书过期 | `sudo certbot renew && sudo systemctl reload nginx` |
