import csv
from app import db, ShopItem, app

def seed_from_csv(csv_path):
    with app.app_context():
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = ShopItem(
                    name=row["name"],
                    icon=row["icon"],
                    cost=int(row["cost"]),
                    description=row["description"],
                    effect=row["effect"]
                )
                db.session.add(item)
            db.session.commit()
            print("✅ Shop items seeded from CSV.")

if __name__ == "__main__":
    seed_from_csv("data/shop_items.csv")
