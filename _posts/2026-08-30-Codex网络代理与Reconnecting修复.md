---
layout: post
title: "Windows 下修复 Codex Reconnecting：检查代理端口并配置 HTTP_PROXY"
categories: [Codex, Windows]
description: "记录如何检查 Windows 本地代理端口，在 Codex 实际配置目录中写入 HTTP_PROXY 和 HTTPS_PROXY，并验证 Reconnecting 是否恢复。"
keywords: Codex, Windows, Reconnecting, HTTP_PROXY, HTTPS_PROXY, CODEX_HOME, 代理端口, FlClash
permalink: /2026/08/30/codex-network-proxy-reconnecting/
mermaid: false
sequence: false
flow: false
mathjax: false
mindmap: false
mindmap2: false
---

这篇文章记录一次 Windows 下 Codex 持续显示 `Reconnecting` 的修复过程。

最后真正有效的处理只有三步：

1. 找到本机代理软件实际监听的 HTTP/mixed 端口；
2. 确认 Codex 真正使用的 `CODEX_HOME`；
3. 在 `${CODEX_HOME}\.env` 中写入 `HTTP_PROXY` 和 `HTTPS_PROXY`，然后完整重启 Codex。

本次使用的代理软件是 FlClash，监听地址为 `127.0.0.1:7890`。这个端口只是本机实测值，不要直接照抄；Clash Verge、v2rayN、sing-box 等软件的端口可能不同。

> 分享命令输出或截图前，请先删除代理账号、密码、访问令牌、用户目录和工作区名称。不要公开粘贴完整 `.env` 或原始日志。

## 一、先确认问题确实在网络层

几个常见现象很容易混在一起：

| 现象 | 优先检查 |
| --- | --- |
| Codex 界面反复显示 `Reconnecting` | 代理端口、HTTPS 连通性、Codex 是否读取代理环境变量 |
| 请求出现 timeout、TLS 或 connection 错误 | 代理上游、证书、DNS、分流规则 |
| 手机远程端提示服务器错误 | 先确认桌面端已经连接，再单独测试远程会话 |
| 点击桌面版后完全没有窗口 | 这是启动或安装问题，通常不是先改代理 |

如果 Codex 已经显示界面，只是无法建立连接，才优先按本文检查网络。

## 二、确认实际的 `CODEX_HOME`

不要默认认为配置一定在 `%USERPROFILE%\.codex`。

[OpenAI Docs 的环境变量说明](https://learn.chatgpt.com/docs/config-file/environment-variables)指出，`CODEX_HOME` 默认是 `~/.codex`，但 CLI、IDE 扩展、app-server 和安装器都会使用显式设置的 `CODEX_HOME`。

在 PowerShell 中解析实际目录：

```powershell
$codexHome = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    Join-Path $env:USERPROFILE '.codex'
} else {
    $env:CODEX_HOME
}

$codexHome
```

再确认目录与 `.env`：

```powershell
Test-Path -LiteralPath $codexHome
Get-ChildItem -LiteralPath $codexHome -Force -ErrorAction SilentlyContinue
```

本次机器配置过自定义 `CODEX_HOME`。如果仍去修改默认的 `~/.codex/.env`，Codex 实际上不会读取那个文件。

## 三、找到本地代理真正监听的端口

### 1. 查看已有代理环境变量

```powershell
Get-ChildItem Env: |
    Where-Object Name -Match 'proxy' |
    Select-Object Name, Value
```

如果代理地址中包含用户名和密码，不要把输出直接发到公开论坛。

### 2. 查看 Windows 系统代理

```powershell
Get-ItemProperty `
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' |
    Select-Object ProxyEnable, ProxyServer
```

`ProxyEnable=1` 表示系统代理已启用。`ProxyServer` 可能是一个统一地址，也可能是下面这种按协议拆分的形式：

```text
http=127.0.0.1:7890;https=127.0.0.1:7890
```

### 3. 查看回环地址上的监听端口

```powershell
Get-NetTCPConnection -State Listen |
    Where-Object {
        $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '::1', '::')
    } |
    Select-Object LocalAddress, LocalPort, OwningProcess,
        @{Name='ProcessName'; Expression={
            (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName
        }} |
    Sort-Object LocalPort
```

重点寻找 FlClash、Clash、v2rayN、sing-box 等代理进程对应的端口，并回到代理软件界面核对端口类型。

必须区分：

- HTTP 端口：可以写成 `http://127.0.0.1:<端口>`；
- mixed 端口：通常同时接受 HTTP 和 SOCKS；
- SOCKS-only 端口：不能直接当作 `HTTP_PROXY` 使用。

本次检查结果是：

```text
代理软件：FlClash
监听地址：127.0.0.1
HTTP/mixed 端口：7890
```

## 四、先验证代理端口，再修改 Codex

先确认本地 TCP 端口可达：

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 7890
```

`TcpTestSucceeded` 应为 `True`。

然后通过该代理访问 HTTPS 目标：

```powershell
curl.exe -sS -o NUL `
    -w "HTTP %{http_code}`n" `
    --proxy http://127.0.0.1:7890 `
    https://api.openai.com/v1/models `
    --max-time 20

"curl exit code: $LASTEXITCODE"
```

未携带 API Key 时，不会返回模型列表。这里关注的是网络结果：

- curl 退出码为 `0`，并收到 `200`、`3xx`、`401` 或 `404`：代理和 TLS 通道基本可用；
- `407`：代理要求认证或认证信息错误；
- `502`：代理上游失败；
- `000`、timeout 或非零退出码：继续检查代理、DNS、证书与分流规则。

这一步只能验证代理链路，不能证明 Codex 进程已经读取了代理设置。

## 五、安全写入 `HTTP_PROXY` 和 `HTTPS_PROXY`

下面的脚本不会直接覆盖整个 `.env`。它会先备份原文件，只替换两个代理变量，并保留其他配置与注释。

把 `$proxyUri` 改成自己刚刚确认的 HTTP/mixed 地址：

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

最终应出现：

```text
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

`HTTPS_PROXY` 使用 `http://` 前缀并不矛盾。它表示通过 HTTP CONNECT 代理访问 HTTPS 目标，而不是把目标网站降级为 HTTP。

需要说明的是：OpenAI 官方环境变量页面列出了 Codex 直接读取的稳定公共变量，但目前没有把 `HTTP_PROXY` 和 `HTTPS_PROXY` 列在其中。`${CODEX_HOME}\.env` 是本次 Windows 桌面版环境中实测有效的兼容方案，升级后仍应重新验证。

如果只使用 Codex CLI，可以先进行一次不落盘的临时测试：

```powershell
$env:HTTP_PROXY = 'http://127.0.0.1:7890'
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
codex
```

关闭这个 PowerShell 窗口后，临时变量就会失效。

## 六、完整重启 Codex

环境变量通常在进程启动时读取，所以改完文件后，仅刷新页面可能无效。

- 桌面版：保存正在进行的工作，正常退出 ChatGPT/Codex，再重新打开；
- VS Code 扩展：保存工作后执行 `Developer: Reload Window`，必要时完整退出 VS Code；
- CLI：关闭旧终端，打开新终端后重新启动 `codex`。

不要在任务仍在执行时直接使用模糊的强制结束命令，否则可能中断正在写入的数据。

## 七、验证修复是否生效

先确认写入的是正确文件：

```powershell
$envFile = Join-Path $codexHome '.env'

Select-String -LiteralPath $envFile `
    -Pattern '^(HTTP_PROXY|HTTPS_PROXY)='
```

然后观察：

1. Codex 是否不再反复显示 `Reconnecting`；
2. 新建线程能否正常发送并接收回复；
3. 桌面端恢复后，手机远程端能否重新加载线程；
4. 代理软件连接记录中是否出现新的 HTTPS 连接。

桌面版日志通常位于 `%LOCALAPPDATA%\Codex\Logs`。可以只筛选网络相关内容：

```powershell
$logRoot = Join-Path $env:LOCALAPPDATA 'Codex\Logs'

$latestLog = Get-ChildItem -LiteralPath $logRoot -Filter '*.log' -Recurse `
    -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $latestLog) {
    Write-Warning '未找到 Codex Desktop 日志。'
} else {
    Get-Content -LiteralPath $latestLog.FullName -Tail 300 |
        Select-String -Pattern 'reconnect|proxy|connect|timeout|certificate|TLS'
}
```

分享日志前务必脱敏，因为其中可能包含本地路径、线程或工作区信息。

## 八、常见误区

### 1. 修改了错误的 `.env`

最常见的问题是系统设置了 `CODEX_HOME`，但仍然修改 `%USERPROFILE%\.codex\.env`。一定先输出 `$codexHome`。

### 2. 把 SOCKS 端口当成 HTTP 端口

如果代理软件的 `7891` 是 SOCKS-only，就不能写成：

```text
HTTP_PROXY=http://127.0.0.1:7891
```

应选择软件提供的 HTTP 或 mixed 端口。

### 3. 只看“端口正在监听”

监听成功不代表上游可用。必须再用 `curl.exe --proxy` 测试 HTTPS。

### 4. 把 Codex 的沙箱网络代理当成上游代理

[OpenAI Docs 的配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)中有 `features.network_proxy.proxy_url`，但它用于沙箱命令的网络访问与域名策略，不负责桌面应用、Web Search、Apps 或 MCP 的连接。

因此，不应通过修改这个实验性配置来解决桌面端 `Reconnecting`。

### 5. 公司代理进行了 TLS 拦截

如果日志出现证书链错误，问题可能不是端口，而是企业代理使用了私有根证书。官方环境变量说明提供了：

- `CODEX_CA_CERTIFICATE`：为 HTTPS、登录和 WebSocket 客户端指定 PEM CA bundle；
- `SSL_CERT_FILE`：当未设置前者时使用的后备 CA bundle。

不要使用关闭 TLS 校验的方式绕过证书错误。

### 6. 改完配置却没有重启进程

旧进程不会自动获得新环境变量。完整退出并重新启动后再判断结果。

## 九、什么时候说明它不是网络问题

这次排障过程中还遇到过另一个独立问题：桌面版更新后有 `ChatGPT.exe` 进程，却没有窗口和 renderer。主进程仍有 CPU 与磁盘活动，最终等待约 4 分 39 秒完成运行时初始化后才显示界面。

因此，如果应用连窗口都没有创建，应先检查启动日志、进程与磁盘活动；不要把所有故障都归因于代理。

## 总结

Windows 下修复 Codex `Reconnecting` 的可靠顺序是：

1. 确认这是连接问题，而不是应用根本没有启动；
2. 解析实际的 `CODEX_HOME`；
3. 找到代理软件真正的 HTTP/mixed 端口；
4. 用 `Test-NetConnection` 和 `curl.exe --proxy` 验证链路；
5. 备份并更新 `${CODEX_HOME}\.env`；
6. 完整重启 Codex，再用新线程和远程端复测。

本次实际修复值为：

```text
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

核心不是记住 `7890`，而是先确认自己机器上正在监听的代理类型、端口和 Codex 实际读取的配置目录。

## 参考资料

- [OpenAI Docs：Environment variables](https://learn.chatgpt.com/docs/config-file/environment-variables)
- [OpenAI Docs：Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference)

> 隐私说明：本文已移除真实用户名、自定义磁盘路径、进程号与会话信息；`127.0.0.1` 是本机回环地址，不是公网 IP。
