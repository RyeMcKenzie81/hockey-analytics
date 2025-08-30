#!/usr/bin/env python3
"""
Download HockeyAI model on first run
"""
import os
import sys
import logging
from pathlib import Path
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_hockey_model():
    """Download the HockeyAI model if not present"""
    model_dir = Path("models")
    model_path = model_dir / "hockey_yolo.pt"
    
    # Create models directory if it doesn't exist
    model_dir.mkdir(exist_ok=True)
    
    if model_path.exists():
        logger.info(f"Hockey model already exists at {model_path}")
        return True
    
    logger.info("Downloading HockeyAI model...")
    
    try:
        # Install git-lfs if not present
        subprocess.run(["git", "lfs", "version"], check=True, capture_output=True)
    except:
        logger.warning("git-lfs not installed, trying to install...")
        try:
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", "git-lfs"], check=True)
            subprocess.run(["git", "lfs", "install"], check=True)
        except:
            logger.error("Could not install git-lfs")
            return False
    
    # Clone the model repository
    try:
        logger.info("Cloning HockeyAI model repository...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "https://huggingface.co/SimulaMet-HOST/HockeyAI", "hockey-model-temp"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to clone: {result.stderr}")
            return False
        
        # Copy the model file
        temp_model = Path("hockey-model-temp/HockeyAI_model_weight.pt")
        if temp_model.exists():
            import shutil
            shutil.copy(temp_model, model_path)
            logger.info(f"Model downloaded successfully to {model_path}")
            
            # Clean up temp directory
            shutil.rmtree("hockey-model-temp")
            return True
        else:
            logger.error("Model file not found in repository")
            return False
            
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return False

if __name__ == "__main__":
    success = download_hockey_model()
    sys.exit(0 if success else 1)