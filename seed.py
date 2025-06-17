# seed.py
# A standalone script to seed the database with all necessary data.
# Run from your terminal with: python seed.py

from asset_manager import create_app, db
from asset_manager.models import User, AssetCategory, Asset
from datetime import date
import random

def seed_database():
    """
    Seeds the database with essential initial data (admin, categories)
    and extra sample data if the database is empty.
    This function is idempotent and safe to run multiple times.
    """
    app = create_app()
    with app.app_context():
        
        # --- 1. Create Initial Admin and Categories (if they don't exist) ---
        initial_data_added = False
        if not User.query.filter_by(username='admin').first():
            admin_user = User(name='Administrator', username='admin', email='admin@example.com', role='admin')
            admin_user.set_password('admin1')
            db.session.add(admin_user)
            print("Default admin user created.")
            initial_data_added = True
        
        if not AssetCategory.query.first():
            default_categories = [
                ("Laptop", "Portable computers"), ("Desktop", "Stationary computer systems"),
                ("Monitor", "Display screens"), ("Printer", "Document printing devices"),
                ("Server", "Network servers"), ("Networking Gear", "Routers, switches, firewalls"),
                ("Software License", "Licenses for software applications"),
                ("Mobile Phone", "Company-issued mobile phones"), ("Tablet", "Company-issued tablet devices"),
                ("Peripheral", "Input/output devices like keyboards, mice, etc."), 
                ("VR Headsets", "Virtual reality headsets for simulation and training.") 
            ]
            for name, desc in default_categories:
                category = AssetCategory(name=name, description=desc)
                db.session.add(category)
            print("Default asset categories created.")
            initial_data_added = True
        
        if initial_data_added:
            try:
                db.session.commit()
                print("Initial data committed successfully.")
            except Exception as e:
                db.session.rollback()
                print(f"Error during initial data creation: {e}")
                return # Stop if initial data fails
        else:
            print("Initial admin and categories already exist.")


        # --- 2. Create Extra Sample Data (if it doesn't exist) ---
        if User.query.count() > 1 or Asset.query.count() > 0:
            print("Database already contains sample data. Aborting extra data seed.")
            return

        print("Seeding with extra sample data...")

        # --- Create Sample Users ---
        sample_users = [
            {'name': 'Jane Doe', 'username': 'Jane3', 'email': 'jane_d@email.com'},
            {'name': 'Jake Smith', 'username': 'JakeS', 'email': 'smith_j@outlook.com'},
            {'name': 'Emily Jones', 'username': 'EmilyJ', 'email': 'EmJ@y@yahoo.com'},
            {'name': 'Michael Brown', 'username': 'MBrown', 'email': 'M_B@hotmail.com'},
            {'name': 'Sarah Davis', 'username': 'sarahD', 'email': 'sarah_davis@gmail.com'},
            {'name': 'David Wilson', 'username': 'DWilson', 'email': 'wilson_d@gmail.com'},
            {'name': 'Laura Taylor', 'username': 'LauraT', 'email': 'Laura_T@hotmail.com'},
            {'name': 'Robert Miller', 'username': 'RobMill', 'email': 'rob_mill@outlook.com'},
            {'name': 'Jessica Garcia', 'username': 'Jess76', 'email': 'Jess76@gmail.com'},
            {'name': 'Chris Evans', 'username': 'ChrisE', 'email': 'chris.evans@hotmail.com'},
        ]
        
        for u_data in sample_users:
            if not User.query.filter_by(username=u_data['username']).first():
                user = User(name=u_data['name'], username=u_data['username'], email=u_data['email'], role='regular')
                user.set_password('password123')
                db.session.add(user)
        
        try:
            db.session.commit()
            print(f"Sample users created.")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating sample users: {e}")
            return
        
        # --- Create Sample Assets ---
        all_categories = AssetCategory.query.all()
        all_users = User.query.filter(User.username != 'admin').all()
        category_map = {cat.name: cat for cat in all_categories}
        
        sample_assets = [
            {'name': 'Dell Latitude 7420', 'tag': 'LAP-001', 'sn': 'SN-DELL-7420-01', 'p_date': date(2023, 5, 15), 'cost': 1250.50, 'vendor': 'Dell Inc.', 'loc': 'Sales Department', 'status': 'In Use', 'cat_name': 'Laptop', 'description': 'Standard issue sales laptop, 16GB RAM, 512GB SSD.'},
            {'name': 'Apple MacBook Pro 16"', 'tag': 'LAP-002', 'sn': 'SN-AAPL-MBP16-01', 'p_date': date(2023, 6, 1), 'cost': 2400.00, 'vendor': 'Apple Store', 'loc': 'Marketing Dept', 'status': 'In Use', 'cat_name': 'Laptop', 'description': 'M2 Pro chip. For graphic design and video editing.'},
            {'name': 'HP LaserJet Pro M404dn', 'tag': 'PRN-001', 'sn': 'SN-HP-M404-01', 'p_date': date(2022, 11, 20), 'cost': 250.00, 'vendor': 'CDW', 'loc': 'Finance Office', 'status': 'In Use', 'cat_name': 'Printer', 'description': 'Main office network printer.'},
            {'name': 'Dell UltraSharp U2721DE', 'tag': 'MON-001', 'sn': 'SN-DELL-U2721-01', 'p_date': date(2023, 5, 15), 'cost': 450.75, 'vendor': 'Dell Inc.', 'loc': 'Sales Department', 'status': 'In Use', 'cat_name': 'Monitor', 'description': 'Primary monitor for hot-desking stations.'},
            {'name': 'iPhone 14 Pro', 'tag': 'MOB-001', 'sn': 'SN-AAPL-IP14P-01', 'p_date': date(2023, 9, 25), 'cost': 999.00, 'vendor': 'Vodafone', 'loc': 'On-person (John Smith)', 'status': 'In Use', 'cat_name': 'Mobile Phone', 'description': 'Company mobile for Sales Director.'},
            {'name': 'Cisco Catalyst 2960', 'tag': 'NET-001', 'sn': 'SN-CIS-C2960-01', 'p_date': date(2021, 8, 10), 'cost': 1500.00, 'vendor': 'Insight', 'loc': 'Server Room A', 'status': 'In Repair', 'cat_name': 'Networking Gear', 'description': 'Port 4 faulty, awaiting engineer visit on 2024-07-10.'},
            {'name': 'Adobe Creative Cloud License', 'tag': 'SW-001', 'sn': None, 'p_date': date(2024, 1, 1), 'cost': 550.00, 'vendor': 'Adobe', 'loc': 'Digital', 'status': 'In Use', 'cat_name': 'Software License', 'description': 'Annual license subscription for all apps. Assigned to Marketing team.'},
            {'name': 'Lenovo ThinkPad X1', 'tag': 'LAP-003', 'sn': 'SN-LEN-X1-OLD', 'p_date': date(2020, 3, 12), 'cost': 1100.00, 'vendor': 'Lenovo UK', 'loc': 'IT Storage', 'status': 'Retired', 'cat_name': 'Laptop', 'description': 'Retired on 2023-05-10. Hard drive wiped and awaiting disposal.'},
            {'name': 'HPE ProLiant DL380 Gen10', 'tag': 'SRV-001', 'sn': 'SN-HPE-DL380-01', 'p_date': date(2022, 2, 22), 'cost': 4500.00, 'vendor': 'HPE', 'loc': 'Server Room A', 'status': 'In Use', 'cat_name': 'Server', 'description': 'Primary domain controller (DC-01).'},
            {'name': 'Logitech MX Keys Combo', 'tag': 'PRP-001', 'sn': 'SN-LOGI-MXK-01', 'p_date': date(2024, 3, 5), 'cost': 190.00, 'vendor': 'Amazon Business', 'loc': 'Marketing Department', 'status': 'In Use', 'cat_name': 'Peripheral', 'description': 'Wireless keyboard and mouse set for new marketing hire.'},
            {'name': 'Meta Quest 3', 'tag': 'VR-001', 'sn': 'SN-META-Q3-01', 'p_date': date(2024, 2, 20), 'cost': 480.00, 'vendor': 'Meta Direct', 'loc': 'R&D Lab', 'status': 'In Use', 'cat_name': 'VR Headsets', 'description': 'Used for developing new training simulations.'},
        ]

        for a_data in sample_assets:
            category = category_map.get(a_data['cat_name'])
            if category and all_users:
                asset = Asset(
                    asset_name=a_data['name'], asset_tag=a_data['tag'], serial_number=a_data['sn'],
                    purchase_date=a_data['p_date'], purchase_cost=a_data['cost'], vendor=a_data['vendor'],
                    storage_location=a_data['loc'], status=a_data['status'], description=a_data['description'],
                    category_id=category.id, creator=random.choice(all_users)
                )
                db.session.add(asset)
        
        try:
            db.session.commit()
            print("Database seeded with sample assets successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding sample assets: {e}")

if __name__ == '__main__':
    seed_database()
