#!/usr/bin/env python3
"""예전 명령을 위한 안내: 뉴스를 포함한 사이트 전체 빌드는 _app/build.py 가 맡는다."""
import os, runpy, sys
sys.argv = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_app", "build.py")] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
