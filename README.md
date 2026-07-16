# 163 邮件自动截图工具

这是一个面向 163 邮箱的桌面自动化工具，用于根据 Excel 中的邮件标题批量搜索邮件、打开邮件详情页并保存截图。

## 功能特点

- 从 Excel 第一列读取邮件标题或搜索关键词
- 使用本机 Chrome 浏览器打开 163 邮箱
- 支持保留 Chrome 用户数据，登录状态可复用
- 自动搜索邮件并打开对应邮件详情
- 进入邮件内部后整页截图
- 截图文件名使用 Excel 中的原始邮件标题
- 支持暂停、继续、停止任务
- 实时显示执行日志和成功/失败数量
- 任务结束后生成 CSV 处理报告

## 使用场景

适合需要批量保存 163 邮箱中结题通知、项目通知、流程邮件等内容截图的场景。

## 环境要求

- Windows 10/11
- Python 3.11+
- Google Chrome
- 163 邮箱账号，需要手动扫码或手动登录

## 安装依赖

```powershell
py -3.11 -m pip install -r requirements.txt
```

## 从源码运行

```powershell
py -3.11 MailAutoScreenshot/main.py
```

## 打包 EXE

如果依赖已经安装：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1 -SkipInstall
```

完整安装依赖并打包：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
```

打包完成后，默认输出文件为：

```text
dist/MailAutoScreenshot.exe
```

## 使用说明

1. 准备一个 Excel 文件，把需要搜索的邮件标题放在第一列。
2. 启动程序。
3. 选择 Excel 文件。
4. 选择截图保存目录。
5. 选择或填写 Chrome 用户数据目录。
6. 点击开始。
7. 如果浏览器提示登录 163 邮箱，请先手动完成登录。
8. 程序会自动逐条搜索、打开邮件详情并保存截图。

## 默认配置

默认配置文件：

```text
MailAutoScreenshot/config/config.json
```

常用默认值：

```text
Chrome 用户数据目录: C:/MailAutoProfile
截图保存目录: D:/MailScreenshot
163 邮箱地址: https://mail.163.com
```

## 输出文件

程序运行后会生成：

- 邮件截图 PNG 文件
- `task_report_YYYYMMDD_HHMMSS.csv` 任务报告
- `logs/app.log` 运行日志

## 发布说明

源码放在 GitHub 仓库中维护，打包后的 EXE 建议通过 GitHub Releases 发布，不建议直接提交到 Git 仓库。

初版发布可以使用：

```text
v0.1.0
```

Release 附件建议命名为：

```text
MailAutoScreenshot-v0.1.0-windows-x64.exe
```

## 注意事项

- 本工具不会自动输入邮箱账号或密码。
- 首次运行需要在打开的 Chrome 中手动登录 163 邮箱。
- 邮箱页面结构可能会变化，如果搜索或截图失败，需要更新选择器和页面判断逻辑。
- 批量任务执行时请保持网络稳定，不要手动关闭自动化浏览器。
