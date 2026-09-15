#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import sys

def check_creo_connection():
    """Проверка подключения к Creo через CREOSON"""
    try:
        # Попробуем выполнить команду connection:is_creo_running
        cmd = [
            "curl", 
            "--data-binary", 
            "@data/req/connection_is_creo_running.json",
            "http://localhost:11434/api/generate",
            "-H", 
            "Content-Type: application/json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print("Результат выполнения команды:")
        print(result.stdout)
        if result.stderr:
            print("Ошибки:")
            print(result.stderr)
            
        return True
    except Exception as e:
        print(f"Ошибка при проверке подключения к Creo: {e}")
        return False

if __name__ == "__main__":
    check_creo_connection()