# 🎵 TikTok Comments Analysis Tool

Chrome Extension để crawl và phân tích comments từ video TikTok với AI-powered insights.

## 🏗️ Cấu trúc dự án (Đã dọn dẹp)

```
insight_analysis/
├── backend_api/                    # FastAPI Backend
│   ├── main.py                    # API server chính
│   ├── start_server.py            # Script khởi động server
│   ├── requirements.txt           # Python dependencies
│   ├── downloads/                 # Thư mục lưu data crawled
│   │   └── .gitkeep
│   └── logs/                      # Thư mục logs
│       └── .gitkeep
├── chrome_extension/              # Chrome Extension
│   ├── manifest.json             # Cấu hình extension
│   ├── content.js                # Content script (floating button)
│   ├── background.js             # Service worker
│   ├── popup.html                # Extension popup UI
│   ├── popup.js                  # Popup logic
│   ├── styles.css                # UI styles
│   └── jeglogo.webp             # Logo
├── TikTok_CMT/                   # TikTok Crawler Module
│   ├── crawlers/
│   │   ├── base_crawler.py      # Base crawler class
│   │   ├── tiktok/web/
│   │   │   ├── web_crawler.py   # TikTok web crawler
│   │   │   ├── endpoints.py     # API endpoints
│   │   │   ├── models.py        # Data models
│   │   │   ├── utils.py         # Utility functions
│   │   │   └── config.yaml      # TikTok API config
│   │   ├── douyin/web/          # Douyin crawler (unused)
│   │   └── utils/               # Shared utilities
│   └── requirements.txt          # TikTok crawler dependencies
├── requirements.txt              # Main dependencies
├── README.md                     # Documentation
└── .gitignore                   # Git ignore rules
```

## 🚀 Tính năng chính

### ✅ Đã hoàn thành
- **Floating Button**: Nút nổi trên TikTok video pages
- **Real-time Progress**: Theo dõi tiến độ crawl và analysis
- **AI Analysis**: Phân tích comments bằng Gemini AI
- **PDF Export**: Tạo báo cáo PDF đẹp mắt
- **Custom Analysis**: Tùy chỉnh prompt phân tích
- **Error Handling**: Xử lý lỗi và retry mechanisms
- **Modern UI**: Giao diện đẹp với animations

### 🔧 API Endpoints

```http
# Health Check
GET /health

# Start Crawling
POST /crawl/start
{
  "video_id": "1234567890",
  "video_url": "https://tiktok.com/@user/video/1234567890",
  "max_comments": 1000,
  "include_replies": true
}

# Check Status
GET /crawl/status/{task_id}

# Start Analysis
POST /analyze/start
{
  "task_id": "task-uuid",
  "custom_analysis": "optional custom prompt"
}

# Analysis Status
GET /analyze/status/{analysis_id}
```

## 📦 Cài đặt

### 1. Backend Setup
```bash
# Cài đặt dependencies
pip install -r requirements.txt
pip install -r backend_api/requirements.txt
pip install -r TikTok_CMT/requirements.txt

# Khởi động server
cd backend_api
python start_server.py
```

### 2. Chrome Extension Setup
1. Mở Chrome và vào `chrome://extensions/`
2. Bật "Developer mode"
3. Click "Load unpacked"
4. Chọn thư mục `chrome_extension/`

## 🎯 Sử dụng

1. **Truy cập TikTok video**: `https://www.tiktok.com/@username/video/1234567890`
2. **Click Floating Button**: Button xuất hiện bên phải màn hình
3. **Theo dõi Progress**: Real-time progress tracking
4. **Xem Kết quả**: AI analysis với typewriter effect
5. **Export PDF**: Tạo báo cáo PDF (tùy chọn)

## 🛠️ Development

### Backend Development
```bash
cd backend_api
python main.py
# Server chạy tại http://localhost:8000
```

### Extension Development
```bash
# Reload extension sau khi thay đổi
# Vào chrome://extensions/ và click "Reload"
```

## 📊 Output Format

```json
{
  "comments": [
    {
      "comment_id": "7473559960091542302",
      "post_id": "7471745341226798379",
      "author_nickname": "username",
      "author_uid": "6627852367013167110",
      "comment_text": "Great video!",
      "like_count": 100,
      "reply_comment_total": 6,
      "comment_date": 1740073818
    }
  ],
  "metadata": {
    "video_id": "7471745341226798379",
    "total_comments": 150,
    "total_replies": 45,
    "crawled_at": "2025-01-23T08:21:32.123456"
  }
}
```

## 🔐 Configuration

### TikTok API Config
File: `TikTok_CMT/crawlers/tiktok/web/config.yaml`
```yaml
TokenManager:
  tiktok:
    headers:
      User-Agent: Mozilla/5.0...
      Cookie: tt_csrf_token=...
    proxies:
      http: ""
      https: ""
```

### Backend Config
File: `backend_api/main.py`
```python
# CORS settings
allow_origins=["*"]

# Rate limiting
await asyncio.sleep(0.3)

# Batch size
batch_size = 8
```

## 🧹 Dọn dẹp đã thực hiện

### ✅ Đã xóa
- File trùng lặp và backup
- File debug và test
- File log và data cũ
- Thư mục không cần thiết
- File media không sử dụng
- Git repositories con

### ✅ Đã giữ lại
- Core functionality files
- Essential configurations
- Production-ready code
- Documentation

### ✅ Đã thêm
- `.gitignore` comprehensive
- `.gitkeep` files cho empty directories
- Clean project structure

## 📝 License

MIT License - see LICENSE file for details.

## ⚠️ Disclaimer

Tool này chỉ dành cho mục đích nghiên cứu và phân tích. Vui lòng tuân thủ Terms of Service của TikTok khi sử dụng. 