import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goldenfork.settings')
django.setup()

from core.models import MenuItem, Category
from django.db import transaction

def merge_categories():
    print("Merging duplicate categories...")
    
    categories = Category.objects.all()
    seen_names = {} # name.lower() -> original_cat_object
    
    with transaction.atomic():
        for cat in categories:
            lower_name = cat.name.lower().strip()
            if lower_name in seen_names:
                original = seen_names[lower_name]
                print(f"Merging '{cat.name}' (ID: {cat.id}) into '{original.name}' (ID: {original.id})")
                
                # Move all items from duplicate category to original
                for item in cat.menu_items.all():
                    item.categories.add(original)
                    item.categories.remove(cat)
                
                # Delete duplicate
                cat.delete()
            else:
                seen_names[lower_name] = cat
                
    print("Merge complete!")

if __name__ == "__main__":
    merge_categories()
