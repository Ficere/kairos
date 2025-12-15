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

分析结果保存在 `plans/` 目录下：

```text
plans/
├── deep_research_2025-12-15.md   # Deep Research 提示词
├── summary_2025-12-15.json       # 分析汇总（含移仓列表）
└── 2025-12-15/
    ├── CU0_decision.json         # 主力合约决策
    └── CU0_technical.json        # 技术分析数据
```

### Deep Research 提示词

每次分析完成后，自动生成 `plans/deep_research_YYYY-MM-DD.md` 文件，包含：

- 当日所有做多/做空信号品种（评分、技术指标摘要）
- 移仓提示信息
- 完整的 LLM 分析模板

可直接复制到 ChatGPT、Claude 等进行**宏观面深度分析**，获取供需、政策、行业等基本面信息。

**提示：自定义 Deep Research 分析的重点品种**

当前系统使用 `docs/deep_research_template.md` 作为 Deep Research 提示词的模板。该模板中包含一个"重点跟踪品种"列表（第 11-18 行），默认配置为：

- **黑色系**：螺纹钢、焦煤、焦炭
- **有色/贵金属**：沪铜、白银
- **新能源**：碳酸锂、多晶硅
- **建材**：玻璃

**你可以根据自己的交易偏好修改这个列表**：

1. 打开 `docs/deep_research_template.md` 文件
2. 找到"## 1. 我当前重点跟踪的品种"章节
3. 修改品种列表，添加或删除你关注的品种类别和具体品种
4. 保存文件后，下次运行 `kairos-analyze --all` 时，生成的 `plans/deep_research_YYYY-MM-DD.md` 将包含你的自定义配置

这样，当你将提示词复制到 ChatGPT/Claude 等 LLM 时，AI 会优先分析你指定的品种，并根据技术信号推荐额外的交易机会。

**注意**：修改模板不会影响技术分析本身，只会改变发送给 LLM 的分析请求内容。

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
