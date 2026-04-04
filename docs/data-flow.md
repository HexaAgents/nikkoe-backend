# Platform Data Flow Diagrams

Every user input in the Nikkoe platform, mapped to its communication path and the database tables it affects.

## Communication Patterns

There are two communication patterns in the platform:

1. **Frontend to Backend API to Supabase Auth** -- Login, Signup, Change Password
2. **Frontend to Backend API to Database** -- All CRUD operations (sales, receipts, items, etc.) and user creation

The frontend never communicates directly with Supabase Auth or the database. All operations go through the backend.

---

## Master Overview

```mermaid
flowchart TD
    User([User Browser])

    subgraph frontend [Frontend - React SPA]
        LoginPage[Login / Signup]
        SalesPage[Sales Page]
        ReceiptsPage[Receipts Page]
        ItemsPage[Items Page]
        SettingsPage[Settings Page]
    end

    subgraph backend [Python FastAPI Backend]
        AuthRouter[Auth Router]
        AuthMW[Auth Middleware]
        Routers[11 API Routers]
        Services[11 Services]
        Repos[11 Repositories]
    end

    subgraph supabaseAuth [Supabase Auth]
        AuthAPI[Auth API]
    end

    subgraph database [Supabase PostgreSQL]
        Tables["sales, receipts, items, suppliers, locations, categories, channels, customer, inventory_movements, supplier_quotes, users"]
        RPCs["create_sale(), create_receipt(), void_sale(), void_receipt()"]
        Views["inventory_balances (view)"]
    end

    subgraph analytics [PostHog]
        Events[Analytics Events]
    end

    User --> frontend
    LoginPage -->|"POST /api/auth/login or /signup"| AuthRouter
    AuthRouter -->|"signInWithPassword() / signUp()"| AuthAPI
    AuthAPI -->|JWT session| AuthRouter
    AuthRouter -->|JWT| LoginPage
    LoginPage -->|"setSession(JWT)"| frontend

    SalesPage -->|"HTTP + JWT"| AuthMW
    ReceiptsPage -->|"HTTP + JWT"| AuthMW
    ItemsPage -->|"HTTP + JWT"| AuthMW
    SettingsPage -->|"HTTP + JWT"| AuthMW

    AuthMW -->|"verify JWT"| AuthAPI
    AuthMW --> Routers
    Routers --> Services
    Services --> Repos
    Repos --> Tables
    Repos --> RPCs
    Repos --> Views

    SettingsPage -->|"POST /api/auth/change-password"| AuthRouter

    frontend -->|"track events"| Events
```

---

## Authentication

### Login

```mermaid
flowchart LR
    subgraph login [Login Page]
        L1[Email input]
        L2[Password input]
        L3[Sign In button]
    end
    L3 -->|"POST /api/auth/login"| Backend[Backend Auth Router]
    Backend -->|"signInWithPassword()"| SupaAuth[Supabase Auth]
    SupaAuth -->|JWT session| Backend
    Backend -->|"{ user, session }"| FE[Frontend]
    FE -->|"setSession(JWT)"| Supabase[Supabase Client - localStorage]
    L3 -->|"analytics.track()"| PostHog[PostHog]
```

### Signup

```mermaid
flowchart LR
    subgraph signup [Signup Page]
        S1[Email input]
        S2[Password input]
        S3[Confirm Password input]
        S4[Create Account button]
    end
    S4 -->|"POST /api/auth/signup"| Backend2[Backend Auth Router]
    Backend2 -->|"signUp()"| SupaAuth2[Supabase Auth]
    SupaAuth2 -->|"user + session (if auto-confirmed)"| Backend2
    Backend2 -->|"{ user, session }"| FE2[Frontend]
```

### Change Password

```mermaid
flowchart LR
    subgraph chpw [Change Password Form]
        CP1[Current Password input]
        CP2[New Password input]
        CP3[Confirm New Password]
        CP4[Update Password button]
    end
    CP4 -->|"POST /api/auth/change-password + JWT"| Backend3[Backend Auth Router]
    Backend3 -->|"signInWithPassword() to verify"| SupaAuth3[Supabase Auth]
    SupaAuth3 -->|"verified"| Backend3
    Backend3 -->|"admin.update_user_by_id()"| SupaAuth3
```

### Sign Out

```mermaid
flowchart LR
    SignOut[Sign Out button] -->|"analytics.track() + reset()"| PostHog2[PostHog]
    SignOut -->|"supabase.auth.signOut()"| LocalStorage[Clear JWT from localStorage]
```

Sign out is the only auth action that stays in the frontend -- it just clears the locally stored JWT. No credentials are involved.

---

## Sales

### Add Sale Form

```mermaid
flowchart TD
    subgraph saleForm [Add Sale Form]
        SF1[Channel dropdown]
        SF2[Customer combobox]
        SF3[Part Number picker]
        SF4[Location picker]
        SF5[Quantity input]
        SF6[Unit Price input]
        SF7[Currency dropdown]
        SF8[Create Sale button]
        SF9[Add Part button]
        SF10[Add New Customer button]
    end

    SF1 -.->|"on page load"| FE1["GET /api/channels"]
    SF2 -.->|"on page load"| FE2["GET /api/customers"]
    SF3 -.->|"on page load"| FE3["GET /api/items"]
    SF4 -.->|"on page load + auto-select"| FE4["GET /api/locations"]
    SF4 -.->|"auto-location lookup"| FE5["GET /api/inventory/on-hand"]

    SF10 -->|"POST /api/customers"| BE10[Backend]
    BE10 -->|"INSERT INTO customer"| DB10[Database]

    SF8 -->|"POST /api/sales"| BE1[Backend]
    BE1 -->|"Validate with Pydantic"| BE2[SaleService]
    BE2 -->|"RPC create_sale()"| DB1[Database]
    DB1 -->|"INSERT sales + sale_lines"| DB2[sales table]
    DB1 -->|"Trigger: inventory_movements"| DB3[inventory tables]
```

### Void Sale

```mermaid
flowchart LR
    subgraph voidSale [Void Sale Dialog]
        VS1[Reason textarea]
        VS2[Void Sale button]
    end
    VS2 -->|"POST /api/sales/:id/void"| BE_VS[Backend]
    BE_VS -->|"Check user.profile exists"| Guard_VS[ForbiddenError guard]
    Guard_VS -->|"RPC void_sale()"| DB_VS[Database]
    DB_VS -->|"Reverse inventory_movements"| Inv_VS[inventory tables]
    DB_VS -->|"Set status=VOIDED"| Status_VS[sales row]
```

---

## Receipts

### Add Receipt Form

```mermaid
flowchart TD
    subgraph receiptForm [Add Receipt Form]
        RF1[Supplier dropdown]
        RF2[Reference input]
        RF3[Note textarea]
        RF4[Part Number picker]
        RF5[Location picker]
        RF6[Quantity input]
        RF7[Unit Cost input]
        RF8[Currency dropdown]
        RF9[Create Receipt button]
        RF10[New Part button]
        RF11[New Location button]
    end

    RF1 -.->|"on page load"| FER1["GET /api/suppliers"]
    RF4 -.->|"on page load"| FER2["GET /api/items"]
    RF5 -.->|"on page load"| FER3["GET /api/locations"]

    RF10 -->|"opens AddItemModal"| ItemModal[Add Item Modal]
    RF11 -->|"opens AddLocationModal"| LocModal[Add Location Modal]

    RF9 -->|"POST /api/receipts"| BER1[Backend]
    BER1 -->|"Validate with Pydantic"| BER2[ReceiptService]
    BER2 -->|"RPC create_receipt()"| DBR1[Database]
    DBR1 -->|"INSERT receipts + receipt_lines"| DBR2[receipts table]
    DBR1 -->|"Trigger: inventory_movements"| DBR3[inventory tables]
```

### Void Receipt

```mermaid
flowchart LR
    subgraph voidReceipt [Void Receipt Dialog]
        VR1[Reason textarea]
        VR2[Void Receipt button]
    end
    VR2 -->|"POST /api/receipts/:id/void"| BE_VR[Backend]
    BE_VR -->|"Check user.profile exists"| Guard_VR[ForbiddenError guard]
    Guard_VR -->|"RPC void_receipt()"| DB_VR[Database]
    DB_VR -->|"Reverse inventory_movements"| Inv_VR[inventory tables]
    DB_VR -->|"Set status=VOIDED"| Status_VR[receipts row]
```

---

## Items

```mermaid
flowchart TD
    subgraph itemActions [Item Actions]
        IA1[Add Item: part_number + description + category]
        IA2[Edit Item: description + category + Save]
        IA3[Delete Item button]
        IA4[Add Quote: supplier + date + cost + currency + note]
        IA5[Delete Quote button]
    end

    IA1 -->|"POST /api/items"| BE_I1[Backend]
    BE_I1 -->|"INSERT INTO items"| DB_I1[items table]

    IA2 -->|"PUT /api/items/:id"| BE_I2[Backend]
    BE_I2 -->|"UPDATE items"| DB_I2[items table]

    IA3 -->|"DELETE /api/items/:id"| BE_I3[Backend]
    BE_I3 -->|"DELETE FROM items"| DB_I3[items table]

    IA4 -->|"POST /api/supplier-quotes"| BE_I4[Backend]
    BE_I4 -->|"INSERT INTO supplier_quotes"| DB_I4[supplier_quotes table]

    IA5 -->|"DELETE /api/supplier-quotes/:id"| BE_I5[Backend]
    BE_I5 -->|"DELETE FROM supplier_quotes"| DB_I5[supplier_quotes table]
```

---

## Settings: Reference Data

```mermaid
flowchart TD
    subgraph refData [Settings Reference Data]
        RD1["Add Category: name"]
        RD2["Delete Category"]
        RD3["Add Supplier: name + address + email + phone"]
        RD4["Delete Supplier"]
        RD5["Add Location: location_code"]
        RD6["Delete Location"]
    end

    RD1 -->|"POST /api/categories"| BE_C1[Backend] -->|"INSERT"| DB_C1[categories]
    RD2 -->|"DELETE /api/categories/:id"| BE_C2[Backend] -->|"DELETE"| DB_C2[categories]
    RD3 -->|"POST /api/suppliers"| BE_S1[Backend] -->|"INSERT"| DB_S1[suppliers]
    RD4 -->|"DELETE /api/suppliers/:id"| BE_S2[Backend] -->|"DELETE"| DB_S2[suppliers]
    RD5 -->|"POST /api/locations"| BE_L1[Backend] -->|"INSERT"| DB_L1[locations]
    RD6 -->|"DELETE /api/locations/:id"| BE_L2[Backend] -->|"DELETE"| DB_L2[locations]
```

---

## Settings: Add User

```mermaid
flowchart LR
    subgraph addUser [Add User Form]
        AU1[Email input]
        AU2[Password input]
        AU3[Confirm Password]
        AU4[Create User button]
    end
    AU4 -->|"POST /api/users"| BE_U[Backend]
    BE_U -->|"Validate with Pydantic"| Svc[UserService]
    Svc -->|"auth.admin.create_user()"| SupaAdmin[Supabase Auth Admin API]
    SupaAdmin -->|"Creates auth account"| AuthDB[Supabase auth.users table]
```

---

## Page Loads (auto-fetched, no user input)

```mermaid
flowchart TD
    subgraph pages [Page Loads - Auto-fetched Data]
        P1[Sales Page]
        P2[Receipts Page]
        P3[Items Page]
        P4[Item Detail Page]
        P5[Sale Detail Page]
        P6[Receipt Detail Page]
        P7[Settings / Log Page]
    end

    P1 -->|"GET /api/sales"| BE_PG[Backend] -->|"SELECT + batch_load"| DB_PG[Database]
    P2 -->|"GET /api/receipts"| BE_PG
    P3 -->|"GET /api/items"| BE_PG
    P4 -->|"GET /api/items/:id + /quotes + /inventory + /receipts + /sales"| BE_PG
    P5 -->|"GET /api/sales/:id + /lines"| BE_PG
    P6 -->|"GET /api/receipts/:id + /lines"| BE_PG
    P7 -->|"GET /api/inventory/movements"| BE_PG
```

---

## Summary: Every User Input

| Page | User Input | Communication Path | Database Table Affected |
|------|-----------|-------------------|----------------------|
| Login | Email + Password + Submit | Frontend -> Backend -> Supabase Auth | auth.users (read) |
| Signup | Email + Password + Submit | Frontend -> Backend -> Supabase Auth | auth.users (insert) |
| Nav bar | Sign Out button | Frontend only (clear localStorage) | none |
| Sales | Channel dropdown (read) | Frontend -> Backend -> channels | none (read) |
| Sales | Customer combobox (read) | Frontend -> Backend -> customer | none (read) |
| Sales | Add New Customer button | Frontend -> Backend -> customer | customer (insert) |
| Sales | Part Number picker (read) | Frontend -> Backend -> items | none (read) |
| Sales | Location picker (read) | Frontend -> Backend -> locations | none (read) |
| Sales | Quantity + Price + Currency | Frontend only (local state) | none |
| Sales | Create Sale button | Frontend -> Backend -> RPC | sales + sale_lines + inventory_movements |
| Sale Detail | Void Reason + Void button | Frontend -> Backend -> RPC | sales + inventory_movements |
| Receipts | Supplier dropdown (read) | Frontend -> Backend -> suppliers | none (read) |
| Receipts | Reference + Note | Frontend only (local state) | none |
| Receipts | Part/Location/Qty/Cost/Currency | Frontend only (local state) | none |
| Receipts | Create Receipt button | Frontend -> Backend -> RPC | receipts + receipt_lines + inventory_movements |
| Receipts | New Part button | Opens modal -> Frontend -> Backend | items (insert) |
| Receipts | New Location button | Opens modal -> Frontend -> Backend | locations (insert) |
| Receipt Detail | Void Reason + Void button | Frontend -> Backend -> RPC | receipts + inventory_movements |
| Items | Add Item (part + desc + cat) | Frontend -> Backend | items (insert) |
| Item Detail | Edit description + category | Frontend -> Backend | items (update) |
| Item Detail | Delete Item button | Frontend -> Backend | items (delete) |
| Item Detail | Add Quote (supplier + cost + ...) | Frontend -> Backend | supplier_quotes (insert) |
| Item Detail | Delete Quote button | Frontend -> Backend | supplier_quotes (delete) |
| Settings | Add Category (name) | Frontend -> Backend | categories (insert) |
| Settings | Delete Category | Frontend -> Backend | categories (delete) |
| Settings | Add Supplier (name + ...) | Frontend -> Backend | suppliers (insert) |
| Settings | Delete Supplier | Frontend -> Backend | suppliers (delete) |
| Settings | Add Location (code) | Frontend -> Backend | locations (insert) |
| Settings | Delete Location | Frontend -> Backend | locations (delete) |
| Settings | Change Password (cur + new) | Frontend -> Backend -> Supabase Auth | auth.users (update) |
| Settings | Add User (email + pw) | Frontend -> Backend -> Supabase Auth Admin | auth.users (insert) |
