---
title: "第一次初始化云服务器：从 SSH 加固到 Docker 代理排障"
date: 2026-08-03
tags: [服务器, Linux, SSH, Docker, 运维, 项目实战]
categories: [部署实践]
description: "完成 cli-chat 上线前的服务器基础准备，记录 Ubuntu 初始化、SSH 密钥登录、UFW 防火墙、Docker 安装与大陆服务器拉取镜像的排障过程"
author: ZhuanZ
---

今天正式开始补齐项目上线与服务器运维的基础能力。我已经购买了云服务器和域名，并提交了备案信息。今天没有急着把 `cli-chat` 上传运行，而是先完成服务器的安全初始化和 Docker 环境验证。

最终完成的基础链路是：

```text
Windows 本地电脑
  └─ SSH 密钥登录
       └─ Ubuntu 云服务器
            ├─ 非 root 管理账户
            ├─ SSH 安全加固
            ├─ UFW 防火墙
            └─ Docker + Docker Compose
```

服务器目前已经具备继续部署 Web 应用的基础条件，但 `cli-chat` 仍是命令行程序。下一阶段需要先在本地完成服务层拆分、FastAPI 接口和前端，再进入正式部署。

## 一、确认本地终端与服务器终端的边界

第一次操作时，我直接在 Windows PowerShell 中运行了：

```bash
whoami
cat /etc/os-release
uname -m
```

结果 `whoami` 返回的是 Windows 用户，另外两条 Linux 命令则无法执行。问题并不在服务器，而是当时根本还没有通过 SSH 登录服务器。

两个终端可以通过提示符快速区分：

```text
PS C:\...>             本地 Windows PowerShell
deploy@server:~$       远程 Linux 普通用户
root@server:~#         远程 Linux root 用户
```

通过 SSH 登录后，确认服务器环境为 Ubuntu 22.04.5 LTS、x86_64 架构。这个小插曲让我意识到，远程运维时首先要明确一条命令究竟在哪台机器上执行。路径、环境变量、网络地址中的 `localhost`，都会随着执行环境改变含义。

## 二、更新系统并建立非 root 管理账户

首次登录后先更新系统软件包：

```bash
# 刷新 Ubuntu 软件包索引
apt update

# 安装当前可用的安全与稳定更新
apt upgrade -y
```

系统没有提示需要重启。随后创建 `deploy` 用户，并授予 `sudo` 权限：

```bash
# 创建日常部署账户
adduser deploy

# 允许 deploy 在必要时执行管理员命令
usermod -aG sudo deploy

# 检查用户及所属用户组
id deploy
```

日常使用非 root 用户并不能消除所有风险，但能减少误操作直接影响整个系统的概率。需要提升权限时显式使用 `sudo`，也会让操作边界更清晰。

## 三、配置 SSH 密钥并关闭密码登录

本地生成了一套专门用于该服务器的 Ed25519 密钥：

```powershell
# 私钥保留在本机，公钥安装到服务器
ssh-keygen -t ed25519 `
  -f "$env:USERPROFILE\.ssh\id_ed25519_cli_chat" `
  -C "deploy@cli-chat-server"
```

这里必须区分两个文件：

- `id_ed25519_cli_chat` 是私钥，不能上传、发送或提交到 Git。
- `id_ed25519_cli_chat.pub` 是公钥，可以写入服务器的 `authorized_keys`。

配置过程中出现了今天最有价值的故障之一：公钥在粘贴时被拆成两行。SSH 公钥必须是一条完整记录，拆行后服务器会把它识别为损坏的公钥文件。通过以下命令检查出了问题：

```bash
# 查看授权文件中每一行的公钥类型和主体长度
awk '{print NR, $1, length($2), $3}' ~/.ssh/authorized_keys

# 读取公钥指纹；文件损坏时会直接报错
ssh-keygen -lf ~/.ssh/authorized_keys
```

重新以完整单行写入后，再对比本地和服务器端的 `SHA256` 指纹，确认两边属于同一对密钥。

密钥登录验证成功后，新增 SSH 加固配置：

```text
# 禁止 root 账户直接远程登录
PermitRootLogin no

# 关闭服务器账户密码登录
PasswordAuthentication no
KbdInteractiveAuthentication no

# 保留公钥登录
PubkeyAuthentication yes
```

应用配置之前使用 `sshd -t` 检查语法，并始终保留一个已登录会话，再打开新窗口验证新连接。这样即使配置有误，也不会立刻把自己锁在服务器外面。

## 四、用两层防火墙控制公网入口

服务器启用了 UFW，并只开放当前需要的端口：

| 端口 | 用途 | 公网策略 |
|---|---|---|
| 22 | SSH 运维 | 开放 |
| 80 | HTTP | 开放 |
| 443 | HTTPS | 开放 |
| 5432 | PostgreSQL | 不开放 |
| 3000 / 8000 | 应用内部端口 | 不开放 |

```bash
# 设置默认流量策略
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 在启用防火墙前保留管理和网站端口
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用并检查规则
sudo ufw enable
sudo ufw status verbose
```

阿里云安全组是云平台边界的第一层规则，UFW 是服务器内部的第二层规则。两边都允许，流量才能进入；任意一层拒绝，连接都会失败。数据库和应用内部端口后续只通过 Docker 网络通信，不直接暴露公网。

## 五、安装 Docker 并理解 docker 组权限

Docker 使用官方软件源安装，同时安装了 Compose 与 Buildx 插件。完成后把 `deploy` 加入 `docker` 用户组，从而不必每次运行 Docker 命令都输入 `sudo`。

需要注意的是，能够控制 Docker 的用户可以挂载宿主机目录、启动特权容器，因此 `docker` 用户组实质上接近 root 权限，只应授予可信管理员。

## 六、排查 Docker Hub 连接超时

第一次执行测试容器时，Docker 守护进程能够响应，但拉取 `hello-world` 镜像超时：

```text
failed to resolve reference
dial tcp ...:443: i/o timeout
```

这说明问题不在 Docker 安装和用户权限，而在服务器到 Docker Hub 的网络链路。诊断时分别检查：

```bash
# Docker Hub 正常可达时通常返回 401，而不是 200
curl -4 -I --connect-timeout 10 https://registry-1.docker.io/v2/

# 检查域名实际解析出的 IPv4 地址
getent ahostsv4 registry-1.docker.io

# 用另一个 HTTPS 地址验证服务器的普通外网能力
curl -4 -I --connect-timeout 10 https://download.docker.com
```

`401 Unauthorized` 在这里是成功信号：它表示网络、TLS 和 HTTP 都已连通，只是请求没有携带仓库凭证。

## 七、通过 SSH 反向隧道临时复用本地代理

为了完成当前环境验证，我通过 SSH 反向隧道，将服务器回环地址上的 `17890` 转发到本地代理的 Mixed 端口 `7897`：

```text
服务器 127.0.0.1:17890
       ↓ SSH 反向隧道
本地电脑 127.0.0.1:7897
       ↓
代理网络
```

本地 PowerShell 使用单行命令建立隧道：

```powershell
# 远端端口只监听服务器回环地址，不向公网暴露代理
ssh -N -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -i "$env:USERPROFILE\.ssh\id_ed25519_cli_chat" -R 127.0.0.1:17890:127.0.0.1:7897 deploy@服务器地址
```

这里还遇到了 PowerShell 反引号续行失败的问题：反引号后只要存在空格，下一行就会被当成新的命令。对较长但只执行一次的命令，使用单行形式反而更不容易出错。

隧道建立后，服务器使用以下命令验证 HTTP 代理：

```bash
# 通过服务器侧的隧道入口访问 Docker Hub
curl -x http://127.0.0.1:17890 -I https://registry-1.docker.io/v2/
```

最初还出现过 `Proxy CONNECT aborted`。原因是必须确认使用的是 HTTP 或 Mixed 代理端口，而不能把 SOCKS5 端口直接当作 HTTP 代理。代理程序“正在运行”并不等于所选端口和协议匹配。

最后为 Docker 的 systemd 服务添加代理环境变量：

```ini
[Service]
# Docker 守护进程通过服务器回环地址进入 SSH 隧道
Environment="HTTP_PROXY=http://127.0.0.1:17890"
Environment="HTTPS_PROXY=http://127.0.0.1:17890"

# 本机和容器内部服务不经过代理
Environment="NO_PROXY=localhost,127.0.0.1,::1"
```

重新加载 systemd 并重启 Docker 后，`hello-world` 成功拉取和运行，说明 Docker 引擎、用户权限、外部网络和容器运行链路全部正常。

这个方案目前只用于安装和调试。电脑代理或 SSH 隧道关闭后，服务器便无法继续通过它拉取新镜像。正式部署时应改用可信且稳定的镜像加速服务或私有镜像仓库，不能让生产服务器长期依赖个人电脑在线。

## 今日最重要的认识

今天学到的并不只是几条 Linux 命令，而是一套逐层缩小问题范围的方法：

- 先分清命令在本地还是远程执行。
- 登录失败时分别检查用户名、认证方式、公钥内容和文件权限。
- 网络失败时区分 DNS、TCP、TLS、HTTP 与应用鉴权。
- Docker CLI 能运行，不代表 Docker 守护进程能够访问外网。
- 云安全组、系统防火墙和 Docker 端口发布属于不同层级。
- 修改远程登录配置时，必须保留可恢复通道并先验证再断开。

## 下一步

服务器基础环境已经就绪，但 `cli-chat` 当前把命令行输入、会话状态、模型调用和异常处理集中在同一个文件里，不适合直接暴露为 Web 服务。

下一阶段会按以下顺序推进：

1. 提取独立的聊天服务层，同时保持原有 CLI 可用。
2. 添加 FastAPI 与 SSE 流式接口。
3. 创建 React 简易聊天界面。
4. 接入 PostgreSQL 与 pgvector，分别处理原始数据和语义检索。
5. 编写 Docker Compose 并部署到服务器。
6. 备案通过后配置域名解析与 HTTPS。

今天先停在一个清晰且可验证的节点：服务器已经安全可登录、网络入口受控、Docker 能够正常运行，下一次可以把注意力重新放回应用架构。
