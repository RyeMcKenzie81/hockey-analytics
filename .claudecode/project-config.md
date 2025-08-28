# Claude Code Project Configuration
<!-- This file should be included at the start of every Claude Code session -->

## 🏗️ Project: Hockey Analytics System

### 📋 Project Overview
**Description**: Multi-tenant hockey video analytics platform that automatically detects events (goals, penalties, shots) from game footage using ML and provides a review interface.

**Tech Stack:**
- **Backend**: FastAPI + Python 3.11 + Pydantic
- **Database**: Supabase (PostgreSQL + Auth + Storage)  
- **Deployment**: Railway (auto-deploy from GitHub)
- **ML/AI**: YOLOv8 + ByteTrack + Gemini Flash 2.0
- **Video**: FFmpeg + HLS streaming
- **Queue**: Redis (Railway addon)
- **Frontend**: Next.js + TypeScript + Tailwind CSS

**Project Status**: Phase 1 - Foundation & Deployment

---

## 🔄 MANDATORY Development Workflow

### Initial Setup (FIRST TIME ONLY)
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/hockey-analytics.git
cd hockey-analytics

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# 5. Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Daily Development Workflow (ALWAYS FOLLOW)
```bash
# 1. ALWAYS activate virtual environment FIRST
cd hockey-analytics/backend
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate    # Windows

# 2. Pull latest changes
git pull origin develop
git checkout -b feature/[descriptive-name]

# 3. Install any new dependencies
pip install -r requirements.txt

# 4. Make your changes
# ... code ...

# 5. Test your changes
pytest tests/ -v

# 6. Commit and push
git add .
git commit -m "[type]: [description]"  # See commit types below
git push origin feature/[descriptive-name]

# 7. Railway auto-deploys to preview environment
# 8. Create PR to develop branch (not main!)
```

### ⚠️ Virtual Environment Rules
- **NEVER** install packages globally - always use venv
- **NEVER** run scripts without activating venv first
- **NEVER** commit venv/ folder to git
- **ALWAYS** check you're in venv: `(venv)` should appear in terminal
- **ALWAYS** update requirements.txt when adding packages:
```bash
pip freeze > requirements.txt
```

### If Virtual Environment is Not Active
```bash
# You'll see errors like:
# - "ModuleNotFoundError: No module named 'fastapi'"
# - "pip: command not found"
# - Wrong Python version

# To fix:
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate    # Windows

# Verify it's active:
which python  # Should show: /path/to/project/venv/bin/python
```

### Commit Message Format (REQUIRED)
- `feat:` Add new feature
- `fix:` Fix bug
- `refactor:` Restructure code
- `perf:` Improve performance
- `test:` Add/update tests
- `docs:` Update documentation
- `chore:` Update dependencies/config

### Branch Strategy
- `main` → Production (auto-deploys)
- `develop` → Staging (auto-deploys)
- `feature/*` → Development (preview deploys)
- **NEVER commit directly to main or develop!**

---

## 📁 Project Structure (MAINTAIN THIS)
```
hockey-analytics/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Environment config
│   │   ├── models.py            # Pydantic models
│   │   ├── database.py          # Supabase client
│   │   ├── routes/              # API endpoints
│   │   ├── services/            # Business logic
│   │   └── workers/             # Async workers
│   ├── tests/                   # Test files
│   ├── requirements.txt         # Python deps
│   └── railway.json             # Railway config
├── frontend/                    # Next.js app
└── .claudecode/                 # This config
```

---

## 🎯 Code Standards (ENFORCE IN ALL CODE)

### Python Standards
```python
# ALWAYS use type hints
from typing import Optional, List, Dict
async def process_video(video_id: str, org_id: str) -> Dict[str, Any]:
    pass

# ALWAYS use Pydantic models for API
class VideoUpload(BaseModel):
    filename: str
    org_id: str
    
# ALWAYS include org_id for multi-tenancy
@app.post("/api/videos")
async def create_video(data: VideoUpload, org_id: str = Depends(get_org_id)):
    pass

# ALWAYS handle errors with ServiceResponse
try:
    result = await risky_operation()
    return ServiceResponse(success=True, data=result)
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return ServiceResponse(success=False, error=str(e))

# ALWAYS use environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")  # Never hardcode
```

### Database Patterns
```python
# ALWAYS filter by org_id
supabase.table('videos').select('*').eq('org_id', org_id)

# ALWAYS use Row Level Security
# Tables must have org_id column
# RLS policies must filter by org_id
```

### Testing Requirements
```python
# ALWAYS write tests for new features
def test_[feature_name]:
    """Test [what it does]"""
    # Arrange
    # Act  
    # Assert

# Run before committing
pytest tests/ -v
```

---

## 🚀 Deployment Configuration

### Environment Variables (Set in Railway Dashboard)
```bash
# Required for all environments
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
REDIS_URL=
GEMINI_API_KEY=

# Auto-provided by Railway
PORT=
RAILWAY_ENVIRONMENT=
```

### Railway Auto-Deploy
- Connected to GitHub repo: `hockey-analytics`
- Production branch: `main`
- Staging branch: `develop`
- Auto-deploys on push: ✅ Enabled

---

## 📋 Current Implementation Checklist

### Phase 1: Foundation ✅
- [ ] FastAPI setup
- [ ] Supabase connection
- [ ] Railway deployment
- [ ] GitHub integration
- [ ] Basic video upload

### Phase 2: Video Processing
- [ ] HLS conversion pipeline
- [ ] Streaming endpoints
- [ ] Frontend player
- [ ] Upload interface

### Phase 3: ML Detection
- [ ] YOLOv8 integration
- [ ] Event detection
- [ ] Referee gesture detection
- [ ] Gemini enhancement

### Phase 4: Review System
- [ ] Event verification UI
- [ ] Training data export
- [ ] Accuracy metrics

### Phase 5: Multi-Tenancy
- [ ] Organization management
- [ ] User roles (RBAC)
- [ ] Usage quotas

---

## 🔧 Common Operations

### Add New API Endpoint
```python
# 1. Add Pydantic model in models.py
class NewFeatureRequest(BaseModel):
    field1: str
    field2: Optional[int] = None

# 2. Add route in routes/[module].py
@router.post("/new-feature")
async def new_feature(
    request: NewFeatureRequest,
    org_id: str = Depends(get_org_id)
):
    # Implementation
    pass

# 3. Add test in tests/test_[module].py
def test_new_feature():
    response = client.post("/api/new-feature", json={...})
    assert response.status_code == 200
```

### Add Database Table
```sql
-- 1. Add to schema.sql
CREATE TABLE new_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id),  -- REQUIRED
    -- other fields
);

-- 2. Add RLS policy
ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Org isolation" ON new_table
    FOR ALL USING (org_id = current_setting('app.current_org_id')::uuid);
```

### Process Video with ML
```python
# Use this pattern for video processing
async def process_video_segment(video_id: str, start: float, end: float):
    # 1. Extract frames (don't load entire video!)
    frames = await extract_frames_streaming(video_id, start, end)
    
    # 2. Run ML detection
    detections = await ml_detector.process_frames(frames)
    
    # 3. Store results
    await store_events(video_id, detections)
    
    # 4. Clean up memory
    del frames
    gc.collect()
```

---

## ⚠️ Critical Rules (NEVER VIOLATE)
- **NEVER** work without activating virtual environment first
- **NEVER** commit .env files or venv/ folder
- **NEVER** hardcode API keys or secrets
- **NEVER** load entire video files into memory
- **NEVER** skip org_id filtering (security breach!)
- **NEVER** commit directly to main branch
- **NEVER** deploy untested code
- **NEVER** install packages globally (always in venv)
- **ALWAYS** use async/await for I/O operations
- **ALWAYS** include error handling
- **ALWAYS** write tests for new features
- **ALWAYS** update requirements.txt when adding packages
- **ALWAYS** update this file when patterns change

---

## 📞 Quick Commands
```bash
# ACTIVATE VIRTUAL ENVIRONMENT FIRST!
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate    # Windows

# Verify venv is active (should show (venv) in prompt)
which python  # Should show: ./venv/bin/python

# Local development
uvicorn app.main:app --reload
# Or
python -m uvicorn app.main:app --reload --port 8000

# Install new package
pip install package-name
pip freeze > requirements.txt  # Update requirements

# Testing
pytest tests/ -v
pytest tests/test_specific.py::test_function -v
pytest --cov=app tests/  # With coverage

# Railway
railway logs
railway logs --tail
railway run python app/main.py
railway open

# Git workflow
git status
git diff
git add .
git commit -m "feat: Add feature"
git push origin feature/branch-name

# Database
# Access Supabase dashboard for DB operations
# Use Railway Redis plugin for queue monitoring

# Deactivate virtual environment when done
deactivate
```

---

## 🐛 Debugging Checklist

### Local Environment Issues
- Is virtual environment activated? Look for `(venv)` in terminal
- Are all dependencies installed? Run `pip install -r requirements.txt`
- Is .env file configured? Check if `.env` exists with correct keys
- Right Python version? Run `python --version` (should be 3.11+)

### Deployment Issues
- Check Railway logs: `railway logs --tail`
- Verify env variables are set in Railway dashboard
- Check Supabase RLS policies
- Verify org_id is being passed
- Check Redis connection
- Review GitHub Actions test results
- Ensure FFmpeg is available for video processing

### Common Virtual Environment Fixes
```bash
# If packages aren't found:
deactivate
source venv/bin/activate
pip install -r requirements.txt

# If wrong Python version:
deactivate
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# If venv is corrupted:
rm -rf venv/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📝 Notes for Claude Code
When asking Claude Code for help, always provide:
- Current phase/feature being worked on
- Relevant error messages
- Current code structure
- Expected behavior vs actual behavior

Example prompt:
```
I'm in Phase 2, working on HLS video conversion.
Error: "FFmpeg command failed with exit code 1"
Current code: [paste video_processor.py]
Expected: Convert MP4 to HLS
Actual: Fails during conversion
Please help fix this issue following our project standards.
```

---

## 🔄 Update Log
- [2024-01-28]: Initial configuration
- [Date]: Added [feature/pattern]
- [Date]: Updated [section]

<!-- End of Claude Code Configuration -->
<!-- Include this file at the start of every Claude Code session -->