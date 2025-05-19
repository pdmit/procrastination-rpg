import csv
from app import db, ShopItem, app

def seed_from_csv(csv_path):
    added = 0
    updated = 0

    with app.app_context():
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing = ShopItem.query.filter_by(name=row["name"]).first()
                if existing:
                    # Update existing
                    existing.icon = row["icon"]
                    existing.cost = int(row["cost"])
                    existing.description = row["description"]
                    existing.effect = row.get("effect", "")
                    existing.slot = row.get("slot", "")
                    existing.bonuses = row.get("bonuses", "")
                    updated += 1
                    print(f"🔁 Updated item: {existing.name}")
                else:
                    # Add new
                    new_item = ShopItem(
                        name=row["name"],
                        icon=row["icon"],
                        cost=int(row["cost"]),
                        description=row["description"],
                        effect=row.get("effect", ""),
                        slot=row.get("slot", ""),
                        bonuses=row.get("bonuses", "")
                    )
                    db.session.add(new_item)
                    added += 1
                    print(f"➕ Added new item: {new_item.name}")

        db.session.commit()

    print("\n✅ Shop inventory sync complete.")
    print(f"🆕 Items added: {added}")
    print(f"♻️  Items updated: {updated}")

if __name__ == "__main__":
    seed_from_csv("data/shop_items_equipment.csv")
