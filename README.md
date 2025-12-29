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
uv sync
```

## 命令行工具

### 分析命令

```bash
uv run kairos-analyze --all         # 一键分析所有品种（推荐）
uv run kairos-analyze AU0 CU0 AG0   # 分析指定品种
```

> **说明**：`kairos-analyze` 会自动更新主力合约配置，无需额外操作。合约代码使用 `XX0` 格式（如 `AU0`、`CU0`）。

### Deep Research 提示词重新生成

```bash
# 从已有分析结果重新生成 Deep Research 提示词（适用于模板调试）
uv run kairos-regenerate-prompt                    # 使用最新分析结果
uv run kairos-regenerate-prompt --date 2025-12-15  # 指定日期
uv run kairos-regenerate-prompt --force            # 强制覆盖已存在文件
```

**使用场景**：

- 📝 **模板调试**：修改 `docs/deep_research_template.md` 后，快速重新生成提示词查看效果
- 📊 **历史回顾**：基于历史分析结果重新生成提示词，验证模板改进效果
- 🔄 **快速迭代**：无需重新运行耗时的数据获取和技术分析

### Perplexity 宏观面分析

系统支持调用 Perplexity API 进行宏观面和基本面分析，自动生成交易建议 CSV 文件。

**配置 API Key**：

在项目根目录创建 `.env` 文件，添加：

```bash
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxxxxxx
```

**使用命令**：

```bash
uv run kairos-perplexity                           # 使用最新提示词
uv run kairos-perplexity --date 2025-12-15         # 指定日期的提示词
uv run kairos-perplexity --prompt-file PATH        # 指定提示词文件
uv run kairos-perplexity --force                   # 强制覆盖已存在的 CSV
```

**输出文件**：`plans/perplexity_suggestion_YYYY-MM-DD.csv`，包含品种、方向、目标价、止损价、技术面/消息面简述等字段。

**注意**：运行 `kairos-analyze --all` 时会自动调用 Perplexity 分析（如已配置 API Key）。

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
- **交易信号追踪模板**（新增）：
  - 做多/做空信号追踪表格（信号状态、触发时间、强度评估、后续验证）
  - 多空信号对比分析（力量对比、冲突处理、优势方向）
  - 历史信号回顾（近5日信号表现、准确率统计）
- 完整的 LLM 分析模板

可直接复制到 ChatGPT、Claude 等进行**宏观面深度分析**，获取供需、政策、行业等基本面信息，并系统化追踪交易信号的生命周期。

### 自定义重点跟踪品种（TRACKING_CONFIG）

系统使用 `docs/deep_research_template.md` 作为 Deep Research 提示词的模板。该模板中包含一个"重点跟踪品种"配置（TRACKING_CONFIG），默认配置为：

- **工业金属**：沪铜
- **贵金属**：白银
- **新能源**：碳酸锂
- **黑色系**：焦炭、焦煤
- **建材**：玻璃

**你可以根据自己的交易偏好修改这个列表**：

1. 打开 `docs/deep_research_template.md` 文件
2. 找到"## 1. 我当前重点跟踪的品种"章节中的 TRACKING_CONFIG JSON 配置块
3. 修改品种列表（contract、name、reason 字段）
4. 保存文件

**重要特性**：

- ✅ **实时数据增强**：系统自动为配置的品种添加当前价格、方向、评分和技术状态
- ✅ **快速更新**：修改配置后，运行 `kairos-regenerate-prompt --force` 即可立即生效
- ✅ **个性化**：AI 会优先分析你指定的品种，并根据技术信号推荐额外的交易机会

**配置示例**（在模板中）：

```json
[
  {"contract": "CU0", "name": "沪铜", "reason": "工业金属龙头，宏观经济风向标"},
  {"contract": "AG0", "name": "白银", "reason": "避险资产，美元/利率敏感"},
  {"contract": "LC0", "name": "碳酸锂", "reason": "新能源板块核心品种"}
]
```

**生成效果**（在提示词中）：

| 品种 | 合约 | 当前价格 | 方向 | 评分 | 跟踪理由 | 技术状态 |
|------|------|---------|------|------|---------|---------|
| 沪铜 | CU2602 | 92490.0 | 观望 | 50 | 工业金属龙头 | MACD多头，RSI超买(71) |

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
