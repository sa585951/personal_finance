from sqlalchemy import Table, Column, String, Float, DateTime, MetaData, Integer, UniqueConstraint, Text, Boolean, Date, func, Numeric, UUID

metadata = MetaData()

# 使用者資料表
users_table = Table(
    'users', metadata,
    Column('user_id', String(255), primary_key=True, index=True),
    Column('display_name', String(255), nullable=True),
    Column('created_at', DateTime, default=func.now()),
    # 可以根據需要添加更多用戶相關的欄位
)

# 資產資料表
assets_table = Table('assets', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String(255), nullable=False, index=True),
    Column('account_key', String, unique=True, nullable=False),
    Column('bank_name', String(100), nullable=False),
    Column('account_type', String(100), nullable=False),
    Column('balance', Numeric(15, 2), nullable=False),
    Column('last_update', DateTime),
    Column('currency', String(10))
)

# 2. transactions 資料表
transactions_table = Table('transactions', metadata,
    Column('id', UUID(as_uuid=True), primary_key=True),
    Column('user_id', String(255), nullable=False, index=True),
    Column('date', Date, nullable=False),
    Column('type', String(50), nullable=False),
    Column('category', String(100), nullable=False),
    Column('budget_category', String(100)),
    Column('amount', Numeric(10, 2), nullable=False),
    Column('description', Text),
    Column('timestamp', DateTime)
)

# 3. budgets 資料表
budget_months_table = Table('budget_months', metadata,
    Column('user_id', String(255), primary_key=True),
    Column('month', String(7), primary_key=True),
    Column('created_date', DateTime)
)

budget_categories_table = Table('budget_categories', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String(255), nullable=False, index=True),
    Column('month', String(7), nullable=False), # 這裡應為 ForeignKey，為簡化暫時省略
    Column('category_name', String(100), nullable=False),
    Column('amount', Numeric(10, 2), nullable=False),
    Column('notes', Text),
    Column('created_date', DateTime),
    UniqueConstraint('user_id', 'month', 'category_name', name='uq_user_month_category')
)

# 4. goals 資料表
goals_table = Table('goals', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String(255), nullable=False, index=True),
    Column('title', String(255), nullable=False),
    Column('type', String(50)),
    Column('target_amount', Numeric(10, 2), nullable=False),
    Column('target_date', Date),
    Column('current_amount', Numeric(10, 2), default=0),
    Column('created_date', DateTime),
    Column('last_update', DateTime),
    Column('status', String(50)),
    Column('description', Text)
)
