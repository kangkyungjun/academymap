#!/usr/bin/env python
"""
Sync data from main.Data to map_api.Academy
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academymap.settings')
django.setup()

from main.models import Data
from map_api.models import Academy

def sync_academies():
    """Sync all Data records to Academy model"""
    print("Starting academy sync...")

    # Get counts
    data_count = Data.objects.count()
    academy_count_before = Academy.objects.count()

    print(f"Data records: {data_count}")
    print(f"Academy records before sync: {academy_count_before}")

    if academy_count_before > 0:
        print("Clearing existing Academy records...")
        Academy.objects.all().delete()

    print("Syncing data...")
    batch_size = 1000
    created_count = 0

    for i in range(0, data_count, batch_size):
        batch = Data.objects.all()[i:i+batch_size]
        academies_to_create = []

        for data in batch:
            # Create Academy object with all fields from Data
            academy_data = {}
            for field in data._meta.fields:
                if field.name != 'id':
                    academy_data[field.name] = getattr(data, field.name)

            academies_to_create.append(Academy(id=data.id, **academy_data))

        # Bulk create
        Academy.objects.bulk_create(academies_to_create, ignore_conflicts=True)
        created_count += len(academies_to_create)
        print(f"Progress: {created_count}/{data_count} records synced")

    academy_count_after = Academy.objects.count()
    print(f"Academy records after sync: {academy_count_after}")
    print("Sync complete!")

    # Verify subject fields
    sample = Academy.objects.filter(과목_수학=True).first()
    if sample:
        print(f"\nSample math academy: {sample.상호명}")
        print(f"  과목_수학: {sample.과목_수학}")
        print(f"  과목_영어: {sample.과목_영어}")
        print(f"  과목_과학: {sample.과목_과학}")

if __name__ == "__main__":
    sync_academies()