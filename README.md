# 华老师导读强化应用

> 类似文言文 web 应用 · 后台保留闪卡答题记录

## 架构

| 层 | 选型 | 部署 |
|---|---|---|
| 前端 | HTML/JS（无构建）| Render Static Site (Free) |
| 后端 | Flask + gunicorn | Render Web Service (Free) |
| 数据库 | Neon Postgres (0.5GB Free) | neon.tech |
| 资源 | 11 节课 audio + flashcards | GitHub repo |

## 11 节课

hua-001 / 009 / 010 / 011 / 203a / 204 / 205 / 206 / 207 / 208 / 209

## 本地开发

```bash
# 前端 (端口 8000)
cd frontend && python3 -m http.server 8000

# 后端 (端口 5000)
cd backend
pip install -r requirements.txt
export DATABASE_URL='postgresql://...'
python app.py
```

## 部署

1. **建 GitHub repo** (Public, 不要勾 README/license)
   ```
   https://github.com/new → gracewang3051-web/hua-web
   ```

2. **建 Neon DB**
   ```
   https://neon.tech → 新建 project
   SQL Editor → 粘贴 backend/migrations/001_init.sql → Run
   Connection Details → 复制 DATABASE_URL (pooled)
   ```

3. **Render Blueprint**
   ```
   https://dashboard.render.com → New → Blueprint
   连 gracewang3051-web/hua-web repo
   添加 env: DATABASE_URL (Neon 复制)
   ```

4. **访问**
   ```
   前端: https://hua-web.onrender.com
   后端: https://hua-web-api.onrender.com
   后台: https://hua-web-api.onrender.com/admin?token=<ADMIN_TOKEN>
   ```

## 关键 API

| Method | Path | 用途 |
|---|---|---|
| POST | `/api/record` | 记录一次答题 |
| GET | `/api/stats?user_id=` | 学习统计 |
| GET | `/api/wrong-cards?user_id=` | 错题列表 |
| GET | `/admin?token=` | 后台 dashboard |
| GET | `/admin/export.csv?token=` | 导出 CSV |

## 用户标识

无登录。首次访问生成 UUID 存 localStorage，跨设备记录不共享。
