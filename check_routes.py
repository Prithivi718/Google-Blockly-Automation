import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

try:
    from app_ui import app
    print("Successfully imported app from app_ui.py\n")
    
    print(f"{'Path':<30} {'Name':<20} {'Methods'}")
    print("-" * 70)
    for route in app.routes:
        methods = getattr(route, 'methods', None)
        path = getattr(route, 'path', None)
        name = getattr(route, 'name', None)
        methods_str = ",".join(methods) if methods else "N/A"
        print(f"{str(path):<30} {str(name):<20} {methods_str}")
        
except Exception as e:
    print(f"Error during route check: {e}")
    import traceback
    traceback.print_exc()
