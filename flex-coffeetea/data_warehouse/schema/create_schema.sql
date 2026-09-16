/* =====================================================================
   FLEX COFFEE & TEA — DATABASE SCHEMA (SQL Server / T-SQL)
   Version: v1.3
   =====================================================================
   Cách chạy:
   1. Mở SSMS hoặc Azure Data Studio.
   2. Kết nối tới SQL Server instance.
   3. Chạy toàn bộ script này (F5).
   ===================================================================== */

IF DB_ID('FlexCoffeeTea') IS NULL
BEGIN
    CREATE DATABASE FlexCoffeeTea;
END
GO

USE FlexCoffeeTea;
GO

/* =====================================================================
   DOMAIN 1: STORE
   ===================================================================== */

CREATE TABLE dim_store (
    store_id                INT             NOT NULL PRIMARY KEY,
    store_code              VARCHAR(10)     NOT NULL UNIQUE,
    store_name              NVARCHAR(150)   NOT NULL,
    city                    NVARCHAR(50)    NOT NULL,
    address                 NVARCHAR(250)   NULL,
    warehouse_region        NVARCHAR(50)    NOT NULL,   -- 'Kho Mien Bac' / 'Kho Mien Nam'
    location_tier           VARCHAR(20)     NOT NULL,   -- prime / standard / secondary
    size_m2                 INT             NOT NULL,
    open_date               DATE            NOT NULL,
    closed_date             DATE            NULL,       -- [v1.3 FIX] typo 'close_date' -> 'closed_date'
    temp_close_start        DATE            NULL,       -- [v1.3 NEW] bat dau dong cua tam
    temp_close_end          DATE            NULL,       -- [v1.3 NEW] ket thuc dong cua tam
    status                  VARCHAR(30)     NOT NULL DEFAULT 'active',
    is_outlier_small_prime  BIT             NOT NULL DEFAULT 0,
    staff_count_baseline    INT             NULL,
    channel_mix_dine_in     DECIMAL(5,3)    NULL,
    channel_mix_app         DECIMAL(5,3)    NULL,
    channel_mix_delivery    DECIMAL(5,3)    NULL,
    created_at              DATETIME2       NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT ck_store_status CHECK (status IN ('active','temporarily_closed_recent','closed')),
    CONSTRAINT ck_store_location_tier CHECK (location_tier IN ('prime','standard','secondary'))
);
GO

CREATE TABLE store_lease (
    lease_id            INT IDENTITY(1,1) PRIMARY KEY,
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    lease_start_date    DATE            NOT NULL,
    lease_end_date      DATE            NULL,
    monthly_rent_vnd    DECIMAL(18,0)   NOT NULL,
    landlord_name       NVARCHAR(150)   NULL,
    is_current          BIT             NOT NULL DEFAULT 1
);
GO
CREATE INDEX ix_store_lease_store ON store_lease(store_id);
GO

CREATE TABLE store_operating_hours (
    operating_hours_id  INT IDENTITY(1,1) PRIMARY KEY,
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    day_of_week         TINYINT         NOT NULL,   -- 1=Mon ... 7=Sun
    open_time           TIME            NOT NULL,
    close_time          TIME            NOT NULL,
    CONSTRAINT ck_day_of_week CHECK (day_of_week BETWEEN 1 AND 7),
    CONSTRAINT uq_store_day UNIQUE (store_id, day_of_week)
);
GO

/* =====================================================================
   DOMAIN 2: PRODUCT
   NOTE: product_id va variant_id doi sang VARCHAR(20) de dung prefix-based
         ID convention (BVR-xxx, FOOD-xxx, RTL-xxx, MER-xxx).
         Toàn bộ FK tham chiếu 2 cột này cũng đổi sang VARCHAR(20).
   ===================================================================== */

CREATE TABLE dim_product_category (
    category_id         VARCHAR(10)     NOT NULL PRIMARY KEY,   -- CAT-01 .. CAT-07
    category_name       NVARCHAR(100)   NOT NULL UNIQUE
);
GO

CREATE TABLE dim_product (
    product_id            VARCHAR(20)     NOT NULL PRIMARY KEY,  -- BVR-001, FOOD-001...
    category_id           VARCHAR(10)     NOT NULL REFERENCES dim_product_category(category_id),
    product_name          NVARCHAR(150)   NOT NULL,
    description           NVARCHAR(500)   NULL,
    launch_date           DATE            NULL,
    discontinued_date     DATE            NULL,
    status                VARCHAR(20)     NOT NULL DEFAULT 'active',
    CONSTRAINT ck_product_status CHECK (status IN ('active','discontinued'))
);
GO
CREATE INDEX ix_product_category ON dim_product(category_id);
GO

CREATE TABLE dim_product_variant (
    variant_id            VARCHAR(20)     NOT NULL PRIMARY KEY,  -- BVR-001-M, FOOD-001...
    product_id            VARCHAR(20)     NOT NULL REFERENCES dim_product(product_id),
    size_code             VARCHAR(5)      NULL,          -- 'M' / 'L' / NULL
    sku                   VARCHAR(30)     NOT NULL UNIQUE,
    base_price_vnd        DECIMAL(18,0)   NOT NULL,
    cost_price_vnd        DECIMAL(18,0)   NULL,          -- NULL cho do uong (tinh qua recipe)
    sourcing_model        VARCHAR(30)     NOT NULL DEFAULT 'in_house_recipe',
    effective_from        DATE            NOT NULL,
    effective_to          DATE            NULL,
    is_current            BIT             NOT NULL DEFAULT 1,
    CONSTRAINT ck_sourcing_model CHECK (sourcing_model IN ('in_house_recipe','outsource_finished_goods'))
);
GO
CREATE INDEX ix_variant_product ON dim_product_variant(product_id);
GO

CREATE TABLE dim_modifier (
    modifier_id           INT IDENTITY(1,1) PRIMARY KEY,
    modifier_group        VARCHAR(30)     NOT NULL,   -- topping / sweetness / ice
    modifier_name         NVARCHAR(100)   NOT NULL,
    extra_price_vnd       DECIMAL(18,0)   NOT NULL DEFAULT 0,
    CONSTRAINT ck_modifier_group CHECK (modifier_group IN ('topping','sweetness','ice'))
);
GO

-- [v1.3 NEW] Bảng chính thức kiểm soát modifier nào bị loại trừ theo category
-- (VD: Da Xay khong ap dung modifier 'ice')
CREATE TABLE dim_category_modifier_exclusion (
    exclusion_id          INT IDENTITY(1,1) PRIMARY KEY,
    category_id           VARCHAR(10)     NOT NULL REFERENCES dim_product_category(category_id),
    modifier_group        VARCHAR(30)     NOT NULL,
    reason                NVARCHAR(200)   NULL,
    CONSTRAINT uq_cat_mod_excl UNIQUE (category_id, modifier_group)
);
GO

CREATE TABLE dim_ingredient (
    ingredient_id         INT IDENTITY(1,1) PRIMARY KEY,
    ingredient_name       NVARCHAR(150)   NOT NULL,
    unit                  VARCHAR(20)     NOT NULL,
    source_type           VARCHAR(20)     NOT NULL,   -- central / local
    avg_shelf_life_days   INT             NULL,
    CONSTRAINT ck_ingredient_source CHECK (source_type IN ('central','local'))
);
GO

CREATE TABLE dim_recipe (
    recipe_id             INT IDENTITY(1,1) PRIMARY KEY,
    variant_id            VARCHAR(20)     NOT NULL REFERENCES dim_product_variant(variant_id),
    ingredient_id         INT             NOT NULL REFERENCES dim_ingredient(ingredient_id),
    quantity_per_unit     DECIMAL(10,3)   NOT NULL,
    CONSTRAINT uq_recipe_variant_ingredient UNIQUE (variant_id, ingredient_id)
);
GO

/* =====================================================================
   DOMAIN 3: CUSTOMER & MEMBERSHIP
   ===================================================================== */

CREATE TABLE dim_membership_tier (
    tier_id                     VARCHAR(10)     NOT NULL PRIMARY KEY,  -- TIER-1, TIER-2, TIER-3
    tier_name                   NVARCHAR(50)    NOT NULL UNIQUE,
    min_spend_rolling_12m_vnd   DECIMAL(18,0)   NOT NULL,
    tier_rank                   INT             NOT NULL
);
GO

CREATE TABLE dim_customer (
    customer_id             INT IDENTITY(1,1) PRIMARY KEY,
    full_name               NVARCHAR(150)   NOT NULL,
    phone_number            VARCHAR(20)     NULL,
    email                   VARCHAR(150)    NULL,
    registration_date       DATE            NOT NULL,
    registration_channel    VARCHAR(20)     NOT NULL,
    home_store_id           INT             NULL REFERENCES dim_store(store_id),
    current_tier_id         VARCHAR(10)     NULL REFERENCES dim_membership_tier(tier_id),
    CONSTRAINT ck_customer_reg_channel CHECK (registration_channel IN ('app','pos'))
);
GO
CREATE INDEX ix_customer_home_store ON dim_customer(home_store_id);
GO

CREATE TABLE fact_customer_membership_history (
    membership_history_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
    customer_id             INT             NOT NULL REFERENCES dim_customer(customer_id),
    effective_date          DATE            NOT NULL,
    old_tier_id             VARCHAR(10)     NULL REFERENCES dim_membership_tier(tier_id),
    new_tier_id             VARCHAR(10)     NOT NULL REFERENCES dim_membership_tier(tier_id),
    change_reason           VARCHAR(30)     NOT NULL   -- upgrade / downgrade_expiry / initial
);
GO
CREATE INDEX ix_membership_hist_customer ON fact_customer_membership_history(customer_id);
GO

CREATE TABLE dim_reward_catalog (
    reward_id               INT IDENTITY(1,1) PRIMARY KEY,
    reward_name             NVARCHAR(150)   NOT NULL,
    points_required         INT             NOT NULL,
    reward_type             VARCHAR(30)     NOT NULL,
    CONSTRAINT ck_reward_type CHECK (reward_type IN ('voucher','physical_gift','free_product'))
);
GO

CREATE TABLE fact_loyalty_point_transaction (
    point_txn_id            BIGINT IDENTITY(1,1) PRIMARY KEY,
    customer_id             INT             NOT NULL REFERENCES dim_customer(customer_id),
    txn_datetime            DATETIME2       NOT NULL,
    txn_type                VARCHAR(20)     NOT NULL,
    points                  INT             NOT NULL,
    related_order_id        BIGINT          NULL,   -- soft FK -> fact_order (no constraint, circular)
    related_redemption_id   BIGINT          NULL,   -- soft FK -> fact_reward_redemption
    CONSTRAINT ck_point_txn_type CHECK (txn_type IN ('earn','redeem'))
);
GO
CREATE INDEX ix_point_txn_customer ON fact_loyalty_point_transaction(customer_id);
GO

CREATE TABLE fact_reward_redemption (
    redemption_id           BIGINT IDENTITY(1,1) PRIMARY KEY,
    customer_id             INT             NOT NULL REFERENCES dim_customer(customer_id),
    reward_id               INT             NOT NULL REFERENCES dim_reward_catalog(reward_id),
    redemption_datetime     DATETIME2       NOT NULL,
    status                  VARCHAR(20)     NOT NULL DEFAULT 'issued',
    CONSTRAINT ck_redemption_status CHECK (status IN ('issued','used','expired'))
);
GO

/* =====================================================================
   DOMAIN 4: SALES / ORDER
   ===================================================================== */

CREATE TABLE dim_sales_channel (
    channel_id      INT IDENTITY(1,1) PRIMARY KEY,
    channel_name    NVARCHAR(50)    NOT NULL UNIQUE,
    channel_group   VARCHAR(20)     NOT NULL,
    launch_date     DATE            NULL,   -- [v1.3 NEW] Option A: khi nao channel bat dau active
    CONSTRAINT ck_channel_group CHECK (channel_group IN ('dine_in','app','delivery'))
);
GO

CREATE TABLE dim_campaign (
    campaign_id         INT IDENTITY(1,1) PRIMARY KEY,
    campaign_name       NVARCHAR(150)   NOT NULL,
    campaign_type       VARCHAR(30)     NOT NULL,
    start_date          DATE            NOT NULL,
    end_date            DATE            NOT NULL,
    scope_type          VARCHAR(20)     NOT NULL,
    scope_store_id      INT             NULL REFERENCES dim_store(store_id),
    scope_channel_id    INT             NULL REFERENCES dim_sales_channel(channel_id),
    discount_value      DECIMAL(10,3)   NULL,
    -- Extra cols from generated data (kept for analytics)
    funding_source      NVARCHAR(100)   NULL,
    budget_vnd          DECIMAL(18,0)   NULL,
    expected_uplift_pct DECIMAL(6,3)    NULL,
    priority            INT             NULL,
    CONSTRAINT ck_campaign_type CHECK (campaign_type IN ('percent_discount','bogo','flash_sale','seasonal')),
    CONSTRAINT ck_campaign_scope CHECK (scope_type IN ('system','store','channel'))
);
GO

CREATE TABLE dim_campaign_product_scope (
    campaign_scope_id   INT IDENTITY(1,1) PRIMARY KEY,
    campaign_id         INT             NOT NULL REFERENCES dim_campaign(campaign_id),
    category_id         VARCHAR(10)     NULL REFERENCES dim_product_category(category_id),
    product_id          VARCHAR(20)     NULL REFERENCES dim_product(product_id)
);
GO

-- [v1.3] dim_date: them cot is_double_day, full_date, day_name, month_num...
-- Luu y: dim_date duoc dinh nghia TRUOC fact_order de fact_order.date_key co the tao FK
CREATE TABLE dim_date (
    date_key        INT             NOT NULL PRIMARY KEY,   -- YYYYMMDD
    full_date       DATE            NOT NULL UNIQUE,        -- [v1.3 NEW]
    day_of_week     TINYINT         NOT NULL,
    day_name        NVARCHAR(20)    NOT NULL,               -- [v1.3 NEW]
    month_num       TINYINT         NOT NULL,               -- [v1.3 NEW]
    month_name      NVARCHAR(20)    NOT NULL,               -- [v1.3 NEW]
    quarter_num     TINYINT         NOT NULL,               -- [v1.3 NEW]
    year_num        SMALLINT        NOT NULL,               -- [v1.3 NEW]
    is_weekend      BIT             NOT NULL,
    is_holiday      BIT             NOT NULL DEFAULT 0,
    holiday_name    NVARCHAR(100)   NULL,
    is_double_day   BIT             NOT NULL DEFAULT 0     -- [v1.3 NEW] ngay doi (1/1, 2/2...) tu 2025
);
GO

CREATE TABLE fact_order (
    order_id            BIGINT IDENTITY(1,1) PRIMARY KEY,
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    customer_id         INT             NULL REFERENCES dim_customer(customer_id),
    channel_id          INT             NOT NULL REFERENCES dim_sales_channel(channel_id),
    date_key            INT             NULL REFERENCES dim_date(date_key),  -- [v1.3 NEW]
    order_datetime      DATETIME2       NOT NULL,
    order_type          VARCHAR(20)     NOT NULL,
    order_status        VARCHAR(20)     NOT NULL DEFAULT 'completed',
    gross_amount_vnd    DECIMAL(18,0)   NOT NULL,
    discount_amount_vnd DECIMAL(18,0)   NOT NULL DEFAULT 0,
    net_amount_vnd      DECIMAL(18,0)   NOT NULL,
    CONSTRAINT ck_order_type   CHECK (order_type   IN ('dine_in','takeaway','delivery')),
    CONSTRAINT ck_order_status CHECK (order_status IN ('completed','canceled','refunded'))
);
GO
CREATE INDEX ix_order_store_date   ON fact_order(store_id, order_datetime);
CREATE INDEX ix_order_customer     ON fact_order(customer_id);
CREATE INDEX ix_order_channel      ON fact_order(channel_id);
CREATE INDEX ix_order_date_key     ON fact_order(date_key);
GO

CREATE TABLE fact_order_item (
    order_item_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    order_id            BIGINT          NOT NULL REFERENCES fact_order(order_id),
    variant_id          VARCHAR(20)     NOT NULL REFERENCES dim_product_variant(variant_id),
    quantity            INT             NOT NULL,
    unit_price_vnd      DECIMAL(18,0)   NOT NULL,
    line_amount_vnd     DECIMAL(18,0)   NOT NULL
);
GO
CREATE INDEX ix_order_item_order   ON fact_order_item(order_id);
CREATE INDEX ix_order_item_variant ON fact_order_item(variant_id);
GO

CREATE TABLE fact_order_item_modifier (
    order_item_modifier_id  BIGINT IDENTITY(1,1) PRIMARY KEY,
    order_item_id           BIGINT          NOT NULL REFERENCES fact_order_item(order_item_id),
    modifier_id             INT             NOT NULL REFERENCES dim_modifier(modifier_id),
    extra_price_vnd         DECIMAL(18,0)   NOT NULL DEFAULT 0
);
GO
CREATE INDEX ix_order_item_modifier_item ON fact_order_item_modifier(order_item_id);
GO

CREATE TABLE fact_payment (
    payment_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    order_id            BIGINT          NOT NULL REFERENCES fact_order(order_id),
    payment_method      VARCHAR(20)     NOT NULL,
    amount_vnd          DECIMAL(18,0)   NOT NULL,
    payment_datetime    DATETIME2       NULL,   -- nullable (pending/async payments)
    payment_status      VARCHAR(20)     NOT NULL DEFAULT 'success',
    CONSTRAINT ck_payment_method CHECK (payment_method IN ('cash','card','ewallet','qr')),
    CONSTRAINT ck_payment_status CHECK (payment_status IN ('success','failed','pending'))
);
GO
CREATE INDEX ix_payment_order ON fact_payment(order_id);
GO

CREATE TABLE fact_order_discount (
    order_discount_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
    order_id            BIGINT          NOT NULL REFERENCES fact_order(order_id),
    campaign_id         INT             NULL REFERENCES dim_campaign(campaign_id),
    discount_amount_vnd DECIMAL(18,0)   NOT NULL,
    discount_reason     NVARCHAR(200)   NULL
);
GO
CREATE INDEX ix_order_discount_order ON fact_order_discount(order_id);
GO

/* =====================================================================
   DOMAIN 6: INVENTORY & SUPPLY CHAIN
   ===================================================================== */

CREATE TABLE dim_supplier (
    supplier_id                 INT IDENTITY(1,1) PRIMARY KEY,
    supplier_name               NVARCHAR(150)   NOT NULL,
    supplies_ingredient_type    VARCHAR(20)     NOT NULL,   -- central / local / outsource
    service_region              NVARCHAR(50)    NULL,
    category_served             NVARCHAR(50)    NULL,
    CONSTRAINT ck_supplier_type CHECK (supplies_ingredient_type IN ('central','local','outsource'))
);
GO

CREATE TABLE dim_warehouse (
    warehouse_id    INT IDENTITY(1,1) PRIMARY KEY,
    warehouse_name  NVARCHAR(100)   NOT NULL,
    region          NVARCHAR(50)    NOT NULL
);
GO

CREATE TABLE fact_purchase_order (
    purchase_order_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    store_id                INT             NULL REFERENCES dim_store(store_id),
    warehouse_id            INT             NULL REFERENCES dim_warehouse(warehouse_id),
    supplier_id             INT             NOT NULL REFERENCES dim_supplier(supplier_id),
    order_date              DATE            NOT NULL,
    expected_delivery_date  DATE            NULL,
    actual_delivery_date    DATE            NULL,
    status                  VARCHAR(20)     NOT NULL DEFAULT 'ordered',
    CONSTRAINT ck_po_status CHECK (status IN ('ordered','delivered','canceled')),
    -- [v1.3 FIX] Dam bao moi PO phai co dich den (store hoac warehouse)
    CONSTRAINT ck_po_has_destination CHECK (
        store_id IS NOT NULL OR warehouse_id IS NOT NULL
    )
);
GO
CREATE INDEX ix_po_store     ON fact_purchase_order(store_id);
CREATE INDEX ix_po_warehouse ON fact_purchase_order(warehouse_id);
GO

CREATE TABLE fact_purchase_order_item (
    purchase_order_item_id  BIGINT IDENTITY(1,1) PRIMARY KEY,
    purchase_order_id       BIGINT          NOT NULL REFERENCES fact_purchase_order(purchase_order_id),
    ingredient_id           INT             NULL REFERENCES dim_ingredient(ingredient_id),
    variant_id              VARCHAR(20)     NULL REFERENCES dim_product_variant(variant_id),
    quantity                DECIMAL(12,3)   NOT NULL,
    unit_cost_vnd           DECIMAL(18,0)   NOT NULL,
    CONSTRAINT ck_po_item_source CHECK (
        (ingredient_id IS NOT NULL AND variant_id IS NULL) OR
        (ingredient_id IS NULL     AND variant_id IS NOT NULL)
    )
);
GO
CREATE INDEX ix_po_item_po ON fact_purchase_order_item(purchase_order_id);
GO

CREATE TABLE fact_inventory_transaction (
    inventory_txn_id    BIGINT IDENTITY(1,1) PRIMARY KEY,
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    ingredient_id       INT             NULL REFERENCES dim_ingredient(ingredient_id),
    variant_id          VARCHAR(20)     NULL REFERENCES dim_product_variant(variant_id),
    txn_date            DATE            NOT NULL,
    txn_type            VARCHAR(20)     NOT NULL,
    quantity            DECIMAL(12,3)   NOT NULL,   -- duong=nhap, am=xuat/hao hut
    unit_cost_vnd       DECIMAL(18,0)   NULL,
    CONSTRAINT ck_inventory_txn_type CHECK (txn_type IN ('stock_in','stock_out_sales','adjustment','wastage')),
    CONSTRAINT ck_inventory_txn_source CHECK (
        (ingredient_id IS NOT NULL AND variant_id IS NULL) OR
        (ingredient_id IS NULL     AND variant_id IS NOT NULL)
    )
);
GO
CREATE INDEX ix_inv_txn_store_ing_date  ON fact_inventory_transaction(store_id, ingredient_id, txn_date);
CREATE INDEX ix_inv_txn_store_var_date  ON fact_inventory_transaction(store_id, variant_id,   txn_date);
GO

/* =====================================================================
   DOMAIN 7: HUMAN RESOURCES
   ===================================================================== */

CREATE TABLE dim_position (
    position_id                 INT IDENTITY(1,1) PRIMARY KEY,
    position_name               NVARCHAR(100)   NOT NULL UNIQUE,
    standard_monthly_salary_vnd DECIMAL(18,0)   NULL
);
GO

CREATE TABLE dim_shift (
    shift_id            INT IDENTITY(1,1) PRIMARY KEY,
    shift_name          NVARCHAR(50)    NOT NULL,
    standard_start_time TIME            NOT NULL,
    standard_end_time   TIME            NOT NULL,
    total_hours         DECIMAL(4,2)    NOT NULL,
    pay_per_shift_vnd   DECIMAL(18,0)   NOT NULL,
    bonus_vnd           DECIMAL(18,0)   NOT NULL DEFAULT 0
);
GO

CREATE TABLE dim_employee (
    employee_id         INT IDENTITY(1,1) PRIMARY KEY,
    full_name           NVARCHAR(150)   NOT NULL,
    position_id         INT             NOT NULL REFERENCES dim_position(position_id),
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    hire_date           DATE            NOT NULL,
    termination_date    DATE            NULL,
    contract_type       VARCHAR(20)     NOT NULL,
    CONSTRAINT ck_contract_type CHECK (contract_type IN ('full_time','part_time'))
);
GO
CREATE INDEX ix_employee_store ON dim_employee(store_id);
GO

CREATE TABLE fact_employee_shift (
    employee_shift_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    employee_id             INT             NOT NULL REFERENCES dim_employee(employee_id),
    store_id                INT             NOT NULL REFERENCES dim_store(store_id),
    shift_id                INT             NOT NULL REFERENCES dim_shift(shift_id),
    work_date               DATE            NOT NULL,
    actual_check_in         DATETIME2       NULL,
    actual_check_out        DATETIME2       NULL,
    late_minutes            INT             NOT NULL DEFAULT 0,
    early_leave_minutes     INT             NOT NULL DEFAULT 0,
    actual_hours_worked     DECIMAL(4,2)    NULL
);
GO
CREATE INDEX ix_emp_shift_employee_date ON fact_employee_shift(employee_id, work_date);
CREATE INDEX ix_emp_shift_store_date    ON fact_employee_shift(store_id,    work_date);
GO

CREATE TABLE fact_payroll (
    payroll_id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    employee_id             INT             NOT NULL REFERENCES dim_employee(employee_id),
    pay_month               DATE            NOT NULL,
    base_salary_vnd         DECIMAL(18,0)   NOT NULL,
    bonus_allowance_vnd     DECIMAL(18,0)   NOT NULL DEFAULT 0,
    total_paid_vnd          DECIMAL(18,0)   NOT NULL,
    CONSTRAINT uq_payroll_employee_month UNIQUE (employee_id, pay_month)
);
GO
CREATE INDEX ix_payroll_employee ON fact_payroll(employee_id);
GO

/* =====================================================================
   DOMAIN 8: FINANCE
   ===================================================================== */

CREATE TABLE dim_expense_category (
    expense_category_id     INT IDENTITY(1,1) PRIMARY KEY,
    expense_category_name   NVARCHAR(100)   NOT NULL UNIQUE
);
GO

CREATE TABLE fact_store_expense (
    store_expense_id        BIGINT IDENTITY(1,1) PRIMARY KEY,
    store_id                INT             NOT NULL REFERENCES dim_store(store_id),
    expense_category_id     INT             NOT NULL REFERENCES dim_expense_category(expense_category_id),
    expense_date            DATE            NOT NULL,
    amount_vnd              DECIMAL(18,0)   NOT NULL,
    note                    NVARCHAR(300)   NULL
);
GO
CREATE INDEX ix_store_expense_store_date ON fact_store_expense(store_id, expense_date);
GO

CREATE TABLE fact_store_pnl_monthly (
    pnl_id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    pnl_month           DATE            NOT NULL,   -- ngay dau thang (VD: 2025-06-01)
    revenue_vnd         DECIMAL(18,0)   NOT NULL,
    cogs_vnd            DECIMAL(18,0)   NOT NULL,
    labor_cost_vnd      DECIMAL(18,0)   NOT NULL,
    rent_cost_vnd       DECIMAL(18,0)   NOT NULL,
    other_expense_vnd   DECIMAL(18,0)   NOT NULL,
    net_profit_vnd      DECIMAL(18,0)   NOT NULL,
    CONSTRAINT uq_pnl_store_month UNIQUE (store_id, pnl_month)
);
GO
CREATE INDEX ix_pnl_store_month ON fact_store_pnl_monthly(store_id, pnl_month);
GO

/* =====================================================================
   DOMAIN 9: KPI & ANALYTICS SUPPORT
   ===================================================================== */

CREATE TABLE fact_kpi_daily_store (
    kpi_id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    kpi_date            DATE            NOT NULL,
    date_key            INT             NULL REFERENCES dim_date(date_key),
    revenue_vnd         DECIMAL(18,0)   NOT NULL,
    order_count         INT             NOT NULL,
    aov_vnd             DECIMAL(18,0)   NOT NULL,
    new_customer_count  INT             NOT NULL DEFAULT 0,
    food_cost_pct       DECIMAL(6,3)    NULL,
    CONSTRAINT uq_kpi_store_date UNIQUE (store_id, kpi_date)
);
GO
CREATE INDEX ix_kpi_store_date ON fact_kpi_daily_store(store_id, kpi_date);
GO

/* =====================================================================
   HET SCRIPT v1.3 — ~36 bang theo 9 domain.
   Buoc tiep theo: nap Dimension data (Phase 1) truoc khi sinh Fact/Transaction (Phase 2).
   ===================================================================== */