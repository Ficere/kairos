# Kairos 微信小程序部署指南

## 项目结构

```
kairos/
├── api/                    # 后端 API 服务
│   ├── main.py            # FastAPI 入口
│   └── pyproject.toml     # 依赖配置
├── miniprogram/           # 微信小程序前端
│   ├── pages/             # 页面
│   │   ├── index/         # 主页（分析结果列表）
│   │   └── detail/        # 详情页
│   ├── utils/             # 工具函数
│   ├── app.js/json/wxss   # 全局配置
│   └── project.config.json
└── plans/                 # 数据目录（API 读取）
```

## 本地开发测试

### 1. 启动后端 API

```bash
cd api
uv sync
uv run python main.py
# API 运行在 http://localhost:8000
```

验证 API：
```bash
curl http://localhost:8000/api/results
curl http://localhost:8000/api/dates
```

### 2. 配置小程序

1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开开发者工具，选择"导入项目"
3. 选择 `miniprogram/` 目录
4. AppID 可先使用测试号或留空（选择"不使用云服务"）

### 3. 配置 API 地址

编辑 `miniprogram/app.js`，修改 `apiBase`：
```javascript
globalData: {
  apiBase: 'http://localhost:8000'  // 本地测试
}
```

### 4. 关闭域名校验（本地测试）

在开发者工具中：设置 → 项目设置 → 勾选"不校验合法域名"

## 生产部署

### 1. 申请微信小程序账号

1. 访问 [微信公众平台](https://mp.weixin.qq.com/)
2. 注册小程序账号（需企业或个人认证）
3. 获取 AppID（设置 → 基本设置）

### 2. 部署后端 API

#### 方案 A：云服务器 + Nginx

```bash
# 1. 安装依赖
cd api && uv sync

# 2. 使用 gunicorn 运行
uv run gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# 3. Nginx 配置
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 方案 B：Serverless（推荐）

使用阿里云函数计算、腾讯云函数等，无需管理服务器。

### 3. 配置 HTTPS（必须）

小程序要求所有请求必须使用 HTTPS。
- 申请 SSL 证书（Let's Encrypt 免费）
- 配置到 Nginx 或云服务

### 4. 配置服务器域名白名单

1. 登录微信公众平台
2. 开发 → 开发管理 → 开发设置
3. 服务器域名 → 修改
4. 添加 `request合法域名`：`https://api.yourdomain.com`

### 5. 更新小程序 API 地址

```javascript
// miniprogram/app.js
globalData: {
  apiBase: 'https://api.yourdomain.com'
}
```

### 6. 发布小程序

1. 在开发者工具中点击"上传"
2. 填写版本号和描述
3. 登录微信公众平台 → 版本管理 → 提交审核
4. 审核通过后发布

## API 接口文档

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/results` | GET | 获取分析结果，支持 `date` 和 `direction` 参数 |
| `/api/summary` | GET | 获取汇总信息 |
| `/api/dates` | GET | 获取可用日期列表 |
| `/api/detail/{contract}` | GET | 获取品种详情 |

## 常见问题

**Q: 小程序显示"网络错误"**
- 检查 API 服务是否正常运行
- 检查域名白名单是否配置正确
- 确认使用 HTTPS

**Q: 本地测试无法访问 API**
- 确保关闭了"校验合法域名"选项
- 检查 API 地址是否正确

