# 部署到 159.75.5.97

SSH 用户为 `ubuntu`（不要用 root）。代码放到 `/opt/aitek`，属主为 `ubuntu`。

推荐用 Git 更新（见下方「从 Git 更新」）。首次也可以 rsync：

```bash
ssh ubuntu@159.75.5.97 'sudo mkdir -p /opt/aitek && sudo chown ubuntu:ubuntu /opt/aitek'

rsync -av --exclude venv --exclude node_modules --exclude .git \
  ./ ubuntu@159.75.5.97:/opt/aitek/
```

装软件、拷 systemd / Nginx 时用 `sudo`。进程由 systemd 以 `ubuntu` 身份运行。

## 1. 微服务

```bash
cd /opt/aitek/ai-testcase-service
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt gunicorn
cp .env.example .env   # 改 DATABASE_URL、TOKEN
```

`DATABASE_URL` 在服务器上建议用 `127.0.0.1`。`AI_SERVICE_INTERNAL_TOKEN` 必须与 Django 一致。

## 2. Django

```bash
cd /opt/aitek/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt gunicorn
cp .env.example .env
python manage.py migrate
python manage.py collectstatic --noinput
```

## 3. 前端

```bash
cd /opt/aitek/frontend
npm ci
npm run build
```

本地开发仍用 `npm run serve`（8081），`/api` 会代理到 8001。

## 4. systemd + Nginx

```bash
sudo cp /opt/aitek/deploy/systemd/aitek-ai.service /etc/systemd/system/
sudo cp /opt/aitek/deploy/systemd/aitek-django.service /etc/systemd/system/
sudo cp /opt/aitek/deploy/nginx/aitek.conf /etc/nginx/sites-available/aitek
sudo ln -sf /etc/nginx/sites-available/aitek /etc/nginx/sites-enabled/aitek
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable --now aitek-ai aitek-django
sudo systemctl reload nginx
```

浏览器访问 `http://159.75.5.97`。安全组只开 80/22，不要开 8001、8002、3306。

生成用例是长连接。更新 `aitek-ai.service` 后必须：

```bash
sudo cp /opt/aitek/deploy/systemd/aitek-ai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart aitek-ai aitek-django
```

若前端出现 `illegal chunk header` / `HTTP/1.1 500`，先看 `journalctl -u aitek-ai -n 80 --no-pager`。

## 从 Git 更新

本地仓库还没有远程时，先在 GitLab/GitHub 建空仓库，再：

```bash
cd /Users/zhuchenyang/AITEK_艾泰克
git init
git add .
git status   # 确认没有 .env、venv、node_modules
git commit -m "chore: 初始化 AITEK 仓库"
git branch -M main
git remote add origin <你的仓库 HTTPS 或 SSH 地址>
git push -u origin main
```

服务器首次（目录已有 rsync 代码、没有 `.git`）：

```bash
ssh ubuntu@159.75.5.97
cd /opt
sudo mv aitek aitek.bak   # 保留服务器上的 .env / venv
git clone <你的仓库地址> aitek
sudo chown -R ubuntu:ubuntu /opt/aitek
cp /opt/aitek.bak/backend/.env /opt/aitek/backend/.env
cp /opt/aitek.bak/ai-testcase-service/.env /opt/aitek/ai-testcase-service/.env
# 也可继续用原来的 venv，不必重装：
# mv /opt/aitek.bak/backend/venv /opt/aitek/backend/
# mv /opt/aitek.bak/ai-testcase-service/venv /opt/aitek/ai-testcase-service/
# mv /opt/aitek.bak/frontend/node_modules /opt/aitek/frontend/
```

之后每次发版：

```bash
# 本机
git add -A && git commit -m "fix: ..." && git push

# 服务器
ssh ubuntu@159.75.5.97
cd /opt/aitek
git pull
cd frontend && npm ci && npm run build
cd /opt/aitek/backend && ./venv/bin/python manage.py migrate && ./venv/bin/python manage.py collectstatic --noinput
sudo cp /opt/aitek/deploy/systemd/aitek-ai.service /etc/systemd/system/
sudo cp /opt/aitek/deploy/systemd/aitek-django.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart aitek-ai aitek-django
```
