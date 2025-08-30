#!/usr/bin/env python3
"""
Create default organization for testing
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_supabase

def create_default_org():
    """Create default organization with UUID 00000000-0000-0000-0000-000000000000"""
    supabase = get_supabase()
    
    default_org = {
        'id': '00000000-0000-0000-0000-000000000000',
        'name': 'Default Organization',
        'plan': 'free',
        'storage_used_gb': 0,
        'video_count': 0
    }
    
    try:
        # Check if it exists
        result = supabase.table('organizations').select('*').eq('id', default_org['id']).execute()
        
        if result.data:
            print(f"Default organization already exists")
            return True
            
        # Create it
        result = supabase.table('organizations').insert(default_org).execute()
        print(f"Created default organization: {default_org['id']}")
        return True
        
    except Exception as e:
        print(f"Error creating default organization: {e}")
        return False

if __name__ == "__main__":
    success = create_default_org()
    sys.exit(0 if success else 1)