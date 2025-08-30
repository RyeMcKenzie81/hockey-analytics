#!/usr/bin/env python3
"""
Download the SimulaMet HockeyAI YOLO model from Hugging Face

This model is specifically trained for hockey and can detect:
- Players (home/away)
- Pucks
- Referees
- Goalies

Dataset: https://huggingface.co/datasets/SimulaMet-HOST/HockeyAI
"""

import os
import sys
from pathlib import Path
import requests
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_file(url: str, dest_path: Path, chunk_size: int = 8192):
    """Download a file with progress bar"""
    
    # Create parent directory if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Start download
    logger.info(f"Downloading from {url}")
    logger.info(f"Saving to {dest_path}")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    # Get total file size
    total_size = int(response.headers.get('content-length', 0))
    
    # Download with progress bar
    with open(dest_path, 'wb') as f:
        with tqdm(total=total_size, unit='iB', unit_scale=True) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    
    logger.info(f"Download complete: {dest_path}")

def download_hockey_models():
    """Download hockey-specific YOLO models"""
    
    # Create models directory
    models_dir = Path(__file__).parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    
    # Model URLs (these are example URLs - need actual HuggingFace URLs)
    models = [
        {
            'name': 'hockey_yolo.pt',
            'url': 'https://huggingface.co/SimulaMet/hockey-yolo/resolve/main/best.pt',
            'description': 'Main hockey detection model (players, pucks, refs)',
            'size': '~100MB'
        },
        {
            'name': 'hockey_yolo_config.yaml',
            'url': 'https://huggingface.co/SimulaMet/hockey-yolo/resolve/main/data.yaml',
            'description': 'Model configuration with class mappings',
            'size': '~1KB'
        }
    ]
    
    print("\n🏒 Hockey Model Downloader")
    print("=" * 50)
    print("\nThis script will download hockey-specific YOLO models")
    print("trained on the SimulaMet-HOST/HockeyAI dataset.\n")
    
    for model in models:
        dest_path = models_dir / model['name']
        
        # Check if already exists
        if dest_path.exists():
            print(f"✓ {model['name']} already exists")
            continue
        
        print(f"\n📥 Downloading {model['name']}")
        print(f"   {model['description']}")
        print(f"   Size: {model['size']}")
        
        try:
            # Note: These URLs are placeholders
            # The actual model would need to be:
            # 1. Trained on the HockeyAI dataset
            # 2. Uploaded to HuggingFace or similar
            # 3. Made publicly available
            
            # For now, inform user about manual download
            print(f"\n⚠️  Automatic download not yet available")
            print(f"   Please manually download the model from:")
            print(f"   https://huggingface.co/datasets/SimulaMet-HOST/HockeyAI")
            print(f"   And place it in: {dest_path}")
            
            # Uncomment when actual URLs are available:
            # download_file(model['url'], dest_path)
            
        except Exception as e:
            logger.error(f"Failed to download {model['name']}: {e}")
            continue
    
    print("\n" + "=" * 50)
    print("✅ Setup complete!")
    print("\nTo use the hockey model:")
    print("1. Ensure the model file is in backend/models/")
    print("2. The ML detector will automatically use it if available")
    print("3. Otherwise it will fall back to generic YOLOv8\n")

def check_existing_models():
    """Check what models are currently available"""
    
    models_dir = Path(__file__).parent.parent / "models"
    
    print("\n📊 Current Models Status:")
    print("-" * 30)
    
    # Check for hockey model
    hockey_model = models_dir / "hockey_yolo.pt"
    if hockey_model.exists():
        size_mb = hockey_model.stat().st_size / (1024 * 1024)
        print(f"✅ hockey_yolo.pt ({size_mb:.1f} MB)")
    else:
        print("❌ hockey_yolo.pt (not found)")
    
    # Check for generic YOLOv8
    yolo_cache = Path.home() / ".cache" / "ultralytics"
    if yolo_cache.exists():
        yolo_models = list(yolo_cache.glob("*.pt"))
        if yolo_models:
            print(f"✅ YOLOv8 models cached ({len(yolo_models)} models)")
        else:
            print("⚠️  No YOLOv8 models cached (will download on first use)")
    
    print()

if __name__ == "__main__":
    print("""
    🏒 Hockey Vision - Model Setup
    ==============================
    
    This project can use two types of models:
    
    1. Hockey-specific YOLO (recommended)
       - Trained on hockey footage
       - Detects: players, pucks, referees, goalies
       - Better accuracy for hockey events
    
    2. Generic YOLOv8 (fallback)
       - General person detection
       - No puck detection
       - Requires additional processing
    """)
    
    check_existing_models()
    
    response = input("Download hockey models? (y/n): ")
    if response.lower() == 'y':
        download_hockey_models()
    else:
        print("\nSkipping download. The system will use generic YOLOv8.")
        print("You can run this script again to download hockey models.\n")