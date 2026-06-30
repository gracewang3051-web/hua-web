"""Flask 主入口。"""
import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import db
import json

app = Flask(__name__)
CORS(app)  # 允许跨域（前端在不同子域时）

# 启动时初始化 schema
with app.app_context():
    try:
        db.init_schema()
    except Exception as e:
        print(f"[warn] init_schema failed: {e}")

# ====== 健康检查 ======
@app.route('/health')
def health():
    return jsonify({"ok": True, "service": "hua-web-api"})

# ====== 答题记录 ======
@app.route('/api/record', methods=['POST'])
def api_record():
    data = request.get_json(force=True)
    uuid = data.get('user_id')
    card_id = data.get('card_id')
    notebook = data.get('notebook')
    rating = data.get('rating')
    if not all([uuid, card_id, notebook, rating]):
        return jsonify({"error": "missing fields"}), 400
    if rating not in ('know', 'fuzzy', 'unknow'):
        return jsonify({"error": "invalid rating"}), 400
    try:
        user_id = db.upsert_user(uuid)
        rec = db.record_answer(user_id, card_id, notebook, rating)
        return jsonify({"ok": True, "id": rec['id'], "created_at": rec['created_at']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ====== 学习统计 ======
@app.route('/api/stats')
def api_stats():
    uuid = request.args.get('user_id')
    if not uuid:
        return jsonify({"error": "missing user_id"}), 400
    try:
        user_id = db.upsert_user(uuid)  # 自动注册
        stats = db.get_user_stats(user_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ====== 错题列表 ======
@app.route('/api/wrong-cards')
def api_wrong_cards():
    uuid = request.args.get('user_id')
    if not uuid:
        return jsonify({"error": "missing user_id"}), 400
    try:
        user_id = db.upsert_user(uuid)
        wrong = db.get_wrong_cards(user_id)
        return jsonify({"wrong": wrong, "count": len(wrong)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ====== Admin: 概览 ======
@app.route('/admin')
def admin():
    import os
    token = os.environ.get('ADMIN_TOKEN', '')
    if token and request.args.get('token') != token:
        return "forbidden", 403
    try:
        ov = db.admin_overview()
        return _render_admin(ov)
    except Exception as e:
        return f"<pre>err: {e}</pre>", 500

@app.route('/admin/export.csv')
def admin_export():
    token = os.environ.get('ADMIN_TOKEN', '')
    if token and request.args.get('token') != token:
        return "forbidden", 403
    csv_text = db.export_records_csv()
    return Response(csv_text, mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename="hua-records.csv"'
    })

def _render_admin(ov: dict) -> str:
    # 简单 HTML + Chart.js（CDN 加载）
    nb_data = json.dumps(ov.get('by_notebook', []))
    return f"""<!doctype html>
<html><head>
<meta charset="utf-8">
<title>华老师 · Admin</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
body{{font-family:-apple-system,sans-serif;max-width:1100px;margin:30px auto;padding:0 20px;background:#f4f1ea;color:#333}}
h1{{color:#5a4e3c}}.card{{background:#fff;border:1px solid #d8d2c2;border-radius:8px;padding:16px;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid #eee}}
.stat{{display:flex;gap:16px}}.stat>div{{flex:1;background:#fff;padding:16px;border-radius:8px;border:1px solid #d8d2c2;text-align:center}}
.stat .n{{font-size:32px;font-weight:700;color:#5a4e3c}}.stat .l{{font-size:13px;color:#888}}
canvas{{max-height:300px}}
</style></head><body>
<h1>🎓 华老师 · 学习后台</h1>
<div class="stat">
  <div><div class="n">{ov['users']}</div><div class="l">注册用户</div></div>
  <div><div class="n">{ov['records']}</div><div class="l">总答题数</div></div>
  <div><div class="n">{len(ov['top_wrong'])}</div><div class="l">高频错题数</div></div>
</div>
<div class="card"><h2>📚 按课答题数</h2><canvas id="nb"></canvas></div>
<div class="card"><h2>🏆 Top 20 用户（答题数）</h2><table><tr><th>UUID</th><th>答题数</th></tr>
{''.join(f'<tr><td>{u["uuid"][:8]}...</td><td>{u["cnt"]}</td></tr>' for u in ov['top_users'])}
</table></div>
<div class="card"><h2>❌ Top 20 高频错题</h2><table><tr><th>Card ID</th><th>错</th><th>总</th><th>错率</th></tr>
{''.join(f'<tr><td>{w["card_id"]}</td><td>{w["wrong"]}</td><td>{w["total"]}</td><td>{w["wrong"]/w["total"]*100:.0f}%</td></tr>' for w in ov['top_wrong'])}
</table></div>
<p><a href="/admin/export.csv?token={os.environ.get('ADMIN_TOKEN','')}">📥 导出 CSV</a></p>
<script>
const nbData = {nb_data};
new Chart(document.getElementById('nb'), {{
  type: 'bar',
  data: {{ labels: nbData.map(d=>d.notebook), datasets: [{{ label:'答题数', data: nbData.map(d=>d.count), backgroundColor:'#a3b5a3' }}] }},
  options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
}});
</script>
</body></html>"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
