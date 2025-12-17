#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武术赛事管理系统 - 验证码生成工具
"""

import random
import string
from PIL import Image, ImageDraw, ImageFont
import io
import os

class CaptchaGenerator:
    """验证码生成器"""
    
    def __init__(self, width=120, height=48):
        self.width = width
        self.height = height
        self.font_size = 28
        
    def generate_text(self, length=4):
        """生成随机验证码文本"""
        # 使用数字和大写字母，避免容易混淆的字符
        chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        return ''.join(random.choice(chars) for _ in range(length))
    
    def generate_image(self, text):
        """生成验证码图片"""
        # 创建图片
        image = Image.new('RGB', (self.width, self.height), color='white')
        draw = ImageDraw.Draw(image)
        
        # 尝试加载字体，如果失败则使用默认字体
        try:
            # 尝试使用系统字体
            font_paths = [
                'C:/Windows/Fonts/arial.ttf',
                'C:/Windows/Fonts/calibri.ttf',
                '/System/Library/Fonts/Arial.ttf',  # macOS
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
            ]
            
            font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, self.font_size)
                    break
            
            if font is None:
                font = ImageFont.load_default()
                
        except Exception:
            font = ImageFont.load_default()
        
        # 添加背景噪点
        for _ in range(50):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill=(random.randint(100, 200), 
                                   random.randint(100, 200), 
                                   random.randint(100, 200)))
        
        # 绘制文字
        text_width = draw.textlength(text, font=font) if hasattr(draw, 'textlength') else len(text) * 15
        text_height = self.font_size
        
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2
        
        # 为每个字符添加随机颜色和位置偏移
        char_width = text_width // len(text)
        for i, char in enumerate(text):
            char_x = x + i * char_width + random.randint(-3, 3)
            char_y = y + random.randint(-3, 3)
            color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
            draw.text((char_x, char_y), char, font=font, fill=color)
        
        # 添加干扰线
        for _ in range(3):
            start = (random.randint(0, self.width), random.randint(0, self.height))
            end = (random.randint(0, self.width), random.randint(0, self.height))
            color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))
            draw.line([start, end], fill=color, width=1)
        
        return image
    
    def generate(self):
        """生成验证码文本和图片"""
        text = self.generate_text()
        image = self.generate_image(text)
        
        # 将图片转换为字节流
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return text, img_buffer.getvalue()

# 全局验证码生成器实例
captcha_generator = CaptchaGenerator()
