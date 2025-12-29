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


def regenerate_prompt():
    """kairos-regenerate-prompt 命令：从已有分析结果重新生成 Deep Research 提示词"""
    from kairos.prompt_generator import regenerate_prompt_from_file

    args = sys.argv[1:]

    # 检查是否需要显示帮助
    if "--help" in args or "-h" in args:
        print("\n🔄 Deep Research 提示词重新生成工具")
        print("\n用法:")
        print("  kairos-regenerate-prompt                    # 使用最新分析结果")
        print("  kairos-regenerate-prompt --date 2025-12-15  # 指定日期")
        print("  kairos-regenerate-prompt --force            # 强制覆盖已存在文件")
        print("  kairos-regenerate-prompt --date 2025-12-15 --force")
        print("\n说明:")
        print("  从已有的分析结果文件重新生成 Deep Research 提示词")
        print("  适用于调试模板或基于历史数据重新生成提示词")
        print("\n参数:")
        print("  --date DATE    指定日期 (格式: YYYY-MM-DD)")
        print("  --force, -f    强制覆盖已存在的文件")
        print("  --help, -h     显示此帮助信息")
        return

    print(f"\n{'='*60}")
    print("🔄 Deep Research 提示词重新生成工具")
    print(f"{'='*60}\n")

    date_str = None
    force = False

    # 解析参数
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--date" and i + 1 < len(args):
            date_str = args[i + 1]
            i += 2
        elif arg == "--force" or arg == "-f":
            force = True
            i += 1
        elif arg.startswith("--"):
            print(f"❌ 未知参数: {arg}")
            print("   使用 --help 查看帮助信息")
            return
        else:
            i += 1

    # 执行重新生成
    result = regenerate_prompt_from_file(date_str, force)

    if result:
        print(f"\n💡 提示: 可以将生成的文件内容复制到 ChatGPT/Claude 进行深度分析")
    else:
        print(f"\n❌ 生成失败")


def run_perplexity():
    """kairos-perplexity 命令：调用 Perplexity API 进行宏观面分析"""
    from kairos.perplexity_client import (
        run_perplexity_analysis,
        get_latest_prompt_file,
        get_prompt_file_by_date,
        check_csv_exists,
    )

    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print("\n🔮 Perplexity 宏观面分析工具")
        print("\n用法:")
        print("  kairos-perplexity                           # 使用最新提示词")
        print("  kairos-perplexity --date 2025-12-15         # 指定日期")
        print("  kairos-perplexity --prompt-file PATH        # 指定提示词文件")
        print("  kairos-perplexity --force                   # 强制覆盖已存在的 CSV")
        print("\n说明:")
        print("  调用 Perplexity API 进行宏观面和基本面分析")
        print("  基于 Deep Research 提示词生成交易建议 CSV 文件")
        print("\n参数:")
        print("  --date DATE         指定日期 (格式: YYYY-MM-DD)")
        print("  --prompt-file PATH  直接指定提示词文件路径")
        print("  --force, -f         强制覆盖已存在的 CSV 文件")
        print("  --help, -h          显示此帮助信息")
        print("\n环境变量:")
        print("  PERPLEXITY_API_KEY  Perplexity API 密钥（必需）")
        return

    print(f"\n{'='*60}")
    print("🔮 Perplexity 宏观面分析工具")
    print(f"{'='*60}\n")

    date_str, prompt_file, force = None, None, False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--date" and i + 1 < len(args):
            date_str = args[i + 1]
            i += 2
        elif arg == "--prompt-file" and i + 1 < len(args):
            prompt_file = args[i + 1]
            i += 2
        elif arg in ("--force", "-f"):
            force = True
            i += 1
        elif arg.startswith("--"):
            print(f"❌ 未知参数: {arg}")
            print("   使用 --help 查看帮助信息")
            return
        else:
            i += 1

    # 确定提示词文件
    if prompt_file:
        prompt_path = Path(prompt_file)
        if not prompt_path.exists():
            print(f"❌ 提示词文件不存在: {prompt_file}")
            return
        # 从文件名提取日期
        import re
        match = re.search(r"(\d{4}-\d{2}-\d{2})", prompt_path.name)
        date_str = match.group(1) if match else datetime.now().strftime("%Y-%m-%d")
    elif date_str:
        prompt_path = get_prompt_file_by_date(date_str)
        if not prompt_path:
            print(f"❌ 未找到日期 {date_str} 的提示词文件")
            print(f"   请先运行 kairos-analyze 或 kairos-regenerate-prompt")
            return
    else:
        prompt_path = get_latest_prompt_file()
        if not prompt_path:
            print("❌ 未找到任何 Deep Research 提示词文件")
            print("   请先运行 kairos-analyze --all 生成提示词")
            return
        import re
        match = re.search(r"(\d{4}-\d{2}-\d{2})", prompt_path.name)
        date_str = match.group(1) if match else datetime.now().strftime("%Y-%m-%d")
        print(f"📅 使用最新提示词: {prompt_path.name}")

    # 检查 CSV 是否已存在
    if check_csv_exists(date_str) and not force:
        resp = input(f"⚠️  CSV 文件已存在，是否覆盖? (y/N): ").strip().lower()
        if resp not in ("y", "yes"):
            print("已取消")
            return

    result = run_perplexity_analysis(prompt_path)
    if result:
        print(f"\n💡 提示: 可以在 Excel 或文本编辑器中查看生成的 CSV 文件")
    else:
        print(f"\n❌ 分析失败")


def main():
    """kairos 主命令"""
    if len(sys.argv) < 2:
        print("Kairos - 期货交易技术分析系统")
        print("\n用法:")
        print("  kairos-analyze [品种...]           分析指定品种（自动更新合约配置）")
        print("  kairos-analyze --all               分析所有品种")
        print("  kairos-web                         启动 Web 展示界面")
        print("  kairos-regenerate-prompt           重新生成 Deep Research 提示词")
        print("  kairos-perplexity                  调用 Perplexity 进行宏观面分析")
        print("\n示例:")
        print("  kairos-analyze CU0 AU0             分析铜和黄金")
        print("  kairos-analyze --all               一键分析所有品种（推荐）")
        print("  kairos-regenerate-prompt --date 2025-12-15")
        print("  kairos-perplexity --date 2025-12-15")
        return

    cmd = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]  # 移除子命令

    if cmd == "analyze":
        analyze()
    elif cmd == "update":
        update_contracts()
    elif cmd == "web":
        run_web()
    elif cmd == "regenerate-prompt":
        regenerate_prompt()
    elif cmd == "perplexity":
        run_perplexity()
    else:
        print(f"未知命令: {cmd}")
        print("可用命令: analyze, update, web, regenerate-prompt, perplexity")


if __name__ == "__main__":
    main()

