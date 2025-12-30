import os
import json
import logging

class AdapterUtils:
    def __init__(self):
        self.adapters_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'adapters')
        self.adapters = {}  # 存储加载的适配器
        self.load_all_adapters()
    
    def load_all_adapters(self):
        """
        加载所有适配器配置文件
        """
        try:
            if not os.path.exists(self.adapters_dir):
                logging.warning(f"适配器目录不存在: {self.adapters_dir}")
                return
            
            for filename in os.listdir(self.adapters_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.adapters_dir, filename)
                    self.load_adapter(file_path)
            
            logging.info(f"成功加载 {len(self.adapters)} 个适配器")
        except Exception as e:
            logging.error(f"加载适配器失败: {str(e)}")
    
    def load_adapter(self, file_path):
        """
        加载单个适配器配置文件
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                adapter_data = json.load(f)
            
            # 使用文件名（不带扩展名）作为适配器ID
            adapter_id = os.path.splitext(os.path.basename(file_path))[0]
            self.adapters[adapter_id] = adapter_data
            logging.info(f"成功加载适配器: {adapter_id} - {adapter_data.get('name', '未命名')}")
        except Exception as e:
            logging.error(f"加载适配器文件 {file_path} 失败: {str(e)}")
    
    def get_adapter(self, adapter_id):
        """
        获取指定ID的适配器
        """
        return self.adapters.get(adapter_id)
    
    def get_all_adapters(self):
        """
        获取所有加载的适配器
        """
        return self.adapters
    
    def apply_adjustment(self, x, y, adapter_id=None, target_type=None):
        """
        应用坐标调整规则
        
        参数:
        - x, y: 原始比例坐标
        - adapter_id: 适配器ID（可选）
        - target_type: 目标类型（如"click"、"address_bar"等）
        
        返回:
        - 调整后的坐标 (adjusted_x, adjusted_y)
        """
        if not adapter_id or adapter_id not in self.adapters:
            return x, y
        
        adapter = self.adapters[adapter_id]
        rules = adapter.get('rules', [])
        
        for rule in rules:
            if rule.get('type') == target_type or rule.get('target') == target_type:
                adjustment = rule.get('adjustment', {})
                adjusted_x = x + adjustment.get('x', 0)
                adjusted_y = y + adjustment.get('y', 0)
                
                # 确保调整后的坐标仍然在0-1范围内
                adjusted_x = max(0, min(1, adjusted_x))
                adjusted_y = max(0, min(1, adjusted_y))
                
                logging.info(f"应用适配器 {adapter_id} 的规则到目标 {target_type}，坐标从 ({x:.3f}, {y:.3f}) 调整为 ({adjusted_x:.3f}, {adjusted_y:.3f})")
                return adjusted_x, adjusted_y
        
        return x, y

# 创建单例实例
_adapter_utils_instance = None

def get_adapter_utils():
    """
    获取适配器工具的单例实例
    """
    global _adapter_utils_instance
    if _adapter_utils_instance is None:
        _adapter_utils_instance = AdapterUtils()
    return _adapter_utils_instance