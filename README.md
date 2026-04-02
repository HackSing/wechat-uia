# wechat-uia

独立的 UIA 聊天记录导出分析 CLI，只保留方案 1。

当前版本覆盖一个核心能力：

- 直接打开指定联系人/群聊聊天窗口
- 读取当前微信界面可见并可向上滚动获取的聊天记录
- 输出基础统计摘要
- 可同时写出 `json`、`csv`、`summary.json`

## 用法

在项目目录执行：

```bash
python -m wechat_uia.cli export-history --target 文件传输助手 --target-type contact --since today
python -m wechat_uia.cli export-history --target 项目讨论组 --target-type group --since week --output-dir .\output\history
```

如果已安装这个子项目：

```bash
cd wechat-uia
pip install -e .
wechat-uia export-history --target 文件传输助手 --target-type contact
```

## 输出

默认会在输出目录下生成：

- `messages.json`
- `messages.csv`
- `summary.json`

## 参数

- `--target`: 联系人或群名
- `--target-type`: `contact` 或 `group`
- `--since`: `today` / `yesterday` / `week` / `all`
- `--max-count`: 最大抓取条数
- `--output-dir`: 输出目录
- `--json-only`: 只输出 `messages.json`
- `--summary-only`: 只输出 `summary.json`

## 限制

- 依赖微信桌面端前台运行
- 首次连接可能触发现有 `wx4py` 的 UIA 初始化逻辑
- 微信 4.x UI 不暴露发送者信息，因此无法区分每条消息是谁发的
- 默认优先从已安装的 `wx4py` 导入；如果未安装，会回退到同级目录下的 `D:\Project\wx4py`
