# WeChat UIA Automation 使用说明

这套 skill 用来在 Windows 上自动操作微信 4.x。

目前建议把它理解成两类能力：

- 单次聊天导出与分析
- 面向销售/客户成功场景的每日客户跟进流水线

它适合两类人：

- 直接和 Agent 对话的人
- 需要手动执行命令验证结果的人

统一入口：

```bash
python scripts/run_wechat_skill.py <command> ...
```

兼容旧入口：

```bash
python scripts/run_wechat_uia.py ...
```

## 使用前提

开始前先确认这些条件成立：

- 操作系统是 Windows
- 微信 PC 版已经打开并登录
- 操作期间尽量不要手动点微信窗口
- 微信窗口最好保持前台
- 机器可以正常执行 `python -m pip install`

先做一次环境检查：

```bash
python scripts/run_wechat_skill.py check-env
```

如果返回 JSON 里 `ok: true`，说明运行环境基本可用。

## 自动安装依赖

这个 skill 在首次使用时会先检测 Python 第三方包。

如果缺少下面这些依赖，会自动安装：

- `pywin32`
- `comtypes`
- `pyperclip`
- `markdown`
- `beautifulsoup4`
- `Pillow`

安装状态会记录到 skill 根目录下的 `.runtime-bootstrap.json`。

也就是说：

- 不依赖外部 `wx4py` 源码仓库
- 也不要求你提前手工把第三方包装好
- 首次运行任意命令时，skill 会先补齐环境，再执行真正任务

## 自然语言任务清单

下面这些话，都是可以直接对 Agent 说的。

### 1. 发消息

- 帮我给文件传输助手发一条消息：测试成功
- 帮我给张三发消息：今天 6 点前回我
- 帮我给“项目同步群”发消息：明天上午 10 点开会
- 帮我给“研发一组”“研发二组”“产品组”群发一条消息：今晚 8 点前提交日报

### 2. 发文件

- 帮我把 `C:\Reports\weekly.pdf` 发给文件传输助手
- 帮我把 `C:\Reports\weekly.pdf` 发到“项目同步群”
- 帮我把 `C:\Docs\a.docx` 和 `C:\Docs\b.xlsx` 一起发给“项目同步群”
- 帮我把 `C:\Reports\weekly.pdf` 发给“项目同步群”，并附言：请今晚前确认

### 3. 搜索联系人或群

- 帮我搜索一下“文件传输助手”
- 帮我看看“项目群”是否能在微信里搜到
- 帮我列出关键词“测试”对应的搜索结果

### 4. 获取聊天记录

- 帮我读取文件传输助手今天的聊天记录
- 帮我读取“项目同步群”昨天的聊天记录
- 帮我抓取“项目同步群”本周最近 50 条消息
- 帮我把“项目同步群”的聊天记录导出来分析

### 5. 导出聊天记录到文件

- 帮我导出文件传输助手今天的聊天记录
- 帮我把“项目同步群”本周的聊天记录导出成 JSON 和 CSV
- 帮我先试导出“项目同步群”最近 20 条消息，确认可行后再导全部

导出后通常会生成：

- `messages.json`
- `messages.csv`
- `summary.json`

### 5.5 客户跟进与日报

- 帮我按客户配置抓取今天的聊天记录并生成跟进报告
- 帮我把今天的客户沟通沉淀到按天文档里
- 帮我为战略客户生成今天的跟进总览
- 帮我更新客户时间轴并输出今天的日报建议

### 6. 群管理

- 帮我获取“项目同步群”的成员列表
- 帮我把我在“项目同步群”的群昵称改成“值班号”
- 帮我开启“项目同步群”的消息免打扰
- 帮我关闭“项目同步群”的消息免打扰
- 帮我置顶“项目同步群”
- 帮我取消置顶“项目同步群”

### 7. 群公告

- 帮我把“项目同步群”的公告改成：今晚 18:00 冻结代码
- 帮我把 `C:\Temp\announcement.md` 的内容设置成“项目同步群”的公告

### 8. 诊断和排查

- 帮我看看当前微信界面是不是已经在聊天窗口
- 帮我抓一下当前微信窗口快照
- 帮我导出当前 UI 控件树，看看为什么按钮找不到
- 帮我检查这台机器上的依赖是否完整

## 推荐使用方式

如果是第一次跑，建议按这个顺序：

1. 先检查环境并让 skill 自动补依赖：

```bash
python scripts/run_wechat_skill.py check-env
```

2. 再做一个最小验证：

```bash
python scripts/run_wechat_skill.py send-to --target "文件传输助手" --target-type contact --message "skill smoke test"
```

3. 再执行正式任务：

- 批量发消息
- 发文件
- 导出聊天记录
- 改群设置

## 命令示例

### 发消息

```bash
python scripts/run_wechat_skill.py send-to --target "文件传输助手" --target-type contact --message "hello"
```

### 批量发消息

```bash
python scripts/run_wechat_skill.py batch-send --targets "群1" "群2" "群3" --target-type group --message "今晚提交日报"
```

### 发文件

```bash
python scripts/run_wechat_skill.py send-file-to --target "项目同步群" --target-type group --file "C:\Reports\weekly.pdf" --message "请查收"
```

### 导出聊天记录

```bash
python scripts/run_wechat_skill.py export-history --target "项目同步群" --target-type group --since week --max-count 100
```

### 客户跟进日报

```bash
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --since today
```

这条命令会在一次运行里完成：

- 抓取客户当天聊天记录
- 归档到按天保存的 JSON
- 重建每个客户的 `timeline.md`
- 刷新项目档案和 issue 列表
- 生成当天日报、周报和总览页

建议阅读顺序：

- 先看 `reports/YYYY-MM-DD/index.md`
- 再看单客户 `reports/YYYY-MM-DD/<customer-id>.md`
- 再看 `customers/<customer-id>/projects/overview.md` 和 `issues/current.json`
- 需要更长历史时再看 `customers/<customer-id>/timeline.md`

如果要启用第二层“芯片选型/相似案例”增强能力，可以额外传：

```bash
python scripts/run_wechat_skill.py customer-followup --config config/customers.yaml --knowledge-dir .\knowledge\real
```

如果没有提供真实知识库，会自动回退到 skill 自带的虚拟资料。

### 获取群成员

```bash
python scripts/run_wechat_skill.py get-group-members --group "项目同步群"
```

### 开启免打扰

```bash
python scripts/run_wechat_skill.py set-do-not-disturb --group "项目同步群" --enable
```

## 常见限制

- 需要微信窗口处于可操作状态
- UI 自动化过程中不要频繁手动切换窗口
- 聊天记录抓取通常拿不到发送者姓名，这是微信 UI 的限制
- 群公告修改、群设置修改可能受权限影响
- 批量操作前建议先在“文件传输助手”做一次小范围验证

优化后的 UIA 方案虽然比之前稳定，但仍然不是数据库级精确读取。当前仍然存在：

- 启发式分页，极端情况下仍可能重复或漏消息
- `reached top (scroll stuck)` 只表示界面不再变化，不一定是绝对最早消息
- 时间粒度是按可见时间分隔块，而不是每条消息精确时间
- 富媒体消息会被简化

完整说明见：

- `docs/known-limitations.md`
- `docs/customer-followup.md`
- `docs/customer-followup-prd.md`

## 看到结果时怎么判断

所有命令都会输出一段 JSON。

重点看这些字段：

- `ok`
- `action`
- `result`
- `error_type`
- `error`

如果 `ok` 是 `false`，就不要把这次操作当成成功。

## 适合给 Agent 的一句话模板

- 帮我先检查环境，再给文件传输助手发一条测试消息
- 帮我把这个 PDF 发到“项目同步群”，附言“请今晚前确认”
- 帮我导出“项目同步群”本周聊天记录，先只试 20 条
- 帮我读取“项目同步群”今天的聊天记录并总结一下重点
- 帮我按客户配置生成今天的客户跟进报告和总览
- 帮我更新 AIWare 和一辣的客户时间轴，再输出今天的日报
- 帮我获取“项目同步群”的成员列表
- 帮我把“项目同步群”的公告更新成这段内容
