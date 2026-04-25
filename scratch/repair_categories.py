import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goldenfork.settings')
django.setup()

from core.models import MenuItem, Category

def repair_categories():
    print("Repairing missing categories...")
    
    # Ensure categories exist
    cat_breakfast, _ = Category.objects.get_or_create(name='Breakfast')
    cat_lunch, _ = Category.objects.get_or_create(name='Lunch')
    cat_dinner, _ = Category.objects.get_or_create(name='Dinner')
    cat_snacks, _ = Category.objects.get_or_create(name='Tea/Snacks')
    cat_juices, _ = Category.objects.get_or_create(name='Juices')
    cat_combos, _ = Category.objects.get_or_create(name='Combo Section')

    items = MenuItem.objects.all()
    repaired_count = 0
    
    for item in items:
        if item.categories.count() == 0:
            name = item.name.lower()
            assigned = False
            
            # 1. Juices
            if 'juice' in name or 'water' in name or 'dew' in name or 'pepsi' in name or '7 up' in name:
                item.categories.add(cat_juices)
                assigned = True
            
            # 2. Breakfast
            if any(k in name for k in ['dosa', 'idle', 'puttu', 'idiyappam', 'appam', 'vada']):
                item.categories.add(cat_breakfast)
                assigned = True
                
            # 3. Snacks
            if any(k in name for k in ['tea', 'samoosa', 'vada', 'ulli', 'bhajji', 'vazhakkappam', 'parippuvada']):
                item.categories.add(cat_snacks)
                assigned = True
            
            # 4. Lunch/Dinner (Main course)
            if any(k in name for k in ['biriyani', 'mandhi', 'meals', 'curry', 'roast', 'porotta', 'chappathi', 'paneer']):
                item.categories.add(cat_lunch, cat_dinner)
                assigned = True
            
            # Default to Lunch if nothing else matches
            if not assigned:
                item.categories.add(cat_lunch)
            
            repaired_count += 1
            print(f"Repaired: {item.name}")

    print(f"Repair complete! {repaired_count} items categorized.")

if __name__ == "__main__":
    repair_categories()
