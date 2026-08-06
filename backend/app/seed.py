"""建立示範資料：一個組織、三個分支、若干樓層、九間房間、幾位用戶與群組。

Idempotent：已有資料就不重複建立。
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from .db.session import SessionLocal
from .db.init_db import init_db
from .core.security import hash_password
from .models import (
    Organization, Branch, Location,
    User, UserGroup, UserGroupMember,
    UserGroupCategory, AssignableRole,
    Resource, Reservation,
    Amenity, ResourceAmenity,
)


ROOMS = [
    ("會議室 A", 10, None, "HQ 1F"),
    ("會議室 B", 12, None, "HQ 1F"),
    ("培訓室", 26, None, "HQ 1F"),
    ("創新實驗室", 28, None, "HQ 1F"),
    ("台北分公司會議室1", 10, "會議室", "台北 1F"),
    ("新竹分公司會議室A", 10, None, "新竹 1F"),
    ("台北分公司會議室B", 10, None, "台北 B1"),
    ("董事長會議室", 10, None, "HQ 1F"),
    ("可合併會議室1", 10, None, "HQ B1"),
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        # 1) 組織
        org = db.execute(select(Organization).where(Organization.slug == "bizlution")).scalar_one_or_none()
        if not org:
            org = Organization(name="bizlution", slug="bizlution", timezone="Asia/Taipei", locale="zh-TW", plan="trial")
            db.add(org); db.flush()
            print(f"[seed] organization created id={org.id}")

        # 2) 分支（含 parent 階層：HQ 為總部，其他分公司 parent=HQ）
        branches: dict[str, Branch] = {}
        for name in ["HQ", "台北分公司", "新竹分公司"]:
            b = db.execute(select(Branch).where(Branch.organization_id == org.id, Branch.name == name)).scalar_one_or_none()
            if not b:
                b = Branch(organization_id=org.id, name=name, timezone="Asia/Taipei",
                           address={"HQ": "—", "台北分公司": "台北市內湖區", "新竹分公司": "新竹市"}[name])
                db.add(b); db.flush()
            branches[name] = b
        # 設定 parent_branch_id：台北 / 新竹 分公司都由 HQ 管
        for sub in ["台北分公司", "新竹分公司"]:
            if branches[sub].parent_branch_id != branches["HQ"].id:
                branches[sub].parent_branch_id = branches["HQ"].id
        db.flush()

        # 3) 樓層
        locations: dict[str, Location] = {}
        for br_name, floor in [("HQ", "1F"), ("HQ", "B1"), ("台北分公司", "1F"), ("台北分公司", "B1"), ("新竹分公司", "1F")]:
            key = f"{br_name.replace('分公司','')} {floor}"
            l = db.execute(select(Location).where(Location.branch_id == branches[br_name].id, Location.name == floor)).scalar_one_or_none()
            if not l:
                l = Location(branch_id=branches[br_name].id, type="floor", name=floor)
                db.add(l); db.flush()
            locations[key] = l

        # 4a) 群組類別（分類）—— 涵蓋既有 category key + 需求指定的「維修組」「部門」
        for key, label, icon, enabled, public in [
            ("admin",       "管理者", "ti-shield-lock",    True,  True),
            ("support",     "支援",   "ti-lifebuoy",        True,  True),
            ("general",     "一般",   "ti-users",           True,  True),
            ("guest",       "訪客",   "ti-user-question",   True,  True),
            ("maintenance", "維修組", "ti-tool",            True,  False),
            ("department",  "部門",   "ti-building",        True,  True),
        ]:
            c = db.execute(select(UserGroupCategory).where(
                UserGroupCategory.organization_id == org.id,
                UserGroupCategory.key == key,
            )).scalar_one_or_none()
            if not c:
                db.add(UserGroupCategory(
                    organization_id=org.id, key=key, label=label, icon=icon,
                    is_enabled=enabled, is_public_visible=public,
                ))
        db.flush()

        # 4) 群組
        groups: dict[str, UserGroup] = {}
        for g_name, cat, desc in [
            ("系統管理員", "admin", "組織全域最高權限，可管理所有模組。"),
            ("支援職員", "support", "可處理工單、瀏覽相關資源；不可修改組織設定。"),
            ("一般員工", "general", "可預約分配到的資源、查看公告。"),
            ("訪客", "guest", "僅可查看公用資訊與大廳看板。"),
        ]:
            g = db.execute(select(UserGroup).where(UserGroup.organization_id == org.id, UserGroup.name == g_name)).scalar_one_or_none()
            if not g:
                g = UserGroup(organization_id=org.id, name=g_name, category=cat, description=desc)
                db.add(g); db.flush()
            groups[g_name] = g

        # 5) 用戶（含所屬分支，供審批權限判斷）
        users_seed = [
            # (email, display_name, password, group_name, branch_name)
            ("ingrid@bizlution.com",      "Ingrid",             "Ingrid1234!",  "系統管理員", "HQ"),
            ("ingridiaim@gmail.com",      "Ingridiaim 台北員工", "User1234!",    "一般員工",   "台北分公司"),
            ("m0341018@mail.hfu.edu.tw",  "新竹分公司維修 A",   "Support1234!", "支援職員",   "新竹分公司"),
            # 台北分公司管理員（測試審批權限用）
            ("tp-admin@bizlution.com",    "台北分公司管理員",   "Admin1234!",   "系統管理員", "台北分公司"),
            # 新竹分公司管理員
            ("hc-admin@bizlution.com",    "新竹分公司管理員",   "Admin1234!",   "系統管理員", "新竹分公司"),
        ]
        user_ids: dict[str, User] = {}
        for email, name, pw, group_name, br_name in users_seed:
            u = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if not u:
                u = User(
                    organization_id=org.id,
                    email=email,
                    display_name=name,
                    status="active",
                    password_hash=hash_password(pw),
                    branch_id=branches[br_name].id,
                )
                db.add(u); db.flush()
                db.add(UserGroupMember(user_id=u.id, group_id=groups[group_name].id))
            elif not u.branch_id:
                # 已存在但沒有分支 → 補上
                u.branch_id = branches[br_name].id
            user_ids[email] = u

        # 5a) 可指派角色（示範）
        for r_name, r_desc, r_icon, bind_group in [
            ("預約審批人",    "各分支的預約單審批人；由「預約規則」在送出時尋找此角色。", "ti-user-check",  None),
            ("房間管理員",    "維護房間資料、設備狀態、關閉／開放房間。",                "ti-door",        "系統管理員"),
            ("樓層管理員",    "維護樓層平面圖、資源座標。",                              "ti-map-pin",     None),
            ("緊急聯絡人",    "緊急事件通知；不掛任何權限。",                            "ti-alert-triangle", None),
        ]:
            r = db.execute(select(AssignableRole).where(
                AssignableRole.organization_id == org.id,
                AssignableRole.name == r_name,
            )).scalar_one_or_none()
            if not r:
                bound_id = groups[bind_group].id if bind_group and bind_group in groups else None
                db.add(AssignableRole(
                    organization_id=org.id, name=r_name, description=r_desc,
                    icon=r_icon, bound_group_id=bound_id, is_enabled=True,
                ))
        db.flush()

        # 6a) 設備（equipment）
        EQUIPMENT = [
            ("筆記型電腦推車",   "Sample equipment resource - 筆記型電腦推車", None),
            ("投影設備",         "Sample equipment resource - 投影設備", None),
            ("視訊會議套件",     "Sample equipment resource - 視訊會議套件", None),
            ("音訊設備",         "Sample equipment resource - 音訊設備", None),
            ("簡報套件",         "Sample equipment resource - 簡報套件", None),
            ("直立式機櫃",       "Sample equipment resource - 直立式機櫃", "其他設備類型"),
            ("電子桌牌T7-1",     "Sample equipment resource - 電子桌牌", "其他設備類型"),
            ("設備 8",           "Sample equipment resource - 設備 8", None),
            ("設備 9",           "Sample equipment resource - 設備 9", None),
        ]
        for name, desc, category in EQUIPMENT:
            e = db.execute(select(Resource).where(Resource.organization_id == org.id, Resource.name == name)).scalar_one_or_none()
            if not e:
                db.add(Resource(
                    organization_id=org.id, type="equipment",
                    name=name, description=desc, category=category,
                    branch_id=branches["HQ"].id if category else None,
                    status="available", requires_approval=False, priority=0,
                ))
        db.flush()

        # 6b) 附屬設備（amenities）
        AMENITIES = [
            ("Wi-Fi",    "wifi"),
            ("投影屏幕", "presentation"),
            ("投影機",   "device-projector"),
            ("視像會議", "video"),
            ("語音會議", "phone-call"),
            ("電視",     "device-tv"),
            ("麥克風",   "microphone"),
        ]
        amenity_objs: dict[str, Amenity] = {}
        for a_name, a_icon in AMENITIES:
            am = db.execute(select(Amenity).where(
                Amenity.organization_id == org.id, Amenity.name == a_name
            )).scalar_one_or_none()
            if not am:
                am = Amenity(organization_id=org.id, name=a_name, icon=a_icon,
                             branch_id=branches["HQ"].id)
                db.add(am)
                db.flush()
            amenity_objs[a_name] = am

        # 6) 房間（預設 requires_approval=True — 每間會議室都需要審批）
        for name, capacity, category, loc_key in ROOMS:
            r = db.execute(select(Resource).where(Resource.organization_id == org.id, Resource.name == name)).scalar_one_or_none()
            if not r:
                r = Resource(
                    organization_id=org.id, type="room", subtype="standard",
                    name=name, capacity=capacity, category=category,
                    location_id=locations[loc_key].id if loc_key in locations else None,
                    status="available",
                    requires_approval=True,
                )
                db.add(r)
            else:
                # 政策遷移：既有房間 → 一律設為需要審批（v3.13）
                if not r.requires_approval:
                    r.requires_approval = True

        db.commit()

        # 6c) 附屬設備 ↔ 房間 關聯
        AMENITY_ROOM_MAP = {
            "Wi-Fi":    ["會議室 B", "培訓室", "創新實驗室", "台北分公司會議室B", "董事長會議室"],
            "投影屏幕": ["新竹分公司會議室A", "董事長會議室"],
            "投影機":   ["會議室 A", "創新實驗室", "新竹分公司會議室A", "台北分公司會議室B"],
            "視像會議": ["會議室 A", "新竹分公司會議室A", "董事長會議室"],
            "語音會議": ["會議室 A", "會議室 B", "培訓室", "創新實驗室", "台北分公司會議室B", "董事長會議室"],
            "電視":     ["培訓室", "新竹分公司會議室A", "董事長會議室"],
            "麥克風":   ["會議室 B", "新竹分公司會議室A", "董事長會議室"],
        }
        for a_name, room_names in AMENITY_ROOM_MAP.items():
            am = amenity_objs.get(a_name)
            if not am:
                continue
            for rn in room_names:
                room = db.execute(select(Resource).where(
                    Resource.organization_id == org.id, Resource.name == rn
                )).scalar_one_or_none()
                if not room:
                    continue
                exists = db.execute(select(ResourceAmenity).where(
                    ResourceAmenity.amenity_id == am.id,
                    ResourceAmenity.resource_id == room.id,
                )).scalar_one_or_none()
                if not exists:
                    db.add(ResourceAmenity(amenity_id=am.id, resource_id=room.id))
        db.commit()

        # 7) 一筆示範預約：明天早上 10:00 - 11:00，會議室 A，主辦人 Ingrid
        room_a = db.execute(select(Resource).where(Resource.name == "會議室 A")).scalar_one_or_none()
        ingrid = user_ids["ingrid@bizlution.com"]
        if room_a and ingrid:
            existing = db.execute(select(Reservation).where(Reservation.resource_id == room_a.id)).first()
            if not existing:
                now = datetime.now(timezone.utc)
                start = (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)  # UTC 02:00 = TW 10:00
                db.add(Reservation(
                    organization_id=org.id,
                    resource_id=room_a.id,
                    organizer_id=ingrid.id,
                    title="週會",
                    start_at=start,
                    end_at=start + timedelta(hours=1),
                    type="normal",
                    status="approved",
                ))
                db.commit()

        print("[seed] done.")
        print("[seed] login: ingrid@bizlution.com / Ingrid1234!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
