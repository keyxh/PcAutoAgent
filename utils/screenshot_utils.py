#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
屏幕截图工具模块
"""

import pyautogui
from PIL import Image
import io
import base64

class ScreenshotUtils:
    """
    屏幕截图工具类，用于获取屏幕截图和处理图像
    """
    
    def __init__(self, max_size=1024):
        self.max_size = max_size
    
    def capture_screenshot(self, coordinate_converter=None, scale_screenshot=True):
        """
        截取当前屏幕截图
        :param coordinate_converter: 坐标转换器实例，如果提供会自动更新分辨率信息
        :param scale_screenshot: 是否缩放截图，默认为True。如果为False，则使用原始分辨率
        :return: (screenshot_buffer, original_width, original_height, scaled_width, scaled_height)
        :raises: PermissionError 当屏幕截图权限不足时抛出
        """
        try:
            # 获取原始屏幕截图
            screenshot = pyautogui.screenshot()
            original_width, original_height = screenshot.size
            
            # 决定是否缩放图片
            if scale_screenshot:
                # 缩小图片尺寸以减少API调用的数据量，但保持宽高比
                width, height = screenshot.size
                if width > height:
                    new_width = min(self.max_size, width)
                    new_height = int(height * new_width / width)
                else:
                    new_height = min(self.max_size, height)
                    new_width = int(width * new_height / height)
                
                scaled_screenshot = screenshot.resize((new_width, new_height))
                scaled_width, scaled_height = new_width, new_height
            else:
                # 不缩放，直接使用原始截图
                scaled_screenshot = screenshot
                scaled_width, scaled_height = original_width, original_height
            
            # 更新坐标转换器的分辨率信息
            if coordinate_converter:
                coordinate_converter.set_original_resolution(original_width, original_height)
                coordinate_converter.set_scaled_resolution(scaled_width, scaled_height)
            
            # 将截图保存到内存缓冲区
            img_buffer = io.BytesIO()
            scaled_screenshot.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer, original_width, original_height, scaled_width, scaled_height
            
        except (OSError, PermissionError) as e:
             # 屏幕截图失败，通常是由于权限不足
             error_msg = f"屏幕截图失败: {str(e)}"
             print(f"❌ {error_msg}")
             print("💡 任务已自动变为暂停状态，请手动处理后继续")
             
             # 抛出更明确的异常
             raise PermissionError(f"屏幕截图失败，任务已暂停。原始错误: {str(e)}")
    
    @staticmethod
    def encode_image_to_base64(image_buffer):
        """
        将图片编码为base64字符串
        :param image_buffer: 图片内存缓冲区
        :return: base64编码的字符串
        """
        return base64.b64encode(image_buffer.read()).decode('utf-8')
