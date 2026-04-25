import os
import django
import shutil
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goldenfork.settings')
django.setup()

from core.models import Order, OrderItem, Payment, Complaint, Review
from django.db import connection

def cleanup():
    print("Starting data cleanup...")

    # 1. Delete data from models
    print("Deleting OrderItems...")
    OrderItem.objects.all().delete()
    
    print("Deleting Payments...")
    Payment.objects.all().delete()
    
    print("Deleting Orders...")
    Order.objects.all().delete()
    
    print("Deleting Complaints...")
    Complaint.objects.all().delete()
    
    print("Deleting Reviews...")
    Review.objects.all().delete()

    # 2. Reset auto-increment counters (SQLite specific)
    print("Resetting auto-increment counters...")
    with connection.cursor() as cursor:
        tables = ['core_order', 'core_orderitem', 'core_payment', 'core_complaint', 'core_review']
        for table in tables:
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")
    
    # 3. Cleanup media files related to deleted data
    print("Cleaning up media files...")
    media_root = 'media'
    subdirs = ['payment_screenshots', 'complaints']
    for subdir in subdirs:
        path = os.path.join(media_root, subdir)
        if os.path.exists(path):
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

    print("Cleanup complete!")

if __name__ == "__main__":
    cleanup()
