"""
Seed the database with realistic SwiftPOS demo data.
Run with: python manage.py seed
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


CATEGORIES = [
    ("Beverages", "Drinks and refreshments"),
    ("Snacks & Confectionery", "Chips, chocolates, and sweets"),
    ("Dairy & Eggs", "Milk, cheese, eggs, and butter"),
    ("Bakery", "Bread, pastries, and baked goods"),
    ("Meat & Seafood", "Fresh and frozen meats and fish"),
    ("Fruits & Vegetables", "Fresh produce"),
    ("Household & Cleaning", "Cleaning supplies and home essentials"),
    ("Personal Care", "Toiletries and personal hygiene"),
    ("Electronics & Accessories", "Cables, chargers, and gadgets"),
    ("Stationery & Office", "Pens, notebooks, and office supplies"),
]

PRODUCTS_BY_CATEGORY = {
    "Beverages": [
        ("Coca-Cola 500ml", 5.00, 3.20),
        ("Pepsi 500ml", 5.00, 3.10),
        ("Fanta Orange 500ml", 5.00, 3.20),
        ("Sprite 500ml", 5.00, 3.20),
        ("Malt Drink 33cl", 7.00, 4.50),
        ("Energy Drink 250ml", 12.00, 8.00),
        ("Bottled Water 500ml", 2.50, 1.20),
        ("Bottled Water 1.5L", 5.00, 2.80),
        ("Fresh Orange Juice 1L", 18.00, 12.00),
        ("Chocolate Milk 250ml", 8.00, 5.00),
        ("Green Tea Pack (25 bags)", 15.00, 9.00),
        ("Coffee Sachet (10 pcs)", 12.00, 7.50),
    ],
    "Snacks & Confectionery": [
        ("Pringles Original 165g", 25.00, 16.00),
        ("Lays Classic 150g", 18.00, 11.00),
        ("KitKat 4-finger", 10.00, 6.50),
        ("Snickers Bar", 8.00, 5.00),
        ("Digestive Biscuits 400g", 14.00, 9.00),
        ("Oreo Cookies 137g", 12.00, 7.50),
        ("Popcorn Microwave 3-pack", 20.00, 13.00),
        ("Choco Wafer Bar", 5.00, 3.00),
        ("Groundnut Brittle 200g", 10.00, 6.00),
        ("Mixed Nuts 300g", 35.00, 22.00),
    ],
    "Dairy & Eggs": [
        ("Full Cream Milk 1L", 16.00, 11.00),
        ("Low Fat Milk 1L", 16.00, 11.00),
        ("Cheddar Cheese 250g", 32.00, 21.00),
        ("Butter 250g", 22.00, 14.00),
        ("Plain Yoghurt 500ml", 18.00, 12.00),
        ("Strawberry Yoghurt 500ml", 20.00, 13.00),
        ("Fresh Eggs (crate of 30)", 70.00, 50.00),
        ("Evaporated Milk 410g", 14.00, 9.00),
        ("Condensed Milk 400g", 16.00, 10.50),
        ("Cream Cheese 200g", 28.00, 18.00),
    ],
    "Bakery": [
        ("Sliced White Bread 600g", 15.00, 10.00),
        ("Whole Wheat Bread 600g", 18.00, 12.00),
        ("Croissant (pack of 4)", 22.00, 14.00),
        ("Chocolate Muffin 4-pack", 25.00, 16.00),
        ("Plain Doughnut (6 pcs)", 20.00, 13.00),
        ("Banana Bread Loaf", 30.00, 19.00),
        ("Pita Bread 6-pack", 14.00, 9.00),
        ("Cinnamon Roll 2-pack", 18.00, 11.50),
    ],
    "Meat & Seafood": [
        ("Chicken Breast 1kg", 65.00, 45.00),
        ("Chicken Thighs 1kg", 55.00, 38.00),
        ("Ground Beef 500g", 70.00, 50.00),
        ("Beef Steak 500g", 90.00, 63.00),
        ("Tuna Can 185g", 18.00, 12.00),
        ("Sardines Can 155g", 12.00, 7.50),
        ("Salmon Fillet 500g", 95.00, 67.00),
        ("Pork Sausage 500g", 48.00, 33.00),
        ("Smoked Mackerel 500g", 55.00, 38.00),
        ("Shrimp 500g", 80.00, 56.00),
    ],
    "Fruits & Vegetables": [
        ("Bananas (bunch ~6)", 12.00, 7.00),
        ("Apples Red 1kg", 25.00, 16.00),
        ("Avocado (each)", 8.00, 5.00),
        ("Tomatoes 1kg", 15.00, 9.00),
        ("Onions 1kg", 10.00, 6.00),
        ("Carrots 500g", 8.00, 5.00),
        ("Spinach 500g", 10.00, 6.50),
        ("Cucumber (each)", 5.00, 3.00),
        ("Bell Peppers 500g", 18.00, 11.00),
        ("Pineapple (each)", 15.00, 9.00),
        ("Watermelon (each)", 40.00, 25.00),
        ("Grapes 500g", 30.00, 20.00),
    ],
    "Household & Cleaning": [
        ("Dishwashing Liquid 750ml", 18.00, 11.00),
        ("Laundry Detergent 1kg", 32.00, 21.00),
        ("Fabric Softener 1L", 25.00, 16.00),
        ("Multi-Purpose Cleaner 500ml", 20.00, 13.00),
        ("Toilet Roll 12-pack", 45.00, 30.00),
        ("Paper Towels 6-pack", 30.00, 19.00),
        ("Trash Bags 30 pcs", 22.00, 14.00),
        ("Air Freshener Spray 300ml", 25.00, 16.00),
        ("Bleach 1L", 14.00, 8.50),
        ("Sponge Scrubber 3-pack", 12.00, 7.50),
    ],
    "Personal Care": [
        ("Shampoo 400ml", 35.00, 22.00),
        ("Conditioner 400ml", 35.00, 22.00),
        ("Body Lotion 400ml", 40.00, 26.00),
        ("Toothpaste 150g", 18.00, 11.00),
        ("Toothbrush (pack of 3)", 15.00, 9.50),
        ("Deodorant Roll-On 50ml", 25.00, 16.00),
        ("Shower Gel 250ml", 22.00, 14.00),
        ("Hand Sanitizer 250ml", 20.00, 12.50),
        ("Sanitary Pads 20 pcs", 28.00, 18.00),
        ("Razor 5-pack", 20.00, 12.50),
        ("Cotton Wool 100g", 10.00, 6.00),
        ("Lip Balm SPF", 12.00, 7.50),
    ],
    "Electronics & Accessories": [
        ("USB-C Cable 1m", 35.00, 20.00),
        ("Phone Charger 18W", 65.00, 40.00),
        ("Power Bank 10000mAh", 180.00, 120.00),
        ("Earphones Wired", 55.00, 35.00),
        ("Bluetooth Earbuds", 280.00, 185.00),
        ("Screen Protector Universal", 25.00, 15.00),
        ("Phone Case Universal", 30.00, 18.00),
        ("AA Batteries 8-pack", 25.00, 16.00),
        ("AAA Batteries 8-pack", 25.00, 16.00),
        ("Extension Board 4-socket", 95.00, 62.00),
        ("LED Bulb 9W", 18.00, 11.00),
    ],
    "Stationery & Office": [
        ("Ballpoint Pens 10-pack", 15.00, 9.00),
        ("A4 Notebook 200 pages", 22.00, 14.00),
        ("Sticky Notes 4-pack", 18.00, 11.00),
        ("Highlighters 4-pack", 20.00, 12.50),
        ("Stapler Desktop", 35.00, 22.00),
        ("Staples Box 1000 pcs", 10.00, 6.00),
        ("Scissors Office", 18.00, 11.00),
        ("Calculator Basic", 45.00, 29.00),
        ("Manila Folder 10-pack", 20.00, 12.50),
        ("Correction Fluid 20ml", 8.00, 5.00),
    ],
}

CUSTOMERS = [
    ("Ama Mensah", "0244100001", "ama.mensah@gmail.com", "1990-03-15"),
    ("Kwame Asante", "0244100002", "kwame.asante@yahoo.com", "1985-07-22"),
    ("Akosua Boateng", "0244100003", "akosua.b@gmail.com", "1992-11-08"),
    ("Kofi Agyei", "0244100004", "kofi.agyei@hotmail.com", "1988-04-30"),
    ("Abena Owusu", "0244100005", "abena.owusu@gmail.com", "1995-09-17"),
    ("Yaw Darko", "0244100006", "yaw.darko@yahoo.com", "1983-12-05"),
    ("Efua Asare", "0244100007", "efua.asare@gmail.com", "1997-02-28"),
    ("Nana Frimpong", "0244100008", "nana.f@gmail.com", "1991-06-14"),
    ("Adjoa Amponsah", "0244100009", "adjoa.a@yahoo.com", "1986-08-19"),
    ("Kweku Acheampong", "0244100010", "kweku.a@gmail.com", "1993-01-11"),
    ("Maame Serwaa", "0244100011", "maame.s@gmail.com", "1989-05-25"),
    ("Fiifi Bondzie", "0244100012", "fiifi.b@hotmail.com", "1994-10-03"),
    ("Akua Tetteh", "0244100013", "akua.t@gmail.com", "1987-07-16"),
    ("Kojo Antwi", "0244100014", "kojo.antwi@yahoo.com", "1996-03-29"),
    ("Esi Quaye", "0244100015", "esi.quaye@gmail.com", "1990-12-22"),
    ("Kwabena Osei", "0244100016", "kwabena.o@gmail.com", "1984-09-07"),
    ("Abiba Alhassan", "0244100017", "abiba.a@yahoo.com", "1998-04-14"),
    ("Seidu Dramani", "0244100018", "seidu.d@gmail.com", "1982-11-30"),
    ("Afia Nyarko", "0244100019", "afia.n@gmail.com", "1993-06-08"),
    ("Osei Bonsu", "0244100020", "osei.bonsu@hotmail.com", "1985-02-19"),
    ("Adwoa Konadu", "0244100021", "adwoa.k@gmail.com", "1991-08-25"),
    ("Kwasi Mensah", "0244100022", "kwasi.m@yahoo.com", "1979-12-12"),
    ("Badu Akuamoah", "0244100023", "badu.a@gmail.com", "1997-03-06"),
    ("Dede Appiah", "0244100024", "dede.appiah@gmail.com", "1988-07-21"),
    ("Prince Amoako", "0244100025", "prince.a@gmail.com", "1995-10-18"),
]

STAFF = [
    ("admin", "Admin User", "admin@swiftpos.com", "admin"),
    ("manager1", "Kofi Manager", "kofi.manager@swiftpos.com", "manager"),
    ("manager2", "Ama Manager", "ama.manager@swiftpos.com", "manager"),
    ("cashier1", "Kwame Cashier", "kwame.cashier@swiftpos.com", "cashier"),
    ("cashier2", "Akosua Cashier", "akosua.cashier@swiftpos.com", "cashier"),
    ("cashier3", "Yaw Cashier", "yaw.cashier@swiftpos.com", "cashier"),
    ("cashier4", "Efua Cashier", "efua.cashier@swiftpos.com", "cashier"),
]

BRANCHES = [
    ("Main Branch - Accra Central", "15 High Street, Accra Central, Greater Accra", "0302000001"),
    ("East Legon Branch", "Plot 45, American House, East Legon, Accra", "0302000002"),
    ("Kumasi Branch", "23 Adum Road, Kumasi, Ashanti Region", "0322000001"),
    ("Takoradi Branch", "7 Market Circle, Takoradi, Western Region", "0312000001"),
]

SUPPLIERS = [
    ("Ghana Beverages Ltd", "Mr. Emmanuel Asante", "0244200001", "beverages@ghbev.com", "30 days net"),
    ("Accra Fresh Produce", "Ms. Akua Sarpong", "0244200002", "produce@accrafresh.com", "7 days"),
    ("WestAfrica Distributors", "Mr. Kwame Boateng", "0244200003", "orders@wadist.com", "30 days net"),
    ("Golden Foods Import Co.", "Mrs. Ama Frimpong", "0244200004", "sales@goldenfoods.com", "14 days"),
    ("TechGadgets Ghana", "Mr. Kofi Darko", "0244200005", "supply@techgh.com", "COD"),
    ("Cleanex Supply Co.", "Ms. Abena Mensah", "0244200006", "cleanex@supply.com", "21 days"),
]

EXPENSE_CATEGORIES = [
    ("Utilities", "bolt"),
    ("Rent", "home"),
    ("Salaries", "users"),
    ("Marketing", "trending-up"),
    ("Maintenance", "tool"),
    ("Transport", "truck"),
    ("Miscellaneous", "more-horizontal"),
]


class Command(BaseCommand):
    help = "Seed the database with realistic demo data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            self._clear_data()

        self.stdout.write("Seeding database...")

        users = self._seed_users()
        branches = self._seed_branches()
        categories, products = self._seed_products()
        customers = self._seed_customers()
        suppliers = self._seed_suppliers()
        self._seed_expenses(users, branches)
        self._seed_sales(users, customers, products)

        self.stdout.write(self.style.SUCCESS("\n✅ Seeding complete!"))
        self.stdout.write(f"   {len(users)} staff members")
        self.stdout.write(f"   {len(branches)} branches")
        self.stdout.write(f"   {len(categories)} categories, {len(products)} products")
        self.stdout.write(f"   {len(customers)} customers")
        self.stdout.write(f"   {len(suppliers)} suppliers")
        self.stdout.write(f"\n   Login: admin / admin123")

    def _clear_data(self):
        from apps.sales.models import Sale, SaleItem
        from apps.customers.models import Customer
        from apps.products.models import Product, Category
        from apps.expenses.models import Expense, ExpenseCategory
        from apps.branches.models import Branch, BranchInventory
        from apps.suppliers.models import Supplier, PurchaseOrder

        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        Customer.objects.all().delete()
        Expense.objects.all().delete()
        ExpenseCategory.objects.all().delete()
        BranchInventory.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Branch.objects.all().delete()
        Supplier.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _seed_users(self):
        users = []
        for username, full_name, email, role in STAFF:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "full_name": full_name,
                    "email": email,
                    "role": role,
                    "is_active": True,
                    "is_staff": role == "admin",
                    "is_superuser": role == "admin",
                },
            )
            if created:
                user.set_password("admin123")
                user.save()
            users.append(user)
            self.stdout.write(f"  {'Created' if created else 'Found'} user: {username} ({role})")
        return users

    def _seed_branches(self):
        from apps.branches.models import Branch

        branches = []
        for name, address, phone in BRANCHES:
            branch, created = Branch.objects.get_or_create(
                name=name,
                defaults={"address": address, "phone": phone},
            )
            branches.append(branch)
            self.stdout.write(f"  {'Created' if created else 'Found'} branch: {name}")
        return branches

    def _seed_products(self):
        from apps.products.models import Category, Product

        categories = []
        all_products = []

        for cat_name, cat_desc in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={"description": cat_desc},
            )
            categories.append(category)

            for prod_name, price, cost in PRODUCTS_BY_CATEGORY.get(cat_name, []):
                qty = random.randint(10, 200)
                reorder = random.randint(5, 20)
                product = Product.objects.filter(product_name=prod_name).first()
                if not product:
                    product = Product.objects.create(
                        product_name=prod_name,
                        category=category,
                        price=Decimal(str(price)),
                        cost_price=Decimal(str(cost)),
                        quantity=qty,
                        reorder_level=reorder,
                        is_active=True,
                    )
                    all_products.append(product)

        self.stdout.write(f"  Created {len(categories)} categories and {len(all_products)} products")
        return categories, list(Product.objects.all())

    def _seed_customers(self):
        from apps.customers.models import Customer

        customers = []
        for full_name, phone, email, birthday in CUSTOMERS:
            customer, created = Customer.objects.get_or_create(
                phone=phone,
                defaults={
                    "full_name": full_name,
                    "email": email,
                    "birthday": date.fromisoformat(birthday),
                    "loyalty_points": random.randint(0, 500),
                },
            )
            customers.append(customer)

        self.stdout.write(f"  Created/found {len(customers)} customers")
        return customers

    def _seed_suppliers(self):
        from apps.suppliers.models import Supplier

        suppliers = []
        for name, contact, phone, email, terms in SUPPLIERS:
            supplier, created = Supplier.objects.get_or_create(
                name=name,
                defaults={
                    "contact_person": contact,
                    "phone": phone,
                    "email": email,
                    "payment_terms": terms,
                    "lead_time_days": random.randint(3, 14),
                },
            )
            suppliers.append(supplier)

        self.stdout.write(f"  Created/found {len(suppliers)} suppliers")
        return suppliers

    def _seed_expenses(self, users, branches):
        from apps.expenses.models import Expense, ExpenseCategory

        for cat_name, icon in EXPENSE_CATEGORIES:
            ExpenseCategory.objects.get_or_create(name=cat_name, defaults={"icon": icon})

        expense_cats = list(__import__("apps.expenses.models", fromlist=["ExpenseCategory"]).ExpenseCategory.objects.all())

        EXPENSE_ITEMS = [
            ("Monthly Electricity Bill", "Utilities", 850.00),
            ("Monthly Water Bill", "Utilities", 320.00),
            ("Branch Rent - Main", "Rent", 5000.00),
            ("Branch Rent - East Legon", "Rent", 7500.00),
            ("Staff Salaries - April", "Salaries", 18000.00),
            ("Facebook Ads Campaign", "Marketing", 1200.00),
            ("AC Maintenance", "Maintenance", 600.00),
            ("Delivery Van Fuel", "Transport", 800.00),
            ("Office Supplies Purchase", "Miscellaneous", 350.00),
            ("Security Guard Salary", "Salaries", 1500.00),
            ("CCTV Camera Repair", "Maintenance", 450.00),
            ("Staff Training Workshop", "Miscellaneous", 2000.00),
            ("Instagram Ads", "Marketing", 900.00),
            ("Generator Fuel", "Utilities", 1100.00),
            ("Cleaning Service Monthly", "Utilities", 400.00),
        ]

        admin_user = users[0]
        cat_map = {c.name: c for c in expense_cats}

        for i, (title, cat_name, amount) in enumerate(EXPENSE_ITEMS):
            expense_date = date.today() - timedelta(days=random.randint(0, 90))
            cat = cat_map.get(cat_name)
            Expense.objects.get_or_create(
                title=title,
                date=expense_date,
                defaults={
                    "amount": Decimal(str(amount)),
                    "category": cat,
                    "branch": random.choice(branches) if branches else None,
                    "description": f"Regular {cat_name.lower()} expense",
                    "recorded_by": admin_user,
                    "status": "approved",
                },
            )

        self.stdout.write(f"  Created expense categories and {len(EXPENSE_ITEMS)} expenses")

    def _seed_sales(self, users, customers, products):
        from apps.sales.models import Sale, SaleItem

        if Sale.objects.count() > 50:
            self.stdout.write("  Sales already seeded, skipping.")
            return

        cashiers = [u for u in users if u.role in ("cashier", "manager")]
        if not cashiers:
            cashiers = users

        payment_methods = ["cash", "mobile_money", "card"]

        sales_to_create = []
        items_map = []  # list of (sale_index, product, qty, unit_price, line_total)

        # Build 120 sales spread over the last 60 days
        for day_offset in range(60):
            sale_date = timezone.now() - timedelta(days=day_offset)
            num_sales = random.randint(1, 4) if day_offset < 20 else random.randint(0, 2)

            for _ in range(num_sales):
                cart = random.sample(products, min(random.randint(1, 5), len(products)))
                cashier = random.choice(cashiers)
                customer = random.choice(customers) if random.random() > 0.4 else None
                payment_method = random.choice(payment_methods)

                subtotal = Decimal("0.00")
                cart_items = []
                for product in cart:
                    qty = random.randint(1, 3)
                    line_total = product.price * qty
                    subtotal += line_total
                    cart_items.append((product, qty, product.price, line_total))

                discount = Decimal("0.00")
                if random.random() < 0.1:
                    discount = round(subtotal * Decimal("0.05"), 2)
                total = subtotal - discount

                sale_idx = len(sales_to_create)
                sales_to_create.append(Sale(
                    user=cashier,
                    customer=customer,
                    subtotal=subtotal,
                    discount_amount=discount,
                    tax_amount=Decimal("0.00"),
                    tax_rate=Decimal("0.00"),
                    total_amount=total,
                    payment_method=payment_method,
                    status="completed",
                ))
                items_map.append((sale_idx, cart_items, sale_date, payment_method, total))

        # Bulk create all sales at once
        created_sales = Sale.objects.bulk_create(sales_to_create)

        # Bulk create all sale items
        all_items = []
        all_payments = []
        for i, (sale_idx, cart_items, sale_date, payment_method, total) in enumerate(items_map):
            sale = created_sales[i]
            for product, qty, unit_price, line_total in cart_items:
                all_items.append(SaleItem(
                    sale=sale,
                    product=product,
                    quantity=qty,
                    unit_price=unit_price,
                    line_total=line_total,
                ))

        SaleItem.objects.bulk_create(all_items)

        # Update sale dates in bulk
        from django.db.models import Case, When, Value
        for i, (sale_idx, cart_items, sale_date, payment_method, total) in enumerate(items_map):
            Sale.objects.filter(sale_id=created_sales[i].sale_id).update(sale_date=sale_date)

        # Bulk create payments
        try:
            from apps.payments.models import Payment
            payments = []
            for i, (sale_idx, cart_items, sale_date, payment_method, total) in enumerate(items_map):
                extra = Decimal("5.00") if payment_method == "cash" else Decimal("0.00")
                payments.append(Payment(
                    sale=created_sales[i],
                    payment_method=payment_method,
                    amount=total,
                    amount_tendered=total + extra,
                    change_due=extra,
                ))
            Payment.objects.bulk_create(payments)
        except Exception:
            pass

        self.stdout.write(f"  Created {len(created_sales)} sales with {len(all_items)} line items")
