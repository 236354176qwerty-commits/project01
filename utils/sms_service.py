#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短信服务模块 - 支持多个短信服务商
"""

import random
import string
import time
import logging
from datetime import datetime, timedelta
import os
import json

from alibabacloud_dypnsapi20170525.client import Client as Dypnsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dypnsapi20170525 import models as dypnsapi_20170525_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
from config import config as config_map

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


class AliyunSMSProvider(SMSService):
    """
    阿里云短信验证服务（Dypnsapi）
    使用阿里云官方 Python SDK 调用 SendSmsVerifyCode / CheckSmsVerifyCode。
    """

    def __init__(self, access_key_id, access_key_secret, sign_name, template_code):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.sign_name = sign_name  # 短信签名
        self.template_code = template_code  # 短信模板CODE

        env_name = os.environ.get('APP_ENV', 'default').lower()
        config_cls = config_map.get(env_name, config_map['default'])

        self.endpoint = getattr(config_cls, 'ALIYUN_DYPN_ENDPOINT', 'dypnsapi.aliyuncs.com')
        self.scheme_name = getattr(config_cls, 'ALIYUN_SMS_SCHEME_NAME', None)
        self.interval = getattr(config_cls, 'ALIYUN_SMS_INTERVAL', 60)
        self.valid_time = getattr(config_cls, 'ALIYUN_SMS_VALID_TIME', 300)
        self.country_code = getattr(config_cls, 'ALIYUN_SMS_COUNTRY_CODE', 'cn')

        self._client = None

    def _get_client(self):
        if self._client is None:
            config = open_api_models.Config(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret,
            )
            config.endpoint = self.endpoint
            self._client = Dypnsapi20170525Client(config)
        return self._client

    def send_verification_code(self, phone):
        """使用阿里云短信验证服务发送验证码"""
        try:
            client = self._get_client()

            valid_minutes = 5
            try:
                if self.valid_time:
                    valid_minutes = max(1, int(self.valid_time // 60))
            except Exception:
                valid_minutes = 5

            template_param = json.dumps({
                "code": "##code##",
                "min": str(valid_minutes),
            }, ensure_ascii=False)

            kwargs = {
                "phone_number": phone,
                "sign_name": self.sign_name,
                "template_code": self.template_code,
                "interval": self.interval,
                "valid_time": self.valid_time,
                "template_param": template_param,
                "code_type": 1,
                "code_length": 6,
            }
            if self.scheme_name:
                kwargs["scheme_name"] = self.scheme_name

            request = dypnsapi_20170525_models.SendSmsVerifyCodeRequest(**kwargs)
            runtime = util_models.RuntimeOptions()

            response = client.send_sms_verify_code_with_options(request, runtime)
            body = response.body

            code_value = getattr(body, 'code', None) or getattr(body, 'Code', None)
            if code_value == 'OK':
                logger.info("阿里云短信验证服务发送成功: %s, response=%s", phone, body)
                return True, '验证码已发送'

            message = getattr(body, 'message', None) or getattr(body, 'Message', None) or '发送失败，请稍后重试'
            logger.error("阿里云短信验证服务发送失败: %s, code=%s, message=%s", phone, code_value, message)
            return False, message

        except Exception as e:
            logger.error("发送验证码失败: %s", str(e))
            return False, '发送失败，请稍后重试'

    def verify_code(self, phone, code):
        """使用阿里云短信验证服务校验验证码"""
        try:
            client = self._get_client()

            kwargs = {
                "phone_number": phone,
                "verify_code": code,
                "country_code": self.country_code,
            }
            if self.scheme_name:
                kwargs["scheme_name"] = self.scheme_name

            request = dypnsapi_20170525_models.CheckSmsVerifyCodeRequest(**kwargs)
            runtime = util_models.RuntimeOptions()

            response = client.check_sms_verify_code_with_options(request, runtime)
            body = response.body

            code_value = getattr(body, 'code', None) or getattr(body, 'Code', None)
            if code_value == 'OK':
                logger.info("阿里云短信验证服务校验成功: %s, response=%s", phone, body)
                return True, '验证成功'

            message = getattr(body, 'message', None) or getattr(body, 'Message', None) or '验证码验证失败'
            logger.warning("阿里云短信验证服务校验失败: %s, code=%s, message=%s", phone, code_value, message)
            return False, message

        except Exception as e:
            logger.error("验证码验证失败: %s", str(e))
            return False, '验证码验证失败，请稍后重试'


def get_sms_provider():
    """
    获取短信服务提供商
    
    可以根据环境变量或配置选择不同的服务商：
    - demo: 演示模式（开发测试）
    - aliyun: 阿里云
    """
    import os

    env_name = os.environ.get('APP_ENV', 'default').lower()
    config_cls = config_map.get(env_name, config_map['default'])

    provider_type = getattr(config_cls, 'SMS_PROVIDER', 'aliyun').lower()

    # 从配置类读取（底层可由 .env / 环境变量或硬编码提供）
    access_key_id = getattr(config_cls, 'ALIYUN_ACCESS_KEY_ID', None)
    access_key_secret = getattr(config_cls, 'ALIYUN_ACCESS_KEY_SECRET', None)
    sign_name = getattr(config_cls, 'ALIYUN_SMS_SIGN_NAME', None)
    template_code = getattr(config_cls, 'ALIYUN_SMS_TEMPLATE_CODE', None)

    if not all([access_key_id, access_key_secret, sign_name, template_code]):
        missing = []
        if not access_key_id:
            missing.append('ALIYUN_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_ID')
        if not access_key_secret:
            missing.append('ALIYUN_ACCESS_KEY_SECRET / ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        if not sign_name:
            missing.append('ALIYUN_SMS_SIGN_NAME')
        if not template_code:
            missing.append('ALIYUN_SMS_TEMPLATE_CODE')

        print("阿里云SMS配置不完整，缺少: " + ", ".join(missing))
        logger.error(
            "阿里云SMS配置不完整，请检查环境变量: "
            "ALIYUN_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_ID, "
            "ALIYUN_ACCESS_KEY_SECRET / ALIBABA_CLOUD_ACCESS_KEY_SECRET, "
            "ALIYUN_SMS_SIGN_NAME, ALIYUN_SMS_TEMPLATE_CODE"
        )
        raise RuntimeError("阿里云SMS配置不完整，无法初始化短信服务")

    if provider_type != 'aliyun':
        logger.warning("SMS_PROVIDER 非 aliyun，已强制使用阿里云短信验证服务")

    return AliyunSMSProvider(access_key_id, access_key_secret, sign_name, template_code)


# 创建全局SMS服务实例
sms_provider = get_sms_provider()
