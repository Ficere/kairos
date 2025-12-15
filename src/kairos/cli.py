"""Kairos CLI - 命令行入口点"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd


def analyze():
    """kairos-analyze 命令：运行完整分析流程"""
    from kairos.futures.config import CONTRACTS, load_contracts
    from kairos.futures.display import get_daily_output_dir
    from kairos.analyzer import run_full_analysis, print_summary
    from kairos.contracts import fetch_futures_rules

    print(f"\n{'='*60}\n🚀 Kairos 自动化交易决策 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}")
    
    args = sys.argv[1:]
    if "--all" in args:
        rules = fetch_futures_rules()
        contract_ids = [f"{v}0" for v in rules.keys()] if rules else list(CONTRACTS.keys())
        print(f"模式: 全部品种 ({len(contract_ids)}个)")
    elif args:
        contract_ids = [c.upper() for c in args if not c.startswith("--")]
        print(f"模式: 指定品种 ({', '.join(contract_ids)})")
    else:
        load_contracts()
        contract_ids = list(CONTRACTS.keys())
        print(f"模式: 已配置品种 ({len(contract_ids)}个)")

    results = run_full_analysis(contract_ids)
    out_dir = get_daily_output_dir()
    pd.DataFrame(results["decisions"]).to_csv(Path(out_dir).parent / f"decisions_summary_{Path(out_dir).name}.csv", index=False)
    print_summary(results, out_dir)
    print(f"\n⚠️ 风险提示: 以上决策仅供参考，不构成投资建议")


def update_contracts():
    """kairos-update 命令：更新主力合约配置"""
    from kairos.contracts import update_contracts as do_update

    print(f"\n主力合约更新工具 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    args = sys.argv[1:]
    add_all = "--add-all" in args
    varieties = [a.upper() for a in args if not a.startswith("--")]

    if add_all:
        print("模式: 添加所有品种")
        do_update(add_all=True)
    elif varieties:
        print(f"模式: 指定品种 ({', '.join(varieties)})")
        do_update(varieties=varieties)
    else:
        print("模式: 更新已配置品种")
        do_update()


def run_web():
    """kairos-web 命令：启动 Web 应用"""
    from kairos.web import app

    print("🚀 启动 Kairos 期货分析系统 Web 应用...")
    print("   访问地址: http://127.0.0.1:8050")
    app.run(debug=True, host="0.0.0.0", port=8050)


def main():
    """kairos 主命令"""
    if len(sys.argv) < 2:
        print("Kairos - 期货交易技术分析系统")
        print("\n用法:")
        print("  kairos-analyze [品种...]    分析指定品种或全部品种")
        print("  kairos-update [品种...]     更新主力合约配置")
        print("  kairos-web                  启动 Web 应用")
        print("\n示例:")
        print("  kairos-analyze CU0 AU0      分析铜和黄金")
        print("  kairos-analyze --all        分析所有品种")
        print("  kairos-update --add-all     添加所有品种到配置")
        return
    
    cmd = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]  # 移除子命令
    
    if cmd == "analyze":
        analyze()
    elif cmd == "update":
        update_contracts()
    elif cmd == "web":
        run_web()
    else:
        print(f"未知命令: {cmd}")
        print("可用命令: analyze, update, web")


if __name__ == "__main__":
    main()

