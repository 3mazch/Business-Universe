/* =====================================================================
   FLEX COFFEE & TEA — DATABASE SCHEMA (SQL Server / T-SQL)
   Version: v1.4 (Logical/Composite Keys Edition)
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
    warehouse_region        NVARCHAR(50)    NOT NULL,  
    location_tier           VARCHAR(20)     NOT NULL,  
    size_m2                 INT             NOT NULL,
    open_date               DATE            NOT NULL,
    closed_date             DATE            NULL,      
    temp_close_start        DATE            NULL,      
    temp_close_end          DATE            NULL,      
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
    lease_id            INT PRIMARY KEY,
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
    operating_hours_id  INT PRIMARY KEY,
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
   ===================================================================== */

CREATE TABLE dim_product_category (
    category_id         VARCHAR(10)     NOT NULL PRIMARY KEY,  
    category_name       NVARCHAR(100)   NOT NULL UNIQUE
);
GO

CREATE TABLE dim_product (
    product_id            VARCHAR(20)     NOT NULL PRIMARY KEY, 
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
    variant_id            VARCHAR(20)     NOT NULL PRIMARY KEY, 
    product_id            VARCHAR(20)     NOT NULL REFERENCES dim_product(product_id),
    size_code             VARCHAR(5)      NULL,    
    sku                   VARCHAR(30)     NOT NULL UNIQUE,
    base_price_vnd        DECIMAL(18,0)   NOT NULL,
    cost_price_vnd        DECIMAL(18,0)   NULL,    
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
    modifier_id           INT PRIMARY KEY,
    modifier_group        VARCHAR(30)     NOT NULL,  
    modifier_name         NVARCHAR(100)   NOT NULL,
    extra_price_vnd       DECIMAL(18,0)   NOT NULL DEFAULT 0,
    CONSTRAINT ck_modifier_group CHECK (modifier_group IN ('topping','sweetness','ice'))
);
GO

CREATE TABLE dim_category_modifier_exclusion (
    exclusion_id          INT PRIMARY KEY,
    category_id           VARCHAR(10)     NOT NULL REFERENCES dim_product_category(category_id),
    modifier_group        VARCHAR(30)     NOT NULL,
    reason                NVARCHAR(200)   NULL,
    CONSTRAINT uq_cat_mod_excl UNIQUE (category_id, modifier_group)
);
GO

CREATE TABLE dim_ingredient (
    ingredient_id         INT PRIMARY KEY,
    ingredient_name       NVARCHAR(150)   NOT NULL,
    unit                  VARCHAR(20)     NOT NULL,
    source_type           VARCHAR(20)     NOT NULL,  
    avg_shelf_life_days   INT             NULL,
    CONSTRAINT ck_ingredient_source CHECK (source_type IN ('central','local'))
);
GO

CREATE TABLE dim_recipe (
    recipe_id             INT PRIMARY KEY,
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
    tier_id                     VARCHAR(10)     NOT NULL PRIMARY KEY, 
    tier_name                   NVARCHAR(50)    NOT NULL UNIQUE,
    min_spend_rolling_12m_vnd   DECIMAL(18,0)   NOT NULL,
    tier_rank                   INT             NOT NULL
);
GO

CREATE TABLE dim_customer (
    customer_id             INT PRIMARY KEY,
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
    history_id              VARCHAR(50)     NOT NULL PRIMARY KEY,
    customer_id             INT             NOT NULL REFERENCES dim_customer(customer_id),
    effective_date          DATE            NOT NULL,
    old_tier_id             VARCHAR(10)     NULL REFERENCES dim_membership_tier(tier_id),
    new_tier_id             VARCHAR(10)     NOT NULL REFERENCES dim_membership_tier(tier_id),
    change_reason           VARCHAR(30)     NOT NULL  
);
GO
CREATE INDEX ix_membership_hist_customer ON fact_customer_membership_history(customer_id);
GO

CREATE TABLE dim_reward_catalog (
    reward_id               INT PRIMARY KEY,
    reward_name             NVARCHAR(150)   NOT NULL,
    points_required         INT             NOT NULL,
    reward_type             VARCHAR(30)     NOT NULL,
    CONSTRAINT ck_reward_type CHECK (reward_type IN ('voucher','physical_gift','free_product'))
);
GO

CREATE TABLE fact_loyalty_point_transaction (
    point_txn_id            VARCHAR(50)     NOT NULL PRIMARY KEY,
    customer_id             INT             NOT NULL REFERENCES dim_customer(customer_id),
    date_keytime            DATETIME2       NOT NULL,
    txn_type                VARCHAR(20)     NOT NULL,
    points                  INT             NOT NULL,
    related_order_id        BIGINT          NULL,  
    related_redemption_id   BIGINT          NULL,  
    CONSTRAINT ck_point_txn_type CHECK (txn_type IN ('earn','redeem'))
);
GO
CREATE INDEX ix_point_txn_customer ON fact_loyalty_point_transaction(customer_id);
GO

CREATE TABLE fact_reward_redemption (
    redemption_id           VARCHAR(50)     NOT NULL PRIMARY KEY,
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
    channel_id      INT PRIMARY KEY,
    channel_name    NVARCHAR(50)    NOT NULL UNIQUE,
    channel_group   VARCHAR(20)     NOT NULL,
    launch_date     DATE            NULL,  
    CONSTRAINT ck_channel_group CHECK (channel_group IN ('dine_in','app','delivery'))
);
GO

CREATE TABLE dim_campaign (
    campaign_id         INT PRIMARY KEY,
    campaign_name       NVARCHAR(150)   NOT NULL,
    campaign_type       VARCHAR(30)     NOT NULL,
    start_date          DATE            NOT NULL,
    end_date            DATE            NOT NULL,
    scope_type          VARCHAR(20)     NOT NULL,
    scope_store_id      INT             NULL REFERENCES dim_store(store_id),
    scope_channel_id    INT             NULL REFERENCES dim_sales_channel(channel_id),
    discount_value      DECIMAL(10,3)   NULL,
    funding_source      NVARCHAR(100)   NULL,
    budget_vnd          DECIMAL(18,0)   NULL,
    expected_uplift_pct DECIMAL(6,3)    NULL,
    priority            INT             NULL,
    CONSTRAINT ck_campaign_type CHECK (campaign_type IN ('percent_discount','bogo','flash_sale','seasonal')),
    CONSTRAINT ck_campaign_scope CHECK (scope_type IN ('system','store','channel'))
);
GO

CREATE TABLE dim_campaign_product_scope (
    campaign_scope_id   INT PRIMARY KEY,
    campaign_id         INT             NOT NULL REFERENCES dim_campaign(campaign_id),
    category_id         VARCHAR(10)     NULL REFERENCES dim_product_category(category_id),
    product_id          VARCHAR(20)     NULL REFERENCES dim_product(product_id)
);
GO

CREATE TABLE dim_date (
    date_key        INT             NOT NULL PRIMARY KEY,   
    full_date       DATE            NOT NULL UNIQUE,        
    day_of_week     TINYINT         NOT NULL,
    day_name        NVARCHAR(20)    NOT NULL,               
    month_num       TINYINT         NOT NULL,               
    month_name      NVARCHAR(20)    NOT NULL,               
    quarter_num     TINYINT         NOT NULL,               
    year_num        SMALLINT        NOT NULL,               
    is_weekend      BIT             NOT NULL,
    is_holiday      BIT             NOT NULL DEFAULT 0,
    holiday_name    NVARCHAR(100)   NULL,
    is_double_day   BIT             NOT NULL DEFAULT 0     
);
GO

CREATE TABLE fact_order (
    order_id            BIGINT PRIMARY KEY,
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    customer_id         INT             NULL REFERENCES dim_customer(customer_id),
    channel_id          INT             NOT NULL REFERENCES dim_sales_channel(channel_id),
    date_key            INT             NULL REFERENCES dim_date(date_key),  -- [v1.4 NEW]
    order_datetime      DATETIME2       NOT NULL,
    order_type          VARCHAR(20)     NOT NULL,
    order_status        VARCHAR(20)     NOT NULL DEFAULT 'completed',
    gross_amount_vnd    DECIMAL(18,0)   NOT NULL,
    discount_amount_vnd DECIMAL(18,0)   NOT NULL DEFAULT 0,
    net_amount_vnd      DECIMAL(18,0)   NOT NULL,
    CONSTRAINT ck_order_type   CHECK (order_type   IN ('dine_in','takeaway','delivery')),
    CONSTRAINT ck_order_status CHECK (order_status IN ('completed','failed','canceled','refunded'))
);
GO
CREATE INDEX ix_order_store_date   ON fact_order(store_id, order_datetime);
CREATE INDEX ix_order_customer     ON fact_order(customer_id);
CREATE INDEX ix_order_channel      ON fact_order(channel_id);
CREATE INDEX ix_order_date_key     ON fact_order(date_key);
GO

CREATE TABLE fact_order_item (
    order_id            BIGINT          NOT NULL REFERENCES fact_order(order_id),
    item_seq            INT             NOT NULL,
    variant_id          VARCHAR(20)     NOT NULL REFERENCES dim_product_variant(variant_id),
    quantity            INT             NOT NULL,
    unit_price_vnd      DECIMAL(18,0)   NOT NULL,
    line_amount_vnd     DECIMAL(18,0)   NOT NULL,
    PRIMARY KEY (order_id, item_seq)
);
GO
CREATE INDEX ix_order_item_order   ON fact_order_item(order_id);
CREATE INDEX ix_order_item_variant ON fact_order_item(variant_id);
GO

CREATE TABLE fact_order_item_modifier (
    order_id            BIGINT          NOT NULL,
    item_seq            INT             NOT NULL,
    modifier_id         INT             NOT NULL REFERENCES dim_modifier(modifier_id),
    modifier_name       NVARCHAR(100)   NULL,
    modifier_group      VARCHAR(30)     NULL,
    extra_price_vnd     DECIMAL(18,0)   NOT NULL DEFAULT 0,
    PRIMARY KEY (order_id, item_seq, modifier_id),
    CONSTRAINT fk_order_item_modifier FOREIGN KEY (order_id, item_seq) REFERENCES fact_order_item(order_id, item_seq)
);
GO

GO

CREATE TABLE fact_payment (
    order_id            BIGINT          NOT NULL REFERENCES fact_order(order_id),
    payment_method      VARCHAR(20)     NOT NULL,
    payment_status      VARCHAR(20)     NOT NULL DEFAULT 'completed',
    payment_amount_vnd  DECIMAL(18,0)   NOT NULL,
    payment_surcharge_vnd DECIMAL(18,0) NOT NULL DEFAULT 0,
    payment_datetime    DATETIME2       NULL,
    PRIMARY KEY (order_id, payment_method),
    CONSTRAINT ck_payment_method CHECK (payment_method IN ('cash','card','ewallet','qr')),
    CONSTRAINT ck_payment_status CHECK (payment_status IN ('completed','failed','pending'))
);
GO
CREATE INDEX ix_payment_order ON fact_payment(order_id);
GO

CREATE TABLE fact_order_discount (
    order_id            BIGINT          NOT NULL REFERENCES fact_order(order_id),
    campaign_id         INT             NOT NULL REFERENCES dim_campaign(campaign_id),
    discount_amount_vnd DECIMAL(18,0)   NOT NULL,
    campaign_type       VARCHAR(30)     NULL,
    PRIMARY KEY (order_id, campaign_id)
);
GO
CREATE INDEX ix_order_discount_order ON fact_order_discount(order_id);
GO

/* =====================================================================
   DOMAIN 6: INVENTORY & SUPPLY CHAIN
   ===================================================================== */

CREATE TABLE dim_supplier (
    supplier_id                 INT PRIMARY KEY,
    supplier_name               NVARCHAR(150)   NOT NULL,
    supplies_ingredient_type    VARCHAR(20)     NOT NULL,   -- central / local / outsource
    service_region              NVARCHAR(50)    NULL,
    category_served             NVARCHAR(50)    NULL,
    CONSTRAINT ck_supplier_type CHECK (supplies_ingredient_type IN ('central','local','outsource'))
);
GO

CREATE TABLE dim_warehouse (
    warehouse_id    INT PRIMARY KEY,
    warehouse_name  NVARCHAR(100)   NOT NULL,
    region          NVARCHAR(50)    NOT NULL
);
GO

CREATE TABLE fact_purchase_order (
    po_id                   VARCHAR(50)     NOT NULL PRIMARY KEY,
    po_type                 VARCHAR(30)     NULL,
    warehouse_id            INT             NULL REFERENCES dim_warehouse(warehouse_id),
    store_id                INT             NULL REFERENCES dim_store(store_id),
    supplier_id             INT             NOT NULL REFERENCES dim_supplier(supplier_id),
    order_date              INT             NOT NULL REFERENCES dim_date(date_key),
    expected_delivery_date  INT             NULL REFERENCES dim_date(date_key),
    actual_delivery_date    INT             NULL REFERENCES dim_date(date_key),
    po_status               VARCHAR(20)     NOT NULL DEFAULT 'ordered',
    total_cost_vnd          DECIMAL(18,0)   NULL,
    CONSTRAINT ck_po_status CHECK (po_status IN ('ordered','delivered','canceled')),
    CONSTRAINT ck_po_has_destination CHECK (
        store_id IS NOT NULL OR warehouse_id IS NOT NULL
    )
);
GO
CREATE INDEX ix_po_store     ON fact_purchase_order(store_id);
CREATE INDEX ix_po_warehouse ON fact_purchase_order(warehouse_id);
GO

CREATE TABLE fact_purchase_order_item (
    po_item_id              VARCHAR(50)     NOT NULL PRIMARY KEY,
    po_id                   VARCHAR(50)     NOT NULL REFERENCES fact_purchase_order(po_id),
    ingredient_id           INT             NULL REFERENCES dim_ingredient(ingredient_id),
    variant_id              VARCHAR(20)     NULL REFERENCES dim_product_variant(variant_id),
    quantity_ordered        DECIMAL(12,3)   NOT NULL,
    unit                    VARCHAR(20)     NULL,
    unit_cost_vnd           DECIMAL(18,0)   NOT NULL,
    total_cost_vnd          DECIMAL(18,0)   NOT NULL,
    CONSTRAINT ck_po_item_source CHECK (
        (ingredient_id IS NOT NULL AND variant_id IS NULL) OR
        (ingredient_id IS NULL     AND variant_id IS NOT NULL)
    )
);
GO
CREATE INDEX ix_po_item_po ON fact_purchase_order_item(po_id);
GO

CREATE TABLE fact_inventory (
    transaction_id      VARCHAR(50)     NOT NULL PRIMARY KEY,
    date_key            INT             NOT NULL REFERENCES dim_date(date_key),
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    warehouse_id        INT             NULL REFERENCES dim_warehouse(warehouse_id),
    ingredient_id       INT             NULL REFERENCES dim_ingredient(ingredient_id),
    variant_id          VARCHAR(20)     NULL REFERENCES dim_product_variant(variant_id),
    transaction_type    VARCHAR(20)     NOT NULL,
    quantity_delta      DECIMAL(12,3)   NOT NULL,  
    unit                VARCHAR(20)     NULL,
    unit_cost_vnd       DECIMAL(18,0)   NULL,
    total_cost_vnd      DECIMAL(18,0)   NULL,
    CONSTRAINT ck_inventory_txn_type CHECK (transaction_type IN ('stock_in','stock_out_sales','adjustment','wastage')),
    CONSTRAINT ck_inventory_txn_source CHECK (
        (ingredient_id IS NOT NULL AND variant_id IS NULL) OR
        (ingredient_id IS NULL     AND variant_id IS NOT NULL)
    )
);
GO
CREATE INDEX ix_inv_txn_store_ing_date  ON fact_inventory(store_id, ingredient_id, date_key);
CREATE INDEX ix_inv_txn_store_var_date  ON fact_inventory(store_id, variant_id,   date_key);
GO

/* =====================================================================
   DOMAIN 7: HUMAN RESOURCES
   ===================================================================== */

CREATE TABLE dim_position (
    position_id                 INT PRIMARY KEY,
    position_name               NVARCHAR(100)   NOT NULL UNIQUE,
    standard_monthly_salary_vnd DECIMAL(18,0)   NULL
);
GO

CREATE TABLE dim_shift (
    shift_id            INT PRIMARY KEY,
    shift_name          NVARCHAR(50)    NOT NULL,
    standard_start_time TIME            NOT NULL,
    standard_end_time   TIME            NOT NULL,
    total_hours         DECIMAL(4,2)    NOT NULL,
    pay_per_shift_vnd   DECIMAL(18,0)   NOT NULL,
    bonus_vnd           DECIMAL(18,0)   NOT NULL DEFAULT 0
);
GO

CREATE TABLE dim_employee (
    employee_id         INT PRIMARY KEY,
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
    employee_id             INT             NOT NULL REFERENCES dim_employee(employee_id),
    store_id                INT             NOT NULL REFERENCES dim_store(store_id),
    shift_id                INT             NOT NULL REFERENCES dim_shift(shift_id),
    work_date               DATE            NOT NULL,
    actual_check_in         DATETIME2       NULL,
    actual_check_out        DATETIME2       NULL,
    late_minutes            INT             NOT NULL DEFAULT 0,
    early_leave_minutes     INT             NOT NULL DEFAULT 0,
    actual_hours_worked     DECIMAL(4,2)    NULL,
    PRIMARY KEY (employee_id, work_date, shift_id)
);
GO
CREATE INDEX ix_emp_shift_employee_date ON fact_employee_shift(employee_id, work_date);
CREATE INDEX ix_emp_shift_store_date    ON fact_employee_shift(store_id,    work_date);
GO

CREATE TABLE fact_payroll (
    employee_id             INT             NOT NULL REFERENCES dim_employee(employee_id),
    pay_month               DATE            NOT NULL,
    base_salary_vnd         DECIMAL(18,0)   NOT NULL,
    bonus_allowance_vnd     DECIMAL(18,0)   NOT NULL DEFAULT 0,
    total_paid_vnd          DECIMAL(18,0)   NOT NULL,
    PRIMARY KEY (employee_id, pay_month)
);
GO
CREATE INDEX ix_payroll_employee ON fact_payroll(employee_id);
GO

/* =====================================================================
   DOMAIN 8: FINANCE
   ===================================================================== */

CREATE TABLE dim_expense_category (
    expense_category_id     INT PRIMARY KEY,
    expense_category_name   NVARCHAR(100)   NOT NULL UNIQUE
);
GO

CREATE TABLE fact_store_expense (
    store_id                INT             NOT NULL REFERENCES dim_store(store_id),
    expense_category_id     INT             NOT NULL REFERENCES dim_expense_category(expense_category_id),
    expense_date            DATE            NOT NULL,
    amount_vnd              DECIMAL(18,0)   NOT NULL,
    note                    NVARCHAR(300)   NULL,
    PRIMARY KEY (store_id, expense_date, expense_category_id)
);
GO
CREATE INDEX ix_store_expense_store_date ON fact_store_expense(store_id, expense_date);
GO

CREATE TABLE fact_store_pnl_monthly (
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    pnl_month           DATE            NOT NULL,  
    revenue_vnd         DECIMAL(18,0)   NOT NULL,
    cogs_vnd            DECIMAL(18,0)   NOT NULL,
    labor_cost_vnd      DECIMAL(18,0)   NOT NULL,
    rent_cost_vnd       DECIMAL(18,0)   NOT NULL,
    other_expense_vnd   DECIMAL(18,0)   NOT NULL,
    net_profit_vnd      DECIMAL(18,0)   NOT NULL,
    PRIMARY KEY (store_id, pnl_month)
);
GO
CREATE INDEX ix_pnl_store_month ON fact_store_pnl_monthly(store_id, pnl_month);
GO

/* =====================================================================
   DOMAIN 9: KPI & ANALYTICS SUPPORT
   ===================================================================== */

CREATE TABLE fact_kpi_daily_store (
    store_id            INT             NOT NULL REFERENCES dim_store(store_id),
    kpi_date            DATE            NOT NULL,
    date_key            INT             NULL REFERENCES dim_date(date_key),
    revenue_vnd         DECIMAL(18,0)   NOT NULL,
    order_count         INT             NOT NULL,
    aov_vnd             DECIMAL(18,0)   NOT NULL,
    new_customer_count  INT             NOT NULL DEFAULT 0,
    food_cost_pct       DECIMAL(6,3)    NULL,
    PRIMARY KEY (store_id, kpi_date)
);
GO
CREATE INDEX ix_kpi_store_date ON fact_kpi_daily_store(store_id, kpi_date);
GO