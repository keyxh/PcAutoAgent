#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLM 电脑操作工具 - 极简GUI界面
"""

import os
import sys
import time
import json
import threading
import queue
import tkinter as tk
from tkinter import ttk
import argparse
from openai import OpenAI

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vlm_agent import VLMAgent
from model_manager import get_model_manager

class MinimalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("任务列表")
        
        # 设置窗口位置在右上角
        self.position_window()
        
        # 初始化变量
        self.api_key = None
        self.agent = None
        self.task_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.current_task = None
        self.is_running = False
        self.task_steps = {}  # 存储每个任务的步骤ID列表
        
        # 创建极简界面
        self.create_minimal_widgets()
        
        # 加载API密钥
        self.load_api_key()
        
        # 启动状态更新线程
        self.update_status()
        
    def position_window(self):
        """将窗口定位到屏幕右上角"""
        # 设置窗口大小尽可能小
        window_width = 300
        window_height = 200
        
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 计算右上角位置
        x = screen_width - window_width - 10  # 距离右边缘10像素
        y = 10  # 距离顶部10像素
        
        # 设置窗口位置和大小
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 设置窗口总是在最前面
        self.root.attributes('-topmost', True)
        
    def create_minimal_widgets(self):
        """创建极简界面组件"""
        # 主框架
        self.main_frame = ttk.Frame(self.root, padding="5")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 任务列表标题
        title_label = ttk.Label(self.main_frame, text="任务列表", font=('Arial', 10, 'bold'))
        title_label.pack(pady=(0, 5))
        
        # 创建树形视图显示任务列表
        columns = ("时间", "状态", "描述")
        self.task_tree = ttk.Treeview(self.main_frame, columns=columns, show="headings", height=8)
        
        # 设置列标题和宽度
        self.task_tree.heading("时间", text="时间")
        self.task_tree.heading("状态", text="状态")
        self.task_tree.heading("描述", text="描述")
        
        self.task_tree.column("时间", width=60)
        self.task_tree.column("状态", width=60)
        self.task_tree.column("描述", width=150)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        
        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加继续按钮
        self.continue_button = ttk.Button(self.main_frame, text="继续", command=self.continue_task, state=tk.DISABLED)
        self.continue_button.pack(pady=(5, 0), fill=tk.X)
        
        # 当前任务ID
        self.current_task_id = None
        # 暂停事件
        self.pause_event = threading.Event()
        
        # 创建暂停界面（初始隐藏）
        self.create_pause_frame()
    
    def create_pause_frame(self):
        """创建暂停界面"""
        self.pause_frame = ttk.Frame(self.root, padding="20")
        
        # 暂停图标和标题
        pause_icon = ttk.Label(self.pause_frame, text="⏸️", font=('Arial', 24))
        pause_icon.pack(pady=(10, 5))
        
        self.pause_title = ttk.Label(self.pause_frame, text="任务已暂停", font=('Arial', 14, 'bold'))
        self.pause_title.pack(pady=(0, 10))
        
        # 暂停原因/提示信息
        self.pause_message = ttk.Label(self.pause_frame, text="", font=('Arial', 10), wraplength=250, justify=tk.CENTER)
        self.pause_message.pack(pady=(0, 15))
        
        # 操作指引
        guide_frame = ttk.Frame(self.pause_frame)
        guide_frame.pack(pady=(0, 15), fill=tk.X)
        
        ttk.Label(guide_frame, text="请手动完成以下操作：", font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(0, 3))
        
        self.guide_list = ttk.Label(guide_frame, text="", font=('Arial', 9), justify=tk.LEFT)
        self.guide_list.pack(anchor=tk.W)
        
        # 继续按钮
        self.pause_continue_button = ttk.Button(self.pause_frame, text="继续", command=self.continue_task, width=15)
        self.pause_continue_button.pack(pady=(10, 5))
    
    def show_pause_interface(self, reason):
        """显示暂停界面"""
        # 隐藏任务列表
        self.main_frame.pack_forget()
        
        # 更新暂停信息
        self.pause_message.config(text=reason)
        
        # 根据不同原因显示不同的操作指引
        guide_text = ""
        if "登录" in reason:
            guide_text = "1. 输入用户名和密码\n2. 完成验证码（如有）\n3. 点击登录按钮"
        elif "支付" in reason:
            guide_text = "1. 确认订单信息\n2. 选择支付方式\n3. 完成支付"
        elif "验证" in reason:
            guide_text = "1. 查看验证码\n2. 输入验证码\n3. 完成验证"
        else:
            guide_text = "1. 执行所需的手动操作\n2. 确认操作已完成\n3. 点击下方继续按钮"
        
        self.guide_list.config(text=guide_text)
        
        # 保存当前窗口大小（任务列表界面）
        if not hasattr(self, '_original_geometry'):
            self._original_geometry = self.root.geometry()
        
        # 调整窗口大小以适应暂停界面内容（更大的窗口）
        self.root.geometry("360x350")
        
        # 显示暂停界面
        self.pause_frame.pack(fill=tk.BOTH, expand=True)
        
        # 确保窗口在可视范围内
        self.root.lift()
        self.root.attributes('-topmost', True)
    
    def hide_pause_interface(self):
        """隐藏暂停界面，恢复任务列表"""
        self.pause_frame.pack_forget()
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 恢复原始窗口大小
        if hasattr(self, '_original_geometry'):
            self.root.geometry(self._original_geometry)
    
    def step_update_callback(self, msg_type, task_id, message=None):
        """处理来自VLMAgent的状态更新回调"""
        if msg_type == "task_paused":
            self.status_queue.put(("task_paused", task_id, message or ""))
            self.root.after(0, lambda: self.show_pause_interface(message or "需要用户操作"))
        
    def load_api_key(self):
        """从 model_config.json 加载配置"""
        config_file = "model_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 从 vision_model 或 classification_model 获取 api_key
                    vision_config = config.get("vision_model", {})
                    classification_config = config.get("classification_model", {})
                    api_key = vision_config.get("apikey") or classification_config.get("apikey")
                    if api_key:
                        self.api_key = api_key
            except Exception:
                pass
    
    def continue_task(self):
        """继续执行暂停的任务"""
        # 隐藏暂停界面，恢复任务列表
        self.hide_pause_interface()
        
        # 触发暂停事件，通知代理继续执行
        if self.pause_event:
            self.pause_event.set()
        
        # 禁用继续按钮
        self.continue_button.config(state=tk.DISABLED)
        
        # 更新任务状态为执行中
        if self.current_task_id:
            values = list(self.task_tree.item(self.current_task_id)["values"])
            values[1] = "执行中"
            self.task_tree.item(self.current_task_id, values=values)
    
    def notify_paused(self, task_id, reason):
        """通知任务已暂停"""
        self.status_queue.put(("task_paused", task_id, reason))
    
    def extract_and_send_step(self, task_id, message, task_description):
        """提取关键步骤信息并添加到GUI"""
        step_info = self.extract_step_info_with_ai(message, task_description)
        if step_info:
            self.status_queue.put(("model_response", task_id, step_info))
    
    def extract_step_info_with_ai(self, message, task_description):
        """使用AI提取关键步骤信息"""
        try:
            # 获取模型管理器
            model_manager = get_model_manager()
            
            # 获取分类模型客户端
            client = model_manager.get_client("classification_model")
            if not client:
                # 如果客户端未初始化，手动创建
                classification_config = model_manager.get_model_config("classification_model")
                api_key = model_manager.get_api_key("classification_model")
                base_url = classification_config.get("base_url") if classification_config else "https://dashscope.aliyuncs.com/compatible-mode/v1"
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
            
            # 获取模型名称
            model_name = model_manager.get_model_name("classification_model")
            
            # 构造提示词 - 简化版
            prompt = f"""
任务：{task_description}

请用一句话描述当前AI正在做什么，不超过20个字。
只返回描述，不要返回任务完成状态。

AI响应：
{message}

当前执行：
"""
            
            # 调用API
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 提取响应
            step_info = response.choices[0].message.content.strip()
            
            # 如果AI返回"无"或空内容，返回None
            if not step_info or step_info == "无" or step_info.lower() == "none":
                return None
                
            # 返回提取的步骤信息
            return step_info
            
        except Exception as e:
            # 如果API调用失败，返回None
            print(f"提取步骤信息失败: {e}")
            return None
    
    def extract_step_info(self, message):
        """从模型响应中提取关键步骤信息"""
        # 转换为小写便于匹配
        lower_msg = message.lower()
        
        # 定义关键动作关键词
        action_keywords = [
            "打开", "搜索", "点击", "输入", "关闭", "切换", "启动", "运行", "执行", "找到", "选择", "确认", "访问", "进入", "导航",
            "open", "search", "click", "type", "close", "switch", "start", "run", "execute", "find", "select", "confirm", "visit", "enter", "navigate"
        ]
        
        # 定义步骤指示词
        step_indicators = [
            "首先", "然后", "接下来", "之后", "最后", "现在", "我需要", "我将", "第一步", "第二步", "第三步",
            "first", "then", "next", "after", "finally", "now", "i need to", "i will", "step 1", "step 2", "step 3"
        ]
        
        # 定义目标关键词
        target_keywords = [
            "浏览器", "网页", "网站", "搜索", "链接", "地址", "url", "tab", "窗口",
            "browser", "web", "website", "search", "link", "address", "url", "tab", "window"
        ]
        
        # 检查是否包含步骤指示词
        for indicator in step_indicators:
            if indicator in lower_msg:
                # 提取包含指示词的句子
                sentences = message.split("。")
                for sentence in sentences:
                    if indicator in sentence.lower():
                        # 清理并返回步骤信息
                        step = sentence.strip()
                        if step and len(step) > 5:  # 确保有意义的步骤
                            return step[:50] + "..." if len(step) > 50 else step
        
        # 检查是否包含动作+目标的组合
        for action in action_keywords:
            if action in lower_msg:
                for target in target_keywords:
                    if target in lower_msg:
                        # 提取包含动作和目标的句子
                        sentences = message.split("。")
                        for sentence in sentences:
                            if action in sentence.lower() and target in sentence.lower():
                                # 清理并返回步骤信息
                                step = sentence.strip()
                                if step and len(step) > 5:
                                    return step[:50] + "..." if len(step) > 50 else step
        
        # 检查是否包含关键动作
        for keyword in action_keywords:
            if keyword in lower_msg:
                # 提取包含关键词的句子或短语
                sentences = message.split("。")
                for sentence in sentences:
                    if keyword in sentence.lower():
                        # 清理并返回步骤信息
                        step = sentence.strip()
                        if step and len(step) > 5:  # 确保有意义的步骤
                            return step[:50] + "..." if len(step) > 50 else step
        
        # 如果没有找到明确的动作，尝试提取第一句话
        sentences = message.split("。")
        if sentences and len(sentences[0].strip()) > 10:
            first_sentence = sentences[0].strip()
            return first_sentence[:50] + "..." if len(first_sentence) > 50 else first_sentence
        
        return None
    
    def execute_task(self, task_description):
        """执行任务"""
        if not self.api_key:
            return
        
        # 添加任务到队列
        self.task_queue.put(task_description)
        
        # 如果没有正在运行的任务，启动新线程执行
        if not self.is_running:
            threading.Thread(target=self.task_worker, daemon=True).start()
    
    def task_worker(self):
        """任务执行工作线程"""
        self.is_running = True
        
        while True:
            try:
                # 从队列获取任务，设置超时避免无限等待
                try:
                    task_description = self.task_queue.get(timeout=0.1)
                except queue.Empty:
                    # 队列为空，退出工作线程
                    break
                
                # 添加任务到树形视图
                task_id = self.task_tree.insert("", tk.END, values=(
                    time.strftime("%H:%M:%S"),
                    "执行中",
                    task_description[:30] + "..." if len(task_description) > 30 else task_description
                ))
                
                # 存储当前任务ID
                self.current_task_id = task_id
                # 存储当前任务的步骤ID列表
                self.task_steps[task_id] = [task_id]
                # 存储当前任务的暂停事件
                self.current_pause_event = self.pause_event
                
                try:
                    # 初始化代理
                    if not self.agent:
                        self.agent = VLMAgent()  # 不再需要传递api_key，因为VLMAgent会从配置中加载
                    
                    # 设置回调和事件
                    self.agent.step_update_callback = self.step_update_callback
                    self.agent.pause_event = self.pause_event
                    self.agent.current_task_id = task_id
                    self.agent.is_paused = False
                    
                    # 使用更安全的方法捕获print输出
                    import builtins
                    original_print = builtins.print
                    
                    def gui_print(*args, **kwargs):
                        # 在控制台输出
                        original_print(*args, **kwargs)
                        
                        # 将模型响应发送到GUI
                        message = " ".join(map(str, args))
                        if message and not message.startswith("--- 步骤") and not message.startswith("检测到工具调用") and not message.startswith("工具执行结果"):
                            # 使用AI提取关键步骤信息
                            threading.Thread(target=self.extract_and_send_step, args=(task_id, message, task_description), daemon=True).start()
                    
                    # 临时替换print函数
                    builtins.print = gui_print
                    
                    try:
                        self.agent.run_task(task_description, max_steps=50)
                        self.status_queue.put(("task_complete", task_id, "完成"))
                    except Exception as e:
                        self.status_queue.put(("task_complete", task_id, f"失败: {str(e)}"))
                    finally:
                        # 恢复原始print方法
                        builtins.print = original_print
                        
                except Exception as e:
                    self.status_queue.put(("task_complete", task_id, f"失败: {str(e)}"))
                
            except Exception:
                break
        
        self.is_running = False
    
    def update_status(self):
        """更新状态"""
        try:
            while True:
                try:
                    # 从状态队列获取消息，不阻塞
                    msg_type, *args = self.status_queue.get_nowait()
                    
                    if msg_type == "task_complete":
                        task_id, status = args
                        # 更新任务状态
                        values = list(self.task_tree.item(task_id)["values"])
                        values[1] = status
                        self.task_tree.item(task_id, values=values)
                        
                        # 禁用继续按钮
                        self.continue_button.config(state=tk.DISABLED)
                        
                        # 任务完成后，根据状态决定延迟时间
                        if "完成" in status:
                            # 成功完成任务，2秒后关闭
                            self.root.after(2000, self.root.quit)
                        elif "失败" in status:
                            # 任务失败，5秒后关闭，给用户时间查看错误
                            self.root.after(5000, self.root.quit)
                        
                    elif msg_type == "task_paused":
                        task_id, reason = args
                        # 更新任务状态为暂停
                        values = list(self.task_tree.item(task_id)["values"])
                        values[1] = "暂停"
                        self.task_tree.item(task_id, values=values)
                        
                        # 启用继续按钮
                        self.continue_button.config(state=tk.NORMAL)
                        
                    elif msg_type == "model_response":
                        task_id, response = args
                        # 为每个步骤创建新的条目
                        step_id = self.task_tree.insert("", tk.END, values=(
                            time.strftime("%H:%M:%S"),
                            "执行中",
                            response
                        ))
                        # 将步骤ID添加到当前任务的步骤列表中
                        if task_id in self.task_steps:
                            self.task_steps[task_id].append(step_id)
                        
                        # 自动滚动到底部，显示最新步骤
                        self.task_tree.see(step_id)
                        
                except queue.Empty:
                    break
        except Exception:
            pass
        
        # 每100ms更新一次
        self.root.after(100, self.update_status)

def main():
    parser = argparse.ArgumentParser(description="VLM 电脑操作工具")
    parser.add_argument("--task", type=str, help="任务描述")
    args = parser.parse_args()
    
    root = tk.Tk()
    app = MinimalGUI(root)
    
    # 如果有命令行任务，执行它
    if args.task:
        # 延迟执行，确保GUI已初始化
        root.after(1000, lambda: app.execute_task(args.task))
    
    root.mainloop()

if __name__ == "__main__":
    main()