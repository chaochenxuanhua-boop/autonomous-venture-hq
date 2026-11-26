(function () {
  'use strict';

  var STORAGE_KEY = 'autonomous_venture_hq_scorecard_v1';

  var FALLBACK_MANIFEST = {
    owner_github: 'chaochenxuanhua-boop',
    owner_contact_email: 'chaochenxuanhua@gmail.com',
    ga4_measurement_id: 'G-F0ZLS15LNQ',
    active_feed_probes: [
      {
        venture_id: '07',
        title_ja: '07: SaaS値上げ・改悪フィード',
        endpoint_label: 'api/v1/changes.json',
        url: 'https://chaochenxuanhua-boop.github.io/saas-shrinkflation-watch/api/v1/changes.json',
        site_url: 'https://chaochenxuanhua-boop.github.io/saas-shrinkflation-watch/',
        cadence_ja: '毎日 15:17 JST'
      },
      {
        venture_id: '08',
        title_ja: '08: 米国FDA/CPSCリコールフィード',
        endpoint_label: 'api/v1/recalls.json',
        url: 'https://chaochenxuanhua-boop.github.io/us-seller-compliance-watch/api/v1/recalls.json',
        site_url: 'https://chaochenxuanhua-boop.github.io/us-seller-compliance-watch/',
        cadence_ja: '毎日 16:33 JST'
      },
      {
        venture_id: '09',
        title_ja: '09: 自己修復APIテレメトリ',
        endpoint_label: 'api/v1/health_status.json',
        url: 'https://chaochenxuanhua-boop.github.io/open-data-api-foundry/api/v1/health_status.json',
        site_url: 'https://chaochenxuanhua-boop.github.io/open-data-api-foundry/',
        cadence_ja: '毎日 14:47 JST'
      }
    ],
    systems: [],
    muse_14d_experiments: []
  };

  var SPLIT_DAY14_PRESET = [
    {
      venture_id: '07',
      elapsed_days: 14,
      gsc_impressions: 420,
      cta_clicks: 34,
      conversions: 4,
      cron_uptime_pct: 100.0
    },
    {
      venture_id: '08',
      elapsed_days: 14,
      gsc_impressions: 95,
      cta_clicks: 6,
      conversions: 0,
      cron_uptime_pct: 99.0
    },
    {
      venture_id: '09',
      elapsed_days: 14,
      gsc_impressions: 280,
      cta_clicks: 29,
      conversions: 3,
      cron_uptime_pct: 100.0
    },
    {
      venture_id: '06',
      elapsed_days: 16,
      gsc_impressions: 18,
      cta_clicks: 1,
      conversions: 0,
      cron_uptime_pct: 100.0
    }
  ];

  var state = {
    manifest: FALLBACK_MANIFEST,
    manifestHash: '--',
    activeCategory: 'ALL',
    searchQuery: '',
    probeResultsByVenture: {},
    experiments: [],
    defaultExperiments: []
  };

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function cloneJson(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  function formatJstTime(dateObj) {
    try {
      return dateObj.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch (_err) {
      return dateObj.toISOString();
    }
  }

  function extractFeedMetrics(payload) {
    var recordCount = 0;
    var collectionKey = '';
    var timestamp = '';
    var extraNote = '';

    if (Array.isArray(payload)) {
      recordCount = payload.length;
      collectionKey = 'items';
    } else if (payload && typeof payload === 'object') {
      var tsKeys = ['generated_at', 'updated_at', 'checked_at', 'verified_at', 'last_updated', 'timestamp'];
      for (var i = 0; i < tsKeys.length; i += 1) {
        if (payload[tsKeys[i]]) {
          timestamp = String(payload[tsKeys[i]]);
          break;
        }
      }

      var listKeys = [
        'changes',
        'recalls',
        'actors',
        'endpoints',
        'feeds',
        'services',
        'dispositions',
        'municipalities',
        'records',
        'items',
        'events',
        'products'
      ];
      for (var j = 0; j < listKeys.length; j += 1) {
        var key = listKeys[j];
        var val = payload[key];
        if (Array.isArray(val)) {
          recordCount = val.length;
          collectionKey = key;
          break;
        }
        if (val && typeof val === 'object') {
          recordCount = Object.keys(val).length;
          collectionKey = key;
          break;
        }
      }

      if (recordCount === 0) {
        var countKeys = ['total_changes', 'total_recalls', 'record_count', 'total_count', 'count'];
        for (var k = 0; k < countKeys.length; k += 1) {
          var ck = countKeys[k];
          if (typeof payload[ck] === 'number') {
            recordCount = payload[ck];
            collectionKey = ck;
            break;
          }
        }
      }

      if (Array.isArray(payload.healed_events)) {
        extraNote = '自己修復イベント: ' + payload.healed_events.length + '件';
      } else if (payload.overall_status) {
        extraNote = '状態: ' + String(payload.overall_status);
      }
    }

    return {
      recordCount: recordCount,
      collectionKey: collectionKey,
      timestamp: timestamp,
      extraNote: extraNote
    };
  }

  function evaluateExperiment(exp) {
    var elapsedDays = Math.max(1, parseInt(exp.elapsed_days, 10) || 14);
    var impressions = Math.max(0, parseInt(exp.gsc_impressions, 10) || 0);
    var ctaClicks = Math.max(0, parseInt(exp.cta_clicks, 10) || 0);
    var conversions = Math.max(0, parseInt(exp.conversions, 10) || 0);
    var cronUptime = Math.max(0, Math.min(100, parseFloat(exp.cron_uptime_pct) || 0));

    var targetImp = Math.max(1, parseInt(exp.target_impressions_14d, 10) || 150);
    var targetCta = Math.max(1, parseInt(exp.target_cta_clicks_14d, 10) || 10);
    var targetConv = Math.max(1, parseInt(exp.target_conversions_14d, 10) || 1);

    var impScore = Math.min(30, (impressions / targetImp) * 22);
    var ctaScore = Math.min(30, (ctaClicks / targetCta) * 22);
    var convScore = Math.min(30, (conversions / targetConv) * 24);
    var uptimeScore = (cronUptime / 100) * 10;

    var momentumScore = Math.round(Math.min(100, impScore + ctaScore + convScore + uptimeScore) * 10) / 10;
    var ctrPct = impressions > 0 ? Math.round((ctaClicks / impressions) * 10000) / 100 : 0;

    var decision = 'ITERATE';
    var badgeClass = 'tag-amber';
    var dotClass = 'dot-amber';
    var decisionLabel = 'ITERATE（改善継続）';
    var actionText = exp.iterate_playbook_ja || 'タイトルとCTA配置を改善して再計測';

    if (cronUptime < 80) {
      decision = 'FIX_CRON';
      badgeClass = 'tag-red';
      dotClass = 'dot-red';
      decisionLabel = '要修復（Cron異常）';
      actionText = '投資判断の前にGitHub Actionsのスケジュール実行ログを確認して修復';
    } else if (momentumScore >= 70 || (conversions >= targetConv && ctaClicks >= targetCta)) {
      decision = 'GO';
      badgeClass = 'tag-green';
      dotClass = 'dot-green';
      decisionLabel = 'GO（集中投資・拡大）';
      actionText = exp.go_playbook_ja || '上位チャネルと提携単価を拡大';
    } else if (elapsedDays >= 14 && momentumScore < 40 && conversions === 0) {
      decision = 'KILL_FREEZE';
      badgeClass = 'tag-slate';
      dotClass = 'dot-slate';
      decisionLabel = 'KILL / 凍結（無人保守）';
      actionText = exp.kill_playbook_ja || '人的工数をゼロにし無料Cronのみ維持';
    }

    return {
      venture_id: exp.venture_id,
      name_ja: exp.name_ja,
      monetization_model: exp.monetization_model || '',
      elapsed_days: elapsedDays,
      gsc_impressions: impressions,
      cta_clicks: ctaClicks,
      conversions: conversions,
      cron_uptime_pct: cronUptime,
      momentumScore: momentumScore,
      ctrPct: ctrPct,
      decision: decision,
      badgeClass: badgeClass,
      dotClass: dotClass,
      decisionLabel: decisionLabel,
      actionText: actionText
    };
  }

  function tierTagClass(tierKey) {
    if (tierKey === 'A8_ACTIVE' || tierKey === 'GCP_MEDIA_AFFILIATE') return 'tag-green';
    if (tierKey === 'RECURRING_SAAS_AFFILIATE' || tierKey === 'US_GOV_COMPLIANCE' || tierKey === 'SELF_HEALING_API_FOUNDRY') {
      return 'tag-blue';
    }
    if (tierKey === 'B2B_OUTREACH_SENT') return 'tag-amber';
    return 'tag-slate';
  }

  function renderProbeCards() {
    var grid = document.getElementById('probe-cards-grid');
    if (!grid) return;

    var probes = (state.manifest && state.manifest.active_feed_probes) || [];
    var htmlParts = [];

    for (var i = 0; i < probes.length; i += 1) {
      var p = probes[i];
      var res = state.probeResultsByVenture[p.venture_id];

      var badgeHtml = '<span class="status-tag tag-slate"><span class="status-dot dot-slate"></span>疎通確認前</span>';
      var latencyText = '-- ms';
      var countText = '-- 件';
      var tsText = p.cadence_ja || '--';

      if (res) {
        if (res.loading) {
          badgeHtml = '<span class="status-tag tag-blue"><span class="status-dot dot-blue"></span>取得中...</span>';
        } else if (res.ok) {
          badgeHtml =
            '<span class="status-tag tag-green"><span class="status-dot dot-green"></span>HTTP ' +
            escapeHtml(res.status) +
            ' 正常</span>';
          latencyText = escapeHtml(res.latencyMs) + ' ms';
          countText = escapeHtml(res.recordCount) + ' 件' + (res.collectionKey ? ' (' + escapeHtml(res.collectionKey) + ')' : '');
          tsText = res.timestamp ? '更新: ' + escapeHtml(res.timestamp.slice(0, 19)) : escapeHtml(p.cadence_ja || '');
        } else {
          badgeHtml =
            '<span class="status-tag tag-amber"><span class="status-dot dot-amber"></span>' +
            escapeHtml(res.errorLabel || '初回ビルド待機') +
            '</span>';
          latencyText = res.latencyMs ? escapeHtml(res.latencyMs) + ' ms' : '-- ms';
          countText = '待機中';
        }
      }

      htmlParts.push(
        '<article class="probe-tile">' +
          '<div class="probe-tile-top">' +
            '<span class="probe-title">' + escapeHtml(p.title_ja) + '</span>' +
            badgeHtml +
          '</div>' +
          '<div class="probe-endpoint mono">' + escapeHtml(p.endpoint_label) + '</div>' +
          '<div class="probe-metrics-row num">' +
            '<span>応答速度: <strong>' + latencyText + '</strong></span>' +
            '<span>データ件数: <strong>' + countText + '</strong></span>' +
            '<span>' + tsText + '</span>' +
          '</div>' +
          '<div class="probe-links-row no-print">' +
            '<a href="' + escapeHtml(p.url) + '" target="_blank" rel="noopener">JSONフィードを開く</a>' +
            '<a href="' + escapeHtml(p.site_url) + '" target="_blank" rel="noopener">Webアプリを開く</a>' +
          '</div>' +
        '</article>'
      );
    }

    grid.innerHTML = htmlParts.join('');
  }

  function renderSystemsTable() {
    var tbody = document.getElementById('systems-table-body');
    var countEl = document.getElementById('filtered-systems-count');
    if (!tbody) return;

    var allSystems = (state.manifest && state.manifest.systems) || [];
    var q = state.searchQuery.trim().toLowerCase();

    var filtered = allSystems.filter(function (sys) {
      if (state.activeCategory !== 'ALL' && sys.category !== state.activeCategory) {
        return false;
      }
      if (!q) return true;
      var hay = [
        sys.id,
        sys.code,
        sys.name_ja,
        sys.name_en,
        sys.repo_slug,
        sys.monetization_badge,
        sys.monetization_detail,
        sys.cron_schedule_ja
      ]
        .join(' ')
        .toLowerCase();
      return hay.indexOf(q) !== -1;
    });

    if (countEl) {
      countEl.textContent = filtered.length + ' / ' + allSystems.length + ' 系統';
    }

    if (filtered.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6">条件に一致するシステムはありません。検索条件をクリアしてください。</td></tr>';
      return;
    }

    var rowsHtml = filtered.map(function (sys) {
      var probeRes = state.probeResultsByVenture[sys.id];
      var healthHtml = '';
      if (!sys.probe_feed_url) {
        healthHtml = '<span class="status-tag tag-slate">静的UI / 手動系</span>';
      } else if (!probeRes) {
        healthHtml = '<span class="status-tag tag-slate"><span class="status-dot dot-slate"></span>待機中</span>';
      } else if (probeRes.loading) {
        healthHtml = '<span class="status-tag tag-blue"><span class="status-dot dot-blue"></span>確認中</span>';
      } else if (probeRes.ok) {
        healthHtml =
          '<span class="status-tag tag-green num"><span class="status-dot dot-green"></span>200 OK (' +
          escapeHtml(probeRes.recordCount) +
          '件)</span>';
      } else {
        healthHtml =
          '<span class="status-tag tag-amber"><span class="status-dot dot-amber"></span>' +
          escapeHtml(probeRes.errorLabel || '公開反映待ち') +
          '</span>';
      }

      var cronHtml =
        '<div>' + escapeHtml(sys.cron_schedule_ja || '') + '</div>' +
        (sys.cron_expression
          ? '<span class="cron-code mono">cron: ' + escapeHtml(sys.cron_expression) + '</span>'
          : '');

      var linksParts = [
        '<a href="' + escapeHtml(sys.live_url) + '" target="_blank" rel="noopener">公開画面</a>',
        '<a href="' + escapeHtml(sys.repo_url) + '" target="_blank" rel="noopener">GitHub Repo</a>'
      ];
      if (sys.probe_feed_url) {
        linksParts.push('<a href="' + escapeHtml(sys.probe_feed_url) + '" target="_blank" rel="noopener">JSON API</a>');
      }
      if (sys.rss_feed_url) {
        linksParts.push('<a href="' + escapeHtml(sys.rss_feed_url) + '" target="_blank" rel="noopener">RSS Feed</a>');
      }

      return (
        '<tr>' +
          '<td><span class="sys-id-badge mono">' + escapeHtml(sys.id) + '</span></td>' +
          '<td>' +
            '<div class="sys-title">' + escapeHtml(sys.name_ja) + '</div>' +
            '<div class="sys-sub">' + escapeHtml(sys.monetization_detail) + '</div>' +
          '</td>' +
          '<td>' +
            '<span class="status-tag ' + tierTagClass(sys.monetization_tier_key) + '">' +
              escapeHtml(sys.monetization_badge) +
            '</span>' +
          '</td>' +
          '<td>' + cronHtml + '</td>' +
          '<td>' + healthHtml + '</td>' +
          '<td class="no-print"><div class="row-links">' + linksParts.join('') + '</div></td>' +
        '</tr>'
      );
    });

    tbody.innerHTML = rowsHtml.join('');
  }

  function saveScorecardToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.experiments));
    } catch (_err) {
      // Ignore storage quota errors in private browsing
    }
  }

  function updateScorecardSummaryAndMailto(evaluatedRows) {
    var goCount = 0;
    var iterateCount = 0;
    var killCount = 0;

    for (var i = 0; i < evaluatedRows.length; i += 1) {
      var d = evaluatedRows[i].decision;
      if (d === 'GO') goCount += 1;
      else if (d === 'KILL_FREEZE') killCount += 1;
      else iterateCount += 1;
    }

    var sorted = evaluatedRows.slice().sort(function (a, b) {
      return b.momentumScore - a.momentumScore;
    });
    var topFocus = sorted.length > 0 ? 'Venture ' + sorted[0].venture_id + ' (' + sorted[0].momentumScore + 'pt)' : '--';

    var elGo = document.getElementById('scorecard-go-count');
    var elIter = document.getElementById('scorecard-iterate-count');
    var elKill = document.getElementById('scorecard-kill-count');
    var elTop = document.getElementById('scorecard-top-focus');

    if (elGo) elGo.textContent = String(goCount);
    if (elIter) elIter.textContent = String(iterateCount);
    if (elKill) elKill.textContent = String(killCount);
    if (elTop) elTop.textContent = topFocus;

    var mailLink = document.getElementById('mailto-memo-link');
    if (mailLink) {
      var lines = ['【Autonomous Venture HQ — 14日間Go/Kill投資判定サマリー】', ''];
      for (var j = 0; j < evaluatedRows.length; j += 1) {
        var r = evaluatedRows[j];
        lines.push(
          '- ' + r.name_ja + ' | ' + r.decisionLabel + ' | Score: ' + r.momentumScore +
          ' | GSC表示: ' + r.gsc_impressions + ' | CTA: ' + r.cta_clicks + ' | 成約: ' + r.conversions
        );
      }
      lines.push('');
      lines.push('最優先フォーカス: ' + topFocus);
      var subject = encodeURIComponent('[Autonomous Venture HQ] 14日間Go/Kill判定メモ');
      var body = encodeURIComponent(lines.join('\n'));
      mailLink.setAttribute('href', 'mailto:chaochenxuanhua@gmail.com?subject=' + subject + '&body=' + body);
    }
  }

  function renderScorecardTable() {
    var tbody = document.getElementById('scorecard-table-body');
    if (!tbody) return;

    var evaluatedRows = state.experiments.map(evaluateExperiment);
    updateScorecardSummaryAndMailto(evaluatedRows);

    var htmlRows = evaluatedRows.map(function (row, idx) {
      return (
        '<tr data-exp-index="' + idx + '">' +
          '<td>' +
            '<div class="sys-title">' + escapeHtml(row.name_ja) + '</div>' +
            '<div class="sys-sub">' + escapeHtml(row.monetization_model) + '</div>' +
          '</td>' +
          '<td class="num-col">' +
            '<input type="number" min="1" max="90" class="metric-input" data-idx="' + idx + '" data-field="elapsed_days" value="' + escapeHtml(row.elapsed_days) + '" aria-label="経過日数">' +
          '</td>' +
          '<td class="num-col">' +
            '<input type="number" min="0" step="10" class="metric-input" data-idx="' + idx + '" data-field="gsc_impressions" value="' + escapeHtml(row.gsc_impressions) + '" aria-label="GSC表示回数">' +
          '</td>' +
          '<td class="num-col">' +
            '<input type="number" min="0" class="metric-input" data-idx="' + idx + '" data-field="cta_clicks" value="' + escapeHtml(row.cta_clicks) + '" aria-label="CTAクリック数">' +
          '</td>' +
          '<td class="num-col">' +
            '<input type="number" min="0" class="metric-input" data-idx="' + idx + '" data-field="conversions" value="' + escapeHtml(row.conversions) + '" aria-label="成約・反応数">' +
          '</td>' +
          '<td class="num-col">' +
            '<input type="number" min="0" max="100" step="0.5" class="metric-input" data-idx="' + idx + '" data-field="cron_uptime_pct" value="' + escapeHtml(row.cron_uptime_pct) + '" aria-label="Cron稼働率">' +
          '</td>' +
          '<td class="num-col num">' +
            '<div><strong id="score-val-' + idx + '">' + escapeHtml(row.momentumScore) + '</strong> / 100</div>' +
            '<div class="sys-sub" id="ctr-val-' + idx + '">CTR ' + escapeHtml(row.ctrPct) + '%</div>' +
          '</td>' +
          '<td id="decision-cell-' + idx + '">' +
            '<span class="status-tag ' + row.badgeClass + '"><span class="status-dot ' + row.dotClass + '"></span>' + escapeHtml(row.decisionLabel) + '</span>' +
            '<div class="action-note">' + escapeHtml(row.actionText) + '</div>' +
          '</td>' +
        '</tr>'
      );
    });

    tbody.innerHTML = htmlRows.join('');
  }

  function refreshScorecardComputedCells() {
    var evaluatedRows = state.experiments.map(evaluateExperiment);
    updateScorecardSummaryAndMailto(evaluatedRows);

    var tbody = document.getElementById('scorecard-table-body');
    if (!tbody) return;
    var trs = tbody.querySelectorAll('tr[data-exp-index]');
    for (var i = 0; i < trs.length; i += 1) {
      var tr = trs[i];
      var idx = parseInt(tr.getAttribute('data-exp-index'), 10);
      var row = evaluatedRows[idx];
      if (!row) continue;

      var cells = tr.querySelectorAll('td');
      if (cells.length >= 8) {
        cells[6].innerHTML =
          '<div><strong>' + escapeHtml(row.momentumScore) + '</strong> / 100</div>' +
          '<div class="sys-sub">CTR ' + escapeHtml(row.ctrPct) + '%</div>';
        cells[7].innerHTML =
          '<span class="status-tag ' + row.badgeClass + '"><span class="status-dot ' + row.dotClass + '"></span>' + escapeHtml(row.decisionLabel) + '</span>' +
          '<div class="action-note">' + escapeHtml(row.actionText) + '</div>';
      }
    }
  }

  function fetchJsonWithTimeout(url, timeoutMs) {
    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = null;
    if (controller) {
      timer = setTimeout(function () {
        controller.abort();
      }, timeoutMs);
    }

    var start = performance.now();
    return fetch(url, {
      method: 'GET',
      cache: 'no-store',
      signal: controller ? controller.signal : undefined
    })
      .then(function (resp) {
        var latencyMs = Math.round(performance.now() - start);
        if (timer) clearTimeout(timer);
        if (!resp.ok) {
          return {
            ok: false,
            status: resp.status,
            latencyMs: latencyMs,
            errorLabel: 'HTTP ' + resp.status
          };
        }
        return resp.json().then(function (data) {
          var metrics = extractFeedMetrics(data);
          return {
            ok: true,
            status: resp.status,
            latencyMs: latencyMs,
            recordCount: metrics.recordCount,
            collectionKey: metrics.collectionKey,
            timestamp: metrics.timestamp,
            extraNote: metrics.extraNote
          };
        });
      })
      .catch(function (_err) {
        var latencyMs = Math.round(performance.now() - start);
        if (timer) clearTimeout(timer);
        return {
          ok: false,
          status: 0,
          latencyMs: latencyMs,
          errorLabel: '公開待機 / CORS制限'
        };
      });
  }

  function runLiveFeedProbes() {
    var btn = document.getElementById('run-live-probe-btn');
    var summaryEl = document.getElementById('probe-status-summary');
    var timeLabelEl = document.getElementById('last-probe-time-label');
    var footerProbedEl = document.getElementById('stat-last-probed');

    if (btn) btn.disabled = true;
    if (summaryEl) summaryEl.textContent = '公開JSONフィードへ並列fetch実行中...';

    var targets = [];
    var seenIds = {};

    var primaryProbes = (state.manifest && state.manifest.active_feed_probes) || [];
    for (var i = 0; i < primaryProbes.length; i += 1) {
      var p = primaryProbes[i];
      targets.push({ id: p.venture_id, url: p.url });
      seenIds[p.venture_id] = true;
      state.probeResultsByVenture[p.venture_id] = { loading: true };
    }

    var allSystems = (state.manifest && state.manifest.systems) || [];
    for (var j = 0; j < allSystems.length; j += 1) {
      var sys = allSystems[j];
      if (sys.probe_feed_url && !seenIds[sys.id]) {
        var resolvedUrl = sys.id === '10' ? './api/v1/hq_status.json' : sys.probe_feed_url;
        targets.push({ id: sys.id, url: resolvedUrl });
        seenIds[sys.id] = true;
        state.probeResultsByVenture[sys.id] = { loading: true };
      }
    }

    renderProbeCards();
    renderSystemsTable();

    var tasks = targets.map(function (t) {
      return fetchJsonWithTimeout(t.url, 6500).then(function (result) {
        state.probeResultsByVenture[t.id] = result;
        return { id: t.id, result: result };
      });
    });

    Promise.all(tasks).then(function (completed) {
      var okCount = 0;
      for (var k = 0; k < completed.length; k += 1) {
        if (completed[k].result && completed[k].result.ok) {
          okCount += 1;
        }
      }

      var nowStr = formatJstTime(new Date());
      if (timeLabelEl) timeLabelEl.textContent = '最終確認: ' + nowStr;
      if (footerProbedEl) footerProbedEl.textContent = nowStr;
      if (summaryEl) {
        summaryEl.textContent = '疎通完了: ' + okCount + ' / ' + completed.length + ' フィード応答';
      }
      if (btn) btn.disabled = false;

      renderProbeCards();
      renderSystemsTable();
    });
  }

  function bindEvents() {
    var searchInput = document.getElementById('system-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', function (e) {
        state.searchQuery = e.target.value || '';
        renderSystemsTable();
      });
    }

    var chipButtons = document.querySelectorAll('.filter-chip[data-category]');
    for (var i = 0; i < chipButtons.length; i += 1) {
      chipButtons[i].addEventListener('click', function (e) {
        var btn = e.currentTarget;
        state.activeCategory = btn.getAttribute('data-category') || 'ALL';
        for (var j = 0; j < chipButtons.length; j += 1) {
          chipButtons[j].classList.remove('active');
        }
        btn.classList.add('active');
        renderSystemsTable();
      });
    }

    var probeBtn = document.getElementById('run-live-probe-btn');
    if (probeBtn) {
      probeBtn.addEventListener('click', function () {
        runLiveFeedProbes();
      });
    }

    var scorecardBody = document.getElementById('scorecard-table-body');
    if (scorecardBody) {
      scorecardBody.addEventListener('input', function (e) {
        var target = e.target;
        if (!target || !target.hasAttribute('data-field')) return;
        var idx = parseInt(target.getAttribute('data-idx'), 10);
        var field = target.getAttribute('data-field');
        if (isNaN(idx) || !state.experiments[idx] || !field) return;

        var rawVal = target.value;
        state.experiments[idx][field] = field === 'cron_uptime_pct' ? parseFloat(rawVal) || 0 : parseInt(rawVal, 10) || 0;
        saveScorecardToStorage();
        refreshScorecardComputedCells();
      });
    }

    var splitBtn = document.getElementById('preset-day14-split-btn');
    if (splitBtn) {
      splitBtn.addEventListener('click', function () {
        state.experiments = cloneJson(state.defaultExperiments).map(function (baseRow) {
          for (var k = 0; k < SPLIT_DAY14_PRESET.length; k += 1) {
            if (SPLIT_DAY14_PRESET[k].venture_id === baseRow.venture_id) {
              return Object.assign({}, baseRow, SPLIT_DAY14_PRESET[k]);
            }
          }
          return baseRow;
        });
        saveScorecardToStorage();
        renderScorecardTable();
      });
    }

    var resetBtn = document.getElementById('preset-default-btn');
    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        state.experiments = cloneJson(state.defaultExperiments);
        try {
          localStorage.removeItem(STORAGE_KEY);
        } catch (_err) {
          // Ignore
        }
        renderScorecardTable();
      });
    }

    var exportBtn = document.getElementById('export-scorecard-json-btn');
    if (exportBtn) {
      exportBtn.addEventListener('click', function () {
        var evaluated = state.experiments.map(evaluateExperiment);
        var payload = {
          exported_at: new Date().toISOString(),
          source: 'Autonomous Venture HQ',
          results: evaluated
        };
        var blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
        var url = URL.createObjectURL(blob);
        var link = document.createElement('a');
        link.href = url;
        link.download = 'muse_14d_scorecard_report.json';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      });
    }

    var printBtn = document.getElementById('print-report-btn');
    if (printBtn) {
      printBtn.addEventListener('click', function () {
        window.print();
      });
    }
  }

  function hydrateExperimentsFromStorage(defaultExps) {
    state.defaultExperiments = cloneJson(defaultExps || []);
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length === state.defaultExperiments.length) {
          state.experiments = parsed;
          return;
        }
      }
    } catch (_err) {
      // Fallback to default manifest experiments
    }
    state.experiments = cloneJson(state.defaultExperiments);
  }

  function updateFooterStats() {
    var systems = (state.manifest && state.manifest.systems) || [];
    var scheduledCount = 0;
    for (var i = 0; i < systems.length; i += 1) {
      if (systems[i].is_scheduled_loop) scheduledCount += 1;
    }

    var elTotal = document.getElementById('stat-total-systems');
    var elSched = document.getElementById('stat-scheduled-loops');
    var elHash = document.getElementById('stat-manifest-hash');

    if (elTotal) elTotal.textContent = String(systems.length);
    if (elSched) elSched.textContent = String(scheduledCount);
    if (elHash) elHash.textContent = state.manifestHash;
  }

  function init() {
    bindEvents();

    Promise.all([
      fetch('./data/portfolio_manifest.json', { cache: 'no-store' })
        .then(function (r) { return r.ok ? r.json() : FALLBACK_MANIFEST; })
        .catch(function () { return FALLBACK_MANIFEST; }),
      fetch('./api/v1/hq_status.json', { cache: 'no-store' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; })
    ]).then(function (results) {
      var manifest = results[0] || FALLBACK_MANIFEST;
      var hqStatus = results[1];

      state.manifest = manifest;
      if (hqStatus && hqStatus.manifest_sha256) {
        state.manifestHash = String(hqStatus.manifest_sha256).slice(0, 16);
      }

      hydrateExperimentsFromStorage(manifest.muse_14d_experiments || []);
      updateFooterStats();
      renderProbeCards();
      renderSystemsTable();
      renderScorecardTable();
      runLiveFeedProbes();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
