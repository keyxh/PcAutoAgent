#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐标转换工具模块
"""

class CoordinateConverter:
    """
    坐标转换类，用于处理截图缩放和实际屏幕坐标之间的转换
    """
    
    def __init__(self):
        self.original_width = 0
        self.original_height = 0
        self.scaled_width = 0
        self.scaled_height = 0
    
    def set_original_resolution(self, width, height):
        """
        设置原始屏幕分辨率
        """
        self.original_width = width
        self.original_height = height
    
    def set_scaled_resolution(self, width, height):
        """
        设置缩放后的截图分辨率
        """
        self.scaled_width = width
        self.scaled_height = height
    
    def convert_proportion_to_actual(self, x_proportion, y_proportion):
        """
        将比例坐标转换为实际屏幕坐标 - 高精度版本
        :param x_proportion: x轴比例 (0-1)
        :param y_proportion: y轴比例 (0-1)
        :return: (actual_x, actual_y) 实际屏幕坐标
        """
        # 确保坐标在有效范围内，使用高精度比较
        x_proportion = max(0.0, min(1.0, float(x_proportion)))
        y_proportion = max(0.0, min(1.0, float(y_proportion)))
        
        # 使用高精度浮点数计算，保留4位小数精度
        actual_x = float(x_proportion) * float(self.original_width)
        actual_y = float(y_proportion) * float(self.original_height)
        
        # 确保坐标不超出屏幕范围，使用高精度边界检查
        # 添加安全边距，避免触发 PyAutoGUI fail-safe（屏幕角落）
        safe_margin = 5  # 距离边缘5像素的安全边距
        max_x = float(self.original_width - safe_margin)
        max_y = float(self.original_height - safe_margin)
        actual_x = max(float(safe_margin), min(max_x, actual_x))
        actual_y = max(float(safe_margin), min(max_y, actual_y))
        
        # 返回高精度的坐标值，保留4位小数
        return round(actual_x, 4), round(actual_y, 4)
    
    def convert_relative_to_actual(self, x_relative, y_relative):
        """
        将相对坐标（基于缩放后的截图）转换为实际屏幕坐标
        :param x_relative: 相对x坐标 (基于缩放后的截图)
        :param y_relative: 相对y坐标 (基于缩放后的截图)
        :return: (actual_x, actual_y) 实际屏幕坐标
        """
        if self.scaled_width == 0 or self.scaled_height == 0:
            return float(x_relative), float(y_relative)
        
        # 计算坐标缩放比例
        x_ratio = float(self.original_width) / float(self.scaled_width)
        y_ratio = float(self.original_height) / float(self.scaled_height)
        
        # 转换坐标，使用更精确的浮点数计算
        actual_x = float(x_relative) * x_ratio
        actual_y = float(y_relative) * y_ratio
        
        # 确保坐标不超出屏幕范围
        # 添加安全边距，避免触发 PyAutoGUI fail-safe（屏幕角落）
        safe_margin = 5  # 距离边缘5像素的安全边距
        actual_x = max(float(safe_margin), min(float(self.original_width - safe_margin), actual_x))
        actual_y = max(float(safe_margin), min(float(self.original_height - safe_margin), actual_y))
        
        return actual_x, actual_y
