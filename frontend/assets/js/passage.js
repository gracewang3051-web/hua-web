// 板块页交互

const params = new URLSearchParams(location.search);
const passageId = params.get('id') || 'p12';
const info = window.PASSAGE_INFO[passageId];

if (!info) {
  document.body.innerHTML = '<div style="padding: 40px; text-align: center;">文章不存在</div>';
} else {
  // 设置标题
  document.querySelector('.topbar h1').textContent = info.title;
  document.getElementById('passage-title').textContent = info.title;
  document.getElementById('knowledge-link').href = info.knowledgeUrl;
  document.getElementById('original-link').href = info.originalUrl;

  // 板块数据（与 mp3 文件名对应）
  const SECTIONS = {
    p12: [
      { file: 'p12-01.mp3', title: '开场引子', desc: '抓住孩子的注意力' },
      { file: 'p12-02.mp3', title: '作者与背景', desc: '元朝 / 欧阳玄 / 四等人制' },
      { file: 'p12-03.mp3', title: '原文朗读 · 引导式导读', desc: '通读 → 思考 → 揭晓 → 核心句' },
      { file: 'p12-04.mp3', title: '重点生词', desc: '逊 / 信 / 胜 / 约 / 旨 …' },
      { file: 'p12-05.mp3', title: '句式拆解', desc: '判断句 / 双重否定 / 倒装' },
      { file: 'p12-06.mp3', title: '文化常识', desc: '四等人制 / 翰林学士承旨' },
      { file: 'p12-07.mp3', title: '白话大意与写作意图', desc: '深层主旨 + 写作悖论' }
    ],
    p13: [
      { file: 'p13-01.mp3', title: '开场引子', desc: '抓住孩子的注意力' },
      { file: 'p13-02.mp3', title: '作者与背景', desc: '南宋 / 杨万里 / 诚斋体' },
      { file: 'p13-03.mp3', title: '原文朗读 · 引导式导读', desc: '通读 → 思考 → 揭晓 → 核心句' },
      { file: 'p13-04.mp3', title: '重点生词', desc: '立 / 假 / 辄 / 市 / 趋 …' },
      { file: 'p13-05.mp3', title: '句式拆解', desc: '主客互换反问 / 并列否定' },
      { file: 'p13-06.mp3', title: '文化常识', desc: '比德传统 / 恬退' },
      { file: 'p13-07.mp3', title: '白话大意与写作意图', desc: '批判假恬退 + 哲学升华' }
    ]
  };

  const sections = SECTIONS[passageId];
  const list = document.getElementById('section-list');

  // 渲染板块列表
  sections.forEach((s, i) => {
    const item = document.createElement('div');
    item.className = 'section-item';
    item.dataset.idx = i;
    item.innerHTML = `
      <div class="idx">${i + 1}</div>
      <div class="info">
        <div class="title">${s.title}</div>
        <div class="meta">${s.desc}</div>
      </div>
    `;
    item.onclick = () => playSection(i);
    list.appendChild(item);
  });

  const audio = document.getElementById('audio');
  const audioSrc = document.getElementById('audio-source');
  const sectionTitle = document.getElementById('section-title');
  const sectionDesc = document.getElementById('section-desc');

  function playSection(idx) {
    const s = sections[idx];
    sectionTitle.textContent = `${idx + 1}. ${s.title}`;
    sectionDesc.textContent = s.desc;
    audioSrc.src = `assets/audio/${s.file}`; // v1.2: served from Render (in repo), not GitHub Releases
    audio.load();
    audio.play().catch(e => {
      // 移动端需要用户交互才能播放
      console.log('需要用户点击播放', e);
    });

    // 标记 active
    document.querySelectorAll('.section-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`.section-item[data-idx="${idx}"]`).classList.add('active');

    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // 暴露给闪卡页用
  window.passageId = passageId;
}