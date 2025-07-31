#!/usr/bin/env python3
# TikTok Comments Crawler - FastAPI Backend

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import uuid
import json
import os
import sys
import time
import markdown
import re
from datetime import datetime
from pathlib import Path
import google.generativeai as genai

# Import TikTok crawler
from crawlers.tiktok.web.web_crawler import TikTokWebCrawler
from crawlers.tiktok.web.utils import TokenManager

# Load GEMINI_API_KEY from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️  GEMINI_API_KEY environment variable not set. Analysis features will be disabled.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Analysis prompt for TikTok POD comments
ANALYSIS_PROMPT = """# PROMPT PHÂN TÍCH COMMENT VIDEO TIKTOK POD

Bạn là chuyên gia R&D sản phẩm Print On Demand (POD) trên TikTok US.

Tôi sẽ cung cấp cho bạn các comment từ một video TikTok viral về sản phẩm POD. Nhiệm vụ của bạn là phân tích và trích xuất insight để cải tiến sản phẩm và xây dựng chiến lược truyền thông phù hợp.

## 1. Phân loại comment theo cảm xúc – hành vi

Phân nhóm các comment vào các loại sau:
- Hài hước
- Cảm động
- Bất ngờ
- Hỏi mua / chốt đơn
- Phàn nàn / khó chịu
- Tag người khác
- Đồng cảm

Với mỗi nhóm:
- Trích dẫn 2–3 comment tiêu biểu
- Phân tích insight rút ra
- Gợi ý hook truyền thông hoặc thông điệp phù hợp

## 2. Trích xuất từ khóa người dùng dùng để gọi tên sản phẩm

- Liệt kê các từ khóa tự nhiên người dùng dùng để gọi tên sản phẩm trong comment
- Gợi ý cách tối ưu caption, tiêu đề, hashtag dựa trên các từ khóa này

## 3. Phân tích rào cản và đề xuất cải tiến sản phẩm

- Từ những comment góp ý hoặc phàn nàn, chỉ ra:
  - Những điểm hạn chế hoặc rào cản khách hàng gặp phải
  - Đề xuất rõ ràng về thay đổi design, form sản phẩm, màu sắc, v.v.

## 4. Viết insight và tạo hook truyền thông

- Tổng hợp 3–5 insight sâu sắc từ tập comment
- Với mỗi insight, viết 3 câu hook truyền thông TikTok
- Hook nên:
  - Sử dụng đúng ngôn ngữ khách đang dùng
  - Ngắn gọn, dễ viral
  - Có phiên bản tiếng Việt và tiếng Anh nếu phù hợp

**Lưu ý:** Nếu khách dùng từ "hay", "thật", "sốc", v.v. thì hãy giữ nguyên ngữ điệu, không cần viết lại cho hay hơn. Giữ đúng chất của người comment.

## 5. Gợi ý thêm các góc nhìn khác

- Nếu phát hiện thêm insight hoặc nhóm khách tiềm năng chưa khai thác, hãy đề xuất thêm các hướng truyền thông phụ hoặc chiến lược sáng tạo.

## FORMAT OUTPUT:

**QUAN TRỌNG:** Trả về response dưới dạng Markdown format ONLY. Không bao gồm thẻ `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` hay bất kỳ HTML document structure nào. Chỉ sử dụng Markdown formatting (headers với #, tables với |, lists với -, bold với **text**, etc.).
"""

app = FastAPI(
    title="TikTok Comments Crawler API",
    description="Backend API for Chrome Extension to crawl TikTok comments",
    version="1.0.0"
)

# CORS middleware for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extensions
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory task storage (use Redis for production)
tasks: Dict[str, Dict[str, Any]] = {}
analyses: Dict[str, Dict[str, Any]] = {}
downloads_dir = Path("downloads")
downloads_dir.mkdir(exist_ok=True)

# Request/Response Models
class CrawlRequest(BaseModel):
    video_id: str
    video_url: Optional[str] = None
    max_comments: Optional[int] = 1000
    include_replies: Optional[bool] = True

class CrawlResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed, cancelled
    progress: float  # 0-100
    message: str
    stats: Optional[Dict[str, Any]] = None
    download_url: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Analysis Models
class AnalysisRequest(BaseModel):
    task_id: str
    custom_analysis: Optional[str] = None

class AnalysisResponse(BaseModel):
    analysis_id: str
    task_id: str
    status: str
    message: str

class AnalysisStatus(BaseModel):
    analysis_id: str
    task_id: str
    status: str  # analyzing, completed, failed
    progress: float  # 0-100
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

@app.get("/")
async def root():
    return {"message": "TikTok Comments Crawler API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/crawl/start", response_model=CrawlResponse)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """Start crawling TikTok comments"""
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Initialize task
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0.0,
        "message": "Initializing crawler...",
        "stats": {"comments": 0, "replies": 0, "duration": 0},
        "download_url": None,
        "error": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "request": request.dict()
    }
    
    # Start background task
    background_tasks.add_task(crawl_video_comments, task_id, request)
    
    return CrawlResponse(
        task_id=task_id,
        status="pending",
        message="Crawling task started"
    )

@app.get("/crawl/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get crawling task status"""
    
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return TaskStatus(**task)

@app.post("/crawl/cancel")
async def cancel_crawl(task_id: Optional[str] = None):
    """Cancel crawling task"""
    
    if task_id:
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if tasks[task_id]["status"] in ["pending", "running"]:
            tasks[task_id]["status"] = "cancelled"
            tasks[task_id]["message"] = "Cancelled by user"
            tasks[task_id]["updated_at"] = datetime.now()
            
        return {"message": "Task cancelled"}
    else:
        # Cancel all running tasks
        cancelled_count = 0
        for task in tasks.values():
            if task["status"] in ["pending", "running"]:
                task["status"] = "cancelled"
                task["message"] = "Cancelled by user"
                task["updated_at"] = datetime.now()
                cancelled_count += 1
        
        return {"message": f"Cancelled {cancelled_count} tasks"}

@app.get("/crawl/list")
async def list_tasks():
    """List all crawling tasks"""
    
    return {
        "tasks": list(tasks.values()),
        "total": len(tasks)
    }

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download crawled data file"""
    
    file_path = downloads_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/json',
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.get("/data/{filename}")
async def get_json_data(filename: str):
    """Get JSON data directly for Chrome Extension"""
    
    file_path = downloads_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

@app.delete("/crawl/cleanup")
async def cleanup_tasks():
    """Cleanup old completed tasks"""
    
    removed_count = 0
    task_ids_to_remove = []
    
    for task_id, task in tasks.items():
        if task["status"] in ["completed", "failed", "cancelled"]:
            # Remove tasks older than 1 hour
            age = datetime.now() - task["created_at"]
            if age.total_seconds() > 3600:
                task_ids_to_remove.append(task_id)
    
    for task_id in task_ids_to_remove:
        del tasks[task_id]
        removed_count += 1
    
    return {"message": f"Removed {removed_count} old tasks"}

# Analysis Endpoints
@app.post("/analyze/start", response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Start GPT analysis of crawled comments"""
    
    # Validate task exists and is completed
    if request.task_id not in tasks:
        raise HTTPException(status_code=404, detail="Crawl task not found")
    
    task = tasks[request.task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Crawl task not completed yet")
    
    # Create analysis task
    analysis_id = str(uuid.uuid4())
    analyses[analysis_id] = {
        "analysis_id": analysis_id,
        "task_id": request.task_id,
        "status": "pending",
        "progress": 0.0,
        "message": "Analysis queued",
        "result": None,
        "error": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    # Start background analysis
    background_tasks.add_task(
        analyze_comments_with_gpt, 
        analysis_id, 
        request.task_id, 
        request.custom_analysis
    )
    
    return AnalysisResponse(
        analysis_id=analysis_id,
        task_id=request.task_id,
        status="pending",
        message="Analysis started"
    )

@app.get("/analyze/status/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    """Get analysis task status"""
    
    if analysis_id not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = analyses[analysis_id]
    return AnalysisStatus(**analysis)

@app.post("/analyze/cancel")
async def cancel_analysis(analysis_id: str = None):
    """Cancel analysis task(s)"""
    
    if analysis_id:
        if analysis_id not in analyses:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analyses[analysis_id]["status"] = "cancelled"
        analyses[analysis_id]["message"] = "Cancelled by user"
        analyses[analysis_id]["updated_at"] = datetime.now()
        
        return {"message": "Analysis cancelled"}
    else:
        # Cancel all running analyses
        cancelled_count = 0
        for analysis in analyses.values():
            if analysis["status"] in ["pending", "analyzing"]:
                analysis["status"] = "cancelled"
                analysis["message"] = "Cancelled by user"
                analysis["updated_at"] = datetime.now()
                cancelled_count += 1
        
        return {"message": f"Cancelled {cancelled_count} analyses"}

@app.get("/analyze/list")
async def list_analyses():
    """List all analysis tasks"""
    
    return {
        "analyses": list(analyses.values()),
        "total": len(analyses)
    }

@app.delete("/analyze/cleanup")
async def cleanup_analyses():
    """Cleanup old completed analyses"""
    
    removed_count = 0
    analysis_ids_to_remove = []
    
    for analysis_id, analysis in analyses.items():
        if analysis["status"] in ["completed", "failed", "cancelled"]:
            # Remove analyses older than 2 hours
            age = datetime.now() - analysis["created_at"]
            if age.total_seconds() > 7200:
                analysis_ids_to_remove.append(analysis_id)
    
    for analysis_id in analysis_ids_to_remove:
        del analyses[analysis_id]
        removed_count += 1
    
    return {"message": f"Removed {removed_count} old analyses"}

async def crawl_video_comments(task_id: str, request: CrawlRequest):
    """Background task to crawl TikTok comments"""
    
    start_time = time.time()
    
    try:
        # Update task status
        tasks[task_id]["status"] = "running"
        tasks[task_id]["message"] = "Getting comments..."
        tasks[task_id]["updated_at"] = datetime.now()
        
        # Initialize crawler
        crawler = TikTokWebCrawler()
        all_comments = []
        
        # Fetch comments with progress tracking
        tasks[task_id]["message"] = "Fetching comments..."
        tasks[task_id]["progress"] = 10.0
        
        comments = await fetch_comments_with_progress(crawler, request.video_id, task_id)
        all_comments.extend(comments)
        
        # Update progress
        tasks[task_id]["progress"] = 50.0
        tasks[task_id]["stats"]["comments"] = len(comments)
        tasks[task_id]["message"] = f"Found {len(comments)} comments"
        
        # Fetch replies if requested
        if request.include_replies:
            tasks[task_id]["message"] = "Fetching replies..."
            tasks[task_id]["progress"] = 60.0
            
            reply_counts = await fetch_replies_with_progress(
                crawler, request.video_id, comments, task_id
            )
            
            total_replies = sum(reply_counts.values())
            tasks[task_id]["stats"]["replies"] = total_replies
        else:
            reply_counts = {}
        
        # Format data
        tasks[task_id]["message"] = "Formatting data..."
        tasks[task_id]["progress"] = 90.0
        
        formatted_data = format_crawled_data(comments, request.video_id, reply_counts)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tiktok_comments_{request.video_id}_{timestamp}.json"
        file_path = downloads_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=2)
        
        # Complete task
        duration = int(time.time() - start_time)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100.0
        tasks[task_id]["message"] = "Crawling completed successfully!"
        tasks[task_id]["stats"]["duration"] = duration
        tasks[task_id]["download_url"] = f"/download/{filename}"
        tasks[task_id]["updated_at"] = datetime.now()
        
    except Exception as e:
        # Handle errors
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["message"] = f"Crawling failed: {str(e)}"
        tasks[task_id]["updated_at"] = datetime.now()
        
        print(f"Crawling error for task {task_id}: {e}")

async def fetch_comments_with_progress(crawler, video_id: str, task_id: str):
    """Fetch comments with progress updates"""
    
    all_comments = []
    has_more = True
    cursor = 0
    page = 0
    
    while has_more and tasks[task_id]["status"] == "running":
        try:
            response = await crawler.fetch_post_comment(
                aweme_id=video_id, cursor=cursor, count=20
            )
            
            comments = response.get("comments", [])
            all_comments.extend(comments)
            
            has_more = response.get("has_more", False)
            cursor = response.get("cursor", 0)
            page += 1
            
            # Update progress (10% to 50%)
            progress = min(10 + (page * 2), 50)
            tasks[task_id]["progress"] = progress
            tasks[task_id]["message"] = f"Fetched {len(all_comments)} comments..."
            tasks[task_id]["stats"]["comments"] = len(all_comments)
            
            await asyncio.sleep(0.3)  # Rate limiting
            
        except Exception as e:
            print(f"Error fetching comments page {page}: {e}")
            break
    
    return all_comments

async def fetch_replies_with_progress(crawler, video_id: str, comments: list, task_id: str):
    """Fetch replies with progress updates"""
    
    reply_counts = {}
    valid_comments = [c for c in comments if c.get("cid")]
    
    if not valid_comments:
        return reply_counts
    
    # Process in batches
    batch_size = 8
    processed = 0
    
    for i in range(0, len(valid_comments), batch_size):
        if tasks[task_id]["status"] != "running":
            break
            
        batch = valid_comments[i:i+batch_size]
        
        # Create tasks for batch
        tasks_batch = []
        for comment in batch:
            task = fetch_comment_replies(crawler, video_id, comment["cid"])
            tasks_batch.append(task)
        
        # Execute batch
        try:
            replies_list = await asyncio.gather(*tasks_batch, return_exceptions=True)
            
            # Process results
            for j, replies in enumerate(replies_list):
                if not isinstance(replies, Exception):
                    comment_id = batch[j]["cid"]
                    reply_counts[comment_id] = len(replies)
            
            processed += len(batch)
            
            # Update progress (50% to 85%)
            progress = 50 + ((processed / len(valid_comments)) * 35)
            total_replies = sum(reply_counts.values())
            
            tasks[task_id]["progress"] = progress
            tasks[task_id]["message"] = f"Processed {processed}/{len(valid_comments)} comments"
            tasks[task_id]["stats"]["replies"] = total_replies
            
            if i + batch_size < len(valid_comments):
                await asyncio.sleep(0.5)  # Rate limiting between batches
                
        except Exception as e:
            print(f"Error in batch {i//batch_size}: {e}")
    
    return reply_counts

async def fetch_comment_replies(crawler, video_id: str, comment_id: str):
    """Fetch replies for a single comment"""
    
    all_replies = []
    has_more = True
    cursor = 0
    
    while has_more:
        try:
            response = await crawler.fetch_post_comment_reply(
                item_id=video_id, comment_id=comment_id, cursor=cursor, count=20
            )
            
            replies = response.get("comments", [])
            all_replies.extend(replies)
            
            has_more = response.get("has_more", False)
            cursor = response.get("cursor", 0)
            
            await asyncio.sleep(0.2)  # Rate limiting
            
        except Exception as e:
            print(f"Error fetching replies for comment {comment_id}: {e}")
            break
    
    return all_replies

def format_crawled_data(comments: list, video_id: str, reply_counts: dict):
    """Format crawled data to standard structure"""
    
    formatted_comments = []
    
    for comment in comments:
        user = comment.get("user", {})
        formatted_comment = {
            "comment_id": comment.get("cid", ""),
            "post_id": video_id,
            "author_nickname": user.get("nickname", ""),
            "author_uid": user.get("uid", ""),
            "author_unique_id": user.get("unique_id", ""),
            "comment_text": comment.get("text", ""),
            "like_count": comment.get("digg_count", 0),
            "reply_comment_total": reply_counts.get(comment.get("cid"), 0),
            "comment_date": comment.get("create_time", 0)
        }
        formatted_comments.append(formatted_comment)
    
    return {
        "comments": formatted_comments,
        "metadata": {
            "video_id": video_id,
            "total_comments": len(formatted_comments),
            "total_replies": sum(reply_counts.values()),
            "crawled_at": datetime.now().isoformat()
        }
    }

# Markdown to HTML Conversion Function
def convert_markdown_to_html(text: str) -> str:
    """Convert markdown text to HTML, with enhanced table formatting"""
    
    # First, check if GPT returned a full HTML document and extract content
    content_text = extract_html_content(text)
    
    # Configure markdown with table extension
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'nl2br'])
    
    # Convert markdown to HTML
    html = md.convert(content_text)
    
    # Additional processing for better table styling
    # Add CSS classes to tables for custom styling
    html = re.sub(r'<table>', '<table class="analysis-table">', html)
    html = re.sub(r'<thead>', '<thead class="analysis-thead">', html)
    html = re.sub(r'<tbody>', '<tbody class="analysis-tbody">', html)
    
    # Improve line breaks and paragraphs for better readability
    html = html.replace('\n\n', '</p><p>')
    
    # Wrap in paragraph tags if not already wrapped
    if not html.startswith('<p>') and not html.startswith('<table>') and not html.startswith('<h'):
        html = f'<p>{html}</p>'
    
    return html

def extract_html_content(text: str) -> str:
    """Extract content from HTML document or return text as-is if not HTML"""
    
    # Check if text contains HTML document structure
    if '<!DOCTYPE' in text and '<html' in text and '<body' in text:
        # Extract content between <body> tags
        body_match = re.search(r'<body[^>]*>(.*?)</body>', text, re.DOTALL | re.IGNORECASE)
        if body_match:
            content = body_match.group(1)
            # Clean up extra whitespace and newlines
            content = re.sub(r'\s+', ' ', content).strip()
            return content
    
    # Check if text contains HTML tags but no document structure
    if '<h1>' in text or '<h2>' in text or '<table>' in text or '<p>' in text:
        # Remove any DOCTYPE, html, head tags if present
        content = re.sub(r'<!DOCTYPE[^>]*>', '', text, flags=re.IGNORECASE)
        content = re.sub(r'<html[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</html>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<head>.*?</head>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<body[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</body>', '', content, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        return content
    
    # Return original text if no HTML structure detected
    return text

# OpenAI Analysis Function
async def analyze_comments_with_gpt(analysis_id: str, task_id: str, custom_analysis: Optional[str] = None):
    """Analyze comments using Gemini"""
    try:
        analyses[analysis_id]["status"] = "analyzing"
        analyses[analysis_id]["progress"] = 10.0
        analyses[analysis_id]["message"] = "Preparing data for analysis..."

        # Get the original task data
        if task_id not in tasks:
            raise Exception("Original crawl task not found")
        
        task = tasks[task_id]
        if task["status"] != "completed":
            raise Exception("Original crawl task not completed")
        
        # Load the comments data
        if not task.get("download_url"):
            raise Exception("No comments data file found")
        
        filename = task["download_url"].replace("/download/", "")
        file_path = downloads_dir / filename
        
        if not file_path.exists():
            raise Exception("Comments data file not found on disk")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            comments_data = json.load(f)
        
        analyses[analysis_id]["progress"] = 30.0
        analyses[analysis_id]["message"] = "Preparing analysis prompt..."
        
        # Prepare comments text for analysis
        comments_text = ""
        for comment in comments_data.get("comments", []):
            comment_text = comment.get("comment_text", "").strip()
            if comment_text:
                comments_text += f"- {comment_text}\n"
        
        if not comments_text.strip():
            raise Exception("No valid comments found for analysis")
        
        # Use custom analysis request or default
        prompt = custom_analysis if custom_analysis else ANALYSIS_PROMPT
        
        analyses[analysis_id]["progress"] = 50.0
        analyses[analysis_id]["message"] = "Sending to Gemini for analysis..."

        # Prepare the full prompt
        full_prompt = f"{prompt}\n\nĐÂY LÀ CÁC COMMENT CẦN PHÂN TÍCH:\n\n{comments_text}"

        # Call Gemini API
        model = genai.GenerativeModel('gemini-2.5-pro')
        response = model.generate_content(full_prompt)
        analysis_text = response.text

        # Convert markdown to HTML (especially tables)
        analysis_html = convert_markdown_to_html(analysis_text)

        # Store as HTML content for direct display
        analysis_result = {
            "analysis_html": analysis_html,
            "analysis_type": "html_formatted"
        }

        # Add metadata
        analysis_result["metadata"] = {
            "video_id": comments_data.get("metadata", {}).get("video_id", ""),
            "total_comments_analyzed": len(comments_data.get("comments", [])),
            "analysis_model": "gemini-pro",
            "analyzed_at": datetime.now().isoformat(),
            "prompt_used": "custom" if custom_analysis else "default"
        }

        # Complete the analysis
        analyses[analysis_id]["status"] = "completed"
        analyses[analysis_id]["progress"] = 100.0
        analyses[analysis_id]["message"] = "Analysis completed successfully"
        analyses[analysis_id]["result"] = analysis_result
        analyses[analysis_id]["updated_at"] = datetime.now()

    except Exception as e:
        analyses[analysis_id]["status"] = "failed"
        analyses[analysis_id]["progress"] = 100.0
        analyses[analysis_id]["message"] = f"Analysis failed: {str(e)}"
        analyses[analysis_id]["error"] = str(e)
        analyses[analysis_id]["updated_at"] = datetime.now()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 