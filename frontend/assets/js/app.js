// 华老师导读强化应用 · 公共脚本
// 数据：Supabase (PostgREST + anon key + RLS permissive)
// 跨设备：user_id 持久化在 localStorage

// 等待 supabase-client.js 加载完成
const _supabase = window.supabase.createClient(
  window.SUPABASE_CONFIG.url,
  window.SUPABASE_CONFIG.anonKey
);

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
    const { data, error } = await _supabase
      .from('records')
      .insert({ user_id: userId, card_id: cardId, notebook, rating })
      .select();
    if (error) throw error;
    return { ok: true, id: data[0]?.id, created_at: data[0]?.created_at };
  } catch (e) {
    console.warn('Supabase fail, fallback localStorage:', e);
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
    // 统计：按 rating 分组计数
    const { data, error } = await _supabase
      .from('records')
      .select('rating')
      .eq('user_id', uid);
    if (error) throw error;
    const stats = { total: data.length, know: 0, fuzzy: 0, unknow: 0, wrong_cards: 0 };
    const wrongSet = new Set();
    for (const r of data) {
      if (r.rating === 'know') stats.know++;
      else if (r.rating === 'fuzzy') { stats.fuzzy++; wrongSet.add(r.card_id); }
      else if (r.rating === 'unknow') { stats.unknow++; wrongSet.add(r.card_id); }
    }
    stats.wrong_cards = wrongSet.size;
    return stats;
  } catch (e) {
    console.warn('Supabase stats fail, fallback localStorage:', e);
    return computeLocalStats();
  }
}

async function fetchWrongCards() {
  const uid = getUserId();
  try {
    // 错题：rating ∈ ('fuzzy', 'unknow')，按 card_id 聚合
    const { data, error } = await _supabase
      .from('records')
      .select('card_id, notebook, rating, created_at')
      .eq('user_id', uid)
      .in('rating', ['fuzzy', 'unknow']);
    if (error) throw error;
    const cardMap = {};
    for (const r of data) {
      if (!cardMap[r.card_id]) cardMap[r.card_id] = { card_id: r.card_id, count: 0, notebook: r.notebook, last: r.created_at };
      cardMap[r.card_id].count++;
      if (r.created_at > cardMap[r.card_id].last) cardMap[r.card_id].last = r.created_at;
    }
    const wrong = Object.values(cardMap).sort((a, b) => b.count - a.count);
    return { wrong, count: wrong.length };
  } catch (e) {
    console.warn('Supabase wrong-cards fail, fallback localStorage:', e);
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
