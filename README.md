# Kairos - 期货技术分析系统

专注于期货品种的**技术面分析**，支持 LLM 宏观分析，生成结构化交易决策。

## 功能

- **技术分析**：MACD、KDJ、RSI、BOLL、均线、ATR、背离检测
- **移仓监控**：自动检测主力合约切换，支持双合约分析
- **Web 展示**：实时查看分析结果（纯展示模式）
- **交易决策**：综合技术面和宏观面生成交易建议

## 安装

```bash
# 开发模式安装
uv pip install -e .
```

## 命令行工具

```bash
uv run kairos-analyze AU0 CU0 AG0   # 分析指定品种
uv run kairos-analyze --all         # 分析所有品种
uv run kairos-update --add-all      # 添加所有品种配置
```

> **注意**：主力合约代码使用 `XX0` 格式（如 `AU0`、`CU0`），表示该品种的主力连续合约。

## Web 界面

```bash
uv run kairos-web                   # 启动 Web 展示界面
# 访问 http://127.0.0.1:8050
```

Web 界面为**纯展示模式**，仅显示已生成的分析结果，不触发新的分析任务。

## 定时任务配置

推荐使用 cron 定时执行分析，Web 界面自动展示最新结果：

```bash
# 编辑 crontab
crontab -e

# 每天早上 9:00 和下午 14:00 执行分析（周一至周五）
0 9,14 * * 1-5 cd /path/to/kairos && uv run kairos-analyze --all >> /tmp/kairos.log 2>&1
```

## 输出

分析结果按日期保存在 `plans/` 目录下：

```text
plans/2025-12-15/
├── CU0_decision.json           # 主力合约决策
├── CU0_decision_previous.json  # 移仓中旧合约决策（如有）
├── CU0_technical.json          # 技术分析数据
└── summary.json                # 汇总（含移仓列表）
```

## 品种配置

配置存储在 `contracts.json`，支持移仓监控：

```json
{
  "CU": {
    "name": "铜",
    "exchange": "SHFE",
    "main_contract": "CU2602",
    "previous_contract": "CU2601",
    "contract_switch_date": "2025-12-14"
  }
}
```
