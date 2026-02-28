"""
JRGS - 재와니의 레트로 게임 보관소
main.py - 진입점
"""

import sys
import os

# src 폴더를 모듈 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from main_window import main

if __name__ == "__main__":
    main()
