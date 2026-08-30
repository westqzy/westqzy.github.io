---
layout: post
title: "Codex 桌面版故障实录：从 Reconnecting、代理端口到更新后无窗口"
categories: [Codex, Windows]
description: "记录 Windows Codex Desktop 持续 Reconnecting、远程端报错以及更新后有进程却无窗口的完整排障过程。"
keywords: Codex, Windows, Reconnecting, HTTP_PROXY, HTTPS_PROXY, 代理, AppX, 桌面版
mermaid: false
sequence: false
flow: false
mathjax: false
mindmap: false
mindmap2: false
---

一次 Codex Desktop 更新后，我连续遇到了几个看起来相似、实际上位于不同层级的问题：

- Codex 一直显示 `Reconnecting`；
- 手机远程端提示“加载消息时出错：Codex 服务器返回了错误”；
- Windows 桌面版进程存在，却迟迟没有显示窗口；
- 反复重启应用，现象仍然不变。

最终确认，`Reconnecting` 需要检查 Codex 是否继承了本地代理；而桌面版无法打开的直接原因不是代理，而是新版本第一次启动时正在初始化约 **334 MB、4680 个文件**的运行时资源。此前多次强制关闭应用，反复中断了这个过程。最后一次保持进程运行，约 **4 分 39 秒**后，主窗口和 renderer 进程正常出现，应用恢复。

本文记录完整的判断过程，并给出一套尽量不破坏账号、项目与本地数据的排障顺序。

> 本文基于 Windows 环境的一次实际排障。Codex 的版本、内部目录与初始化行为都可能变化。Windows 桌面版的安装和基础使用方式可参考 [OpenAI 官方 Windows 桌面应用文档](https://learn.chatgpt.com/docs/windows/windows-app)。

## 先区分三个不同问题

排障过程中最容易犯的错误，是把所有现象都归结为“代理坏了”。

| 现象 | 更可能对应的层级 | 优先检查 |
| --- | --- | --- |
| 桌面端持续 `Reconnecting` | 网络、代理、认证或长连接 | 代理端口、`.env`、代理对 HTTPS 长连接的支持 |
| 手机远程端提示服务器错误 | 远程会话、服务端状态或桌面端不可用 | 先恢复桌面端，再单独测试远程 |
| 点击应用后完全没有窗口 | Windows AppX、首次初始化、renderer 或本地状态 | 包状态、进程树、日志、CPU 与磁盘活动 |

手机上的“Codex 服务器返回了错误”是一个通用错误。单凭这句话，不能证明本地代理端口一定有问题。

同样，如果桌面应用连 renderer 进程都没有创建，修改代理通常也不能让窗口突然出现，因为应用此时可能还没有完成 UI 初始化。

> 分享命令输出或截图前，请删除代理凭据、访问令牌、用户目录、会话 ID 和工作区名称。不要公开粘贴完整 `.env`、进程命令行或原始日志。

## 一、确认 Codex 实际使用的配置目录

Codex 默认配置目录通常是：

```text
%USERPROFILE%\.codex
```

但如果系统设置了 `CODEX_HOME`，真正生效的是 `CODEX_HOME` 指向的目录，而不是默认的 `~/.codex`。

在 PowerShell 中检查：

```powershell
$codexHome = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    Join-Path $env:USERPROFILE '.codex'
} else {
    $env:CODEX_HOME
}

$codexHome
```

本次机器使用了自定义 `CODEX_HOME`。如果只修改默认目录下的 `.env`，Codex 可能根本不会读取它。

这里的 `${CODEX_HOME}\.env` 是本次机器验证过的配置方式，不代表它是官方文档承诺长期不变的接口。升级后如果行为变化，应重新核对当前版本。

## 二、检查本地正在监听的代理端口

先查看环境中已有的代理变量：

```powershell
Get-ChildItem Env: |
    Where-Object Name -Match 'proxy' |
    Select-Object Name, Value
```

再检查 Windows 当前用户的系统代理：

```powershell
Get-ItemProperty `
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' |
    Select-Object ProxyEnable, ProxyServer
```

查看本机监听端口及其所属进程：

```powershell
Get-NetTCPConnection -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess,
        @{Name='Process'; Expression={
            (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName
        }} |
    Sort-Object LocalPort
```

本次使用的是 FlClash，本地 mixed/HTTP 代理监听在：

```text
127.0.0.1:7890
```

需要注意：

- 端口正在监听，只能证明代理程序已启动；
- 要确认它是 HTTP 或 mixed 端口，而不是仅支持 SOCKS 的端口；
- 还要验证它确实能建立 HTTPS 通道。

先测试本地端口：

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 7890
```

再通过代理访问一个 HTTPS 地址：

```powershell
curl.exe -sS -o NUL `
    -w "HTTP %{http_code}`n" `
    --proxy http://127.0.0.1:7890 `
    https://api.openai.com/v1/models `
    --max-time 20

"curl exit code: $LASTEXITCODE"
```

未携带 API Key 时，接口通常不会返回业务数据。若 curl 退出码为 `0`，并收到目标服务的 `200`、`3xx`、`401` 或 `404`，说明代理与 TLS 通道基本可用。`407` 表示代理认证失败；`502`、`000`、超时或非零退出码仍需检查代理上游、DNS 与证书。这个测试并不能证明 Codex 登录与远程功能一定正常。

## 三、安全修改或创建 `.env`

不要直接覆盖整个 `.env`，其中可能还有其他配置。下面的 PowerShell 脚本会：

1. 解析实际的 Codex 配置目录；
2. 创建缺失的目录；
3. 备份已有 `.env`；
4. 只替换 `HTTP_PROXY` 和 `HTTPS_PROXY`；
5. 保留其他配置与注释。

```powershell
$codexHome = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    Join-Path $env:USERPROFILE '.codex'
} else {
    $env:CODEX_HOME
}

$envFile = Join-Path $codexHome '.env'
$proxyUri = 'http://127.0.0.1:7890'
$utf8NoBom = [Text.UTF8Encoding]::new($false)

New-Item -ItemType Directory -Force -Path $codexHome | Out-Null

if (Test-Path -LiteralPath $envFile) {
    $backup = "$envFile.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -LiteralPath $envFile -Destination $backup
    $lines = @([IO.File]::ReadAllLines($envFile, $utf8NoBom))
} else {
    $lines = @()
}

$lines = @(
    $lines | Where-Object {
        $_ -notmatch '^\s*(HTTP_PROXY|HTTPS_PROXY)\s*='
    }
)

$lines += "HTTP_PROXY=$proxyUri"
$lines += "HTTPS_PROXY=$proxyUri"

[IO.File]::WriteAllLines(
    $envFile,
    [string[]]$lines,
    $utf8NoBom
)

"Updated: $envFile"
```

最终相关内容为：

```text
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

这里 `HTTPS_PROXY` 的值仍以 `http://` 开头是正常的。它表示客户端通过 HTTP CONNECT 代理访问 HTTPS 目标，并不表示目标网站使用 HTTP。

修改 `.env` 后，需要完整退出并重新启动 Codex，让新进程重新读取环境变量。

## 四、桌面版无窗口时检查 AppX 包

如果点击桌面版后完全没有窗口，下一步应检查安装包，而不是继续修改代理。

Windows 版的包名是 `OpenAI.Codex`，桌面进程名则是 `ChatGPT.exe`。查看包状态：

```powershell
Get-AppxPackage OpenAI.Codex |
    Select-Object Name, Version, Status,
        PackageFamilyName, InstallLocation
```

本次更新期间曾观察到：

```text
PackageOffline
DataOffline
NotAvailable
```

随后 AppX 卷重新上线，包状态恢复为：

```text
Ok
```

还可以查看 AppX 卷：

```powershell
Get-AppxVolume |
    Select-Object PackageStorePath, IsOffline
```

这些状态说明 Windows Store 更新期间，包或数据卷曾暂时不可用。但当状态已经恢复为 `Ok`、签名有效且系统能够成功激活应用时，不应立即执行 Reset 或重装。

更安全的顺序是：

1. 等待 Windows Store 更新结束；
2. 确认 AppX 卷已在线；
3. 尝试正常启动；
4. 必要时使用“设置 → 应用 → 已安装的应用 → Codex/ChatGPT → 高级选项 → 修复”；
5. 备份数据后，才考虑 Reset 或重装。

“修复”与“重置”不是同一个操作。重置可能清除本地应用状态，执行前需要确认备份。

## 五、进程存在，为什么还是没有窗口

查看 Codex Desktop 的进程树：

```powershell
Get-CimInstance Win32_Process |
    Where-Object Name -EQ 'ChatGPT.exe' |
    Select-Object ProcessId, ParentProcessId,
        ExecutablePath, CommandLine
```

Electron/Chromium 应用正常启动后，通常会看到带有以下参数的子进程：

```text
--type=renderer
--type=gpu-process
--type=utility
```

这次故障期间观察到的事实是：

- 主进程已经存在；
- CPU 持续占用；
- 有 crashpad、GPU、network、storage 等子进程；
- 没有 `--type=renderer` 进程；
- 主窗口句柄为 `0`；
- 隐藏的 Chromium 窗口位于正常屏幕范围内，并非窗口跑到屏幕外；
- AppX 激活事件显示应用已成功创建进程。

这说明问题不在快捷方式，也不是窗口坐标错误。应用已经启动，但还没有走到创建可用 UI renderer 的阶段。

可以用下面的命令快速查看主窗口和 renderer：

```powershell
Get-Process ChatGPT -ErrorAction SilentlyContinue |
    Select-Object Id, StartTime, CPU, MainWindowHandle, Responding

Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq 'ChatGPT.exe' -and
        $_.CommandLine -match '--type=renderer'
    } |
    Select-Object ProcessId, ParentProcessId
```

## 六、日志停在启动行，不一定代表崩溃

Codex Desktop 日志通常位于：

```text
%LOCALAPPDATA%\Codex\Logs
```

查看最近的日志：

```powershell
$logRoot = Join-Path $env:LOCALAPPDATA 'Codex\Logs'

$latestLog = Get-ChildItem -LiteralPath $logRoot -Filter '*.log' -Recurse |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $latestLog) {
    Write-Warning '未找到 Codex Desktop 日志。'
} else {
    $latestLog | Select-Object FullName, Length, LastWriteTime
    Get-Content -LiteralPath $latestLog.FullName -Tail 100
}
```

本次日志一开始只有少量启动信息，例如：

```text
in_app_updates_policy_wait_started timeoutMs=300000
Launching app ...
```

`timeoutMs=300000` 只是在记录一个五分钟计时参数。不能仅凭这一行断言“更新检查卡死”。

真正有价值的旁证是：

- 日志没有明确的 fatal 或崩溃栈；
- 主进程仍在持续消耗 CPU；
- 磁盘上仍有初始化文件活动；
- 还没有 renderer；
- 保持进程运行后，相关文件数量继续增长。

## 七、定位结论：首次运行时初始化很可能被反复中断

继续观察后发现，新版本第一次启动时正在 staging 一个内置运行时。这个内部实现和路径可能随版本变化，因此不建议把某个目录硬编码进清理脚本。

本次实测数据为：

```text
约 4680 个文件
约 334 MB
```

此前因为“点击后长时间没有窗口”，应用被多次强制关闭。结合 staging 目录和文件增长情况判断，强制结束进程很可能中断资源准备；下一次启动需要继续或重新准备这些资源，因此表现为反复打不开。

最后一次启动没有再强制结束进程。等待约 4 分 39 秒后，观察到：

- staging 目录切换为最终运行时目录；
- renderer 进程从 0 增加到 4；
- 主窗口从句柄 `0` 变为可见窗口；
- 日志出现 `window ready-to-show`；
- Codex CLI 初始化完成，本地服务状态变为 `connected`；
- 后续启动明显变快。

### 已确认的事实

- 问题发生在应用更新后；
- AppX 包曾短暂离线，随后恢复为 `Ok`；
- 卡住期间主进程持续使用 CPU，但没有 renderer；
- 初始化期间写入约 4680 个文件、334 MB 数据；
- 不再打断进程后，应用在 4 分 39 秒内恢复。

### 基于证据的判断

最符合全部现象的原因是：新版本第一次启动正在进行运行时资源初始化，而此前的反复强制退出打断了这个过程。

这不是仅凭一条日志得出的判断，也不能由此推导出所有 Codex 启动问题都只需要等待。

## 八、什么时候应该等待，什么时候应该重启

如果同时满足以下条件，可以先等待 5～10 分钟：

- 刚完成版本更新；
- AppX 包状态已经恢复为 `Ok`；
- Codex 主进程仍有 CPU 或磁盘活动；
- 日志中没有明确的 fatal 或崩溃信息；
- 尚未创建 renderer，但相关文件或日志仍在变化。

如果 CPU、磁盘、日志和文件数量长时间完全不再变化，再考虑修复或重启。

不要一上来就执行：

```powershell
Stop-Process -Name ChatGPT -Force
```

这种写法范围过宽，也可能再次打断初始化。

确实需要重启时，先确认目标进程属于 Codex 的 WindowsApps 安装目录：

```powershell
$targets = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq 'ChatGPT.exe' -and
        $_.ExecutablePath -like '*\WindowsApps\OpenAI.Codex_*'
    }

$targets |
    Select-Object ProcessId, ParentProcessId, ExecutablePath |
    Format-Table
```

确认范围无误，并保存相关工作后，再对这些明确的 PID 操作。不要结束 VS Code 中的 `codex.exe`；它与桌面版 `ChatGPT.exe` 不是同一个进程范围。

## 九、远程端仍报错时如何继续判断

桌面端恢复后，再重新测试手机远程端。

如果仍提示“Codex 服务器返回错误”，应作为一个独立问题继续检查：

- 桌面端与手机端账号是否一致；
- 对应线程或工作区是否仍然存在；
- 桌面端本地服务是否已经完成连接；
- 代理是否支持 HTTPS 长连接；
- 新建一个最小线程能否在远程端打开。

不要因为桌面版启动问题已经解决，就直接宣称远程错误也一定解决；反过来也不要把远程端的通用错误文案直接等同于代理端口错误。

## 总结

这次排障最关键的经验有三点：

1. `Reconnecting`、远程服务器错误、桌面应用无窗口，是三个不同层级的问题；
2. 修改 `.env` 前，要先确认实际的 `CODEX_HOME`，并验证代理端口确实提供 HTTP/mixed 代理；
3. 更新后的高 CPU、无 renderer、仍有磁盘活动，不一定是死锁，也可能是第一次运行时初始化。过早强制关闭，反而会让初始化反复重来。

最终修复没有重置账号、项目或 Codex 配置，也没有重装应用，而是保留现有设置，让已经确认仍在推进的初始化过程完整执行结束。

## 参考资料

- [OpenAI 官方 Windows 桌面应用文档](https://learn.chatgpt.com/docs/windows/windows-app)

> 隐私说明：本文中的用户名、PID、自定义数据盘路径和会话信息均已删除或泛化；`127.0.0.1` 是本机回环地址，不是公网 IP。
