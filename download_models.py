"""
Download face-api.js models for face detection
"""
import os
import json

# Create models directory if it doesn't exist
models_dir = os.path.join(os.path.dirname(__file__), 'static', 'models')
os.makedirs(models_dir, exist_ok=True)

print("Downloading face-api.js models...")
print(f"Target directory: {models_dir}\n")

try:
    import requests
    
    # Try multiple sources with the correct filenames
    sources = [
        {
            "name": "GitHub raw content",
            "base": "https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights/",
            "files": [
                "tiny_face_detector_model-weights_manifest.json",
                "tiny_face_detector_model-shard1"
            ]
        },
        {
            "name": "jsDelivr GitHub mirror",
            "base": "https://cdn.jsdelivr.net/gh/justadudewhohacks/face-api.js@master/weights/",
            "files": [
                "tiny_face_detector_model-weights_manifest.json",
                "tiny_face_detector_model-shard1"
            ]
        }
    ]
    
    success = False
    
    for source in sources:
        print(f"Trying source: {source['name']}")
        print(f"Base URL: {source['base']}\n")
        source_success = True
        
        try:
            for file in source['files']:
                print(f"  Downloading {file}...")
                url = source['base'] + file
                output_path = os.path.join(models_dir, file)
                
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = os.path.getsize(output_path) / 1024  # Size in KB
                print(f"  Downloaded {file} ({file_size:.1f} KB)")
            
            success = True
            print(f"Successfully downloaded from {source['name']}\n")
            break
            
        except requests.exceptions.HTTPError as e:
            print(f"  Error: {e}")
            source_success = False
        except Exception as e:
            print(f"  Error: {e}")
            source_success = False
        
        print()
    
    if success:
        print("=" * 60)
        print("All models downloaded successfully!")
        print("=" * 60)
        print("\nModels are ready. You can now use face-api.js for face detection.")
        
        # List downloaded files
        print("\nDownloaded files:")
        for file in os.listdir(models_dir):
            filepath = os.path.join(models_dir, file)
            size = os.path.getsize(filepath) / 1024
            print(f"  - {file} ({size:.1f} KB)")
    else:
        print("Failed to download from all sources")
        print("\nTrying to create placeholder models for testing...")
        
        # Create a basic manifest as fallback
        manifest = {
            "modelTopology": {},
            "weightsManifest": [{"paths": ["tiny_face_detector_model-shard1"]}]
        }
        
        manifest_path = os.path.join(models_dir, "tiny_face_detector_model-weights_manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)
        
        print("✓ Created placeholder manifest file")
        
except ImportError:
    print("Requests library not installed")
    print("Run: pip install requests")
except Exception as e:
    print(f"Unexpected error: {e}")
