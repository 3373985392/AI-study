# 生产部署说明

本目录只保存可审查的模板，不保存真实密钥、数据库或证书。

## 首次准备

1. 安装 Python 3.12、`python3.12-venv`、Node.js 24、Nginx 和 rsync。
2. 创建无登录服务用户与数据目录：

   ```bash
   sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin ai-study
   sudo install -d -o ai-study -g ai-study -m 750 /var/lib/ai-study
   sudo install -d -o root -g ai-study -m 750 /etc/ai-study
   ```

3. 将 `deploy/chat.env.example` 复制为 `/etc/ai-study/chat.env`，填入真实值，
   然后设置 `root:ai-study` 和 `0640` 权限。
4. 安装 systemd 与 Nginx 模板：

   ```bash
   sudo install -m 644 deploy/systemd/ai-study-chat.service /etc/systemd/system/
   sudo install -m 644 deploy/nginx/chienzz.top.conf /etc/nginx/sites-available/chienzz.top
   sudo ln -s /etc/nginx/sites-available/chienzz.top /etc/nginx/sites-enabled/chienzz.top
   sudo systemctl daemon-reload
   sudo systemctl enable ai-study-chat
   ```

5. HTTPS 证书生效后保持 `CHAT_COOKIE_SECURE=true`；纯 HTTP 调试环境必须临时设为
   `false`，否则浏览器不会回传会话 Cookie。

## 邀请码管理

以服务用户运行管理命令，确保数据库权限一致：

```bash
cd /srv/ai-study/projects/cli-chat
sudo -u ai-study /srv/ai-study/.venv/bin/python -m app.invite_admin create --label "朋友A"
sudo -u ai-study /srv/ai-study/.venv/bin/python -m app.invite_admin list
```

## 日常发布

本机推送到 GitHub 后，在服务器执行：

```bash
cd /srv/ai-study
bash deploy/deploy.sh
```

SQLite 数据库和 `/etc/ai-study/chat.env` 必须单独备份；缺少 Pepper 时已有邀请码
和会话无法继续验证。
