# Customer Follow-Up Pipeline

`customer-followup` 是当前 `wechat-uia-cli` 里最高层的业务流水线。

它不是单次“导出聊天记录”，而是面向销售 / 客户成功 / FAE 的持续客户跟进能力。

## 它解决什么问题

适合这些场景：

- 每天按客户抓微信聊天
- 按天沉淀聊天记录
- 自动提炼业务重点、风险、技术问题和待办
- 给客户和项目建立持续更新的档案
- 生成日报和周报草稿

如果只是一次性看某个聊天窗口，优先用 `export-history`。
如果要把客户沟通变成长期资产，优先用 `customer-followup`。

## 命令

```bash
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --since today
```

常见变体：

```bash
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --group 战略客户
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --customer acme --customer betaco --no-cache
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --output-root .\output\customer-followup --history-days 14
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --knowledge-dir .\knowledge\real
```

## 推荐日常操作

1. 维护 `config/customers.yaml`
   保持 `target`、`aliases`、`owner`、`chip_focus`、`project_hints` 尽量准确。
2. 每天运行一次 `--since today`
   这是推荐的稳定模式。
3. 先看日报总览
   打开 `reports/YYYY-MM-DD/index.md`，快速看今天哪些客户有新增动作。
4. 再看单客户日报
   打开 `reports/YYYY-MM-DD/<customer-id>.md`，查看当天进展、风险、建议动作。
5. 需要更长上下文时看 `timeline.md`
   这是给其他智能体接手时最好的长期背景文件。

## 输出结构

```text
output/customer-followup/
  customers/
    <customer-id>/
      customer.json
      timeline.md
      daily/
        YYYY-MM-DD.json
      projects/
        overview.md
        overview.json
        <project-id>.json
      issues/
        current.json
        history/
          YYYY-MM-DD.json
  reports/
    YYYY-MM-DD/
      index.md
      batch.json
      <customer-id>.md
      <customer-id>.json
    weekly/
      YYYY-MM-DD/
        index.md
        batch.json
        <customer-id>.md
        <customer-id>.json
```

## 文件含义

- `customers/<id>/daily/YYYY-MM-DD.json`
  当天原始抓取结果 + 结构化分析结果。
- `customers/<id>/timeline.md`
  客户级长时间轴，按天重建。
- `customers/<id>/projects/overview.md`
  当前识别到的项目快照总览。
- `customers/<id>/issues/current.json`
  当前仍在跟踪的 issue 列表。
- `reports/YYYY-MM-DD/<id>.md`
  当天客户日报。
- `reports/weekly/YYYY-MM-DD/<id>.md`
  周报草稿。
- `reports/YYYY-MM-DD/index.md`
  当天所有客户的总览页。

## 第二层知识库能力

`customer-followup` 可以额外做两类增强判断：

- 芯片选型规则校验
- 相似项目案例召回

它会优先读取 `--knowledge-dir` 下的真实文件：

- `chip_catalog.json`
- `project_cases.json`

如果没有提供，会自动回退到 skill 自带的虚拟资料：

- `knowledge/chip_catalog.virtual.json`
- `knowledge/project_cases.virtual.json`

虚拟资料只用于演示流程，不建议当真实业务判断依据。

## 代码层和大模型层的分工

### 代码已经完成

- 抓取微信聊天
- 按天归档
- 输出客户时间轴
- 提炼需求、商务、技术、风险、待办
- 生成项目快照
- 生成 issue 列表
- 生成日报和周报草稿
- 命中知识库时做规则化选型/案例提示

### 建议交给使用 skill 的大模型

- 写成更自然的客户跟进纪要
- 根据上下文补全模糊需求
- 产出更成熟的跟进建议和回复话术
- 结合多个客户日报输出管理视角总结
- 对“是否升级给技术团队”做更细致的判断

## 适合其他智能体的读取顺序

处理某个客户时，推荐按这个顺序读：

1. `reports/YYYY-MM-DD/index.md`
2. `reports/YYYY-MM-DD/<id>.md`
3. `customers/<id>/projects/overview.md`
4. `customers/<id>/issues/current.json`
5. `customers/<id>/timeline.md`

## 相关文档

- `docs/customer-followup-prd.md`
- `docs/known-limitations.md`
- `references/cli-contract.md`
- `config/customers.yaml.example`
