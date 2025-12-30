#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLM代理核心模块
"""

from openai import OpenAI
import pyautogui
import platform
import time
import logging

import os

from utils.coordinate_utils import CoordinateConverter
from utils.screenshot_utils import ScreenshotUtils
from utils.tool_utils import ToolUtils
from utils.voice_utils import get_voice_utils
from utils.adapter_utils import get_adapter_utils
from model_manager import get_model_manager
from prompts.prompt_manager import PromptManager

class VLMAgent:
    """
    VLM代理类，用于与LLM交互并控制电脑
    """
    
    def __init__(self, api_key=None, model_name=None):
        """
        初始化VLM代理
        :param api_key: API密钥 (可选，如果不提供则从配置文件加载)
        :param model_name: 模型名称 (可选，如果不提供则从配置文件加载)
        """
        # 获取模型管理器
        self.model_manager = get_model_manager()
        
        # 获取视觉模型配置
        vision_config = self.model_manager.get_model_config("vision_model")
        
        # 使用提供的参数或配置文件中的参数
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self.model_manager.get_api_key("vision_model")
            
        if model_name:
            self.model_name = model_name
        else:
            self.model_name = self.model_manager.get_model_name("vision_model")
        
        # 初始化OpenAI客户端
        self.client = self.model_manager.get_client("vision_model")
        if not self.client:
            # 如果客户端未初始化，手动创建
            base_url = vision_config.get("base_url") if vision_config else "https://dashscope.aliyuncs.com/compatible-mode/v1"
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=base_url
            )
        self.messages = []
        
        # 获取屏幕分辨率
        self.screen_width, self.screen_height = pyautogui.size()
        
        # 设置pyautogui的参数
        pyautogui.FAILSAFE = True  # 启用安全模式，鼠标移到屏幕左上角会停止操作
        pyautogui.PAUSE = 0.1  # 减少操作间隔时间，提高响应速度
        
        # 初始化工具
        self.coordinate_converter = CoordinateConverter()
        self.screenshot_utils = ScreenshotUtils()
        self.tool_utils = ToolUtils(self.coordinate_converter)
        self.voice_utils = get_voice_utils()
        self.adapter_utils = get_adapter_utils()
        
        # 判断是否需要缩放截图
        self.scale_screenshot = self._should_scale_screenshot()
        
        # 操作历史记录
        self.operation_history = []
        self.last_successful_positions = {}  # 记录成功操作的坐标
        
        # 暂停/继续机制
        self.is_paused = False
        self.pause_event = None  # 由外部设置 threading.Event
        self.pause_reason = ""  # 暂停原因
        self.step_update_callback = None  # 由外部设置，用于GUI回调
        self.current_task_id = None  # 当前任务ID，用于GUI回调
        self.manual_intervention_detected = False  # 标记是否检测到需要手动干预
        
        # 初始化Prompt管理器
        try:
            self.prompt_manager = PromptManager()
            logging.info("Prompt管理器初始化成功")
        except Exception as e:
            logging.warning(f"Prompt管理器初始化失败: {e}")
            self.prompt_manager = None
    
    def record_operation(self, operation_type, position_info, success=True, result_message=""):
        """记录操作历史"""
        operation_record = {
            "type": operation_type,
            "position": position_info,
            "success": success,
            "result": result_message,
            "timestamp": time.time()
        }
        self.operation_history.append(operation_record)
        
        # 记录成功的位置用于后续参考
        if success and position_info:
            if operation_type not in self.last_successful_positions:
                self.last_successful_positions[operation_type] = []
            self.last_successful_positions[operation_type].append(position_info)
            # 只保留最近5个成功的操作位置
            self.last_successful_positions[operation_type] = self.last_successful_positions[operation_type][-5:]
    
    def check_and_handle_pause(self, step_callback, step):
        """检查暂停状态并处理手动干预"""
        # 检查是否检测到需要手动干预
        if self.manual_intervention_detected:
            self.manual_intervention_detected = False  # 重置标记
            self.handle_manual_intervention_pause(self.pause_reason, step_callback, step)
            return True
        return False
    
    def get_operation_history_summary(self):
        """获取操作历史摘要"""
        if not self.operation_history:
            return "无操作历史"
        
        recent_operations = self.operation_history[-5:]  # 最近5个操作
        summary_parts = []
        
        for op in recent_operations:
            status = "成功" if op["success"] else "失败"
            position_info = f"坐标({op['position'].get('x', 'unknown')}, {op['position'].get('y', 'unknown')})" if op["position"] else "无坐标"
            summary_parts.append(f"{op['type']}: {position_info} - {status}")
        
        return "; ".join(summary_parts)
    
    def get_similar_positions(self, operation_type, current_x, current_y, threshold=0.1):
        """查找相似的历史操作位置"""
        if operation_type not in self.last_successful_positions:
            return []
        
        similar_positions = []
        for pos in self.last_successful_positions[operation_type]:
            if "actual_x" in pos and "actual_y" in pos:
                distance = ((pos["actual_x"] - current_x) ** 2 + (pos["actual_y"] - current_y) ** 2) ** 0.5
                max_dimension = max(self.screen_width, self.screen_height)
                if distance < threshold * max_dimension:
                    similar_positions.append(pos)
        
        return similar_positions
    
    def get_screen_resolution(self):
        """
        获取屏幕分辨率
        """
        return self.screen_width, self.screen_height
    
    def _should_scale_screenshot(self):
        """
        判断是否需要缩放截图
        如果屏幕分辨率较小（如1920x1080或更小），则不缩放，使用原始分辨率
        如果屏幕分辨率较大，则缩放到1024以减少API调用数据量
        """
        max_dimension = max(self.screen_width, self.screen_height)
        return max_dimension > 1920
    
    def capture_screenshot(self):
        """
        截取当前屏幕截图
        """
        return self.screenshot_utils.capture_screenshot(self.coordinate_converter, self.scale_screenshot)
    
    def encode_image_to_base64(self, image_buffer):
        """
        将图片编码为base64字符串
        """
        return self.screenshot_utils.encode_image_to_base64(image_buffer)
    
    
    
    def clear_input(self, x, y):
        """清空指定输入框中的所有文本"""
        try:
            # 将比例坐标转换为实际屏幕坐标
            actual_x, actual_y = self.coordinate_converter.convert_proportion_to_actual(x, y)
            
            # 确保坐标为整数（pyautogui需要整数坐标）
            actual_x = int(round(actual_x))
            actual_y = int(round(actual_y))
            
            # 先点击输入框获取焦点
            pyautogui.click(actual_x, actual_y)
            time.sleep(0.5)
            
            # 使用Ctrl+A全选所有内容
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            
            # 按Delete键删除所有内容
            pyautogui.press('delete')
            time.sleep(0.2)
            
            return f"已清空坐标({x}, {y})处的输入框内容"
        except Exception as e:
            return f"清空输入框失败: {str(e)}"
    
    def parse_and_execute_tools(self, response_text):
        """
        解析并执行工具调用
        :param response_text: 模型响应文本
        :return: 工具执行结果
        """
        tool_calls = self.tool_utils.parse_tool_calls(response_text)
        if tool_calls:
            results = []
            for call in tool_calls:
                tool_name = call['name']
                args = call['arguments']
                
                try:
                    if tool_name == "mouse_click":
                        x = args.get('x', 0.5)
                        y = args.get('y', 0.5)
                        button = args.get('button', 'left')
                        clicks = args.get('clicks', 1)
                        move_first = args.get('move_first', True)
                        result = self.tool_utils.mouse_click(x, y, button, clicks, move_first=move_first)
                    elif tool_name == "type_text":
                        x = args.get('x', 0.5)
                        y = args.get('y', 0.5)
                        text = args.get('text', '')
                        result = self.type_text(x, y, text)
                    elif tool_name == "scroll_window":
                        x = args.get('x', 0.5)
                        y = args.get('y', 0.5)
                        direction = args.get('direction', 'up')
                        result = self.scroll_window(x, y, direction)
                    elif tool_name == "close_window":
                        x = args.get('x', 0.5)
                        y = args.get('y', 0.5)
                        result = self.close_window(x, y)
                    elif tool_name == "press_windows_key":
                        result = self.press_windows_key()
                    elif tool_name == "press_enter":
                        result = self.press_enter()
                    elif tool_name == "delete_text":
                        x = args.get('x', 0.5)
                        y = args.get('y', 0.5)
                        count = args.get('count', 1)
                        result = self.delete_text(x, y, count)
                    elif tool_name == "mouse_drag":
                        start_x = args.get('start_x', 0.5)
                        start_y = args.get('start_y', 0.5)
                        end_x = args.get('end_x', 0.5)
                        end_y = args.get('end_y', 0.5)
                        duration = args.get('duration', 0.5)
                        result = self.mouse_drag(start_x, start_y, end_x, end_y, duration)
                    elif tool_name == "wait":
                        seconds = args.get('seconds', 1)
                        result = self.wait(seconds)
                    elif tool_name == "open_terminal":
                        command = args.get('command', '')
                        result = self.open_terminal(command)
                    elif tool_name == "press_hotkey":
                        x = args.get('x', 0.5)
                        y = args.get('y', 0.5)
                        hotkey = args.get('hotkey', '')
                        result = self.press_hotkey(x, y, hotkey)
                    elif tool_name == "clear_input":
                        x = args.get('x', 0.5)
                        y = args.get('y', 0.5)
                        result = self.clear_input(x, y)
                    else:
                        result = f"未知工具: {tool_name}"
                    
                    results.append(result)
                except Exception as e:
                    results.append(f"执行工具 {tool_name} 时出错: {str(e)}")
            
            return "\n".join(results)
        else:
            return "未检测到工具调用"
    
    def run_task(self, task_description, max_steps=50, step_callback=None):
        """
        运行任务
        :param task_description: 任务描述
        :param max_steps: 最大执行步骤数
        :param step_callback: 步骤回调函数，用于向GUI报告每个步骤
        """
        print(f"开始执行任务: {task_description}")
        print(f"屏幕分辨率: {self.screen_width} x {self.screen_height}")
        
        # 添加系统提示词(这个提示词，需要ai修正。。。)
        # 获取操作历史和动态调整信息
        operation_history_summary = self.get_operation_history_summary()
        successful_positions_info = self.last_successful_positions if self.last_successful_positions else {}
        dynamic_adjustment_info = "如果当前操作与历史操作类型相同且位置相近，请参考上次成功位置进行微调。如果之前操作失败，请尝试调整坐标位置。"
        
        # 动态获取相关平台和系统prompt (RAG功能保持不变)
        combined_prompt = ""
        if self.prompt_manager:
            try:
                # 分析任务描述，识别关键词
                task_lower = task_description.lower()
                applicant_keywords = []
                system_keywords = []
                
                # 应用关键词检测
                if any(word in task_lower for word in ["抖音", "douyin", "短视频"]):
                    applicant_keywords.append("抖音")
                if any(word in task_lower for word in ["快手", "kuaishou"]):
                    applicant_keywords.append("快手")
                if any(word in task_lower for word in ["excel", "电子表格", "表格", "spreadsheet", "微软表格"]):
                    applicant_keywords.append("excel")
                
                # 系统关键词检测
                if any(word in task_lower for word in ["windows", "win", "微软"]):
                    system_keywords.append("Windows")
                if any(word in task_lower for word in ["linux", "ubuntu", "centos"]):
                    system_keywords.append("Linux")
                
                # 获取当前操作系统
                current_system = platform.system()
                if current_system.lower() == "windows":
                    system_keywords.append("Windows")
                elif current_system.lower() == "linux":
                    system_keywords.append("Linux")
                
                # 获取组合的prompt
                combined_prompt = self.prompt_manager.get_combined_prompt(
                    platform_keywords=applicant_keywords,
                    system_keywords=system_keywords
                )
                
                if combined_prompt:
                    print("已加载相关应用和系统专用prompt")
                else:
                    combined_prompt = ""
                    
            except Exception as e:
                print(f"获取prompt时出错: {e}")
                combined_prompt = ""
        
        # 从txt文件读取基础prompt
        try:
            current_system = platform.system().lower()
            if current_system == "windows":
                prompt_file_path = os.path.join(os.path.dirname(__file__), "prompts", "windows.txt")
            elif current_system == "linux":
                prompt_file_path = os.path.join(os.path.dirname(__file__), "prompts", "linux.txt")
            else:
                # 默认使用Windows prompt
                prompt_file_path = os.path.join(os.path.dirname(__file__), "prompts", "windows.txt")
            
            if os.path.exists(prompt_file_path):
                with open(prompt_file_path, 'r', encoding='utf-8') as f:
                    base_prompt_content = f.read()
                # 替换变量
                base_prompt_content = base_prompt_content.format(
                    screen_width=self.screen_width,
                    screen_height=self.screen_height
                )
                print(f"已从 {prompt_file_path} 加载系统专用prompt")
            else:
                print(f"Prompt文件不存在: {prompt_file_path}")
                base_prompt_content = ""
                
        except Exception as e:
            print(f"读取prompt文件时出错: {e}")
            base_prompt_content = ""
        
        system_prompt = f"""
操作历史信息：
最近操作历史: {operation_history_summary}
上次成功操作位置参考: {successful_positions_info}
动态调整建议: {dynamic_adjustment_info}
{combined_prompt}

{base_prompt_content}
        """.strip()
        
        self.messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        step = 0
        while step < max_steps:
            step += 1
            print(f"\n========== 步骤 {step} 开始 ==========")
            
            try:
                # 获取屏幕截图
                print("正在获取屏幕截图...")
                try:
                    screenshot_buffer, original_width, original_height, scaled_width, scaled_height = self.capture_screenshot()
                    base64_image = self.encode_image_to_base64(screenshot_buffer)
                    if self.scale_screenshot:
                        print(f"屏幕截图获取完成，原始尺寸: {original_width}x{original_height}, 已缩放至: {scaled_width}x{scaled_height}")
                    else:
                        print(f"屏幕截图获取完成，使用原始分辨率: {original_width}x{original_height}")
                except PermissionError as e:
                    # 屏幕截图权限错误处理
                    print(f"❌ {str(e)}")
                    
                    # 使用语音提示用户
                    try:
                        if self.voice_utils:
                            self.voice_utils.speak("屏幕截图失败，任务已暂停。请手动处理后继续。")
                            print("🔊 语音提示已播放")
                    except Exception as voice_error:
                        print(f"⚠️ 语音提示播放失败: {voice_error}")
                    
                    print("\n" + "="*50)
                    print("⏸️  任务已自动变为暂停状态")
                    print("💡 请手动处理屏幕截图问题后，任务将在任务列表中等待您继续")
                    print("="*50)
                    
                    # 记录失败操作
                    self.record_operation("screenshot", {"error": str(e)}, False, "屏幕截图失败，任务暂停")
                    
                    # 如果有步骤回调函数，通知暂停状态
                    if step_callback:
                        step_callback(f"步骤 {step}: 屏幕截图失败 - 任务暂停", "paused")
                    
                    # 抛出异常让上层处理
                    raise
                except Exception as e:
                    # 其他截图相关错误
                    print(f"❌ 屏幕截图过程中发生其他错误: {str(e)}")
                    
                    # 记录失败操作
                    self.record_operation("screenshot", {"error": str(e)}, False, "屏幕截图其他错误")
                    
                    # 抛出异常让上层处理
                    raise
                
                # 构造消息
                if step == 1:
                    content = [
                        {"type": "text", "text": f"请完成以下任务: {task_description}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                    print("任务描述: " + f"请完成以下任务: {task_description}")
                else:
                    content = [
                        {"type": "text", "text": "这是当前屏幕状态，请继续完成任务"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                    print("继续执行任务，上次操作后需要继续")
                
                self.messages.append({
                    "role": "user",
                    "content": content
                })
                
                # 记录模型调用前的消息历史
                print(f"\n模型调用前的消息历史: {len(self.messages)} 条消息")
                for i, msg in enumerate(self.messages[-3:]):  # 只显示最近3条消息
                    role = msg["role"]
                    content_preview = str(msg["content"])[:100] + "..." if len(str(msg["content"])) > 100 else str(msg["content"])
                    print(f"  消息 {len(self.messages)-3+i+1}: {role}: {content_preview}")
                
                print(f"\n正在调用模型: {self.model_name}")
                print(f"模型参数: temperature=0.3, max_tokens=1024")
                
                # 调用模型前检查暂停状态
                if self.check_and_handle_pause(step_callback, step):
                    # 暂停后已恢复，重新获取截图
                    screenshot_buffer, original_width, original_height, scaled_width, scaled_height = self.capture_screenshot()
                    base64_image = self.encode_image_to_base64(screenshot_buffer)
                    content = [
                        {"type": "text", "text": "用户已完成操作，请继续执行任务"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                    self.messages.append({
                        "role": "user",
                        "content": content
                    })
                    print(f"重新构建消息，准备再次调用模型...")
                
                # 调用模型
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    temperature=0.3,
                    max_tokens=1024
                )
                
                response_text = response.choices[0].message.content
                self.messages.append({
                    "role": "assistant",
                    "content": response_text
                })
                
                print(f"\n模型响应完成:")
                print(f"响应长度: {len(response_text)} 字符")
                print("="*60)
                print("模型响应:")
                print(response_text)
                print("="*60)
                
                # 如果有回调函数，向GUI报告当前步骤
                if step_callback:
                    # 提取模型响应中的主要操作描述
                    lines = response_text.strip().split('\n')
                    step_description = ""
                    for line in lines:
                        line = line.strip()
                        # 跳过工具调用行，只找描述性文本
                        if line and not line.startswith('<|tool_call|>') and not line.startswith('工具执行结果'):
                            step_description = line
                            break
                    
                    # 如果没有找到描述性文本，使用默认描述
                    if not step_description:
                        step_description = f"步骤 {step}"
                    
                    # 调用回调函数，向GUI报告步骤
                    step_callback(step_description, "执行中")
                
                # 将模型响应保存到全局变量中，供model_manager获取
                # 注释掉错误的导入语句，因为项目中没有modules.model_manager模块
                # import sys
                # import os
                # sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                # from modules.model_manager import ModelManager
                # ModelManager.last_vision_result = response_text
                
                # 解析并执行工具调用
                print(f"\n开始解析工具调用...")
                print(f"原始响应文本: {repr(response_text)}")
                
                tool_calls = self.tool_utils.parse_tool_calls(response_text)
                print(f"工具调用解析完成，结果: {len(tool_calls)} 个工具调用")
                
                if tool_calls:
                    print("\n检测到工具调用:")
                    for i, call in enumerate(tool_calls):
                        print(f"  工具调用 {i+1}: {call['name']}({', '.join([f'{k}={v}' for k, v in call['arguments'].items()])})")
                    
                    print(f"\n开始执行工具调用...")
                    try:
                        tool_result = self.tool_utils.execute_tool_calls(tool_calls)
                        print(f"工具执行结果:")
                        print(tool_result)
                        
                        # 检查是否有暂停或完成任务调用
                        for call in tool_calls:
                            if call['name'] == 'pause_task':
                                reason = call['arguments'].get('reason', '用户手动操作')
                                print(f"检测到暂停任务调用: {reason}")
                                
                                # 通知GUI暂停
                                if self.step_update_callback:
                                    try:
                                        self.step_update_callback("task_paused", self.current_task_id, reason)
                                    except Exception:
                                        pass
                                
                                # 等待GUI继续按钮
                                if self.pause_event:
                                    print("⏳ 等待用户操作完成后点击'继续'...")
                                    self.pause_event.wait()
                                    self.pause_event.clear()
                                    print("✅ 用户已点击继续，继续执行任务")
                                
                                # 获取新的屏幕截图，继续执行任务
                                screenshot_buffer, original_width, original_height, scaled_width, scaled_height = self.capture_screenshot()
                                base64_image = self.encode_image_to_base64(screenshot_buffer)
                                
                                content = [
                                    {"type": "text", "text": f"用户已完成{reason}操作，请继续执行任务"},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{base64_image}"
                                        }
                                    }
                                ]
                                
                                self.messages.append({
                                    "role": "user",
                                    "content": content
                                })
                                
                                # 重新发送请求给模型，继续执行
                                continue
                                
                            elif call['name'] == 'complete_task':
                                message = call['arguments'].get('message', '任务已完成')
                                print(f"检测到完成任务调用: {message}")
                                
                                # 通知GUI任务完成
                                if self.step_update_callback:
                                    try:
                                        self.step_update_callback("task_complete", self.current_task_id, f"完成: {message}")
                                    except Exception:
                                        pass
                                
                                # 任务完成，退出循环
                                print("✅ 任务已完成")
                                return f"任务已完成: {message}"
                                
                    except Exception as e:
                        print(f"工具执行失败: {str(e)}")
                        import traceback
                        print(f"错误详情: {traceback.format_exc()}")
                        tool_result = f"工具执行失败: {str(e)}"
                    
                    # 将工具执行结果添加到消息历史中
                    self.messages.append({
                        "role": "user",
                        "content": f"工具执行结果:\n{tool_result}"
                    })
                    
                    # 短暂等待，让操作生效
                    time.sleep(0.5)
                else:
                    # 没有检测到工具调用，可能任务已完成
                    print("未检测到工具调用，任务可能已完成")
                    
                    # 检查是否需要用户手动干预
                    manual_intervention_detected, intervention_type = self.detect_manual_intervention_required(response_text)
                    
                    if manual_intervention_detected:
                        print(f"检测到需要用户手动干预的操作: {intervention_type}")
                        # 设置手动干预标记，下次模型调用前会检查并暂停
                        self.manual_intervention_detected = True
                        self.pause_reason = intervention_type
                        
                        # 通知GUI暂停
                        if self.step_update_callback:
                            try:
                                self.step_update_callback("task_paused", self.current_task_id, intervention_type)
                            except Exception:
                                pass
                        
                        # 等待GUI继续按钮
                        if self.pause_event:
                            print("⏳ 等待用户操作完成后点击'继续'...")
                            self.pause_event.wait()
                            self.pause_event.clear()
                            print("✅ 用户已点击继续，继续执行任务")
                    else:
                        print("开始检查是否需要用户输入...")
                        
                        # 检查是否需要用户输入或帮助
                        need_user_input = any(keyword in response_text.lower() for keyword in ["需要用户", "请用户", "用户帮忙", "用户操作", "请输入", "请选择", "等待", "请稍候"])
                        print(f"用户输入检查结果: {need_user_input}")
                        
                        if need_user_input:
                            print("检测到需要用户操作，开始语音提示...")
                            # 生成语音提示
                            try:
                                self.voice_utils.speak_async("需要用户操作，请查看屏幕并完成操作，完成后请点击继续")
                            except Exception as e:
                                print(f"语音提示失败: {e}")
                            
                            print("需要用户输入或操作，点击GUI中的'继续'按钮继续执行...")
                            
                            # 通知GUI暂停
                            if self.step_update_callback:
                                try:
                                    self.step_update_callback("task_paused", self.current_task_id, "需要用户操作")
                                except Exception:
                                    pass
                            
                            # 等待GUI继续按钮
                            if self.pause_event:
                                print("⏳ 等待用户操作完成后点击'继续'...")
                                self.pause_event.wait()
                                self.pause_event.clear()
                                print("✅ 用户已点击继续，继续执行任务")
                            
                            print("用户确认继续，获取新的屏幕截图...")
                            # 用户确认继续后，获取当前屏幕截图
                            screenshot_buffer, original_width, original_height, scaled_width, scaled_height = self.capture_screenshot()
                            base64_image = self.encode_image_to_base64(screenshot_buffer)
                            
                            # 发送新截图给模型，继续执行任务
                            content = [
                                {"type": "text", "text": "用户已完成操作，请继续执行任务"},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                            
                            self.messages.append({
                                "role": "user",
                                "content": content
                            })
                        else:
                            # 真的没有工具调用，任务可能真的完成了
                            print("没有检测到工具调用，也没有需要用户操作的提示，任务可能已完成")
                            # 添加消息历史记录
                            self.messages.append({
                                "role": "user",
                                "content": "任务检测为完成状态，等待用户确认或继续指令"
                            })
                            # 移除重复的break语句，保持逻辑清晰
                            break
                    
            except Exception as e:
                print(f"执行步骤时发生错误: {e}")
                import traceback
                print(f"错误详情: {traceback.format_exc()}")
                # 询问用户是否继续
                return "任务执行失败,可能是缺少额度"
        
        print(f"\n任务执行完成，共执行 {step} 步")
        
        # 返回最后一个AI的回复
        for message in reversed(self.messages):
            if message["role"] == "assistant":
                return message["content"]
        
        return "任务已完成，但没有可用的回复内容"
    
    def detect_manual_intervention_required(self, model_response):
        """检测是否需要用户手动干预（登录/购买等操作）"""
        # 定义需要手动干预的关键词模式
        manual_intervention_patterns = [
            # 登录相关
            "登录", "login", "sign in", "登陆", "登录验证", "双因子验证", "2fa",
            "账号", "密码", "用户名", "user", "password", "account",
            # 支付购买相关
            "购买", "支付", "pay", "purchase", "付款", "结算", "确认支付", "支付方式",
            "订单", "下单", "立即购买", "立即支付", "购物车", "结算",
            # 安全验证相关
            "验证码", "captcha", "verification code", "验证", "安全验证", "security check",
            "拖动验证", "滑块验证", "短信验证", "邮箱验证", "人机验证",
            # 其他需要用户操作
            "授权", "permission", "权限", "同意", "accept", "确认授权",
            "实名认证", "身份验证", "银行卡", "身份证", "实名",
            "邮箱验证", "手机验证", "绑定手机", "绑定邮箱"
        ]
        
        # 将模型响应转换为小写进行匹配
        response_lower = model_response.lower()
        
        for pattern in manual_intervention_patterns:
            if pattern in response_lower:
                return True, pattern
        
        return False, None
    
    def handle_manual_intervention_pause(self, intervention_type, step_callback, step):
        """处理需要用户手动干预的暂停状态"""
        # 记录操作历史
        self.record_operation("manual_intervention", {"type": intervention_type}, False, f"检测到需要手动干预: {intervention_type}")
        
        # 使用语音提示用户
        voice_played = False
        try:
            if self.voice_utils:
                voice_message = f"检测到{intervention_type}操作，任务已暂停。请手动完成操作后继续。"
                print(f"🔊 正在播放语音提示: {voice_message}")
                self.voice_utils.speak(voice_message)
                voice_played = True
                print("🔊 语音提示播放完成")
        except Exception as voice_error:
            print(f"⚠️ 语音提示播放失败: {voice_error}")
        
        if not voice_played:
            print("⚠️ 未播放语音提示（可能没有安装语音引擎或初始化失败）")
        
        print("\n" + "="*60)
        print("⏸️  任务已自动变为暂停状态")
        print(f"💡 检测到需要手动操作: {intervention_type}")
        print("📝 请手动完成以下操作：")
        print("   1. 执行登录操作（如输入用户名、密码）")
        print("   2. 完成支付流程（如确认订单、选择支付方式）")
        print("   3. 通过安全验证（如输入验证码、完成验证）")
        print("   4. 其他需要人工操作的步骤")
        print("🎯 操作完成后，请在任务列表中点击'继续'继续执行任务")
        print("="*60)
        
        # 如果有步骤回调函数，通知暂停状态
        if step_callback:
            step_callback(f"需要手动操作: {intervention_type}", "paused")
        
        # 设置暂停状态
        self.is_paused = True
        self.pause_reason = intervention_type
        
        # 通知GUI任务已暂停
        if self.step_update_callback:
            try:
                # 传递当前任务ID和暂停原因
                self.step_update_callback("task_paused", self.current_task_id, intervention_type)
            except Exception:
                pass
        
        # 等待外部事件触发继续
        if self.pause_event:
            print("⏳ 等待用户操作完成后点击'继续'...")
            self.pause_event.wait()
            # 重置事件，为下次使用做准备
            self.pause_event.clear()
            print("✅ 用户已点击继续，任务继续执行")
        
        self.is_paused = False
        self.pause_reason = ""

