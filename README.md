# Hockey Analytics System

Multi-tenant hockey video analytics platform that automatically detects events from game footage using ML and provides an intuitive interface for review and analysis.

## 📊 Current Status: Phase 2 Complete ✅
- **Backend**: https://hockey-analytics-production.up.railway.app
- **Frontend**: https://frontend-production-2b5b.up.railway.app
- **Branch**: phase-2-production
- **Next Phase**: Phase 3 - ML Detection & Analysis

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Supabase account
- Railway account (for deployment)

### Local Development Setup

1. **Clone and navigate to the project:**
```bash
git clone https://github.com/yourusername/hockey-analytics.git
cd hockey-analytics
```

2. **Set up Python virtual environment:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

5. **Run the development server:**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

## 🎯 Phase 2 Features (Completed)
- ✅ Video upload system (up to 5GB)
- ✅ HLS video processing with FFmpeg
- ✅ Multi-quality streaming (1080p/720p/480p)
- ✅ Real-time WebSocket updates
- ✅ React video player with timeline
- ✅ Event management UI
- ✅ Statistics dashboard

## 🏗️ Project Structure

```
hockey-analytics/
├── backend/              # FastAPI backend
│   ├── app/             # Application code
│   ├── tests/           # Test files
│   └── requirements.txt # Python dependencies
├── frontend/            # Next.js frontend (Phase 2)
├── infrastructure/      # Database schemas & configs
└── .claudecode/        # Project configuration
```

## 📋 Project Status

### ✅ Phase 1 - Foundation (Complete)
- FastAPI setup with health check
- Supabase database schema
- Railway deployment configuration
- Multi-tenant architecture foundation

### ✅ Phase 2 - Frontend & Streaming (Complete)
- Next.js frontend with TypeScript
- Video upload interface (chunked upload for large files)
- HLS video processing and streaming
- Interactive event timeline
- Event list and statistics panel
- WebSocket real-time updates

See [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md) for details and [TESTING_GUIDE.md](TESTING_GUIDE.md) for testing instructions.

### ⏳ Phase 3 - ML Detection (Next)
- YOLO v8 for player/puck detection
- ByteTrack for object tracking
- Gemini Flash 2.0 for event analysis

## 🚀 Deployment

### Railway Deployment

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login and initialize:
```bash
railway login
railway link [project-id]
```

3. Set environment variables in Railway dashboard:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`

4. Deploy:
```bash
railway up
```

### Database Setup (Supabase)

1. Create a new Supabase project
2. Run the schema file: `infrastructure/database/schema.sql`
3. Enable Row Level Security on all tables
4. Copy your project URL and keys to `.env`

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

## 📝 API Endpoints

- `GET /health` - Health check
- `POST /api/videos/upload` - Upload video file
- `GET /api/videos` - List videos (coming soon)
- `GET /api/events` - List detected events (coming soon)

## 🔒 Security

- Row Level Security (RLS) enabled on all tables
- Multi-tenant isolation via `org_id`
- JWT authentication via Supabase Auth
- Environment variables for sensitive data

## 📚 Documentation

- API Documentation: `/docs` when running locally
- Project Configuration: `.claudecode/project-config.md`

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes following the project standards
3. Test your changes: `pytest tests/`
4. Commit: `git commit -m "feat: Add new feature"`
5. Push and create a PR

## 📄 License

[Your License Here]

## 🆘 Support

For issues or questions, please open an issue on GitHub.