"""
seed_data.py — Run from the backend/ directory:
    python seed_data.py

Populates the DB with realistic test data for development/testing.
Safe to run multiple times (skips already-existing records by email).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, UTC
from app.core.database import SessionLocal
from app.core.security import get_password_hash

# ── Models ────────────────────────────────────────────────────────────────────
from app.modules.users.models      import User, UserRole
from app.modules.clients.models    import Client
from app.modules.shops.models      import Shop
from app.modules.visits.models     import Visit, VisitStatus
from app.modules.projects.models   import Project, ProjectStatus
from app.modules.issues.models     import Issue, IssueStatus, IssueSeverity
from app.modules.todos.models      import Todo
from app.modules.notifications.models import Notification

db = SessionLocal()

def already_exists(model, **kwargs):
    return db.query(model).filter_by(**kwargs).first()

# ── 1. USERS ──────────────────────────────────────────────────────────────────
print("Seeding users...")

users_data = [
    dict(email="admin@crmsetu.com",     name="Arjun Mehta",    role=UserRole.ADMIN,                    phone="9800000001"),
    dict(email="sales1@crmsetu.com",    name="Priya Sharma",   role=UserRole.SALES,                    phone="9800000002"),
    dict(email="sales2@crmsetu.com",    name="Rahul Verma",    role=UserRole.SALES,                    phone="9800000003"),
    dict(email="tele1@crmsetu.com",     name="Sneha Joshi",    role=UserRole.TELESALES,                phone="9800000004"),
    dict(email="pm1@crmsetu.com",       name="Vikram Nair",    role=UserRole.PROJECT_MANAGER,          phone="9800000005"),
    dict(email="pm2@crmsetu.com",       name="Neha Gupta",     role=UserRole.PROJECT_MANAGER_AND_SALES, phone="9800000006"),
    dict(email="client1@example.com",   name="Karan Patel",    role=UserRole.CLIENT,                   phone="9800000007"),
]

created_users = {}
for u in users_data:
    if not already_exists(User, email=u["email"]):
        user = User(
            email=u["email"],
            name=u["name"],
            role=u["role"],
            phone=u["phone"],
            hashed_password=get_password_hash("Test@1234"),
            is_active=True,
        )
        db.add(user)
        db.flush()
        created_users[u["email"]] = user
        print(f"  + User: {u['name']} ({u['role']})")
    else:
        created_users[u["email"]] = already_exists(User, email=u["email"])
        print(f"  ~ Exists: {u['email']}")

db.commit()

admin = created_users["admin@crmsetu.com"]
sales1 = created_users["sales1@crmsetu.com"]
sales2 = created_users["sales2@crmsetu.com"]
pm1   = created_users["pm1@crmsetu.com"]
pm2   = created_users["pm2@crmsetu.com"]

# ── 2. CLIENTS ────────────────────────────────────────────────────────────────
print("\nSeeding clients...")

clients_data = [
    dict(name="TechNova Solutions",   email="technova@biz.com",     phone="9811111111", organization="TechNova Pvt Ltd",  owner_id=sales1.id, pm_id=pm1.id),
    dict(name="Green Infra Corp",     email="greeninfra@biz.com",   phone="9822222222", organization="Green Infra Ltd",   owner_id=sales1.id, pm_id=pm2.id),
    dict(name="Star Retail Group",    email="starretail@biz.com",   phone="9833333333", organization="Star Retail",       owner_id=sales2.id, pm_id=pm1.id),
    dict(name="Maple Finance",        email="maple@finance.com",    phone="9844444444", organization="Maple Finance Co",  owner_id=sales2.id, pm_id=pm2.id),
    dict(name="BlueSky Logistics",    email="bluesky@logistics.com",phone="9855555555", organization="BlueSky Pvt Ltd",  owner_id=sales1.id, pm_id=pm1.id),
]

created_clients = []
for c in clients_data:
    if not already_exists(Client, email=c["email"]):
        client = Client(**c, is_active=True)
        db.add(client)
        db.flush()
        created_clients.append(client)
        print(f"  + Client: {c['name']}")
    else:
        created_clients.append(already_exists(Client, email=c["email"]))
        print(f"  ~ Exists: {c['email']}")

db.commit()

# ── 3. SHOPS ──────────────────────────────────────────────────────────────────
print("\nSeeding shops...")

shops_data = [
    dict(name="Central Electronics",  address="MG Road, Pune",          contact_person="Amit Shah",   phone="9866666661", source="Walk-in"),
    dict(name="Metro Furniture Store",address="FC Road, Pune",           contact_person="Ritu Desai",  phone="9866666662", source="Online"),
    dict(name="Prime Auto Parts",     address="Hadapsar, Pune",          contact_person="Deepak Rao",  phone="9866666663", source="Referral"),
    dict(name="Sunrise Pharmacy",     address="Kothrud, Pune",           contact_person="Meena Kulk",  phone="9866666664", source="Walk-in"),
    dict(name="Nova Clothing Hub",    address="Viman Nagar, Pune",       contact_person="Sanjay Modi", phone="9866666665", source="Social Media"),
    dict(name="Horizon Books",        address="Camp, Pune",              contact_person="Priya Lal",   phone="9866666666", source="Online"),
]

created_shops = []
for s in shops_data:
    if not already_exists(Shop, name=s["name"]):
        shop = Shop(**s)
        db.add(shop)
        db.flush()
        created_shops.append(shop)
        print(f"  + Shop: {s['name']}")
    else:
        created_shops.append(already_exists(Shop, name=s["name"]))
        print(f"  ~ Exists: {s['name']}")

db.commit()

# ── 4. VISITS ─────────────────────────────────────────────────────────────────
print("\nSeeding visits...")

now = datetime.now(UTC)
visits_data = [
    dict(shop_id=created_shops[0].id, user_id=sales1.id, status="SCHEDULED",  notes="Scheduled demo call",               visit_date=now - timedelta(days=5)),
    dict(shop_id=created_shops[1].id, user_id=sales1.id, status="COMPLETED",  notes="Very happy with the product",       visit_date=now - timedelta(days=4)),
    dict(shop_id=created_shops[2].id, user_id=sales2.id, status="MISSED",     notes="Client not available",              visit_date=now - timedelta(days=3)),
    dict(shop_id=created_shops[3].id, user_id=sales2.id, status="SCHEDULED",  notes="Needs internal approval first",     visit_date=now - timedelta(days=2)),
    dict(shop_id=created_shops[4].id, user_id=sales1.id, status="COMPLETED",  notes="Ready to sign contract",            visit_date=now - timedelta(days=1)),
    dict(shop_id=created_shops[5].id, user_id=sales2.id, status="CANCELLED",  notes="Client cancelled",  decline_remarks="Will reschedule next month", visit_date=now),
]

# Use raw SQL since Visit model column names differ from actual DB columns
from sqlalchemy import text
for v in visits_data:
    db.execute(text("""
        INSERT INTO visits (shop_id, user_id, status, notes, decline_remarks, visit_date, created_at, updated_at)
        VALUES (:shop_id, :user_id, :status, :notes, :decline_remarks, :visit_date, :created_at, :updated_at)
    """), {
        "shop_id": v["shop_id"],
        "user_id": v["user_id"],
        "status": v["status"],
        "notes": v.get("notes"),
        "decline_remarks": v.get("decline_remarks"),
        "visit_date": v["visit_date"],
        "created_at": now,
        "updated_at": now,
    })
db.commit()
print(f"  + {len(visits_data)} visits added")

# ── 5. PROJECTS ───────────────────────────────────────────────────────────────
print("\nSeeding projects...")

projects_data = [
    dict(name="CRM Portal Rollout",    description="Full CRM deployment for TechNova",      client_id=created_clients[0].id, pm_id=pm1.id, status="ONGOING",    budget=250000.0, start_date=now - timedelta(days=30), end_date=now + timedelta(days=60)),
    dict(name="Infra Monitoring Setup",description="Setup monitoring dashboard for Infra",  client_id=created_clients[1].id, pm_id=pm2.id, status="PLANNED",    budget=150000.0, start_date=now + timedelta(days=5),  end_date=now + timedelta(days=90)),
    dict(name="Retail ERP Integration",description="Integrate ERP with retail POS system",  client_id=created_clients[2].id, pm_id=pm1.id, status="ON_HOLD",    budget=320000.0, start_date=now - timedelta(days=10), end_date=now + timedelta(days=45)),
    dict(name="Finance App Revamp",    description="UI/UX overhaul for finance web app",    client_id=created_clients[3].id, pm_id=pm2.id, status="COMPLETED",  budget=180000.0, start_date=now - timedelta(days=90), end_date=now - timedelta(days=5)),
    dict(name="Logistics Dashboard",   description="Real-time shipment tracking dashboard", client_id=created_clients[4].id, pm_id=pm1.id, status="ONGOING",    budget=210000.0, start_date=now - timedelta(days=15), end_date=now + timedelta(days=30)),
]

from sqlalchemy import text
project_ids = []
for p in projects_data:
    existing = db.execute(text("SELECT id FROM projects WHERE name=:name"), {"name": p["name"]}).fetchone()
    if existing:
        project_ids.append(existing[0])
        print(f"  ~ Exists: {p['name']}")
    else:
        result = db.execute(text("""
            INSERT INTO projects (name, description, client_id, pm_id, status, budget, start_date, end_date, created_at, updated_at)
            VALUES (:name, :description, :client_id, :pm_id, :status::projectstatus, :budget, :start_date, :end_date, :now, :now)
            RETURNING id
        """), {**p, "now": now})
        proj_id = result.fetchone()[0]
        project_ids.append(proj_id)
        print(f"  + Project: {p['name']} [{p['status']}]")

db.commit()

# ── 6. ISSUES ─────────────────────────────────────────────────────────────────
print("\nSeeding issues...")

issues_data = [
    dict(title="Login page crashes on mobile",      description="Users report 500 error on mobile login", status="OPEN",        severity="HIGH",   client_id=created_clients[0].id, project_id=project_ids[0], reporter_id=admin.id, assigned_to_id=pm1.id),
    dict(title="Report export timeout",             description="CSV export times out for large data",    status="IN_PROGRESS", severity="MEDIUM", client_id=created_clients[1].id, project_id=project_ids[1], reporter_id=sales1.id, assigned_to_id=pm2.id),
    dict(title="Invoice number not auto-generated", description="Billing module missing auto-increment",  status="OPEN",        severity="HIGH",   client_id=created_clients[2].id, project_id=project_ids[2], reporter_id=sales2.id, assigned_to_id=pm1.id),
    dict(title="Dashboard charts not loading",      description="Pie chart throws JS error on Safari",    status="RESOLVED",    severity="LOW",    client_id=created_clients[3].id, project_id=project_ids[3], reporter_id=admin.id, assigned_to_id=pm2.id),
    dict(title="Slow API response on filters",      description="Filter endpoint takes 8+ seconds",       status="IN_PROGRESS", severity="MEDIUM", client_id=created_clients[4].id, project_id=project_ids[4], reporter_id=pm1.id, assigned_to_id=pm2.id),
    dict(title="Email notifications not firing",    description="Notification emails queued but unsent",  status="OPEN",        severity="HIGH",   client_id=created_clients[0].id, project_id=None,            reporter_id=admin.id, assigned_to_id=pm1.id),
]

for i in issues_data:
    db.execute(text("""
        INSERT INTO issues (title, description, status, severity, client_id, project_id, reporter_id, assigned_to_id)
        VALUES (:title, :description, :status, :severity, :client_id, :project_id, :reporter_id, :assigned_to_id)
    """), i)
db.commit()
print(f"  + {len(issues_data)} issues added")

# ── 7. TODOS ──────────────────────────────────────────────────────────────────
print("\nSeeding todos...")

try:
    todos_data = [
        dict(user_id=admin.id,  title="Review Q1 sales report",      description="Go through all region-wise sales data", status="PENDING",     due_date=now + timedelta(days=2)),
        dict(user_id=sales1.id, title="Follow up with TechNova",     description="Schedule demo call with client",        status="IN_PROGRESS", due_date=now + timedelta(days=1)),
        dict(user_id=sales2.id, title="Prepare proposal for Maple",  description="Draft pricing proposal document",       status="PENDING",     due_date=now + timedelta(days=3)),
        dict(user_id=pm1.id,    title="Update project timeline",     description="Revise milestones after delay",         status="COMPLETED",   due_date=now - timedelta(days=1)),
        dict(user_id=pm2.id,    title="Conduct sprint retrospective",description="Team retrospective for sprint 4",       status="PENDING",     due_date=now + timedelta(days=4)),
    ]

    from app.modules.todos.models import Todo
    for t in todos_data:
        todo = Todo(**t)
        db.add(todo)
    db.commit()
    print(f"  + {len(todos_data)} todos added")
except Exception as e:
    db.rollback()
    print(f"  ! Skipped todos: {e}")

# ── 8. NOTIFICATIONS ──────────────────────────────────────────────────────────
print("\nSeeding notifications...")

try:
    notifs_data = [
        dict(user_id=admin.id,  title="New Issue Raised",    message="A HIGH severity issue was reported on CRM Portal Rollout.", is_read=False),
        dict(user_id=pm1.id,    title="Project Assigned",    message="You have been assigned as PM for Logistics Dashboard.",      is_read=False),
        dict(user_id=sales1.id, title="Visit Follow-up Due", message="Follow up with Central Electronics within 24 hours.",        is_read=True),
        dict(user_id=pm2.id,    title="Budget Alert",        message="Infra Monitoring Setup budget is 80% utilised.",             is_read=False),
        dict(user_id=admin.id,  title="Client Onboarded",    message="BlueSky Logistics has been successfully onboarded.",         is_read=True),
    ]

    from app.modules.notifications.models import Notification
    for n in notifs_data:
        notif = Notification(**n)
        db.add(notif)
    db.commit()
    print(f"  + {len(notifs_data)} notifications added")
except Exception as e:
    db.rollback()
    print(f"  ! Skipped notifications: {e}")

# ── Done ──────────────────────────────────────────────────────────────────────
db.close()
print("\n[DONE] Seed complete! Login credentials:")
print("   All users password: Test@1234")
print("   Admin   -> admin@crmsetu.com")
print("   Sales   -> sales1@crmsetu.com / sales2@crmsetu.com")
print("   Tele    -> tele1@crmsetu.com")
print("   PM      -> pm1@crmsetu.com / pm2@crmsetu.com")
