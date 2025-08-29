# Testing Guide - Phase 2

## Prerequisites

1. **Environment Setup**
   ```bash
   # Install Python dependencies
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Install Node dependencies
   cd frontend
   npm install
   cd ..
   ```

2. **FFmpeg Installation**
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt update
   sudo apt install ffmpeg

   # Verify installation
   ffmpeg -version
   ffprobe -version
   ```

3. **Supabase Configuration**
   - Create a Supabase project at https://supabase.com
   - Get your project URL and keys from Settings > API
   - Create the required buckets in Storage:
     - Create a bucket named `videos` (public)

## Environment Configuration

1. **Backend Configuration**
   Create `backend/.env`:
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-service-role-key
   ENVIRONMENT=development
   ```

2. **Frontend Configuration**
   Create `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   ```

## Starting the Application

1. **Start Backend Server**
   ```bash
   cd backend
   source ../venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```
   Backend will be available at: http://localhost:8000

2. **Start Frontend Server**
   ```bash
   cd frontend
   npm run dev
   ```
   Frontend will be available at: http://localhost:3000 (or 3003 if 3000 is in use)

## Testing Workflow

### 1. Test Video Upload (Small File)

1. Open http://localhost:3000 in your browser
2. Click "Click to upload VEO 3 recording"
3. Select a small test video (< 100MB) for quick testing
4. Watch the upload progress bar
5. You'll be redirected to the game analysis page

**Expected Results:**
- Progress bar shows upload percentage
- Redirects to `/games/{video-id}` after upload
- Video status shows "processing"

### 2. Test Chunked Upload (Large File)

1. Use a larger video file (> 100MB) to trigger chunked upload
2. Monitor the console for chunk upload logs
3. Verify all chunks are uploaded successfully

**Expected Results:**
- Multiple chunk upload requests in Network tab
- Smooth progress indication
- Successful assembly and processing

### 3. Test Video Processing

1. After upload, wait for video processing
2. Check the video status on the game page
3. Monitor backend logs for FFmpeg processing

**Expected Results:**
- Status changes from "processing" to "ready"
- Multiple quality levels created (1080p, 720p, 480p)
- HLS files uploaded to Supabase Storage

### 4. Test Video Playback

1. Once status is "ready", video player should appear
2. Test playback controls (play, pause, seek)
3. Check quality switching (if supported by browser)

**Expected Results:**
- Smooth video playback
- Seeking works without buffering issues
- No playback errors

### 5. Test Event Timeline

1. Mock events should appear on the timeline
2. Hover over event markers to see tooltips
3. Click event markers to jump to that time

**Expected Results:**
- 7 sample events appear on timeline
- Tooltips show event details
- Clicking jumps video to correct timestamp

### 6. Test Event List

1. Check the event list in the right sidebar
2. Test filtering by event type
3. Test show/hide unverified events
4. Click verify/reject buttons
5. Click play button to jump to event

**Expected Results:**
- Events display with correct icons
- Filtering works properly
- Verification state updates visually
- Jump to event works

### 7. Test Statistics Panel

1. View statistics in the right sidebar
2. Check event counts match the event list
3. Verify the verification percentage

**Expected Results:**
- Correct total event count
- Event breakdown by type
- Accurate verification percentage

### 8. Test WebSocket Connection

1. Open browser DevTools Console
2. Look for WebSocket connection logs
3. Disconnect network briefly
4. Reconnect and check for auto-reconnection

**Expected Results:**
- "WebSocket connected" message
- Auto-reconnection after disconnect
- Exponential backoff on reconnect attempts

## API Testing with cURL

### Test Video List
```bash
curl http://localhost:8000/api/videos
```

### Test Video Details
```bash
curl http://localhost:8000/api/videos/{video-id}
```

### Test WebSocket
```bash
# Use wscat or similar WebSocket client
npm install -g wscat
wscat -c ws://localhost:8000/api/videos/ws/{video-id}
```

## Common Issues & Solutions

### Issue: Video upload fails
**Solution:** Check Supabase storage bucket permissions and size limits

### Issue: FFmpeg not found
**Solution:** Ensure FFmpeg is installed and in PATH

### Issue: WebSocket connection fails
**Solution:** Check CORS settings and WebSocket URL protocol (ws vs wss)

### Issue: Video processing stuck
**Solution:** Check backend logs for FFmpeg errors, ensure temp directories are writable

### Issue: HLS playback fails
**Solution:** Verify HLS files are uploaded to Supabase and accessible

## Database Verification

Check Supabase dashboard or run SQL queries:

```sql
-- Check uploaded videos
SELECT id, filename, status, created_at 
FROM videos 
ORDER BY created_at DESC;

-- Check video metadata
SELECT id, metadata 
FROM videos 
WHERE status = 'ready';

-- Check events (for Phase 3)
SELECT video_id, event_type, timestamp, confidence 
FROM events 
ORDER BY timestamp;
```

## Performance Testing

1. **Upload Speed Test**
   - Time a 100MB file upload
   - Calculate MB/s throughput

2. **Processing Time**
   - Note video duration
   - Time the processing phase
   - Should be ~2x video duration

3. **Streaming Latency**
   - Time from seek to playback
   - Should be < 2 seconds

## Success Criteria

✅ **Phase 2 is working if:**
1. Videos upload successfully (both small and large)
2. Videos process and generate HLS streams
3. Video playback works smoothly
4. Event timeline displays and is interactive
5. Event list shows mock events
6. Statistics panel shows correct data
7. WebSocket maintains connection
8. No console errors during normal operation

## Next Steps

Once all tests pass:
1. Document any issues found
2. Check error handling with invalid inputs
3. Test with different video formats
4. Prepare for Phase 3 ML integration

---

*For issues or questions, check the logs:*
- Frontend: Browser DevTools Console
- Backend: Terminal running uvicorn
- Network: Browser DevTools Network tab