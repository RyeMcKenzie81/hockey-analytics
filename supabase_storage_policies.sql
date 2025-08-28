-- Enable RLS on storage.objects table
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Create policies for the videos bucket
-- Policy for inserting (uploading) objects to videos bucket
CREATE POLICY "Allow public uploads to videos bucket" ON storage.objects
FOR INSERT 
TO public
WITH CHECK (bucket_id = 'videos');

-- Policy for selecting (downloading) objects from videos bucket  
CREATE POLICY "Allow public downloads from videos bucket" ON storage.objects
FOR SELECT 
TO public
USING (bucket_id = 'videos');

-- Policy for updating objects in videos bucket
CREATE POLICY "Allow public updates to videos bucket" ON storage.objects
FOR UPDATE
TO public
USING (bucket_id = 'videos')
WITH CHECK (bucket_id = 'videos');

-- Policy for deleting objects in videos bucket
CREATE POLICY "Allow public deletes from videos bucket" ON storage.objects
FOR DELETE
TO public
USING (bucket_id = 'videos');