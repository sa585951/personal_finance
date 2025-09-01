import json
import os
from datetime import datetime
from config import DATA_FOLDER

def create_data_folder():
    """建立資料資料夾"""
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        print(f"建立 {DATA_FOLDER} 資料夾")

def load_json_file(file_path, default_value=None):
    """載入JSON檔案的通用函數"""
    if default_value is None:
        default_value = {}
        
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return default_value
    except Exception as e:
        print(f"載入資料失敗 {file_path}: {e}")
        return default_value

def save_json_file(file_path, data):
    """儲存JSON檔案的通用函數"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"儲存失敗 {file_path}: {e}")
        return False