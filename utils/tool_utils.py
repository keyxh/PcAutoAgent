#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具调用模块
"""

import re
import time
import pyautogui
import subprocess
import platform
import os
from utils.adapter_utils import get_adapter_utils

class ToolUtils:
    """
    工具调用类，用于解析和执行工具调用
    """
    
    def __init__(self, coordinate_converter):
        self.coordinate_converter = coordinate_converter
        self.adapter_utils = get_adapter_utils()
        self.tools = {
            'mouse_click': self.mouse_click,
            'double_click': self.double_click,
            'right_click': self.right_click,
            'mouse_hover': self.mouse_hover,
            'mouse_down': self.mouse_down,
            'mouse_up': self.mouse_up,
            'type_text': self.type_text,
            'scroll_window': self.scroll_window,
            'close_window': self.close_window,
            'press_windows_key': self.press_windows_key,
            'press_enter': self.press_enter,
            'delete_text': self.delete_text,
            'mouse_drag': self.mouse_drag,
            'wait': self.wait,
            'open_terminal': self.open_terminal,
            'press_hotkey': self.press_hotkey,
            'pause_task': self.pause_task,
            'complete_task': self.complete_task
        }
    
    def parse_tool_calls(self, response_text):
        """
        从模型响应中解析工具调用
        :param response_text: 模型响应文本
        :return: 工具调用列表
        """
        tool_calls = []
        
        # 支持三种工具调用格式：
        # 1. <|tool_call|>function_name(param1=value1, param2=value2)<|tool_call|>  (完整格式)
        # 2. function_name(param1=value1, param2=value2)<|tool_call|>               (简化格式)
        # 3. function_name(param1=value1, param2=value2)                           (无标签格式)
        
        # 按优先级匹配，避免重复
        
        # 首先匹配完整格式 <|tool_call|>function_name(params)<|tool_call|>
        pattern1 = r'<\|tool_call\|>([^<\|tool_call\|>]*?)<\|tool_call\|>'
        matches1 = re.findall(pattern1, response_text, re.DOTALL)
        
        # 然后匹配简化格式 function_name(params)<|tool_call|>，排除已被完整格式匹配的内容
        pattern2 = r'([a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\))\s*<\|tool_call\|>'
        matches2 = re.findall(pattern2, response_text)
        
        # 最后匹配无标签格式（只在行尾或句末，避免误匹配）
        # 限制匹配范围：只匹配行尾或句子结束的无标签工具调用
        pattern3 = r'(mouse_click|type_text|scroll_window|close_window|clear_input|wait|press_hotkey|pause_task|complete_task)\s*\([^)]*\)(?=\s*\n|$|\.)'
        matches3 = re.findall(pattern3, response_text)
        # 重新匹配完整内容以获得参数部分
        if matches3:
            full_pattern3 = r'((mouse_click|type_text|scroll_window|close_window|clear_input|wait|press_hotkey|pause_task|complete_task)\s*\([^)]*\))(?=\s*\n|$|\.)'
            full_matches3 = re.findall(full_pattern3, response_text)
            matches3 = [match[0] for match in full_matches3]
        
        # 合并匹配结果，但避免重复
        all_matches = []
        seen_matches = set()
        
        for match_list in [matches1, matches2, matches3]:
            for match in match_list:
                if match not in seen_matches:
                    all_matches.append(match)
                    seen_matches.add(match)
        
        print(f"工具调用匹配详情:")
        print(f"  完整格式匹配: {len(matches1)} 个")
        print(f"  简化格式匹配: {len(matches2)} 个") 
        print(f"  无标签格式匹配: {len(matches3)} 个")
        print(f"  去重后总数: {len(all_matches)} 个")
        
        for match in all_matches:
            # 解析函数名和参数
            function_pattern = r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)\s*$'
            function_match = re.match(function_pattern, match)
            if not function_match:
                print(f"    跳过无法解析的匹配: {repr(match)}")
                continue
            
            function_name = function_match.group(1)
            args_str = function_match.group(2)
            
            print(f"    解析工具调用: {function_name}({args_str})")
            
            # 解析参数
            args = {}
            if args_str.strip():
                # 匹配参数名和值，支持字符串值
                arg_pattern = r'\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*("[^"]*"|\d+\.\d+|\d+|\w+)\s*'
                arg_matches = re.findall(arg_pattern, args_str)
                
                for arg_name, arg_value in arg_matches:
                    # 处理字符串值
                    if arg_value.startswith('"') and arg_value.endswith('"'):
                        arg_value = arg_value[1:-1]
                    # 处理数值
                    elif '.' in arg_value:
                        try:
                            arg_value = float(arg_value)
                        except ValueError:
                            pass
                    elif arg_value.isdigit():
                        arg_value = int(arg_value)
                    
                    args[arg_name] = arg_value
                
                print(f"      解析后的参数: {args}")
            else:
                print(f"      无参数")
            
            tool_calls.append({
                'name': function_name,
                'arguments': args
            })
        
        return tool_calls
    
    def execute_tool_calls(self, tool_calls):
        """
        执行工具调用
        :param tool_calls: 工具调用列表
        :return: 执行结果字符串
        """
        results = []
        for call in tool_calls:
            func_name = call["name"]
            args = call["arguments"]
            
            if func_name in self.tools:
                try:
                    result = self.tools[func_name](**args)
                    results.append(f"工具 {func_name} 执行结果: {result}")
                except Exception as e:
                    results.append(f"执行工具 {func_name} 时出错: {str(e)}")
            else:
                results.append(f"未知工具: {func_name}")
        
        return "\n".join(results)
    
    def mouse_click(self, x, y, button="left", clicks=1, adapter_id=None, move_first=True):
        """
        鼠标点击工具 - 使用比例坐标 (0-1之间的浮点数)
        
        参数:
        - x, y: 比例坐标
        - button: 鼠标按钮 (left/right)
        - clicks: 点击次数 (1/2)
        - adapter_id: 适配器ID (可选)
        - move_first: 是否先移动鼠标 (True先移动，False智能判断)
        """
        # 应用适配器调整
        adjusted_x, adjusted_y = self.adapter_utils.apply_adjustment(x, y, adapter_id, 'click')
        
        # 将比例坐标转换为实际屏幕坐标，保留更高精度
        actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(adjusted_x, adjusted_y)
        
        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        # 确保坐标在屏幕范围内，使用浮点数计算避免过早损失精度
        # 添加安全边距，避免触发 PyAutoGUI fail-safe（屏幕角落）
        safe_margin = 5  # 距离边缘5像素的安全边距
        actual_x = max(float(safe_margin), min(float(screen_width - safe_margin), actual_x))
        actual_y = max(float(safe_margin), min(float(screen_height - safe_margin), actual_y))
        
        try:
            # 获取当前鼠标位置（使用浮点数）
            current_x, current_y = pyautogui.position()
            distance_to_target = ((current_x - actual_x) ** 2 + (current_y - actual_y) ** 2) ** 0.5
            
            # 智能判断是否需要移动鼠标
            if move_first or distance_to_target > 50:  # 距离超过50像素或明确要求移动
                # 平滑移动鼠标到目标位置（提高精度），使用亚像素精度
                # 先移动到接近位置
                intermediate_x = actual_x + (actual_x - current_x) * 0.8
                intermediate_y = actual_y + (actual_y - current_y) * 0.8
                
                if abs(intermediate_x - current_x) > 10 or abs(intermediate_y - current_y) > 10:
                    pyautogui.moveTo(intermediate_x, intermediate_y, duration=0.05)
                
                # 最终精确移动
                pyautogui.moveTo(actual_x, actual_y, duration=0.05, tween=pyautogui.easeInOutQuad)
                
                # 精确验证鼠标位置（使用更高精度的偏差阈值）
                final_x, final_y = pyautogui.position()
                x_error = abs(final_x - actual_x)
                y_error = abs(final_y - actual_y)
                
                # 如果位置偏差超过2像素，进行精细微调
                if x_error > 2 or y_error > 2:
                    # 计算修正方向
                    correction_x = actual_x - final_x
                    correction_y = actual_y - final_y
                    
                    # 分步微调，避免过度校正
                    steps = max(int(max(x_error, y_error) / 2), 1)  # 每步最多移动2像素
                    step_x = correction_x / steps
                    step_y = correction_y / steps
                    
                    for i in range(steps):
                        temp_x = final_x + step_x * (i + 1)
                        temp_y = final_y + step_y * (i + 1)
                        pyautogui.moveTo(temp_x, temp_y, duration=0.02)
                    
                    # 最终验证
                    final_x, final_y = pyautogui.position()
                
                move_action = "已移动并"
            else:
                # 鼠标已在附近，直接点击
                final_x, final_y = current_x, current_y
                move_action = "直接"
            
            # 在最后时刻转换为整数，确保最小精度损失
            click_x = int(round(actual_x))
            click_y = int(round(actual_y))
            final_click_x = int(round(final_x))
            final_click_y = int(round(final_y))
            
            # 执行点击操作，使用更精确的点击方式
            pyautogui.click(button=button, clicks=clicks, interval=0.03)
            
            # 短暂等待，确保点击生效
            # 如果点击的是任务栏区域（y坐标接近屏幕底部），增加等待时间
            if actual_y > screen_height * 0.95:  # 任务栏通常在屏幕底部5%区域内
                time.sleep(0.4)  # 任务栏应用启动需要更长时间
            else:
                time.sleep(0.08)
            
            return f"{move_action}在坐标 ({click_x}, {click_y}) 处{clicks}次{button}键点击（实际位置: ({final_click_x}, {final_click_y})，移动距离: {int(distance_to_target)}像素，误差: X{int(x_error)}px, Y{int(y_error)}px）"
        except Exception as e:
            # 异常情况下的备用点击方式
            print(f"精确点击失败，使用备用方式: {str(e)}")
            backup_x = int(round(actual_x))
            backup_y = int(round(actual_y))
            pyautogui.click(backup_x, backup_y, button=button, clicks=clicks)
            time.sleep(0.1)
            return f"使用备用方式在坐标 ({backup_x}, {backup_y}) 处{clicks}次{button}键点击"
    
    def double_click(self, x, y, button="left", adapter_id=None, move_first=True):
        """
        鼠标双击工具 - 高精度版本
        
        参数:
        - x, y: 比例坐标 (0-1)
        - button: 鼠标按钮 (left/right)
        - adapter_id: 适配器ID (可选)
        - move_first: 是否先移动鼠标 (True先移动，False智能判断)
        """
        # 应用适配器调整
        adjusted_x, adjusted_y = self.adapter_utils.apply_adjustment(x, y, adapter_id, 'click')
        
        # 将比例坐标转换为实际屏幕坐标，保留更高精度
        actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(adjusted_x, adjusted_y)
        
        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        # 确保坐标在屏幕范围内，使用浮点数计算避免过早损失精度
        # 添加安全边距，避免触发 PyAutoGUI fail-safe（屏幕角落）
        safe_margin = 5  # 距离边缘5像素的安全边距
        actual_x = max(float(safe_margin), min(float(screen_width - safe_margin), actual_x))
        actual_y = max(float(safe_margin), min(float(screen_height - safe_margin), actual_y))
        
        try:
            # 获取当前鼠标位置（使用浮点数）
            current_x, current_y = pyautogui.position()
            distance_to_target = ((current_x - actual_x) ** 2 + (current_y - actual_y) ** 2) ** 0.5
            
            # 智能判断是否需要移动鼠标
            if move_first or distance_to_target > 50:  # 距离超过50像素或明确要求移动
                # 平滑移动鼠标到目标位置（提高精度），使用亚像素精度
                # 先移动到接近位置
                intermediate_x = actual_x + (actual_x - current_x) * 0.8
                intermediate_y = actual_y + (actual_y - current_y) * 0.8
                
                if abs(intermediate_x - current_x) > 10 or abs(intermediate_y - current_y) > 10:
                    pyautogui.moveTo(intermediate_x, intermediate_y, duration=0.05)
                
                # 最终精确移动
                pyautogui.moveTo(actual_x, actual_y, duration=0.05, tween=pyautogui.easeInOutQuad)
                
                # 精确验证鼠标位置（使用更高精度的偏差阈值）
                final_x, final_y = pyautogui.position()
                x_error = abs(final_x - actual_x)
                y_error = abs(final_y - actual_y)
                
                # 如果位置偏差超过2像素，进行精细微调
                if x_error > 2 or y_error > 2:
                    # 计算修正方向
                    correction_x = actual_x - final_x
                    correction_y = actual_y - final_y
                    
                    # 分步微调，避免过度校正
                    steps = max(int(max(x_error, y_error) / 2), 1)  # 每步最多移动2像素
                    step_x = correction_x / steps
                    step_y = correction_y / steps
                    
                    for i in range(steps):
                        temp_x = final_x + step_x * (i + 1)
                        temp_y = final_y + step_y * (i + 1)
                        pyautogui.moveTo(temp_x, temp_y, duration=0.02)
                    
                    # 最终验证
                    final_x, final_y = pyautogui.position()
                    
                move_action = f"高精度移动后"
            else:
                final_x, final_y = current_x, current_y
                move_action = "原地"
            
            # 执行双击操作（使用clicks=2）
            pyautogui.click(button=button, clicks=2, interval=0.05)
            
            # 在最后时刻转换为整数，避免早期精度损失
            click_x = int(round(final_x))
            click_y = int(round(final_y))
            final_click_x = int(round(final_x))
            final_click_y = int(round(final_y))
            
            # 短暂等待，确保双击生效
            time.sleep(0.15)  # 双击后等待稍长一些
            
            return f"{move_action}在坐标 ({click_x}, {click_y}) 处进行{button}键双击（实际位置: ({final_click_x}, {final_click_y})，移动距离: {int(distance_to_target)}像素，误差: X{int(x_error)}px, Y{int(y_error)}px）"
        except Exception as e:
            # 异常情况下的备用双击方式
            print(f"精确双击失败，使用备用方式: {str(e)}")
            backup_x = int(round(actual_x))
            backup_y = int(round(actual_y))
            pyautogui.click(backup_x, backup_y, button=button, clicks=2, interval=0.05)
            time.sleep(0.15)
            return f"使用备用方式在坐标 ({backup_x}, {backup_y}) 处进行{button}键双击"
    
    def scroll_window(self, x, y, direction="up", adapter_id=None):
        """
        滚动窗口工具 - 高精度版本
        
        参数:
        - x, y: 比例坐标
        - direction: 滚动方向 (up/down)
        - adapter_id: 适配器ID (可选)
        """
        # 应用适配器调整
        adjusted_x, adjusted_y = self.adapter_utils.apply_adjustment(x, y, adapter_id, 'scroll')
        
        # 将比例坐标转换为实际屏幕坐标，保留高精度
        actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(adjusted_x, adjusted_y)
        
        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        # 确保坐标在屏幕范围内，保留浮点数精度
        # 添加安全边距，避免触发 PyAutoGUI fail-safe（屏幕角落）
        safe_margin = 5  # 距离边缘5像素的安全边距
        actual_x = max(float(safe_margin), min(float(screen_width - safe_margin), actual_x))
        actual_y = max(float(safe_margin), min(float(screen_height - safe_margin), actual_y))
        
        # 平滑移动鼠标到指定位置
        pyautogui.moveTo(actual_x, actual_y, duration=0.05, tween=pyautogui.easeInOutQuad)
        
        # 执行滚动操作
        scroll_amount = 300
        if direction == "down":
            scroll_amount = -scroll_amount
        
        pyautogui.scroll(scroll_amount)
        
        # 短暂等待
        time.sleep(0.1)
        
        # 在最后时刻转换为整数
        click_x = int(round(actual_x))
        click_y = int(round(actual_y))
        
        return f"在坐标 ({click_x}, {click_y}) 处向{direction}滚动窗口（精度: {actual_x:.2f}, {actual_y:.2f}）"
    
    def type_text(self, x, y, text, adapter_id=None):
        """
        文本输入工具 - 高精度版本
        
        参数:
        - x, y: 比例坐标
        - text: 要输入的文本
        - adapter_id: 适配器ID (可选)
        """
        import pyperclip
        
        # 应用适配器调整
        adjusted_x, adjusted_y = self.adapter_utils.apply_adjustment(x, y, adapter_id, 'type')
        
        # 将比例坐标转换为实际屏幕坐标，保留高精度
        actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(adjusted_x, adjusted_y)
        
        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        # 确保坐标在屏幕范围内，保留浮点数精度
        actual_x = max(0.0, min(float(screen_width - 1), actual_x))
        actual_y = max(0.0, min(float(screen_height - 1), actual_y))
        
        # 平滑移动到指定位置并点击获取焦点
        pyautogui.moveTo(actual_x, actual_y, duration=0.05, tween=pyautogui.easeInOutQuad)
        pyautogui.click(button='left', clicks=1, interval=0.02)
        time.sleep(0.1)
        
        try:
            # 使用pyperclip复制粘贴文本，支持中英文
            pyperclip.copy(text)
            time.sleep(0.05)
            
            # 粘贴文本
            if platform.system() == "Darwin":  # macOS
                pyautogui.hotkey('command', 'v')
            else:  # Windows, Linux
                pyautogui.hotkey('ctrl', 'v')
            
            time.sleep(0.1)
            # 在最后时刻转换为整数
            click_x = int(round(actual_x))
            click_y = int(round(actual_y))
            return f"在坐标 ({click_x}, {click_y}) 处输入文本: {text}（精度: {actual_x:.2f}, {actual_y:.2f}）"
        except Exception as e:
            # 如果pyperclip失败，使用备用方案
            print(f"pyperclip输入失败，使用备用方案: {e}")
            return self._type_text_fallback(x, y, text)
    
    def _type_text_fallback(self, x, y, text):
        """
        文本输入备用方案
        """
        # 应用适配器调整
        adjusted_x, adjusted_y = self.adapter_utils.apply_adjustment(x, y, None, 'type')
        
        # 将比例坐标转换为实际屏幕坐标
        actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(adjusted_x, adjusted_y)
        
        # 点击指定位置获取焦点
        pyautogui.click(actual_x, actual_y)
        time.sleep(0.1)
        
        # 直接输入文本
        pyautogui.typewrite(text, interval=0.01)
        
        # 短暂等待
        time.sleep(0.1)
        
        return f"使用备用方式在坐标 ({actual_x}, {actual_y}) 处输入文本: {text}"
    
    def close_window(self, x, y):
        """
        窗口关闭工具
        """
        # 将比例坐标转换为实际屏幕坐标
        actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(x, y)
        
        # 确保坐标为整数（pyautogui需要整数坐标）
        actual_x = int(round(actual_x))
        actual_y = int(round(actual_y))
        
        try:
            # 首先尝试点击窗口右上角的关闭按钮
            pyautogui.click(actual_x, actual_y)
            time.sleep(0.2)
            return f"在坐标 ({actual_x}, {actual_y}) 处点击关闭按钮"
        except Exception as e:
            # 如果点击失败，尝试使用Alt+F4关闭窗口
            print(f"点击关闭按钮失败，尝试使用Alt+F4: {str(e)}")
            pyautogui.hotkey('alt', 'f4')
            time.sleep(0.2)
            return f"使用Alt+F4关闭窗口"
    
    def press_windows_key(self):
        """
        按下Windows键工具
        """
        # 模拟按下Windows键
        pyautogui.press('winleft')
        time.sleep(0.1)
        
        return "按下Windows键"
    
    def press_enter(self):
        """
        按下回车键
        """
        pyautogui.press('enter')
        time.sleep(0.1)
        return "按下回车键"
    
    def delete_text(self, x, y, count=1):
        """
        删除文本工具
        
        参数:
        - x, y: 比例坐标，用于获取焦点
        - count: 删除数量，当count=-1时表示删除所有选中内容
        """
        try:
            # 将比例坐标转换为实际屏幕坐标
            actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(x, y)
            
            # 确保坐标为整数（pyautogui需要整数坐标）
            actual_x = int(round(actual_x))
            actual_y = int(round(actual_y))
            
            # 点击指定位置获取焦点
            pyautogui.click(actual_x, actual_y)
            time.sleep(0.1)
            
            # 执行删除操作
            if count == -1:
                # 批量删除：先全选再删除
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.1)
                pyautogui.press('delete')
                result_msg = f"在坐标 ({actual_x}, {actual_y}) 处删除所有选中内容"
            else:
                # 逐个删除
                pyautogui.press('delete', presses=count)
                result_msg = f"在坐标 ({actual_x}, {actual_y}) 处删除 {count} 个字符"
            
            time.sleep(0.1)
            
            return result_msg
        except Exception as e:
            return f"删除文本失败: {str(e)}"
    
    def mouse_drag(self, start_x, start_y, end_x, end_y, duration=0.5):
        """
        鼠标拖拽工具 - 高精度版本
        """
        # 将比例坐标转换为实际屏幕坐标，保留高精度
        start_actual_x, start_actual_y = self.coordinate_converter.convert_proportion_to_actual(start_x, start_y)
        end_actual_x, end_actual_y = self.coordinate_converter.convert_proportion_to_actual(end_x, end_y)
        
        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        # 确保坐标在屏幕范围内，保留浮点数精度
        start_actual_x = max(0.0, min(float(screen_width - 1), start_actual_x))
        start_actual_y = max(0.0, min(float(screen_height - 1), start_actual_y))
        end_actual_x = max(0.0, min(float(screen_width - 1), end_actual_x))
        end_actual_y = max(0.0, min(float(screen_height - 1), end_actual_y))
        
        # 在最后时刻转换为整数，确保最小精度损失
        start_x_int = int(round(start_actual_x))
        start_y_int = int(round(start_actual_y))
        end_x_int = int(round(end_actual_x))
        end_y_int = int(round(end_actual_y))
        
        # 平滑移动到起始位置
        pyautogui.moveTo(start_actual_x, start_actual_y, duration=0.1, tween=pyautogui.easeInOutQuad)
        
        # 执行高精度拖拽操作
        pyautogui.dragTo(end_actual_x, end_actual_y, duration=duration, tween=pyautogui.easeInOutQuad)
        
        return f"从坐标 ({start_x_int}, {start_y_int}) 拖拽到 ({end_x_int}, {end_y_int})（实际精度: {start_actual_x:.2f},{start_actual_y:.2f} → {end_actual_x:.2f},{end_actual_y:.2f}）"
    
    def right_click(self, x, y, adapter_id=None, move_first=True):
        """
        鼠标右键点击工具 - 高精度版本
        
        参数:
        - x, y: 比例坐标 (0-1)
        - adapter_id: 适配器ID (可选)
        - move_first: 是否先移动鼠标 (True先移动，False智能判断)
        """
        return self.mouse_click(x, y, button="right", clicks=1, adapter_id=adapter_id, move_first=move_first)
    
    def mouse_hover(self, x, y, adapter_id=None, move_first=True):
        """
        鼠标悬停工具 - 高精度版本
        
        参数:
        - x, y: 比例坐标 (0-1)
        - adapter_id: 适配器ID (可选)
        - move_first: 是否先移动鼠标 (True先移动，False智能判断)
        """
        # 应用适配器调整
        adjusted_x, adjusted_y = self.adapter_utils.apply_adjustment(x, y, adapter_id, 'click')
        
        # 将比例坐标转换为实际屏幕坐标，保留更高精度
        actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(adjusted_x, adjusted_y)
        
        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        # 确保坐标在屏幕范围内，使用浮点数计算避免过早损失精度
        actual_x = max(0.0, min(float(screen_width - 1), actual_x))
        actual_y = max(0.0, min(float(screen_height - 1), actual_y))
        
        try:
            # 获取当前鼠标位置（使用浮点数）
            current_x, current_y = pyautogui.position()
            distance_to_target = ((current_x - actual_x) ** 2 + (current_y - actual_y) ** 2) ** 0.5
            
            # 智能判断是否需要移动鼠标
            if move_first or distance_to_target > 50:  # 距离超过50像素或明确要求移动
                # 平滑移动鼠标到目标位置（提高精度），使用亚像素精度
                # 先移动到接近位置
                intermediate_x = actual_x + (actual_x - current_x) * 0.8
                intermediate_y = actual_y + (actual_y - current_y) * 0.8
                
                if abs(intermediate_x - current_x) > 10 or abs(intermediate_y - current_y) > 10:
                    pyautogui.moveTo(intermediate_x, intermediate_y, duration=0.05)
                
                # 最终精确移动
                pyautogui.moveTo(actual_x, actual_y, duration=0.05, tween=pyautogui.easeInOutQuad)
                
                # 精确验证鼠标位置（使用更高精度的偏差阈值）
                final_x, final_y = pyautogui.position()
                x_error = abs(final_x - actual_x)
                y_error = abs(final_y - actual_y)
                
                # 如果位置偏差超过2像素，进行精细微调
                if x_error > 2 or y_error > 2:
                    # 计算修正方向
                    correction_x = actual_x - final_x
                    correction_y = actual_y - final_y
                    
                    # 分步微调，避免过度校正
                    steps = max(int(max(x_error, y_error) / 2), 1)  # 每步最多移动2像素
                    step_x = correction_x / steps
                    step_y = correction_y / steps
                    
                    for i in range(steps):
                        temp_x = final_x + step_x * (i + 1)
                        temp_y = final_y + step_y * (i + 1)
                        pyautogui.moveTo(temp_x, temp_y, duration=0.02)
                    
                    # 最终验证
                    final_x, final_y = pyautogui.position()
                    
                move_action = f"高精度移动后"
            else:
                final_x, final_y = current_x, current_y
                move_action = "原地"
            
            # 在最后时刻转换为整数，避免早期精度损失
            hover_x = int(round(final_x))
            hover_y = int(round(final_y))
            
            return f"{move_action}在坐标 ({hover_x}, {hover_y}) 处悬停（实际位置: ({final_x}, {final_y})，移动距离: {int(distance_to_target)}像素，误差: X{int(x_error)}px, Y{int(y_error)}px）"
        except Exception as e:
            # 异常情况下的备用悬停方式
            print(f"精确悬停失败，使用备用方式: {str(e)}")
            backup_x = int(round(actual_x))
            backup_y = int(round(actual_y))
            pyautogui.moveTo(backup_x, backup_y)
            time.sleep(0.1)
            return f"使用备用方式在坐标 ({backup_x}, {backup_y}) 处悬停"
    
    def mouse_down(self, x, y, button="left", adapter_id=None, move_first=True):
        """
        鼠标按下工具 - 高精度版本
        
        参数:
        - x, y: 比例坐标 (0-1)
        - button: 鼠标按钮 (left/right)
        - adapter_id: 适配器ID (可选)
        - move_first: 是否先移动鼠标 (True先移动，False智能判断)
        """
        # 应用适配器调整
        adjusted_x, adjusted_y = self.adapter_utils.apply_adjustment(x, y, adapter_id, 'click')
        
        # 将比例坐标转换为实际屏幕坐标，保留更高精度
        actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(adjusted_x, adjusted_y)
        
        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        # 确保坐标在屏幕范围内，使用浮点数计算避免过早损失精度
        actual_x = max(0.0, min(float(screen_width - 1), actual_x))
        actual_y = max(0.0, min(float(screen_height - 1), actual_y))
        
        try:
            # 获取当前鼠标位置（使用浮点数）
            current_x, current_y = pyautogui.position()
            distance_to_target = ((current_x - actual_x) ** 2 + (current_y - actual_y) ** 2) ** 0.5
            
            # 智能判断是否需要移动鼠标
            if move_first or distance_to_target > 50:  # 距离超过50像素或明确要求移动
                # 平滑移动鼠标到目标位置（提高精度），使用亚像素精度
                # 先移动到接近位置
                intermediate_x = actual_x + (actual_x - current_x) * 0.8
                intermediate_y = actual_y + (actual_y - current_y) * 0.8
                
                if abs(intermediate_x - current_x) > 10 or abs(intermediate_y - current_y) > 10:
                    pyautogui.moveTo(intermediate_x, intermediate_y, duration=0.05)
                
                # 最终精确移动
                pyautogui.moveTo(actual_x, actual_y, duration=0.05, tween=pyautogui.easeInOutQuad)
                
                # 精确验证鼠标位置（使用更高精度的偏差阈值）
                final_x, final_y = pyautogui.position()
                x_error = abs(final_x - actual_x)
                y_error = abs(final_y - actual_y)
                
                # 如果位置偏差超过2像素，进行精细微调
                if x_error > 2 or y_error > 2:
                    # 计算修正方向
                    correction_x = actual_x - final_x
                    correction_y = actual_y - final_y
                    
                    # 分步微调，避免过度校正
                    steps = max(int(max(x_error, y_error) / 2), 1)  # 每步最多移动2像素
                    step_x = correction_x / steps
                    step_y = correction_y / steps
                    
                    for i in range(steps):
                        temp_x = final_x + step_x * (i + 1)
                        temp_y = final_y + step_y * (i + 1)
                        pyautogui.moveTo(temp_x, temp_y, duration=0.02)
                    
                    # 最终验证
                    final_x, final_y = pyautogui.position()
                    
                move_action = f"高精度移动后"
            else:
                final_x, final_y = current_x, current_y
                move_action = "原地"
            
            # 执行鼠标按下操作
            pyautogui.mouseDown(button=button)
            
            # 在最后时刻转换为整数，避免早期精度损失
            down_x = int(round(final_x))
            down_y = int(round(final_y))
            
            # 短暂等待，确保按下生效
            time.sleep(0.05)
            
            return f"{move_action}在坐标 ({down_x}, {down_y}) 处按下{button}键（实际位置: ({final_x}, {final_y})，移动距离: {int(distance_to_target)}像素，误差: X{int(x_error)}px, Y{int(y_error)}px）"
        except Exception as e:
            # 异常情况下的备用按下方式
            print(f"精确按下失败，使用备用方式: {str(e)}")
            backup_x = int(round(actual_x))
            backup_y = int(round(actual_y))
            pyautogui.moveTo(backup_x, backup_y)
            pyautogui.mouseDown(button=button)
            time.sleep(0.05)
            return f"使用备用方式在坐标 ({backup_x}, {backup_y}) 处按下{button}键"
    
    def mouse_up(self, x, y, button="left", adapter_id=None, move_first=True):
        """
        鼠标释放工具 - 高精度版本
        
        参数:
        - x, y: 比例坐标 (0-1)
        - button: 鼠标按钮 (left/right)
        - adapter_id: 适配器ID (可选)
        - move_first: 是否先移动鼠标 (True先移动，False智能判断)
        """
        # 应用适配器调整
        adjusted_x, adjusted_y = self.adapter_utils.apply_adjustment(x, y, adapter_id, 'click')
        
        # 将比例坐标转换为实际屏幕坐标，保留更高精度
        actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(adjusted_x, adjusted_y)
        
        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        
        # 确保坐标在屏幕范围内，使用浮点数计算避免过早损失精度
        actual_x = max(0.0, min(float(screen_width - 1), actual_x))
        actual_y = max(0.0, min(float(screen_height - 1), actual_y))
        
        try:
            # 获取当前鼠标位置（使用浮点数）
            current_x, current_y = pyautogui.position()
            distance_to_target = ((current_x - actual_x) ** 2 + (current_y - actual_y) ** 2) ** 0.5
            
            # 智能判断是否需要移动鼠标
            if move_first or distance_to_target > 50:  # 距离超过50像素或明确要求移动
                # 平滑移动鼠标到目标位置（提高精度），使用亚像素精度
                # 先移动到接近位置
                intermediate_x = actual_x + (actual_x - current_x) * 0.8
                intermediate_y = actual_y + (actual_y - current_y) * 0.8
                
                if abs(intermediate_x - current_x) > 10 or abs(intermediate_y - current_y) > 10:
                    pyautogui.moveTo(intermediate_x, intermediate_y, duration=0.05)
                
                # 最终精确移动
                pyautogui.moveTo(actual_x, actual_y, duration=0.05, tween=pyautogui.easeInOutQuad)
                
                # 精确验证鼠标位置（使用更高精度的偏差阈值）
                final_x, final_y = pyautogui.position()
                x_error = abs(final_x - actual_x)
                y_error = abs(final_y - actual_y)
                
                # 如果位置偏差超过2像素，进行精细微调
                if x_error > 2 or y_error > 2:
                    # 计算修正方向
                    correction_x = actual_x - final_x
                    correction_y = actual_y - final_y
                    
                    # 分步微调，避免过度校正
                    steps = max(int(max(x_error, y_error) / 2), 1)  # 每步最多移动2像素
                    step_x = correction_x / steps
                    step_y = correction_y / steps
                    
                    for i in range(steps):
                        temp_x = final_x + step_x * (i + 1)
                        temp_y = final_y + step_y * (i + 1)
                        pyautogui.moveTo(temp_x, temp_y, duration=0.02)
                    
                    # 最终验证
                    final_x, final_y = pyautogui.position()
                    
                move_action = f"高精度移动后"
            else:
                final_x, final_y = current_x, current_y
                move_action = "原地"
            
            # 执行鼠标释放操作
            pyautogui.mouseUp(button=button)
            
            # 在最后时刻转换为整数，避免早期精度损失
            up_x = int(round(final_x))
            up_y = int(round(final_y))
            
            # 短暂等待，确保释放生效
            time.sleep(0.05)
            
            return f"{move_action}在坐标 ({up_x}, {up_y}) 处释放{button}键（实际位置: ({final_x}, {final_y})，移动距离: {int(distance_to_target)}像素，误差: X{int(x_error)}px, Y{int(y_error)}px）"
        except Exception as e:
            # 异常情况下的备用释放方式
            print(f"精确释放失败，使用备用方式: {str(e)}")
            backup_x = int(round(actual_x))
            backup_y = int(round(actual_y))
            pyautogui.moveTo(backup_x, backup_y)
            pyautogui.mouseUp(button=button)
            time.sleep(0.05)
            return f"使用备用方式在坐标 ({backup_x}, {backup_y}) 处释放{button}键"
    
    def wait(self, seconds):
        """
        等待工具
        """
        time.sleep(seconds)
        return f"等待{seconds}秒"
    
    def open_terminal(self, command=""):
        """
        打开终端工具
        """
        system = platform.system()
        
        try:
            if system == "Windows":
                if command:
                    subprocess.Popen(["cmd.exe", "/k", command])
                else:
                    subprocess.Popen(["cmd.exe"])
            elif system == "Linux":
                # 尝试打开不同的终端
                terminals = ["gnome-terminal", "konsole", "xterm", "terminal"]
                terminal_opened = False
                
                for terminal in terminals:
                    try:
                        if command:
                            subprocess.Popen([terminal, "-e", f"bash -c '{command}; exec bash'"])
                        else:
                            subprocess.Popen([terminal])
                        terminal_opened = True
                        break
                    except FileNotFoundError:
                        continue
                
                if not terminal_opened:
                    return "未找到可用的终端"
            elif system == "Darwin":  # macOS
                if command:
                    subprocess.Popen(["open", "-a", "Terminal", "--args", "-c", command])
                else:
                    subprocess.Popen(["open", "-a", "Terminal"])
            else:
                return "不支持的操作系统"
            
            time.sleep(0.5)
            return f"打开终端{(f'并执行命令: {command}' if command else '')}"
        except Exception as e:
            return f"打开终端失败: {str(e)}"
    
    def press_hotkey(self, x, y, hotkey):
        """
        快捷键工具
        """
        try:
            # 将比例坐标转换为实际屏幕坐标
            actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(x, y)
            
            # 确保坐标为整数（pyautogui需要整数坐标）
            actual_x = int(round(actual_x))
            actual_y = int(round(actual_y))
            
            # 点击指定位置获取焦点
            pyautogui.click(actual_x, actual_y)
            time.sleep(0.1)
            
            # 改进快捷键解析，支持多种格式（如"ctrl+a"或"ctrl + a"）
            hotkey = hotkey.replace(' ', '')  # 移除空格
            hotkey_parts = hotkey.split('+')
            
            # 标准化按键名称
            normalized_parts = []
            for part in hotkey_parts:
                part = part.lower()
                # 处理常见的按键别名
                if part == 'ctrl':
                    normalized_parts.append('ctrl')
                elif part == 'alt':
                    normalized_parts.append('alt')
                elif part == 'shift':
                    normalized_parts.append('shift')
                elif part == 'win' or part == 'windows':
                    normalized_parts.append('winleft')
                else:
                    normalized_parts.append(part)
            
            # 对系统级快捷键进行特殊处理
            if 'alt' in normalized_parts and 'f4' in normalized_parts:
                print(f"警告：检测到系统级快捷键 {hotkey}，正在安全执行...")
                time.sleep(0.2)  # 额外延迟避免误操作
            
            # 针对批量操作快捷键的特殊优化
            batch_shortcuts = ['ctrl+a', 'ctrl+c', 'ctrl+v', 'ctrl+x', 'ctrl+z', 'ctrl+y']
            normalized_hotkey = '+'.join(normalized_parts)
            if normalized_hotkey in batch_shortcuts:
                print(f"检测到批量操作快捷键 {normalized_hotkey}，正在执行...")
                # 确保焦点稳定
                time.sleep(0.1)
            
            # 执行快捷键操作
            pyautogui.hotkey(*normalized_parts)
            
            # 针对批量操作增加适当延迟，确保操作完成
            if normalized_hotkey in batch_shortcuts:
                time.sleep(0.2)
            else:
                time.sleep(0.1)
            
            return f"在坐标 ({actual_x}, {actual_y}) 处执行快捷键: {hotkey}"
        except Exception as e:
            return f"执行快捷键失败: {str(e)}"
    
    def pause_task(self, reason="用户手动操作", adapter_id=None):
        """
        暂停任务工具 - 让模型调用此工具来暂停任务执行
        
        参数:
        - reason: 暂停原因描述
        - adapter_id: 适配器ID (可选)
        """
        print(f"🔸 任务暂停: {reason}")
        print(f"请手动完成操作后继续...")
        
        # 如果有语音工具，使用语音提示
        if hasattr(self, 'voice_utils') and self.voice_utils:
            try:
                voice_message = f"检测到{reason}操作，任务已暂停。请手动完成操作后继续。"
                self.voice_utils.speak(voice_message)
                print("🔊 语音提示播放完成")
            except Exception as voice_error:
                print(f"⚠️ 语音提示播放失败: {voice_error}")
        
        # 返回暂停消息，让代理知道需要等待用户
        return f"任务因'{reason}'已暂停，等待用户手动完成操作后继续"
    
    def complete_task(self, message="任务已完成", adapter_id=None):
        """
        完成任务工具 - 让模型调用此工具来标记任务完成
        
        参数:
        - message: 完成消息描述
        - adapter_id: 适配器ID (可选)
        """
        print(f"✅ 任务完成: {message}")
        
        # 返回完成消息，让代理知道任务已完成
        return f"任务已完成: {message}"
