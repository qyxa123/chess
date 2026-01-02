"""
启动Dashboard服务
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dashboard.app import app
except ImportError:
    print("错误: Dashboard模块未找到")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
    print("并确保dashboard/目录存在")
    sys.exit(1)

if __name__ == '__main__':
    import webbrowser
    import threading
    
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:5173')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("=" * 60)
    print("🎯 OTBReview Dashboard")
    print("=" * 60)
    print(f"访问地址: http://127.0.0.1:5173")
    print(f"Runs目录: {project_root / 'runs'}")
    print("=" * 60)
    print("按 Ctrl+C 停止服务")
    print("=" * 60)
    
    try:
        app.run(host='127.0.0.1', port=5173, debug=False)
    except KeyboardInterrupt:
        print("\n服务已停止")
