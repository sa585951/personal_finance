from datetime import datetime
from models.schema import transactions_table,budget_categories_table
from models.database import engine
from sqlalchemy import select, desc, func

class ExpenseHandler:
    """處理支出相關邏輯"""
    def __init__(self, budget_manager):
        self.budget_manager = budget_manager
    
    def handle(self, data, user_id):
        """
        處理支出記錄
        
        Args:
            data (dict): 解析後的支出資料
            user_id (str): 用戶 ID
            
        Returns:
            dict: 處理結果 {"success": bool, "data": dict, "message": str}
        """
        try:
            success, message = self.budget_manager.add_transaction(
                user_id=user_id,
                date=datetime.now().strftime("%Y-%m-%d"),
                item=data.get("category", "Line記帳"),
                amount=data["amount"],
                transaction_type="expense",
                budget_category=data.get("budget_category"),
                description=data.get("description", "")
            )

            if success:
                # 獲取預算狀況
                budget_status = self._get_budget_status(user_id, data.get("budget_category"))
                return {
                    "success": True, 
                    "data": data, 
                    "budget_status": budget_status,
                    "message": "記帳成功"
                }
            else:
                return {"success": False, "data": data, "message": message}
            
        except Exception as e:
            return {"success": False, "data": data, "message": str(e)}

    def _get_budget_status(self, user_id, category):
        """獲取指定使用者的預算狀況"""
        try:
            current_month = datetime.now().strftime("%Y-%m")

            stmt = select(budget_categories_table).where(
                budget_categories_table.c.user_id == user_id,
                budget_categories_table.c.month == current_month,
                budget_categories_table.c.category_name == category
            )

            with engine.connect() as conn:
                budget_result = conn.execute(stmt).first()
                if not budget_result:
                    return None
                
            budget_amount = float(budget_result.amount)

            # 計算已花費
            expenses = self.budget_manager.calculate_monthly_expenses(user_id, current_month)
            spent = expenses.get(category, 0)
            remaining = budget_amount - float(spent)
            usage_rate = (float(spent) / budget_amount) * 100

            # 根據使用率回應
            if usage_rate >= 100:
                return {
                    "title": "⚠️ 預算超支",
                    "message": f"已超支 ${abs(remaining):,}",
                    "color": "#F44336"
                }
            elif usage_rate >= 80:
                return {
                    "title": "⚠️ 預算警告", 
                    "message": f"剩餘 ${remaining:,} ({100-usage_rate:.0f}%)",
                    "color": "#FF9800"
                }
            elif usage_rate >= 50:
                return {
                    "title": "✅ 預算正常",
                    "message": f"剩餘 ${remaining:,} ({100-usage_rate:.0f}%)",
                    "color": "#4CAF50"
                }
            else:
                return {
                    "title": "✅ 預算充足",
                    "message": f"剩餘 ${remaining:,}",
                    "color": "#4CAF50"
                }
        except Exception as e:
            return None
        
class IncomeHandler:
    """處理收入相關邏輯"""

    def __init__(self, budget_manager):
        self.budget_manager = budget_manager

    def handle(self, data, user_id):
        try:
            success, message = self.budget_manager.add_transaction(
                user_id=user_id,
                date=datetime.now().strftime("%Y-%m-%d"),
                item=data.get("category", "Line收入"),
                amount=data["amount"],
                transaction_type="income",
                budget_category=data.get("budget_category", "收入"),
                description=data.get("description", "")
            )
            
            if success:
                return {"success": True, "data": data, "message": "收入記錄成功"}
            else:
                return {"success": False, "data": data, "message": message}
                
        except Exception as e:
            return {"success": False, "data": data, "message": str(e)}

class QueryHandler:
    """處理查詢相關邏輯"""

    def __init__(self, budget_manager):
        self.budget_manager = budget_manager
    
    def handle(self, user_id):
        """
        處理查詢請求
        
        Args:
            user_id (str): 用戶 ID
            
        Returns:
            dict: 查詢結果數據
        """
        try:
            current_month = datetime.now().strftime("%Y-%m")
            expenses = self.budget_manager.calculate_monthly_expenses(user_id, current_month)

            if not expenses:
                return {"success": False, "message": "本月尚無支出記錄"}
            
            # 獲取詳細交易記錄
            recent_transactions = self._get_recent_transactions(user_id, current_month, limit=5)
            total_expenses = sum(expenses.values())
            transaction_count = self._get_all_month_transactions(user_id, current_month)

            category_stats = self._get_category_expenses(user_id, current_month)

            return {
                "success": True,
                "month": current_month,
                "total_expenses": total_expenses,
                "transaction_count": transaction_count,
                "recent_transactions": recent_transactions,
                "category_stats": category_stats
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
        
    def _get_recent_transactions(self, user_id, month, limit=5):
        """獲取指定使用者最近交易記錄"""
        try:
            stmt = select(transactions_table).where(
                transactions_table.c.user_id == user_id,
                func.to_char(transactions_table.c.date, 'YYYY-MM') == month,
                transactions_table.c.type == 'expense'
            ).order_by(desc(transactions_table.c.date)).limit(limit)

            with engine.connect() as conn:
                result = conn.execute(stmt)
                return [dict(row._mapping) for row in result]
            
        except Exception as e:
            print(f"獲取交易記錄失敗: {e}")
            return []
        
    def _get_all_month_transactions(self, user_id, month):
        """獲取指定使用者整月交易數量"""
        try:
            stmt = select(func.count(transactions_table.c.id)).where(
                transactions_table.c.user_id == user_id,
                func.to_char(transactions_table.c.date, 'YYYY-MM') == month,
                transactions_table.c.type == 'expense'
            )

            with engine.connect() as conn:
                result = conn.execute(stmt).scalar()
                return result if result else 0
            
        except Exception as e:
            return 0
        
    def _get_category_expenses(self, user_id, month):
        """獲取指定使用者分類支出統計"""
        try:
            stmt = select(transactions_table.c.budget_category,
                func.sum(transactions_table.c.amount).label('total'),
                func.count(transactions_table.c.id).label('count')
            ).where(
                transactions_table.c.user_id == user_id,
                func.to_char(transactions_table.c.date, 'YYYY-MM') == month,
                transactions_table.c.type == 'expense'
            ).group_by(transactions_table.c.budget_category).order_by(
                func.sum(transactions_table.c.amount).desc()
            )

            with engine.connect() as conn:
                result = conn.execute(stmt)
                return [
                    {
                        'category': row.budget_category,
                        'total': float(row.total),
                        'count': row.count
                    }
                    for row in result
                ]
        except Exception as e:
            print(f"獲取分類統計失敗: {e}")
            return []
        
class AssetHandler:
    """處理資產查詢相關邏輯"""
    def __init__(self, asset_manager):
        self.asset_manager = asset_manager

    def handle(self, user_id):
        """
        處理資產查詢
        
        Args:
            user_id (str): 用戶 ID
            
        Returns:
            dict: 資產數據
        """
        try:
            totals = self.asset_manager.calculate_totals(user_id)
            return {"success": True, "totals": totals}
        except Exception as e:
            return {"success": False, "message": str(e)}

class GoalHandler:
    """財務目標處理器"""
    
    def __init__(self, goal_manager):
        self.goal_manager = goal_manager
    
    def handle_goal_query(self, user_id):
        """處理目標查詢"""
        try:
            goals_data = self.goal_manager.get_all_goals(user_id)
            summary = self.goal_manager.calculate_goal_summary(user_id)
            
            return {
                "success": True,
                "goals": goals_data,
                "summary": summary
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"查詢財務目標失敗: {str(e)}"
            }