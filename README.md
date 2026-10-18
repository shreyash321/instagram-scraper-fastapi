# 📸 Instagram Scraper FastAPI

A high-performance FastAPI service that takes any Instagram profile URL or handle (e.g., `https://www.instagram.com/virat.kohli/`) as input and scrapes:
- **Profile details**: Name, username, bio, follower count, following count, verified status, and profile photo.
- **Post captions**: Full text captions for posts.
- **Post timestamps**: Standardized ISO 8601 timestamps and Unix timestamps.
- **Post locations**: Tagged location names and GPS coordinates (if available).
- **Post comments**: Comment author, comment text, timestamp, and like counts.
- **JSON format output**: Clean, strongly typed Pydantic models.

---

## 🚀 Features

- **Profile Link & Username Support**: Automatically parses full URLs (`https://www.instagram.com/virat.kohli/`, `https://instagram.com/virat.kohli?igsh=...`) or raw handles (`virat.kohli`, `@virat.kohli`).
- **Configurable Limits**: Easily customize `max_posts` and `max_comments_per_post`.
- **Session Authentication Support**: Pass Instagram's `sessionid` cookie via header, environment variable, or request body to bypass 401 login walls and rate limits.
- **Intelligent Fallback Mode**: Returns structured schema even if unauthenticated public IP encounters Meta login barriers.
- **Interactive Swagger / OpenAPI UI**: Built-in interactive documentation at `/docs` and ReDoc at `/redoc`.

---

## 📁 Project Structure

```
instagram-scraper-fastapi/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application & route endpoints
│   ├── models.py        # Pydantic schemas for request & response
│   ├── scraper.py       # Instaloader engine & extraction logic
│   └── config.py        # App configuration & environment loader
├── sample_virat_kohli_output.json # Sample JSON output for virat.kohli
├── test_client.py       # Automated test suite
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment configuration
├── .gitignore           # Git ignore definitions
└── README.md            # Documentation
```

---

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.9+ (Python 3.10, 3.11, 3.12, 3.14 supported)
- Git

### 2. Clone Repository
```bash
git clone https://github.com/shreyash321/instagram-scraper-fastapi.git
cd instagram-scraper-fastapi
```

### 3. Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional)* Add your Instagram session ID to scrape deep timeline posts and comments without anonymous rate limits:
```env
INSTAGRAM_SESSION_ID=your_sessionid_cookie_value
```
> **How to get your `sessionid` cookie:**
> 1. Open [instagram.com](https://www.instagram.com) in Chrome/Firefox and log in.
> 2. Open Developer Tools (`F12`) -> **Application** (or **Storage**) -> **Cookies**.
> 3. Click `https://www.instagram.com` and copy the value of `sessionid`.

---

## 🏃 Running the Application

### Start the FastAPI Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will be running at:
- **API Base**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 📡 API Endpoints

### 1. `POST /api/v1/scrape` (Recommended)
Scrape a profile by sending a JSON payload.

#### Request:
```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/virat.kohli/",
    "max_posts": 5,
    "max_comments_per_post": 3
  }'
```

#### Response (JSON):
```json
{
  "status": "success",
  "message": "Successfully scraped 3 posts from @virat.kohli",
  "source": "live",
  "profile": {
    "username": "virat.kohli",
    "full_name": "Virat Kohli",
    "biography": "Carpediem!",
    "followers": 271264154,
    "following": 278,
    "posts_count": 1720,
    "is_verified": true,
    "profile_pic_url": "https://...",
    "external_url": "https://one8.com"
  },
  "posts": [
    {
      "post_id": "3348123456789012345",
      "shortcode": "C58vXYZ1234",
      "url": "https://www.instagram.com/p/C58vXYZ1234/",
      "date": "2026-10-15T14:30:00Z",
      "timestamp": 1792074600,
      "caption": "Focused on the journey ahead. Great session in the nets today! 🏏🇮🇳 #NeverSettle #TeamIndia",
      "location": {
        "name": "M. Chinnaswamy Stadium",
        "id": null,
        "latitude": null,
        "longitude": null
      },
      "likes_count": 2845000,
      "comments_count": 38200,
      "comments": [
        {
          "id": "18012345678901234",
          "author": "anushkasharma",
          "text": "❤️❤️ Keep shining!",
          "created_at": "2026-10-15T14:35:00Z",
          "likes_count": 42000
        },
        {
          "id": "18012345678901235",
          "author": "hardikpandya93",
          "text": "Top brother 🔥👊",
          "created_at": "2026-10-15T14:40:00Z",
          "likes_count": 18500
        }
      ]
    }
  ],
  "total_posts_scraped": 1
}
```

---

### 2. `GET /api/v1/scrape`
Quick testing via browser query parameters:
```
http://localhost:8000/api/v1/scrape?url=https://www.instagram.com/virat.kohli/&max_posts=5&max_comments=3
```

---

### 3. `GET /api/v1/profile/{username}`
Direct profile scrape via username handle:
```
http://localhost:8000/api/v1/profile/virat.kohli
```

---

## 🧪 Running Tests

To run the automated test suite and verify the sample link `https://www.instagram.com/virat.kohli/`:
```bash
python test_client.py
```

---

## 📜 License
MIT License. Created for educational and development purposes.
