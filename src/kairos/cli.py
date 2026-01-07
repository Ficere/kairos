"""Kairos CLI - 命令行入口点"""
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 自动加载 .env 文件（在任何命令执行前）
load_dotenv()


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
    from kairos.web import main
    main()


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
        print("  kairos-regenerate-prompt --recalc-technical # 重算技术面评分")
        print("\n说明:")
        print("  从已有的分析结果文件重新生成 Deep Research 提示词")
        print("  使用 --recalc-technical 可基于缓存数据重新计算技术指标")
        print("\n参数:")
        print("  --date DATE          指定日期 (格式: YYYY-MM-DD)")
        print("  --force, -f          强制覆盖已存在的文件")
        print("  --recalc-technical   重新计算技术面评分（基于缓存数据）")
        print("  --help, -h           显示此帮助信息")
        return

    print(f"\n{'='*60}")
    print("🔄 Deep Research 提示词重新生成工具")
    print(f"{'='*60}\n")

    date_str = None
    force = False
    recalc = False

    # 解析参数
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--date" and i + 1 < len(args):
            date_str = args[i + 1]
            i += 2
        elif arg in ("--force", "-f"):
            force = True
            i += 1
        elif arg == "--recalc-technical":
            recalc = True
            i += 1
        elif arg.startswith("--"):
            print(f"❌ 未知参数: {arg}")
            print("   使用 --help 查看帮助信息")
            return
        else:
            i += 1

    # 如果需要重算技术面
    if recalc:
        result = _recalc_and_regenerate(date_str, force)
    else:
        result = regenerate_prompt_from_file(date_str, force)

    if result:
        print(f"\n💡 提示: 可以将生成的文件内容复制到 ChatGPT/Claude 进行深度分析")
    else:
        print(f"\n❌ 生成失败")


def _recalc_and_regenerate(date_str: str | None, force: bool) -> str | None:
    """重算技术面并重新生成提示词"""
    from kairos.prompt_loader import get_latest_analysis_date, validate_date_format
    from kairos.recalculator import recalc_all_decisions, save_recalculated_decisions
    from kairos.prompt_generator import regenerate_prompt_from_file

    # 确定日期
    if date_str is None:
        date_str = get_latest_analysis_date()
        if date_str is None:
            print("❌ 未找到任何分析结果文件")
            return None
        print(f"📅 使用最新分析结果: {date_str}")
    elif not validate_date_format(date_str):
        print(f"❌ 日期格式错误: {date_str}")
        return None

    # 重算技术面
    print(f"\n🔄 重新计算技术面评分...")
    results = recalc_all_decisions(date_str)

    if not results["decisions"]:
        print(f"❌ 无法重算：{results.get('error', '未找到缓存数据')}")
        print(f"   请确保 data/snapshots/{date_str}/ 目录存在缓存数据")
        return None

    # 保存决策文件
    save_recalculated_decisions(date_str, results["decisions"])

    # 重新生成提示词
    print(f"\n📝 重新生成 Deep Research 提示词...")
    return regenerate_prompt_from_file(date_str, force=True)


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


def run_api():
    """kairos-api 命令：启动 API 服务"""
    from kairos.api import run_server
    args = sys.argv[1:]
    port = 8000
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
    print(f"🚀 启动 Kairos API 服务，端口: {port}")
    run_server(port=port)


def main():
    """kairos 主命令"""
    if len(sys.argv) < 2:
        print("Kairos - 期货交易技术分析系统")
        print("\n用法:")
        print("  kairos-analyze [品种...]           分析指定品种（自动更新合约配置）")
        print("  kairos-analyze --all               分析所有品种")
        print("  kairos-web                         启动 Web 展示界面")
        print("  kairos-api                         启动 API 服务（小程序后端）")
        print("  kairos-regenerate-prompt           重新生成 Deep Research 提示词")
        print("  kairos-perplexity                  调用 Perplexity 进行宏观面分析")
        print("\n示例:")
        print("  kairos-analyze CU0 AU0             分析铜和黄金")
        print("  kairos-analyze --all               一键分析所有品种（推荐）")
        print("  kairos-api --port 8000             在指定端口启动 API")
        return

    cmd = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]  # 移除子命令

    cmds = {"analyze": analyze, "update": update_contracts, "web": run_web,
            "api": run_api, "regenerate-prompt": regenerate_prompt, "perplexity": run_perplexity}
    if cmd in cmds:
        cmds[cmd]()
    else:
        print(f"未知命令: {cmd}")
        print(f"可用命令: {', '.join(cmds.keys())}")


if __name__ == "__main__":
    main()

