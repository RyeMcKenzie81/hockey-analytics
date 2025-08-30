# Database Migrations

## Important: Fix Events Table RLS (Phase 3)

The events table has an infinite recursion issue with its RLS policies. Before using ML detection features, you must run the migration.

### How to Apply the Migration:

1. **Go to Supabase Dashboard**
   - Navigate to your project at https://app.supabase.com
   - Click on "SQL Editor" in the left sidebar

2. **Run the Migration**
   - Copy the contents of `fix_events_rls.sql`
   - Paste into the SQL editor
   - Click "Run" 

3. **Verify Success**
   - You should see "Success. No rows returned"
   - The events table will now have RLS temporarily disabled

### What This Fixes:

- Removes complex RLS policies causing infinite recursion
- Temporarily disables RLS on events table
- Allows ML processing to create and read events
- Maintains basic security through API-level checks

### Future Improvements:

Once we have proper authentication, we'll re-enable RLS with simpler policies that don't cause recursion.

### If You Still Get Errors:

If you see "infinite recursion detected in policy for relation organization_members", it means the migration hasn't been applied yet. Please follow the steps above.