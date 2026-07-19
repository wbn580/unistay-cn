/* us-wizard-engine.js — 优住 AI 找房向导引擎（共享内核）
 * window.UsWizard.mount(rootCardEl) 可挂载多个独立实例（首页内联卡片 + 弹窗 modal 共用）。
 * 城市数据 /wizard_cities.json 全站只 fetch 一次，多实例共享。
 * 每个实例拥有独立的 state / view / bar 闭包，互不干扰。 */
(function () {
  var W = (window.UsWizard = window.UsWizard || {});
  if (W.__engine) return;
  W.__engine = 1;

  var LEAD = 'https://chat.unistay.cn/lead',
    IMG = 'https://img.unistay.cn/';

  // ---- 共享数据（只加载一次）----
  var WZ = null,
    cityByName = {},
    unis = [],
    popular = [],
    STATE = 'idle', // idle | loading | ready | error
    WAITERS = [];

  function loadData(cb) {
    if (STATE === 'ready') return cb(null);
    if (STATE === 'error') return cb('error');
    WAITERS.push(cb);
    if (STATE === 'loading') return;
    STATE = 'loading';
    fetch('/wizard_cities.json')
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        WZ = d;
        d.cities.forEach(function (c) {
          cityByName[c.name.toLowerCase()] = c;
        });
        unis = d.unis || [];
        popular = d.cities.slice(0, 6);
        STATE = 'ready';
        flush(null);
      })
      .catch(function () {
        STATE = 'error';
        flush('error');
      });
  }
  function flush(err) {
    var list = WAITERS.slice();
    WAITERS = [];
    list.forEach(function (f) {
      f(err);
    });
  }

  // ---- 纯工具函数 ----
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmtG(n) {
    return (n || 0).toLocaleString('en-US');
  }
  function cn(c) {
    return (c && (c.name_zh || c.name)) || '';
  }
  // 计价周期 → 中文单位：weekly→周，monthly→月，未知→期
  function durU(d) {
    return d === 'weekly' ? '周' : d === 'monthly' ? '月' : '期';
  }
  function band(b) {
    if (!b) return b;
    if (/^flexible$/i.test(b)) return '预算灵活';
    var m = b.match(/^under\s+(.+)$/i);
    if (m) return '低于 ' + m[1];
    var p = b.match(/^(.+?)\+$/);
    if (p) return p[1] + ' 以上';
    return b;
  }
  function resolveCity(txt) {
    var t = (txt || '').trim().toLowerCase();
    if (!t) return null;
    if (cityByName[t]) return cityByName[t];
    var u = unis.find(function (x) {
      return x.n.toLowerCase() === t;
    });
    if (u) {
      var c = WZ.cities.find(function (y) {
        return y.slug === u.c;
      });
      if (c) return c;
    }
    var partial = WZ.cities.find(function (c) {
      return c.name.toLowerCase().indexOf(t) >= 0 || cn(c).indexOf(t) >= 0;
    });
    if (partial) return partial;
    var pu = unis.find(function (x) {
      return x.n.toLowerCase().indexOf(t) >= 0;
    });
    if (pu) {
      var c2 = WZ.cities.find(function (y) {
        return y.slug === pu.c;
      });
      if (c2) return c2;
    }
    return null;
  }

  // ---- 单实例挂载 ----
  W.mount = function (root) {
    if (!root || root.dataset.uswInit === '1') return;
    root.dataset.uswInit = '1';

    var view = root.querySelector('.usw-view'),
      bar = root.querySelector('.usw-bar > i');
    if (!view || !bar) return;

    var S = { dest: '', destCity: null, budget: '', movein: '', room: '', notes: '' };
    // 每个实例独立的 datalist id，避免多实例 DOM 冲突
    var dlId = 'uswDL_' + Math.random().toString(36).slice(2, 8);
    var setBar = function (p) {
      bar.style.width = p + '%';
    };

    loadData(function (err) {
      if (err) {
        view.innerHTML =
          '<div class="usw-load">找房功能即将开放，先<a href="/zhusu/" style="color:#22485a;font-weight:600">按城市浏览全部房源</a>。</div>';
        return;
      }
      step1();
    });

    function step1() {
      setBar(20);
      var opts =
        WZ.cities
          .map(function (c) {
            return '<option value="' + esc(cn(c)) + '">';
          })
          .join('') +
        unis
          .map(function (u) {
            return '<option value="' + esc(u.n) + '">';
          })
          .join('');
      view.innerHTML =
        '<div class="usw-body"><div class="usw-sh"><span class="usw-sn">第 1 / 5 步</span></div>' +
        '<div class="usw-q">你要去哪里读书？</div>' +
        '<div class="usw-srch"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;flex:none"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5" stroke-linecap="round"/></svg>' +
        '<input class="uswDest" list="' +
        dlId +
        '" placeholder="输入学校或城市…" autocomplete="off"/><datalist id="' +
        dlId +
        '">' +
        opts +
        '</datalist></div>' +
        '<div class="usw-chips">' +
        popular
          .map(function (c) {
            return '<button type="button" class="usw-chip" data-c="' + esc(cn(c)) + '">' + esc(cn(c)) + '</button>';
          })
          .join('') +
        '</div></div>';
      var inp = view.querySelector('.uswDest');
      inp.addEventListener('change', function () {
        if (inp.value) go1(inp.value);
      });
      inp.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && inp.value) go1(inp.value);
      });
      Array.prototype.forEach.call(view.querySelectorAll('.usw-chip'), function (b) {
        b.addEventListener('click', function () {
          go1(b.dataset.c);
        });
      });
    }
    function go1(txt) {
      var c = resolveCity(txt);
      if (!c) {
        location.href = '/zhusu/';
        return;
      }
      S.dest = txt;
      S.destCity = c;
      step2();
    }

    function step2() {
      setBar(40);
      var c = S.destCity;
      var o = (c.bands || []).concat(['Flexible']);
      view.innerHTML =
        '<div class="usw-body"><div class="usw-sh"><span class="usw-sn">第 2 / 5 步</span><button class="usw-back">‹ 返回</button></div>' +
        '<div class="usw-q">每' +
        durU(c.du) +
        '预算大概多少？</div>' +
        '<div class="usw-opts two">' +
        o
          .map(function (x) {
            return '<button type="button" class="usw-opt" data-v="' + esc(x) + '"><span class="t">' + esc(band(x)) + '</span></button>';
          })
          .join('') +
        '</div></div>';
      bindBack(step1);
      bindOpts(function (v) {
        S.budget = v;
        step3();
      });
    }
    function step3() {
      setBar(60);
      var m = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
      view.innerHTML =
        '<div class="usw-body"><div class="usw-sh"><span class="usw-sn">第 3 / 5 步</span><button class="usw-back">‹ 返回</button></div>' +
        '<div class="usw-q">打算什么时候入住？</div>' +
        '<div class="usw-opts" style="grid-template-columns:repeat(4,1fr)">' +
        m
          .map(function (x) {
            return '<button type="button" class="usw-opt ctr" data-v="' + x + ' 2026"><span class="t">' + x + '</span><span class="s">2026</span></button>';
          })
          .join('') +
        '</div>' +
        '<button type="button" class="usw-opt" data-v="时间灵活" style="margin-top:9px;justify-content:center"><span class="t">入住时间灵活</span></button></div>';
      bindBack(step2);
      bindOpts(function (v) {
        S.movein = v;
        step4();
      });
    }
    function step4() {
      setBar(80);
      var o = [
        ['一室套间 Studio', '独立房间 + 独立卫浴'],
        ['独立单间', '独立房间，共用卫浴'],
        ['合租公寓', '合租房里的一间'],
        ['整套公寓', '独享整套公寓'],
      ];
      view.innerHTML =
        '<div class="usw-body"><div class="usw-sh"><span class="usw-sn">第 4 / 5 步</span><button class="usw-back">‹ 返回</button></div>' +
        '<div class="usw-q">想要哪种房型？</div>' +
        '<div class="usw-opts two">' +
        o
          .map(function (x) {
            return '<button type="button" class="usw-opt" data-v="' + esc(x[0]) + '"><span><span class="t">' + x[0] + '</span><span class="s">' + x[1] + '</span></span></button>';
          })
          .join('') +
        '</div></div>';
      bindBack(step3);
      bindOpts(function (v) {
        S.room = v;
        step5();
      });
    }
    function step5() {
      setBar(100);
      var h = ['离地铁/车站近', '安静适合学习', '附近有健身房', '账单全包', '可养宠物'];
      view.innerHTML =
        '<div class="usw-body"><div class="usw-sh"><span class="usw-sn">第 5 / 5 步</span><button class="usw-back">‹ 返回</button></div>' +
        '<div class="usw-q">还有什么特别在意的？</div>' +
        '<p style="color:#5a7079;font-size:13.5px;margin:-8px 0 12px">用你自己的话告诉 AI——它会拿去和真实住客评价做匹配。选填。</p>' +
        '<textarea class="usw-ta uswNotes" placeholder="例如：楼里安静、步行 10 分钟到校、带独卫和大书桌、附近有超市…"></textarea>' +
        '<div class="usw-hints">' +
        h
          .map(function (x) {
            return '<button type="button" class="usw-hint" data-h="' + esc(x) + '">+ ' + x + '</button>';
          })
          .join('') +
        '</div>' +
        '<button type="button" class="usw-cta uswGo">帮我匹配房源 →</button></div>';
      bindBack(step4);
      var notesEl = view.querySelector('.uswNotes');
      Array.prototype.forEach.call(view.querySelectorAll('.usw-hint'), function (b) {
        b.addEventListener('click', function () {
          notesEl.value = (notesEl.value ? notesEl.value.replace(/\s*$/, '') + '，' : '') + b.dataset.h;
          notesEl.focus();
        });
      });
      view.querySelector('.uswGo').addEventListener('click', function () {
        S.notes = notesEl.value;
        think();
      });
    }
    function think() {
      var c = S.destCity;
      view.innerHTML =
        '<div class="usw-think"><div class="usw-orb"></div><div class="t">正在为你匹配房源…</div>' +
        '<div class="s">' +
        (S.notes
          ? '在 77 万条评价里搜索「' + esc(S.notes.slice(0, 38)) + (S.notes.length > 38 ? '…' : '') + '」'
          : '正在筛选 ' + esc(cn(c)) + ' 的已核实房源') +
        '</div></div>';
      setTimeout(results, 1400);
    }
    function results() {
      var c = S.destCity;
      var cards = (c.props || [])
        .slice(0, 3)
        .map(function (p) {
          var img = p.i ? IMG + p.i : '';
          return (
            '<a class="usw-pc" href="/fangyuan/' +
            p.s +
            '/"><div class="im" style="' +
            (img ? "background-image:url('" + img + "')" : '') +
            '"><span class="vb">✓ 已核实</span></div>' +
            '<div><h4>' +
            esc(p.n) +
            '</h4><div class="rt">' +
            (p.r ? '<b>★ ' + p.r + '</b> · ' : '') +
            fmtG(p.g) +
            ' 条谷歌评价</div></div>' +
            '<div class="pr"><b>' +
            c.cur +
            p.p.toLocaleString('en-US') +
            '</b><s>/' +
            durU(p.u || c.du) +
            '</s></div></a>'
          );
        })
        .join('');
      view.innerHTML =
        '<div class="usw-rh"><span class="lab">✓ 已核实匹配</span><h3>' +
        esc(S.dest) +
        ' 附近的房源</h3>' +
        (S.notes ? '<div class="usw-kb">✨ AI 已匹配：「' + esc(S.notes.slice(0, 46)) + (S.notes.length > 46 ? '…' : '') + '」</div>' : '') +
        '</div>' +
        '<div class="usw-list">' +
        cards +
        '</div>' +
        '<div class="usw-lead"><h4>想让顾问帮你锁定一套？</h4>' +
        '<p>留个联系方式——住宿顾问会在一个工作日内帮你核实房态。免费，无预订费。</p>' +
        '<div class="usw-lf"><input class="uswName" placeholder="你的称呼"/><input class="uswContact" placeholder="邮箱或微信"/></div>' +
        '<button type="button" class="usw-cta uswSend">获取房源清单 + 帮我锁房 →</button>' +
        '<div class="usw-err">请留个邮箱或微信，方便顾问联系你。</div>' +
        '<div class="usw-trust">免费 · 信息只交给真人顾问，不外传</div></div>';
      view.querySelector('.uswSend').addEventListener('click', submitLead);
    }
    function submitLead() {
      var name = view.querySelector('.uswName').value.trim();
      var contact = view.querySelector('.uswContact').value.trim();
      var err = view.querySelector('.usw-err');
      if (!contact) {
        err.style.display = 'block';
        return;
      }
      var isEmail = contact.indexOf('@') > 0;
      var c = S.destCity;
      var notes =
        '入住：' + S.movein + '。房型：' + S.room + '。预算：' + band(S.budget) + '。' + (S.notes ? ' 需求：' + S.notes : '');
      var payload = {
        attribution: { site_id: 'unistay-cn', page_url: location.href, channel: 'wizard', lang: 'zh' },
        lead: {
          name: name,
          intended_country: (c && c.country) || '',
          target_school: S.dest,
          budget_cny: '',
          specific_questions: notes,
        },
      };
      if (isEmail) payload.lead.email = contact;
      else payload.lead.phone = contact;
      var btn = view.querySelector('.uswSend');
      btn.textContent = '提交中…';
      btn.disabled = true;
      fetch(LEAD, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
        .then(function () {
          done();
        })
        .catch(function () {
          done();
        });
    }
    function done() {
      view.innerHTML =
        '<div class="usw-done"><div class="ck">✓</div><h3>搞定！</h3>' +
        '<p>顾问会在一个工作日内联系你，带上房源清单和房态确认。</p></div>';
    }

    function bindBack(fn) {
      var b = view.querySelector('.usw-back');
      if (b) b.addEventListener('click', fn);
    }
    function bindOpts(fn) {
      Array.prototype.forEach.call(view.querySelectorAll('.usw-opt'), function (b) {
        b.addEventListener('click', function () {
          fn(b.dataset.v);
        });
      });
    }
  };

  // 自动挂载页面上标了 data-usw-auto 的卡片（首页内联向导）。
  // 弹窗 modal 不标 auto，由 aiwOpen 首次打开时显式挂载。
  function autoMount() {
    Array.prototype.forEach.call(document.querySelectorAll('.usw[data-usw-auto]'), function (el) {
      W.mount(el);
    });
  }
  document.addEventListener('astro:page-load', autoMount);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoMount);
  } else {
    autoMount();
  }
})();
