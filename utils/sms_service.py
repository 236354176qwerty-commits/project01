#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短信服务模块 - 支持多个短信服务商
"""

import random
import string
import time
import hashlib
import requests
import logging
from datetime import datetime, timedelta
import os
import json
import hmac
import base64
from urllib.parse import quote, urlencode

logger = logging.getLogger(__name__)


def _get_redis_client():
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        return None
    try:
        import redis
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis client init failed, fallback to memory: {e}")
        return None


class SMSService:
    """短信服务基类"""
    
    # 验证码存储（生产环境建议使用Redis）
    verification_codes = {}

    redis_client = _get_redis_client()

    @staticmethod
    def _redis_key(phone: str) -> str:
        return f"sms_verification:{phone}"

    @staticmethod
    def _get_record(phone):
        if SMSService.redis_client is not None:
            try:
                raw = SMSService.redis_client.get(SMSService._redis_key(phone))
                if not raw:
                    return None
                return json.loads(raw)
            except Exception as e:
                logger.warning(f"Redis get failed, fallback to memory: {e}")

        return SMSService.verification_codes.get(phone)

    @staticmethod
    def _set_record(phone, record, expire_seconds: int):
        if SMSService.redis_client is not None:
            try:
                SMSService.redis_client.setex(
                    SMSService._redis_key(phone),
                    expire_seconds,
                    json.dumps(record, ensure_ascii=False),
                )
                return
            except Exception as e:
                logger.warning(f"Redis set failed, fallback to memory: {e}")

        SMSService.verification_codes[phone] = record

    @staticmethod
    def _del_record(phone):
        if SMSService.redis_client is not None:
            try:
                SMSService.redis_client.delete(SMSService._redis_key(phone))
                return
            except Exception as e:
                logger.warning(f"Redis delete failed, fallback to memory: {e}")

        if phone in SMSService.verification_codes:
            del SMSService.verification_codes[phone]
    
    @staticmethod
    def generate_code(length=6):
        """生成随机验证码"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def store_code(phone, code, expire_minutes=5):
        """
        存储验证码
        生产环境建议使用Redis，并设置过期时间
        注意：每次存储会覆盖该手机号的旧验证码，确保只有最新验证码有效
        """
        expire_time = datetime.now() + timedelta(minutes=expire_minutes)
        send_time = datetime.now()

        record = {
            'code': code,
            'send_time': send_time.isoformat(),
        }

        SMSService._set_record(phone, record, expire_seconds=int(expire_minutes * 60))
        logger.info(f"验证码已存储 - 手机: {phone}, 过期时间: {expire_time}")
    
    @staticmethod
    def check_code(phone, code):
        """
        检查验证码是否正确（不删除验证码）
        用于预验证，避免因重复提交导致验证码被提前删除
        返回: (是否成功, 错误消息)
        """
        stored = SMSService._get_record(phone)
        if not stored:
            return False, '验证码不存在或已过期'

        stored_code = stored.get('code')
        if stored_code != code:
            return False, '验证码错误'

        return True, '验证成功'
    
    @staticmethod
    def verify_code(phone, code):
        """
        验证验证码并删除
        返回: (是否成功, 错误消息)
        """
        # 先检查验证码
        success, message = SMSService.check_code(phone, code)
        
        if success:
            SMSService._del_record(phone)

        return success, message
    
    @staticmethod
    def can_resend(phone, interval_seconds=30):
        """
        检查是否可以重新发送
        防止频繁发送
        默认间隔30秒（与前端倒计时一致）
        """
        stored = SMSService._get_record(phone)
        if not stored:
            return True, None

        send_time_raw = stored.get('send_time')
        try:
            send_time = datetime.fromisoformat(send_time_raw) if send_time_raw else None
        except Exception:
            send_time = None

        if not send_time:
            return True, None

        elapsed = (datetime.now() - send_time).total_seconds()
        
        if elapsed < interval_seconds:
            remaining = int(interval_seconds - elapsed)
            return False, f'请在{remaining}秒后再试'
        
        return True, None


class DemoSMSProvider(SMSService):
    """
    演示用短信服务商（开发测试用）
    不实际发送短信，只在控制台打印
    """
    
    @staticmethod
    def send_verification_code(phone):
        """发送验证码（演示模式）"""
        try:
            # 检查是否可以发送
            can_send, error_msg = SMSService.can_resend(phone)
            if not can_send:
                return False, error_msg
            
            # 生成验证码
            code = SMSService.generate_code()
            
            # 存储验证码
            SMSService.store_code(phone, code)
            
            # 演示模式：只在控制台打印
            logger.info(f"【演示模式】发送验证码到 {phone}: {code}")
            print(f"\n{'='*50}")
            print(f"【短信验证码 - 演示模式】")
            print(f"手机号: {phone}")
            print(f"验证码: {code}")
            print(f"有效期: 5分钟")
            print(f"{'='*50}\n")
            
            return True, code
            
        except Exception as e:
            logger.error(f"发送验证码失败: {str(e)}")
            return False, '发送失败，请稍后重试'


class AliyunSMSProvider(SMSService):
    """
    阿里云短信服务
    文档: https://help.aliyun.com/document_detail/101414.html
    """
    
    def __init__(self, access_key_id, access_key_secret, sign_name, template_code):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.sign_name = sign_name  # 短信签名
        self.template_code = template_code  # 短信模板CODE
        self.endpoint = 'https://dysmsapi.aliyuncs.com/'
    
    @staticmethod
    def _percent_encode(value):
        return quote(str(value), safe='-_.~').replace('+', '%20').replace('*', '%2A').replace('%7E', '~')

    def _sign(self, params):
        sorted_params = sorted(params.items())
        canonicalized = '&'.join(
            f'{self._percent_encode(k)}={self._percent_encode(v)}' for k, v in sorted_params
        )
        string_to_sign = 'GET&%2F&' + self._percent_encode(canonicalized)
        key = (self.access_key_secret + '&').encode('utf-8')
        h = hmac.new(key, string_to_sign.encode('utf-8'), hashlib.sha1)
        signature = base64.b64encode(h.digest()).decode('utf-8')
        return self._percent_encode(signature)

    def send_verification_code(self, phone):
        """发送验证码（阿里云）"""
        try:
            # 检查是否可以发送
            can_send, error_msg = SMSService.can_resend(phone)
            if not can_send:
                return False, error_msg
            
            # 生成验证码
            code = SMSService.generate_code()
            
            # 构建请求参数
            params = {
                'RegionId': os.getenv('ALIYUN_SMS_REGION_ID', 'cn-hangzhou'),
                'AccessKeyId': self.access_key_id,
                'Format': 'JSON',
                'SignatureMethod': 'HMAC-SHA1',
                'SignatureNonce': str(int(time.time() * 1000)),
                'SignatureVersion': '1.0',
                'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'Version': '2017-05-25',
                'Action': 'SendSms',
                'PhoneNumbers': phone,
                'SignName': self.sign_name,
                'TemplateCode': self.template_code,
                'TemplateParam': json.dumps({'code': code}, ensure_ascii=False),
                # 其他阿里云必需参数...
            }
            
            # 发送请求
            signature = self._sign(params)
            query = urlencode({'Signature': signature, **params})
            url = f'{self.endpoint}?{query}'
            response = requests.get(url, timeout=5)
            result = response.json()
            
            # if result.get('Code') == 'OK':
            #     # 存储验证码
            #     SMSService.store_code(phone, code)
            #     logger.info(f"阿里云短信发送成功: {phone}")
            #     return True, '验证码已发送'
            # else:
            #     logger.error(f"阿里云短信发送失败: {result}")
            #     return False, '发送失败，请稍后重试'
            
            # 临时：使用演示模式
            if result.get('Code') == 'OK':
                SMSService.store_code(phone, code)
                logger.info(f"阿里云短信发送成功: {phone}")
                return True, '验证码已发送'
            else:
                logger.error(f"阿里云短信发送失败: {result}")
                return False, result.get('Message', '发送失败，请稍后重试')
            
        except Exception as e:
            logger.error(f"发送验证码失败: {str(e)}")
            return False, '发送失败，请稍后重试'


class TencentSMSProvider(SMSService):
    """
    腾讯云短信服务
    文档: https://cloud.tencent.com/document/product/382
    """
    
    def __init__(self, secret_id, secret_key, sms_sdk_app_id, sign_name, template_id):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.sms_sdk_app_id = sms_sdk_app_id
        self.sign_name = sign_name
        self.template_id = template_id
    
    def send_verification_code(self, phone):
        """发送验证码（腾讯云）"""
        try:
            # 检查是否可以发送
            can_send, error_msg = SMSService.can_resend(phone)
            if not can_send:
                return False, error_msg
            
            # 生成验证码
            code = SMSService.generate_code()
            
            # 腾讯云SMS实现...
            # 临时：使用演示模式
            logger.warning("腾讯云SMS未配置，使用演示模式")
            return DemoSMSProvider.send_verification_code(phone)
            
        except Exception as e:
            logger.error(f"发送验证码失败: {str(e)}")
            return False, '发送失败，请稍后重试'


# 默认使用演示模式
def get_sms_provider():
    """
    获取短信服务提供商
    
    可以根据环境变量或配置选择不同的服务商：
    - demo: 演示模式（开发测试）
    - aliyun: 阿里云
    - tencent: 腾讯云
    """
    import os
    
    provider_type = os.getenv('SMS_PROVIDER', 'demo').lower()
    
    if provider_type == 'aliyun':
        # 从环境变量读取配置
        access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID')
        access_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        sign_name = os.getenv('ALIYUN_SMS_SIGN_NAME')
        template_code = os.getenv('ALIYUN_SMS_TEMPLATE_CODE')
        
        if all([access_key_id, access_key_secret, sign_name, template_code]):
            return AliyunSMSProvider(access_key_id, access_key_secret, sign_name, template_code)
        else:
            logger.warning("阿里云SMS配置不完整，使用演示模式")
            return DemoSMSProvider()
    
    elif provider_type == 'tencent':
        # 从环境变量读取配置
        secret_id = os.getenv('TENCENT_SECRET_ID')
        secret_key = os.getenv('TENCENT_SECRET_KEY')
        sms_sdk_app_id = os.getenv('TENCENT_SMS_SDK_APP_ID')
        sign_name = os.getenv('TENCENT_SMS_SIGN_NAME')
        template_id = os.getenv('TENCENT_SMS_TEMPLATE_ID')
        
        if all([secret_id, secret_key, sms_sdk_app_id, sign_name, template_id]):
            return TencentSMSProvider(secret_id, secret_key, sms_sdk_app_id, sign_name, template_id)
        else:
            logger.warning("腾讯云SMS配置不完整，使用演示模式")
            return DemoSMSProvider()
    
    else:
        # 默认使用演示模式
        return DemoSMSProvider()


# 创建全局SMS服务实例
sms_provider = get_sms_provider()
