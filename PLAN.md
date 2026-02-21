# Plan: Merge 3 User Tables into Single `users` Table

## Summary
Merge `customers`, `dealers`, and `system_users` into one unified `users` table with role flags (`is_customer`, `is_dealer`, `is_admin`). A user can have multiple roles simultaneously (e.g., a dealer who also shops as a customer).

---

## Design Decisions

### 1. Single Flat Table (Option A)
One `users` table with nullable role-specific fields. No separate profile tables — role-specific fields (tier_id, api_key, admin_role, etc.) are nullable columns only used when the corresponding role flag is `True`.

**Why**: Simpler queries, no JOINs, fewer files, easier migration.

### 2. Role Flags (not enum)
```python
is_customer = Column(Boolean, default=False)
is_dealer   = Column(Boolean, default=False)
is_admin    = Column(Boolean, default=False)
```
A user can be any combination (customer+dealer, customer+admin, all three, etc.).

### 3. Single Auth Cookie
Replace 3 cookies (`auth_token`, `dealer_token`, `customer_token`) with ONE `auth_token` cookie. JWT payload contains `sub=mobile`. The `get_current_active_user()` function queries the single `users` table.

### 4. Wallet Simplification
Replace `(owner_type, owner_id, asset_code)` with `(user_id, asset_code)`. Remove `owner_type` polymorphism since all users are in one table now.

### 5. Ticket Simplification
Replace `customer_id` + `dealer_id` FKs with single `user_id` FK. Keep `sender_type` enum to track "in what capacity" the ticket was sent.

---

## Merged User Model Fields

```
Identity:       id, mobile(11), national_id(unique,nullable)
Profile:        first_name, last_name, birth_date, avatar_path
Auth:           otp_code, otp_expiry
Roles:          is_customer, is_dealer, is_admin, is_active
Customer:       customer_type, company_name, economic_code, referral_code, referred_by, referral_rewarded
Dealer:         tier_id(FK), commission_percent, is_warehouse, is_postal_hub, api_key, province_id(FK), city_id(FK), district_id(FK), landline_phone
Admin:          admin_role("admin"|"operator"), admin_permissions(JSON)
Address:        postal_code, address, phone
Audit:          created_at, updated_at
```

**Name handling**: `first_name` + `last_name` stored separately. Property `full_name` computes `f"{first_name} {last_name}"`. For dealers/admins created without split names, both fields are populated on creation.

---

## Implementation Phases

### Phase 1: Create New User Model
**File: `modules/user/__init__.py`** (new)
**File: `modules/user/models.py`** (new)
- Define `User` model with all merged fields
- Properties: `full_name`, `display_name`, `is_profile_complete`, `is_staff`, `roles`
- Backward-compat properties: `has_permission()`, `role` (for admin), `type_label`/`type_icon`/`type_color` (for dealer)
- Keep `hashed_password` field from SystemUser (for admin login with password)

### Phase 2: Update Auth System
**Files:**
- `modules/auth/deps.py` — Single `get_current_active_user()` reading ONE cookie, querying `users` table. Update `require_customer`, `require_dealer`, `require_staff`, etc.
- `modules/auth/service.py` — Single `create_token(mobile)` and `verify_token()`. Remove separate staff/customer/dealer token functions.
- `modules/auth/routes.py` — Single login flow: enter mobile → OTP → set `auth_token` cookie. After login, redirect based on roles (admin→dashboard, dealer→dealer panel, customer→shop).
- `common/security.py` — Simplify JWT functions if needed.

### Phase 3: Update All FK References
Each model file needs FKs changed from `customers.id`/`dealers.id`/`system_users.id` to `users.id`:

| File | Changes |
|------|---------|
| `modules/inventory/models.py` | Bar.customer_id→user_id, Bar.reserved_customer_id, Bar.dealer_id→dealer_user_id (or just user_id with context), OwnershipHistory.previous_owner_id/new_owner_id, BarTransfer.from_customer_id→from_user_id, DealerTransfer.from_dealer_id/to_dealer_id→from_user_id/to_user_id |
| `modules/order/models.py` | Order.customer_id→user_id, Order.pickup_dealer_id→pickup_dealer_user_id |
| `modules/cart/models.py` | Cart.customer_id→user_id |
| `modules/wallet/models.py` | Account: remove owner_type, add user_id(FK→users), unique=(user_id, asset_code). WalletTopup.customer_id→user_id. WithdrawalRequest: remove customer_id+dealer_id, add user_id |
| `modules/coupon/models.py` | CouponUsage.customer_id→user_id |
| `modules/ticket/models.py` | Ticket: remove customer_id+dealer_id, add user_id(FK→users). Keep sender_type + assigned_to→FK users |
| `modules/dealer/models.py` | DealerSale.dealer_id→user_id. BuybackRequest.dealer_id→user_id. Remove Dealer model class. |
| `modules/dealer_request/models.py` | DealerRequest.customer_id→user_id |
| `modules/customer/address_models.py` | CustomerAddress.customer_id→user_id |
| `modules/review/models.py` | Review.customer_id→user_id, ProductComment.customer_id→user_id, CommentLike.customer_id→user_id |

### Phase 4: Update Services
Each service that imports Customer/Dealer/SystemUser must use User instead:

| File | Key Changes |
|------|-------------|
| `modules/dealer/service.py` | `from modules.user.models import User`. Query `User` with `is_dealer==True`. Update create_pos_sale, create_buyback, etc. |
| `modules/customer/admin_service.py` | Query `User` with `is_customer==True` |
| `modules/wallet/service.py` | Remove OwnerType logic, use user_id directly. `get_or_create_account(user_id, asset_code)` |
| `modules/ticket/service.py` | Use user_id instead of customer_id/dealer_id |
| `modules/order/service.py` | Use user_id |
| `modules/coupon/service.py` | Use user_id |
| `modules/ownership/service.py` | Use user_id |
| `modules/admin/dashboard_service.py` | Count users by role flags |
| `modules/admin/staff_service.py` | Query `User` with `is_admin==True` |
| `modules/pricing/feed_service.py` | No user refs (skip) |

### Phase 5: Update Routes
Every route file using auth dependencies:

| File | Key Changes |
|------|-------------|
| `modules/shop/routes.py` | `require_customer` still works (checks user.is_customer) |
| `modules/cart/routes.py` | Use user.id instead of customer.id |
| `modules/order/routes.py` | Use user.id |
| `modules/payment/routes.py` | Use user.id |
| `modules/wallet/routes.py` | Use user.id, remove owner_type |
| `modules/dealer/routes.py` | `require_dealer` checks user.is_dealer |
| `modules/dealer/admin_routes.py` | Query users with is_dealer |
| `modules/dealer/api_routes.py` | API key lookup on User table |
| `modules/dealer/wallet_routes.py` | Use user.id |
| `modules/customer/routes.py` | Use user.id |
| `modules/customer/admin_routes.py` | Query users with is_customer |
| `modules/ticket/routes.py` | Use user.id |
| `modules/ticket/admin_routes.py` | Use user.id |
| `modules/ownership/routes.py` | Use user.id |
| `modules/review/routes.py` | Use user.id |
| `modules/coupon/admin_routes.py` | Use user.id |
| `modules/dealer_request/routes.py` | Use user.id |
| `modules/dealer_request/admin_routes.py` | Use user.id |
| `modules/admin/routes.py` | Use user.id |

### Phase 6: Update Templates
- `templates/shop/base_shop.html` — `user.is_staff` → `user.is_admin`; show dealer menu if `user.is_dealer`
- `templates/admin/base_admin.html` — `user.has_permission()` stays (method on User)
- `templates/dealer/base_dealer.html` — `user.is_dealer` check
- All templates that reference `user.full_name` → works via property
- Navbar: if user has multiple roles, show role switcher or links to all panels

### Phase 7: Update main.py
- Import `User` from `modules/user/models`
- Remove imports of `Customer`, `Dealer`, `SystemUser`
- Update `_identify_user()` to read single `auth_token` cookie
- Update model registration for `Base.metadata.create_all()`

### Phase 8: Update Seeds
- `scripts/seed.py` — Create User objects with role flags
- `scripts/seed_production.py` — Same
- `scripts/init_db.py` — Update imports
- Test accounts: same mobiles, but now single User per mobile

### Phase 9: Update CLAUDE.md & Docs
- Update model documentation
- Update API docs
- Update Feature-Catalog.md, Test-Playbook.md

---

## Migration Notes
- **No production data** → clean `--reset` seed is sufficient
- Old `customers`, `dealers`, `system_users` tables will be dropped
- `migrate_production.sql` will be updated with proper SQL if needed later
- Alembic env.py updated to import new User model

## Risk Mitigation
- Each phase will be tested incrementally
- Seed script tested after model changes
- Server startup verified after each phase
- All role-based access tested (customer, dealer, admin flows)

## Estimated Scope
- ~30 Python files modified
- ~15 template files modified
- ~2 new files created (modules/user/)
- ~3 files deleted (old model references consolidated)
