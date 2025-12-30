#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音提示工具模块
"""

import pyttsx3
import threading
import logging

class VoiceUtils:
    """
    语音提示工具类，用于在需要用户操作时生成语音告知
    """
    
    def __init__(self):
        self.engine = pyttsx3.init()
        self.voice_lock = threading.Lock()
        
        # 配置语音参数
        self._configure_voice()
    
    def _configure_voice(self):
        """
        配置语音参数
        """
        try:
            # 获取所有可用语音
            voices = self.engine.getProperty('voices')
            
            # 尝试选择中文语音
            for voice in voices:
                if 'zh' in voice.id.lower() or 'chinese' in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            
            # 设置语速 (100-200)
            self.engine.setProperty('rate', 150)
            
            # 设置音量 (0.0-1.0)
            self.engine.setProperty('volume', 0.8)
            
        except Exception as e:
            logging.error(f"配置语音参数失败: {str(e)}")
    
    def speak_async(self, text):
        """
        异步语音播放
        :param text: 要播放的文本
        """
        def speak_thread():
            with self.voice_lock:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    logging.error(f"语音播放失败: {str(e)}")
        
        thread = threading.Thread(target=speak_thread)
        thread.daemon = True
        thread.start()
    
    def speak_sync(self, text):
        """
        同步语音播放
        :param text: 要播放的文本
        """
        with self.voice_lock:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logging.error(f"语音播放失败: {str(e)}")
    
    def speak(self, text):
        """
        默认语音播放方法（异步）
        :param text: 要播放的文本
        """
        self.speak_async(text)

# 单例模式
global_voice_utils = None

def get_voice_utils():
    """
    获取语音工具实例
    """
    global global_voice_utils
    if not global_voice_utils:
        global_voice_utils = VoiceUtils()
    return global_voice_utils
