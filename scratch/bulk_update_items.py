import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goldenfork.settings')
django.setup()

from core.models import MenuItem

def bulk_update():
    print("Starting bulk update of menu items...")
    
    # Update all items
    updated_count = MenuItem.objects.all().update(stock_quantity=50, is_available=True)
    
    print(f"Successfully updated {updated_count} menu items.")
    print("Set stock_quantity to 50 and is_available to True for all.")

if __name__ == "__main__":
    bulk_update()
