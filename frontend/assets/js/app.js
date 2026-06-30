// 华老师导读强化应用 · 公共脚本
// 功能：user_id 持久化、API 调用、统计刷新

const API_BASE = 'https://hua-web-api.onrender.com';  // 生产：Render Web Service；本地 dev 改 http://127.0.0.1:5000

// ====== 用户标识 ======
function getUserId() {
  let uid = localStorage.getItem('hua_uid');
  if (!uid) {
    uid = (crypto.randomUUID ? crypto.randomUUID() :
      'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random()*16|0; return (c==='x'?r:(r&0x3|0x8)).toString(16);
      }));
    localStorage.setItem('hua_uid', uid);
  }
  return uid;
}

// ====== API 调用 ======
async function recordAnswer(cardId, notebook, rating) {
  // rating: 'know' | 'fuzzy' | 'unknow'
  const userId = getUserId();
  try {
    const r = await fetch(`${API_BASE}/api/record`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        card_id: cardId,
        notebook: notebook,
        rating: rating
      })
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  } catch (e) {
    // 后端不通时降级到 localStorage
    console.warn('API fail, fallback localStorage:', e);
    return recordLocal(cardId, notebook, rating);
  }
}

function recordLocal(cardId, notebook, rating) {
  const key = `hua_local_${cardId}`;
  const prev = JSON.parse(localStorage.getItem(key) || '{"count":0,"last":0,"wrong":0}');
  prev.count = (prev.count || 0) + 1;
  if (rating === 'unknow' || rating === 'fuzzy') prev.wrong = (prev.wrong || 0) + 1;
  prev.last = Date.now();
  prev.notebook = notebook;
  prev.rating = rating;
  localStorage.setItem(key, JSON.stringify(prev));
  return { ok: true, local: true };
}

async function fetchStats() {
  const uid = getUserId();
  try {
    const r = await fetch(`${API_BASE}/api/stats?user_id=${uid}`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  } catch (e) {
    return computeLocalStats();
  }
}

async function fetchWrongCards() {
  const uid = getUserId();
  try {
    const r = await fetch(`${API_BASE}/api/wrong-cards?user_id=${uid}`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  } catch (e) {
    return computeLocalWrong();
  }
}

function computeLocalStats() {
  const stats = { total: 0, know: 0, fuzzy: 0, unknow: 0, wrong_cards: 0 };
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (!k.startsWith('hua_local_')) continue;
    const r = JSON.parse(localStorage.getItem(k));
    stats.total += r.count || 0;
    if (r.rating === 'know') stats.know++;
    else if (r.rating === 'fuzzy') stats.fuzzy++;
    else if (r.rating === 'unknow') stats.unknow++;
  }
  stats.wrong_cards = stats.fuzzy + stats.unknow;
  return stats;
}

function computeLocalWrong() {
  const wrong = [];
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (!k.startsWith('hua_local_')) continue;
    const r = JSON.parse(localStorage.getItem(k));
    if (r.rating === 'fuzzy' || r.rating === 'unknow') {
      const cardId = k.replace('hua_local_', '');
      wrong.push({ card_id: cardId, count: r.wrong, notebook: r.notebook });
    }
  }
  return { wrong: wrong.sort((a, b) => b.count - a.count) };
}
