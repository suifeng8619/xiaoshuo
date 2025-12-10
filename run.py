#!/usr/bin/env python3
"""
仙途 - 文字修仙游戏
启动入口
"""
import argparse
import os
import sys
from pathlib import Path

# 确保能找到engine模块
sys.path.insert(0, str(Path(__file__).parent))

from engine import Game


def main():
    parser = argparse.ArgumentParser(description='仙途 - 文字修仙游戏')
    parser.add_argument('--mock', action='store_true',
                       help='使用模拟AI（测试用，不消耗API）')
    parser.add_argument('--api-key', type=str,
                       help='Anthropic API密钥（也可通过环境变量ANTHROPIC_API_KEY设置）')
    parser.add_argument('--data-dir', type=str, default='data',
                       help='数据目录路径')
    parser.add_argument('--config-dir', type=str, default='config',
                       help='配置目录路径')

    args = parser.parse_args()

    # 切换到脚本所在目录
    os.chdir(Path(__file__).parent)

    # 检查API密钥
    api_key = args.api_key or os.getenv('ANTHROPIC_API_KEY')
    if not api_key and not args.mock:
        print("=" * 50)
        print("警告：未设置API密钥！")
        print()
        print("请通过以下方式之一设置API密钥：")
        print("1. 设置环境变量: export ANTHROPIC_API_KEY='your-key'")
        print("2. 使用参数: python run.py --api-key 'your-key'")
        print()
        print("获取API密钥: https://console.anthropic.com/")
        print()
        print("或者使用 --mock 参数进行测试（不消耗API）")
        print("=" * 50)
        print()

        choice = input("是否使用模拟模式进行测试？(y/n): ").strip().lower()
        if choice == 'y':
            args.mock = True
        else:
            sys.exit(1)

    try:
        game = Game(
            data_dir=args.data_dir,
            config_dir=args.config_dir,
            use_mock_ai=args.mock,
            api_key=api_key
        )
        game.start()
    except KeyboardInterrupt:
        print("\n\n游戏已退出。")
    except Exception as e:
        print(f"\n发生错误: {e}")
        raise


if __name__ == '__main__':
    main()
