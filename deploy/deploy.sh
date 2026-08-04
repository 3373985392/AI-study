#!/usr/bin/env bash
set -euo pipefail

# 路径模块：源码与发布目录固定，避免 --delete 意外作用到其他目录。
readonly REPOSITORY_DIR="/srv/ai-study"
readonly WEB_ROOT="/var/www/chienzz.top"
readonly VENV_DIR="${REPOSITORY_DIR}/.venv"

if [[ "$(readlink -f "${REPOSITORY_DIR}")" != "/srv/ai-study" ]]; then
  echo "源码目录校验失败" >&2
  exit 1
fi
if [[ "$(readlink -f "${WEB_ROOT}")" != "/var/www/chienzz.top" ]]; then
  echo "网站目录校验失败" >&2
  exit 1
fi

cd "${REPOSITORY_DIR}"

# 更新模块：服务器不合并本地改动，只接受 GitHub master 的快进更新。
git status --short
git pull --ff-only origin master

# 后端依赖模块：复用 Python 3.12 虚拟环境并检查所有源码可编译。
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  python3.12 -m venv "${VENV_DIR}"
fi
"${VENV_DIR}/bin/python" -m pip install -r projects/cli-chat/requirements.txt
"${VENV_DIR}/bin/python" -m compileall -q projects/cli-chat projects/minimal-rag

# 前端构建模块：独立域名从根路径提供 VitePress 页面。
npm ci
VITEPRESS_BASE=/ npm run build

# 发布模块：只同步已校验的构建目录，并清理旧版本残留文件。
rsync -a --delete "${REPOSITORY_DIR}/.vitepress/dist/" "${WEB_ROOT}/"

# 重新加载模块：后端重启读取新代码，Nginx 无中断加载配置。
sudo systemctl restart ai-study-chat
sudo nginx -t
sudo systemctl reload nginx

echo "部署完成：$(git rev-parse --short HEAD)"
