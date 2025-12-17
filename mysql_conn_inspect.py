#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 连接占用检查脚本

功能：
1. 汇总各客户端(设备/IP) + 用户的连接数和 Sleep 连接数；
2. 输出每条连接的详细信息（客户端、解析到的设备名、用户、数据库、状态、命令、执行时间、当前语句等）。

使用前请根据实际情况修改 DB_CONFIG 中的连接参数。
需要账号具备 PROCESS 权限才能访问 information_schema.PROCESSLIST。
"""

import mysql.connector
from mysql.connector import Error
import socket
from textwrap import shorten

# 根据你的实际情况填写
DB_CONFIG = {
    "host": "127.0.0.1",   # MySQL 服务器地址
    "port": 3306,           # 端口
    "user": "root",       # 有 PROCESS 权限的账号
    "password": "your_password",  # 密码
    # 不需要指定 database，只查全局连接
}


def resolve_hostname(ip_or_host: str) -> str:
    """尝试把 IP/主机解析成设备名；失败则返回原值。"""
    if not ip_or_host:
        return ""
    try:
        if ip_or_host in ("localhost", "127.0.0.1", "::1"):
            return socket.gethostname()
        return socket.gethostbyaddr(ip_or_host)[0]
    except Exception:
        return ip_or_host


def print_summary(cursor):
    """输出按客户端和用户汇总的连接情况。"""
    query = """
    SELECT
        SUBSTRING_INDEX(host, ':', 1) AS client_host,
        user,
        COUNT(*) AS conn_count,
        SUM(CASE WHEN command = 'Sleep' THEN 1 ELSE 0 END) AS sleep_count
    FROM information_schema.PROCESSLIST
    GROUP BY client_host, user
    ORDER BY conn_count DESC;
    """

    cursor.execute(query)

    print("\n=== 连接汇总（按客户端 + 用户） ===")
    print(f"{'ClientHost':<20} {'DeviceName':<40} {'User':<16} {'Total':<8} {'Sleep':<8}")
    print("-" * 100)

    for client_host, user, conn_count, sleep_count in cursor:
        device_name = resolve_hostname(client_host or "")
        print(f"{(client_host or ''):<20} {device_name:<40} {user:<16} {conn_count:<8} {sleep_count:<8}")


def print_details(cursor, max_rows: int = 500):
    """输出详细连接列表。"""
    query = """
    SELECT
        id,
        user,
        host,
        db,
        command,
        time,
        state,
        info
    FROM information_schema.PROCESSLIST
    ORDER BY time DESC
    LIMIT %s;
    """

    cursor.execute(query, (max_rows,))

    print("\n=== 详细连接列表（按执行时间降序，最多 %d 条） ===" % max_rows)
    header = f"{'Id':<6} {'ClientHost':<20} {'DeviceName':<40} {'User':<16} {'DB':<16} {'Cmd':<10} {'Time':<6} {'State':<20} {'Info'}"
    print(header)
    print("-" * len(header))

    for row in cursor:
        pid, user, host, db, command, time_val, state, info = row
        client_host = (host or '').split(':', 1)[0]
        device_name = resolve_hostname(client_host or "")

        info_short = shorten(info or "", width=80, placeholder="...")
        state_short = shorten(state or "", width=20, placeholder="...")

        print(f"{pid:<6} {client_host:<20} {device_name:<40} {user:<16} {str(db or ''):<16} {command:<10} {str(time_val or ''):<6} {state_short:<20} {info_short}")


def main():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print_summary(cursor)

        # 重新创建游标以避免影响上一个查询的结果集
        cursor.close()
        cursor = conn.cursor()

        print_details(cursor, max_rows=500)

    except Error as e:
        print(f"[ERROR] MySQL 连接或查询失败: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn and conn.is_connected():
                conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
