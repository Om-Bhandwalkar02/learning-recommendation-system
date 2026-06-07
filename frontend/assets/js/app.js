/**
 * LearnPath AI — Frontend Application
 * Improvements: AI explain on cards, localStorage profile, Groq resume analyzer
 */

// ─── Config ────────────────────────────────────────────────────────────────────
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? `http://${window.location.hostname}:8000/api/v1`
  : '/api/v1';

// ─── State ─────────────────────────────────────────────────────────────────────
const state = {
  selectedSkills: [],
  freeOnly: false,
  availableRoles: [],
  groqEnabled: false,
  lastRecommendPayload: null,   // stored for AI explain context
};

// Course data store for safe modal access (avoids inline JSON in onclick)
const courseStore = new Map();
let courseStoreKey = 0;

function storeCourse(course) {
  const key = `c${courseStoreKey++}`;
  courseStore.set(key, course);
  return key;
}

// ─── LocalStorage Profile ─────────────────────────────────────────────────────

const PROFILE_KEY = 'learnpath_profile';

function saveProfile() {
  try {
    const profile = {
      skills:     state.selectedSkills,
      targetRole: document.getElementById('target-role')?.value || '',
      difficulty: document.getElementById('difficulty')?.value || 'All',
    };
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  } catch (e) { /* ignore */ }
}

function loadProfile() {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return;
    const profile = JSON.parse(raw);
    if (profile.skills?.length) {
      profile.skills.forEach(s => addSkill(s));
    }
    if (profile.targetRole) {
      const el = document.getElementById('target-role');
      if (el) el.value = profile.targetRole;
    }
    if (profile.difficulty) {
      const el = document.getElementById('difficulty');
      if (el) el.value = profile.difficulty;
    }
  } catch (e) { /* ignore */ }
}

// ─── API Client ────────────────────────────────────────────────────────────────

async function api(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiPost(endpoint, body) {
  return api(endpoint, { method: 'POST', body: JSON.stringify(body) });
}

// ─── Initialization ────────────────────────────────────────────────────────────

async function init() {
  await checkHealth();
  await loadStats();
  await loadRoles();
  loadProfile();          // restore saved profile
  lucide.createIcons();
}

async function checkHealth() {
  try {
    const data = await api('/health');
    state.groqEnabled = data.gemini_enabled;

    const badge = document.getElementById('api-status');
    badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-acid"></span><span>API Ready</span>`;
    badge.className = 'flex items-center gap-2 tag tag-acid text-xs';

    const statusText = document.getElementById('gemini-status-text');
    if (statusText) {
      statusText.textContent = data.gemini_enabled
        ? `✅ Groq AI active — ${data.ai_model || 'llama-3.3-70b-versatile'}`
        : '⚠️ Configure GROQ_API_KEY in .env to enable';
    }
  } catch (e) {
    const badge = document.getElementById('api-status');
    badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose"></span><span>API Offline</span>`;
    badge.className = 'flex items-center gap-2 tag tag-rose text-xs';
    console.error('Health check failed:', e);
  }
}

async function loadStats() {
  try {
    const data = await api('/stats');
    document.getElementById('stat-courses').textContent   = data.total_courses?.toLocaleString() || '—';
    document.getElementById('stat-skills').textContent    = data.skill_count?.toLocaleString() || '—';
    document.getElementById('stat-platforms').textContent = Object.keys(data.platforms || {}).length || '—';
  } catch (e) {
    console.error('Stats load failed:', e);
  }
}

async function loadRoles() {
  try {
    const data = await api('/roles');
    state.availableRoles = data.roles || [];
    document.getElementById('stat-roles').textContent = state.availableRoles.length || '—';

    ['roles-datalist', 'roles-datalist2'].forEach(id => {
      const dl = document.getElementById(id);
      if (dl) dl.innerHTML = state.availableRoles.map(r => `<option value="${r}">`).join('');
    });
  } catch (e) {
    console.error('Roles load failed:', e);
  }
}

// ─── Tab Navigation ────────────────────────────────────────────────────────────

const TABS = ['recommend', 'gap', 'roadmap', 'resume', 'advisor'];

function switchTab(tab) {
  TABS.forEach(t => {
    document.getElementById(`panel-${t}`)?.classList.toggle('hidden', t !== tab);
    document.getElementById(`tab-${t}`)?.classList.toggle('active', t === tab);
    document.getElementById(`tab-m-${t}`)?.classList.toggle('active', t === tab);
  });

  if (tab !== 'recommend') {
    document.getElementById('hero-section')?.classList.add('hidden');
  }

  setTimeout(() => lucide.createIcons(), 50);
}

// ─── Skill Management ──────────────────────────────────────────────────────────

function addSkill(skill) {
  const s = skill.trim().toLowerCase();
  if (!s || state.selectedSkills.includes(s)) return;
  state.selectedSkills.push(s);
  renderSelectedSkills();
  saveProfile();
}

function removeSkill(skill) {
  state.selectedSkills = state.selectedSkills.filter(s => s !== skill);
  document.querySelectorAll('.skill-pill').forEach(el => {
    if (el.dataset.skill === skill) el.classList.remove('selected');
  });
  renderSelectedSkills();
  saveProfile();
}

function addSkillFromInput() {
  const input = document.getElementById('skill-input');
  input.value.split(',').forEach(s => addSkill(s));
  input.value = '';
  input.focus();
}

function toggleSuggestion(el, skill) {
  el.dataset.skill = skill;
  if (el.classList.contains('selected')) {
    el.classList.remove('selected');
    removeSkill(skill);
  } else {
    el.classList.add('selected');
    addSkill(skill);
  }
}

function renderSelectedSkills() {
  const container = document.getElementById('selected-skills');
  if (!container) return;

  if (state.selectedSkills.length === 0) {
    container.innerHTML = '<span class="text-ghost text-xs italic">No skills selected yet</span>';
    return;
  }

  container.innerHTML = state.selectedSkills.map(skill => `
    <span class="tag tag-acid flex items-center gap-1 cursor-pointer"
          onclick="removeSkill('${escHtml(skill)}')">
      ${escHtml(skill)}
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </span>
  `).join('');
}

// ─── Free Only Toggle ──────────────────────────────────────────────────────────

function toggleFreeOnly(btn) {
  state.freeOnly = !state.freeOnly;
  const knob = btn.querySelector('span');
  if (state.freeOnly) {
    btn.style.background = '#B8FF3C';
    knob.style.transform = 'translateX(20px)';
    knob.style.background = '#0D0F12';
  } else {
    btn.style.background = '';
    knob.style.transform = '';
    knob.style.background = '';
  }
}

// ─── PANEL: Recommendations ────────────────────────────────────────────────────

async function getRecommendations() {
  if (state.selectedSkills.length === 0) {
    showToast('Please add at least one skill first.', 'warning');
    return;
  }

  const btn = document.getElementById('rec-btn');
  setLoading(btn, true);

  const payload = {
    profile: {
      current_skills:       state.selectedSkills,
      target_role:          document.getElementById('target-role').value || null,
      preferred_difficulty: document.getElementById('difficulty').value,
      n_recommendations:    parseInt(document.getElementById('n-recs').value),
      free_only:            state.freeOnly,
      max_duration_hours:   parseFloat(document.getElementById('max-duration').value) || null,
      completed_courses:    [],
    },
    sort_by:              document.getElementById('sort-by').value,
    include_explanations: true,
  };

  // Save profile after getting recs
  saveProfile();

  // Store for AI explain context
  state.lastRecommendPayload = payload;

  try {
    const data = await apiPost('/recommend', payload);
    renderRecommendations(data);
    showToast(`Found ${data.recommendations.length} courses in ${data.processing_time_ms?.toFixed(0)}ms`, 'success');
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderRecommendations(data) {
  document.getElementById('rec-empty').classList.add('hidden');
  const container = document.getElementById('rec-cards');
  container.classList.remove('hidden');

  if (!data.recommendations.length) {
    container.innerHTML = `<div class="card p-8 text-center col-span-2">
      <p class="text-ghost">No matching courses found. Try different skills or filters.</p>
    </div>`;
    return;
  }

  container.innerHTML = data.recommendations.map((c, i) => courseCard(c, i)).join('');
  setTimeout(() => lucide.createIcons(), 50);
}

function courseCard(c, index) {
  const key   = storeCourse(c);
  const pct   = `${c.recommendation_score}%`;
  const stars = '★'.repeat(Math.round(c.rating)) + '☆'.repeat(5 - Math.round(c.rating));

  return `
  <div class="card course-card p-5 fade-up" style="animation-delay:${index * 0.06}s">
    <div class="flex items-start gap-3 mb-3">
      <div class="score-ring" style="--pct:${pct}" data-tooltip="Match score">
        <span>${Math.round(c.recommendation_score)}</span>
      </div>
      <div class="flex-1 min-w-0">
        <h4 class="font-display font-semibold text-snow text-sm leading-snug line-clamp-2 cursor-pointer hover:text-acid transition-colors"
            onclick="openCourseModal('${key}')">
          ${escHtml(c.title)}
        </h4>
        <p class="text-ghost text-xs mt-1">${escHtml(c.provider)} · ${escHtml(c.platform)}</p>
      </div>
    </div>

    <div class="flex flex-wrap gap-1.5 mb-3">
      ${difficultyTag(c.difficulty)}
      ${platformBadge(c.platform)}
      ${c.certificate ? '<span class="tag tag-cyan">🎓 Certificate</span>' : ''}
      ${c.price_usd === 0 ? '<span class="tag tag-acid">Free</span>' : `<span class="tag tag-ghost">$${c.price_usd}</span>`}
    </div>

    <p class="text-ghost text-xs leading-relaxed mb-3 line-clamp-2">${escHtml(c.description)}</p>

    ${c.skill_overlap && c.skill_overlap.length ? `
    <div class="mb-3">
      <p class="text-ghost text-xs mb-1.5">Skill matches:</p>
      <div class="flex flex-wrap gap-1">
        ${c.skill_overlap.slice(0, 4).map(s => `<span class="tag tag-acid text-xs">${escHtml(s)}</span>`).join('')}
        ${c.skill_overlap.length > 4 ? `<span class="tag tag-ghost text-xs">+${c.skill_overlap.length - 4}</span>` : ''}
      </div>
    </div>` : ''}

    ${c.match_reasons && c.match_reasons.length ? `
    <div style="background:rgba(46,51,64,0.5);border-radius:10px;padding:10px;margin-bottom:12px">
      ${c.match_reasons.slice(0, 2).map(r => `
        <p class="text-ghost text-xs flex items-center gap-1.5">
          <span class="text-acid">✓</span> ${escHtml(r)}
        </p>`).join('')}
    </div>` : ''}

    <!-- AI Explanation section (hidden by default) -->
    <div id="ai-explain-${key}" class="hidden mb-3 p-3"
      style="border-radius:10px;background:rgba(124,110,255,0.07);border:1px solid rgba(124,110,255,0.2)">
      <p class="text-xs text-ghost" id="ai-explain-text-${key}">Loading AI explanation…</p>
    </div>

    <div class="flex items-center justify-between mt-auto pt-3 border-t border-border/50">
      <div class="flex items-center gap-3 text-xs text-ghost">
        <span class="text-amber">${stars}</span>
        <span>${c.rating.toFixed(1)}</span>
        <span>·</span>
        <span>${formatEnrolled(c.enrolled)}</span>
        <span>·</span>
        <span>${c.duration_hours}h</span>
      </div>
      <div class="flex gap-2">
        ${state.groqEnabled ? `
        <button onclick="aiExplain('${key}')" class="btn-secondary py-1 px-3 text-xs"
          style="border-color:rgba(124,110,255,0.3);color:#9D91FF"
          title="Get AI explanation">🤖 Why this?</button>` : ''}
        <button onclick="openCourseModal('${key}')" class="btn-secondary py-1 px-3 text-xs">Details</button>
      </div>
    </div>
  </div>`;
}

// ─── AI Explain ────────────────────────────────────────────────────────────────

async function aiExplain(key) {
  const course  = courseStore.get(key);
  if (!course) return;

  const box     = document.getElementById(`ai-explain-${key}`);
  const textEl  = document.getElementById(`ai-explain-text-${key}`);
  if (!box || !textEl) return;

  // Show loading
  box.classList.remove('hidden');
  textEl.textContent = '🤖 Getting AI explanation…';

  const profile = state.lastRecommendPayload?.profile || {};

  try {
    const data = await apiPost('/explain', {
      course_title:     course.title,
      user_skills:      profile.current_skills || state.selectedSkills,
      target_role:      profile.target_role || null,
      similarity_score: course.similarity_score || 0.5,
    });
    textEl.innerHTML = `<span class="text-violet font-medium">🤖 AI:</span> <span class="text-ghost">${escHtml(data.explanation)}</span>`;
  } catch (e) {
    textEl.textContent = '⚠️ Could not get AI explanation.';
  }
}

// ─── PANEL: Skill Gap ──────────────────────────────────────────────────────────

async function analyzeSkillGap() {
  const skillsRaw = document.getElementById('gap-skills').value;
  const role      = document.getElementById('gap-role').value.trim();

  if (!skillsRaw.trim()) { showToast('Please enter your current skills.', 'warning'); return; }
  if (!role)             { showToast('Please enter a target role.', 'warning'); return; }

  const skills = skillsRaw.split(',').map(s => s.trim()).filter(Boolean);
  const btn    = document.getElementById('gap-btn');
  setLoading(btn, true);

  try {
    const data = await apiPost('/skill-gap', { current_skills: skills, target_role: role });
    renderSkillGap(data);
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderSkillGap(data) {
  document.getElementById('gap-empty').classList.add('hidden');
  const container = document.getElementById('gap-content');
  container.classList.remove('hidden');

  const gapPct   = data.gap_percentage || 0;
  const fillPct  = 100 - gapPct;
  const gapColor = gapPct > 60 ? '#FF5C6A' : gapPct > 30 ? '#FFB547' : '#B8FF3C';

  container.innerHTML = `
    <div class="card p-5 fade-up">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h3 class="font-display font-bold text-snow text-lg">${escHtml(data.target_role)}</h3>
          <p class="text-ghost text-sm">Skill Gap Analysis</p>
        </div>
        <div class="text-center">
          <div class="text-4xl font-display font-extrabold" style="color:${gapColor}">${gapPct.toFixed(0)}%</div>
          <div class="text-ghost text-xs">Skills Gap</div>
        </div>
      </div>
      <div class="progress-bar mb-4">
        <div class="progress-fill" style="width:${fillPct}%;background:${gapColor}"></div>
      </div>
      <div class="flex justify-between text-xs text-ghost mb-4">
        <span>You have: <strong class="text-acid">${data.proficiency_skills.length}</strong></span>
        <span>Missing: <strong class="text-rose">${data.missing_skills.length}</strong></span>
        <span>Required: <strong>${data.required_skills.length}</strong></span>
      </div>
    </div>

    ${data.priority_skills && data.priority_skills.length ? `
    <div class="card p-5 fade-up fade-up-delay-1">
      <h4 class="font-display font-semibold text-snow mb-3 flex items-center gap-2">
        <i data-lucide="target" class="w-4 h-4 text-rose"></i>
        Priority Skills to Learn
      </h4>
      <div class="space-y-2">
        ${data.priority_skills.map((s, i) => `
        <div class="gap-skill">
          <div class="flex items-center gap-3">
            <span style="width:24px;height:24px;border-radius:50%;background:rgba(255,92,106,0.15);color:#FF5C6A;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center">${i + 1}</span>
            <span class="text-snow text-sm">${escHtml(s)}</span>
          </div>
          <span class="tag tag-rose text-xs">Missing</span>
        </div>`).join('')}
      </div>
    </div>` : ''}

    ${data.proficiency_skills && data.proficiency_skills.length ? `
    <div class="card p-5 fade-up fade-up-delay-2">
      <h4 class="font-display font-semibold text-snow mb-3 flex items-center gap-2">
        <i data-lucide="check-circle" class="w-4 h-4 text-acid"></i>
        Skills You Already Have
      </h4>
      <div class="flex flex-wrap gap-2">
        ${data.proficiency_skills.map(s => `<span class="tag tag-acid">${escHtml(s)}</span>`).join('')}
      </div>
    </div>` : ''}

    ${data.recommended_courses && data.recommended_courses.length ? `
    <div class="card p-5 fade-up fade-up-delay-3">
      <h4 class="font-display font-semibold text-snow mb-4 flex items-center gap-2">
        <i data-lucide="book-open" class="w-4 h-4 text-cyan"></i>
        Courses to Bridge the Gap
      </h4>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        ${data.recommended_courses.slice(0, 6).map(c => miniCourseCard(c)).join('')}
      </div>
    </div>` : ''}
  `;
  setTimeout(() => lucide.createIcons(), 50);
}

// ─── PANEL: Roadmap ────────────────────────────────────────────────────────────

async function generateRoadmap() {
  const skillsRaw = document.getElementById('rm-skills').value;
  const role      = document.getElementById('rm-role').value.trim();
  const timeframe = parseInt(document.getElementById('timeframe').value);

  if (!skillsRaw.trim()) { showToast('Please enter your current skills.', 'warning'); return; }
  if (!role)             { showToast('Please enter a target role.', 'warning'); return; }

  const skills = skillsRaw.split(',').map(s => s.trim()).filter(Boolean);
  const btn    = document.getElementById('rm-btn');
  setLoading(btn, true);

  try {
    const data = await apiPost('/roadmap', { current_skills: skills, target_role: role, timeframe_months: timeframe });
    renderRoadmap(data);
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderRoadmap(data) {
  document.getElementById('rm-empty').classList.add('hidden');
  const container = document.getElementById('rm-content');
  container.classList.remove('hidden');

  const phaseColors = ['#B8FF3C', '#38F5E8', '#7C6EFF', '#FFB547'];

  container.innerHTML = `
    <div class="card p-5 fade-up">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 class="font-display font-bold text-snow text-xl">${escHtml(data.target_role)} Roadmap</h3>
          <p class="text-ghost text-sm mt-1">${escHtml(data.overview)}</p>
        </div>
        <div class="flex gap-4 text-center">
          <div><div class="font-display font-bold text-amber text-2xl">${data.total_duration_months}</div><div class="text-ghost text-xs">months</div></div>
          <div><div class="font-display font-bold text-cyan text-2xl">${data.total_courses}</div><div class="text-ghost text-xs">courses</div></div>
          <div><div class="font-display font-bold text-acid text-2xl">${data.estimated_hours}h</div><div class="text-ghost text-xs">total</div></div>
        </div>
      </div>
    </div>

    ${(data.phases || []).map((phase, i) => {
      const color = phaseColors[i % phaseColors.length];
      const colorRgb = color === '#B8FF3C' ? '184,255,60'
                     : color === '#38F5E8' ? '56,245,232'
                     : color === '#7C6EFF' ? '124,110,255' : '255,181,71';
      return `
      <div class="flex gap-4 fade-up" style="animation-delay:${(i+1)*0.1}s">
        <div class="flex flex-col items-center">
          <div style="width:40px;height:40px;border-radius:50%;background:rgba(${colorRgb},0.15);border:2px solid rgba(${colorRgb},0.4);display:flex;align-items:center;justify-content:center;flex-shrink:0">
            <span class="font-display font-bold text-sm" style="color:${color}">${phase.phase_number}</span>
          </div>
          ${i < data.phases.length - 1 ? `<div class="phase-line flex-1 mt-2" style="min-height:40px"></div>` : ''}
        </div>
        <div class="card p-5 flex-1 mb-2">
          <div class="flex flex-wrap items-start justify-between gap-3 mb-3">
            <div>
              <h4 class="font-display font-semibold text-snow">${escHtml(phase.title)}</h4>
              <p class="text-ghost text-sm">${escHtml(phase.description)}</p>
            </div>
            <span class="tag tag-ghost">${phase.duration_weeks} weeks</span>
          </div>
          ${phase.skills_to_learn && phase.skills_to_learn.length ? `
          <div class="flex flex-wrap gap-1.5 mb-3">
            ${phase.skills_to_learn.map(s => `<span class="tag" style="background:rgba(${colorRgb},0.12);color:${color};border:1px solid rgba(${colorRgb},0.25)">${escHtml(s)}</span>`).join('')}
          </div>` : ''}
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            ${(phase.courses || []).slice(0, 4).map(c => miniCourseCard(c)).join('')}
          </div>
          ${phase.milestone ? `
          <div class="mt-3 p-3" style="border-radius:10px;background:rgba(${colorRgb},0.07);border:1px solid rgba(${colorRgb},0.2)">
            <p class="text-xs text-ghost flex items-center gap-2">
              <span style="color:${color}">🏁</span>
              <span><strong class="text-snow">Milestone:</strong> ${escHtml(phase.milestone)}</span>
            </p>
          </div>` : ''}
        </div>
      </div>`;
    }).join('')}
  `;
  setTimeout(() => lucide.createIcons(), 50);
}

// ─── PANEL: Resume ─────────────────────────────────────────────────────────────

async function analyzeResume() {
  const text       = document.getElementById('resume-text').value.trim();
  const targetRole = document.getElementById('resume-role').value.trim();

  if (!text || text.length < 50) {
    showToast('Please paste your resume text (at least 50 characters).', 'warning');
    return;
  }

  const btn = document.getElementById('resume-btn');
  setLoading(btn, true);

  try {
    const data = await apiPost('/resume-analyze', {
      resume_text: text,
      target_role: targetRole || null,
    });
    renderResumeResults(data);
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderResumeResults(data) {
  document.getElementById('resume-empty').classList.add('hidden');
  const container = document.getElementById('resume-content');
  container.classList.remove('hidden');

  const score = data.skill_strength_score || 0;
  const strengthColor = score >= 70 ? '#B8FF3C' : score >= 40 ? '#FFB547' : '#FF5C6A';

  container.innerHTML = `
    ${data.ai_powered ? `
    <div class="flex items-center gap-2 mb-1">
      <span class="tag tag-violet text-xs">🤖 Analyzed by Groq AI — llama-3.3-70b-versatile</span>
    </div>` : `
    <div class="flex items-center gap-2 mb-1">
      <span class="tag tag-ghost text-xs">🔍 Keyword-based analysis (add GROQ_API_KEY for AI-powered)</span>
    </div>`}

    <div class="card p-5 fade-up">
      <div class="flex items-center justify-between mb-3">
        <h4 class="font-display font-semibold text-snow flex items-center gap-2">
          <i data-lucide="zap" class="w-4 h-4" style="stroke:${strengthColor}"></i>
          Skill Strength Score
        </h4>
        <span class="text-3xl font-display font-extrabold" style="color:${strengthColor}">${score}/100</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" style="width:${score}%;background:${strengthColor}"></div>
      </div>
      <p class="text-ghost text-xs mt-2">Based on ${data.extracted_skills.length} skills detected across ${Object.keys(data.skill_categories).length} domains</p>
    </div>

    ${data.strengths && data.strengths.length ? `
    <div class="card p-5 fade-up">
      <h4 class="font-display font-semibold text-snow mb-3 flex items-center gap-2">
        <i data-lucide="star" class="w-4 h-4 text-amber"></i>
        Your Key Strengths
      </h4>
      <div class="space-y-2">
        ${data.strengths.map(s => `
        <div class="flex items-center gap-2 p-2" style="border-radius:8px;background:rgba(255,181,71,0.07)">
          <span class="text-amber">⭐</span>
          <span class="text-snow text-sm">${escHtml(s)}</span>
        </div>`).join('')}
      </div>
    </div>` : ''}

    ${Object.keys(data.skill_categories).length ? `
    <div class="card p-5 fade-up fade-up-delay-1">
      <h4 class="font-display font-semibold text-snow mb-4 flex items-center gap-2">
        <i data-lucide="layers" class="w-4 h-4 text-cyan"></i>
        Detected Skills by Domain
      </h4>
      <div class="space-y-3">
        ${Object.entries(data.skill_categories).map(([cat, skills]) => `
        <div>
          <p class="text-ghost text-xs font-medium mb-1.5">${escHtml(cat)}</p>
          <div class="flex flex-wrap gap-1.5">
            ${(Array.isArray(skills) ? skills : []).map(s => `<span class="tag tag-cyan">${escHtml(s)}</span>`).join('')}
          </div>
        </div>`).join('')}
      </div>
    </div>` : ''}

    ${data.suggested_roles && data.suggested_roles.length ? `
    <div class="card p-5 fade-up fade-up-delay-2">
      <h4 class="font-display font-semibold text-snow mb-3 flex items-center gap-2">
        <i data-lucide="briefcase" class="w-4 h-4 text-violet"></i>
        Suggested Career Roles
      </h4>
      <div class="flex flex-wrap gap-2">
        ${data.suggested_roles.map((r, i) => `
        <span class="tag ${i === 0 ? 'tag-violet' : 'tag-ghost'}" ${i === 0 ? 'style="font-size:13px;padding:6px 14px"' : ''}>
          ${i === 0 ? '🌟 ' : ''}${escHtml(r)}
        </span>`).join('')}
      </div>
    </div>` : ''}

    ${data.missing_skills_for_target && data.missing_skills_for_target.length ? `
    <div class="card p-5 fade-up fade-up-delay-3">
      <h4 class="font-display font-semibold text-snow mb-3 flex items-center gap-2">
        <i data-lucide="alert-circle" class="w-4 h-4 text-rose"></i>
        Missing Skills for Target Role
      </h4>
      <div class="flex flex-wrap gap-2">
        ${data.missing_skills_for_target.map(s => `<span class="tag tag-rose">${escHtml(s)}</span>`).join('')}
      </div>
    </div>` : ''}

    ${data.recommendations && data.recommendations.length ? `
    <div class="card p-5 fade-up">
      <h4 class="font-display font-semibold text-snow mb-4 flex items-center gap-2">
        <i data-lucide="book-open" class="w-4 h-4 text-acid"></i>
        Recommended Courses for You
      </h4>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        ${data.recommendations.slice(0, 6).map(c => miniCourseCard(c)).join('')}
      </div>
    </div>` : ''}
  `;
  setTimeout(() => lucide.createIcons(), 50);
}

// ─── PANEL: AI Advisor ─────────────────────────────────────────────────────────

async function getCareerAdvice() {
  const skillsRaw = document.getElementById('adv-skills').value.trim();
  const role      = document.getElementById('adv-role').value.trim();

  if (!skillsRaw) { showToast('Please enter your skills.', 'warning'); return; }
  if (!role)      { showToast('Please enter a target role.', 'warning'); return; }

  const skills = skillsRaw.split(',').map(s => s.trim()).filter(Boolean);
  const exp    = document.getElementById('adv-exp').value;
  const edu    = document.getElementById('adv-edu').value;
  const btn    = document.getElementById('adv-btn');
  setLoading(btn, true);

  try {
    const data = await apiPost('/career-advice', {
      current_skills:   skills,
      target_role:      role,
      experience_years: exp ? parseInt(exp) : null,
      education_level:  edu || null,
    });
    renderCareerAdvice(data);
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderCareerAdvice(data) {
  document.getElementById('adv-empty').classList.add('hidden');
  const container = document.getElementById('adv-content');
  container.classList.remove('hidden');

  container.innerHTML = `
    <div class="flex items-center gap-2 mb-2">
      <span class="tag tag-violet text-xs">🤖 ${escHtml(data.powered_by || 'AI Career Advisor')}</span>
    </div>

    <div class="card p-5 fade-up" style="border-color:rgba(124,110,255,0.25)">
      <h4 class="font-display font-semibold text-snow mb-3 flex items-center gap-2">
        <i data-lucide="message-square" class="w-4 h-4 text-violet"></i>
        Personalized Career Advice
      </h4>
      <p class="text-ghost text-sm leading-relaxed" style="white-space:pre-line">${escHtml(data.advice)}</p>
    </div>

    ${data.action_items && data.action_items.length ? `
    <div class="card p-5 fade-up fade-up-delay-1">
      <h4 class="font-display font-semibold text-snow mb-4 flex items-center gap-2">
        <i data-lucide="check-square" class="w-4 h-4 text-acid"></i>
        Action Items
      </h4>
      <div class="space-y-2">
        ${data.action_items.map((item, i) => `
        <div class="flex items-start gap-3 p-3" style="border-radius:10px;background:rgba(46,51,64,0.5)">
          <span style="width:24px;height:24px;border-radius:50%;background:rgba(184,255,60,0.15);color:#B8FF3C;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">${i + 1}</span>
          <p class="text-ghost text-sm">${escHtml(item)}</p>
        </div>`).join('')}
      </div>
    </div>` : ''}

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 fade-up fade-up-delay-2">
      ${data.timeline ? `
      <div class="card p-4">
        <h5 class="font-display font-semibold text-snow text-sm mb-2 flex items-center gap-2">
          <i data-lucide="clock" class="w-4 h-4 text-amber"></i> Timeline
        </h5>
        <p class="text-ghost text-sm">${escHtml(data.timeline)}</p>
      </div>` : ''}
      ${data.resources && data.resources.length ? `
      <div class="card p-4">
        <h5 class="font-display font-semibold text-snow text-sm mb-2 flex items-center gap-2">
          <i data-lucide="link" class="w-4 h-4 text-cyan"></i> Resources
        </h5>
        <ul class="space-y-1">
          ${data.resources.map(r => `<li class="text-ghost text-sm flex items-center gap-1.5">
            <span class="text-cyan">→</span> ${escHtml(r)}
          </li>`).join('')}
        </ul>
      </div>` : ''}
    </div>
  `;
  setTimeout(() => lucide.createIcons(), 50);
}

// ─── Mini Course Card ─────────────────────────────────────────────────────────

function miniCourseCard(c) {
  const key = storeCourse(c);
  return `
  <div class="p-3 cursor-pointer hover:border-violet/30 transition-colors"
       style="border-radius:12px;background:rgba(46,51,64,0.6);border:1px solid rgba(46,51,64,0.9)"
       onclick="openCourseModal('${key}')">
    <p class="text-snow text-xs font-medium line-clamp-2 mb-1.5">${escHtml(c.title)}</p>
    <div class="flex items-center gap-2 flex-wrap">
      <span class="tag tag-ghost text-xs">${escHtml(c.platform)}</span>
      ${c.recommendation_score ? `<span class="text-acid text-xs font-bold">${Math.round(c.recommendation_score)}%</span>` : ''}
      <span class="text-amber text-xs">★ ${c.rating ? c.rating.toFixed(1) : '—'}</span>
    </div>
  </div>`;
}

// ─── Course Modal ─────────────────────────────────────────────────────────────

function openCourseModal(key) {
  const course = courseStore.get(key);
  if (!course) return;

  const overlay = document.getElementById('modal-overlay');
  const header  = document.getElementById('modal-header');
  const body    = document.getElementById('modal-body');

  header.innerHTML = `
    <div>
      <div class="flex flex-wrap gap-2 mb-2">
        ${difficultyTag(course.difficulty)}
        ${platformBadge(course.platform)}
        ${course.certificate ? '<span class="tag tag-cyan">🎓 Certificate</span>' : ''}
      </div>
      <h3 class="font-display font-bold text-snow text-xl leading-snug">${escHtml(course.title)}</h3>
      <p class="text-ghost text-sm mt-1">${escHtml(course.provider)} · ${escHtml(course.platform)}</p>
    </div>`;

  body.innerHTML = `
    <div class="grid grid-cols-4 gap-3 mb-5">
      ${course.recommendation_score ? `
      <div class="stat-card items-center text-center">
        <span class="text-2xl font-display font-extrabold text-acid">${Math.round(course.recommendation_score)}</span>
        <span class="text-ghost text-xs">Score</span>
      </div>` : ''}
      <div class="stat-card items-center text-center">
        <span class="text-2xl font-display font-extrabold text-amber">★ ${course.rating ? course.rating.toFixed(1) : '—'}</span>
        <span class="text-ghost text-xs">Rating</span>
      </div>
      <div class="stat-card items-center text-center">
        <span class="text-xl font-display font-bold text-cyan">${formatEnrolled(course.enrolled)}</span>
        <span class="text-ghost text-xs">Enrolled</span>
      </div>
      <div class="stat-card items-center text-center">
        <span class="text-xl font-display font-bold text-violet">${course.duration_hours}h</span>
        <span class="text-ghost text-xs">Duration</span>
      </div>
    </div>

    <div class="mb-5">
      <h5 class="text-ghost text-xs font-medium uppercase tracking-wider mb-2">About This Course</h5>
      <p class="text-ghost text-sm leading-relaxed">${escHtml(course.description)}</p>
    </div>

    ${course.learning_outcomes ? `
    <div class="mb-5">
      <h5 class="text-ghost text-xs font-medium uppercase tracking-wider mb-2">What You'll Learn</h5>
      <p class="text-snow text-sm leading-relaxed">${escHtml(course.learning_outcomes)}</p>
    </div>` : ''}

    <div class="mb-5">
      <h5 class="text-ghost text-xs font-medium uppercase tracking-wider mb-2">Skills Covered</h5>
      <div class="flex flex-wrap gap-2">
        ${(course.skills || []).map(s => `<span class="tag tag-violet">${escHtml(s)}</span>`).join('')}
      </div>
    </div>

    ${course.prerequisites && course.prerequisites.length ? `
    <div class="mb-5">
      <h5 class="text-ghost text-xs font-medium uppercase tracking-wider mb-2">Prerequisites</h5>
      <div class="flex flex-wrap gap-2">
        ${course.prerequisites.map(p => `<span class="tag tag-ghost">${escHtml(p)}</span>`).join('')}
      </div>
    </div>` : ''}

    ${course.match_reasons && course.match_reasons.length ? `
    <div class="mb-5 p-3" style="border-radius:12px;background:rgba(184,255,60,0.05);border:1px solid rgba(184,255,60,0.15)">
      <h5 class="text-acid text-xs font-medium uppercase tracking-wider mb-2">Why Recommended</h5>
      ${course.match_reasons.map(r => `<p class="text-ghost text-sm flex items-center gap-2"><span class="text-acid">✓</span>${escHtml(r)}</p>`).join('')}
    </div>` : ''}

    <div class="flex items-center justify-between pt-4 border-t border-border/50">
      <div>
        <span class="font-display font-bold text-xl">
          ${course.price_usd === 0 ? '<span class="text-acid">Free</span>' : `<span class="text-snow">$${course.price_usd}</span>`}
        </span>
        <span class="text-ghost text-xs ml-2">on ${escHtml(course.platform)}</span>
      </div>
      <button class="btn-primary"
        onclick="window.open('https://www.google.com/search?q=${encodeURIComponent((course.title || '') + ' ' + (course.platform || ''))}','_blank')">
        <i data-lucide="external-link" class="w-4 h-4"></i>
        View Course
      </button>
    </div>
  `;

  overlay.classList.remove('hidden');
  overlay.classList.add('flex');
  setTimeout(() => lucide.createIcons(), 30);
}

function closeModal(event) {
  if (event.target === document.getElementById('modal-overlay')) {
    closeModalForce();
  }
}

function closeModalForce() {
  const overlay = document.getElementById('modal-overlay');
  overlay.classList.add('hidden');
  overlay.classList.remove('flex');
}

// ─── UI Helpers ────────────────────────────────────────────────────────────────

function setLoading(btn, loading) {
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn._original = btn.innerHTML;
    btn.innerHTML = `<svg class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" opacity="0.25"/>
      <path d="M21 12a9 9 0 00-9-9"/>
    </svg> Processing…`;
  } else {
    btn.disabled = false;
    btn.innerHTML = btn._original || btn.innerHTML;
  }
}

let toastTimer;
function showToast(msg, type = 'info') {
  const toast  = document.getElementById('toast');
  const msgEl  = document.getElementById('toast-msg');
  const icons  = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };

  msgEl.textContent = `${icons[type] || ''} ${msg}`;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
}

function difficultyTag(level) {
  const map = { Beginner: 'tag-acid', Intermediate: 'tag-amber', Advanced: 'tag-rose' };
  return `<span class="tag ${map[level] || 'tag-ghost'}">${escHtml(level)}</span>`;
}

function platformBadge(platform) {
  const map = { Coursera: 'tag-cyan', Udemy: 'tag-violet', Google: 'tag-amber', edX: 'tag-ghost' };
  return `<span class="tag ${map[platform] || 'tag-ghost'}">${escHtml(platform)}</span>`;
}

function formatEnrolled(n) {
  if (!n) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K`;
  return n.toString();
}

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ─── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  init();
  renderSelectedSkills();

  document.getElementById('skill-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addSkillFromInput(); }
  });

  // Save profile when target role or difficulty changes
  document.getElementById('target-role')?.addEventListener('change', saveProfile);
  document.getElementById('difficulty')?.addEventListener('change', saveProfile);
});
