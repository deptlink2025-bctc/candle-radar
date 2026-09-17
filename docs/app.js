/* Candle Radar — giao diện điện thoại. JS thuần, đọc data/latest.json do job sau phiên ghi.
   Không nhận dạng gì ở đây: thứ hiện trên màn hình đúng bằng thứ đã rung chuông. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const CFG = window.CR_CONFIG || {};
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const dmy = (iso) => iso ? iso.slice(0, 10).split("-").reverse().slice(0, 2).join("/") : "—";
  const dow = (iso) => ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"][new Date(iso + "T00:00:00").getDay()];
  const px = (v) => v == null ? "—" : Number(v).toFixed(2);
  const pad2 = (n) => String(n).padStart(2, "0");

  // Kết quả đo lại 39 mã × 750 ngày (reports/replay-2026-09-16.md): số lần/tháng và một dòng nhận xét.
  const REPLAY = {
    bull_engulfing:        { pm: 31.7, note: "Đo 2 năm: +0,98% sau 10 phiên, hơn mua-và-giữ (t 3,4) — có giá trị nhưng ồn." },
    morning_star:          { pm: 18.3, note: "Đo 2 năm: +0,45% sau 5 phiên (t 1,7) — yếu." },
    morning_doji_star:     { pm: 7.9,  note: "Đo 2 năm: +1,17% sau 5 phiên (t 2,6) — mẫu MUA tốt nhất." },
    three_white_soldiers:  { pm: 0.1,  note: "Gần như không xuất hiện trên nến ngày VN (3 lần/2 năm)." },
    hammer_confirm:        { pm: 7.6,  note: "Đo 2 năm: âm sau 5 và 10 phiên — không có giá trị dự báo." },
    inv_hammer_confirm:    { pm: 4.7,  note: "Đo 2 năm: ≈ 0 — không có giá trị dự báo." },
    piercing:              { pm: 11.9, note: "Đo 2 năm: ≈ 0 — không có giá trị dự báo." },
    bear_engulfing:        { pm: 41.9, note: "Đo 2 năm: giá vẫn tăng sau tín hiệu — không dự báo được giảm." },
    evening_star:          { pm: 9.9,  note: "Đo 2 năm: −0,33% sau 5 phiên (t −0,9) — yếu." },
    evening_doji_star:     { pm: 4.1,  note: "Đo 2 năm: không dự báo được giảm." },
    three_black_crows:     { pm: 1.4,  note: "Đo 2 năm: sau tín hiệu giá TĂNG +2% — ngược kỳ vọng." },
    hanging_man_confirm:   { pm: 2.6,  note: "Đo 2 năm: −0,75% sau 5 phiên rồi bật lại — yếu." },
    shooting_star_confirm: { pm: 13.0, note: "Đo 2 năm: không dự báo được giảm." },
    dark_cloud:            { pm: 16.0, note: "Đo 2 năm: −0,89% sau 10 phiên (t −2,5) — mẫu BÁN duy nhất có chút giá trị." },
    three_inside_down:     { pm: 9.7,  note: "Đo 2 năm: không dự báo được giảm." },
    // 3 mẫu khối lượng (reports/replay-2026-09-18-khoi-luong.md, 08/2022 → 09/2026)
    limit_up_climax:       { pm: 3.8,  note: "Đo 4 năm: +2,76% sau 10 phiên (t 3,2), thắng mua-và-giữ cả 5/5 năm kể cả cú sập 2022 — tín hiệu MUA vững nhất." },
    limit_down_volume:     { pm: 3.8,  note: "Đo 4 năm: +2,12% sau 10 phiên, +5,13% sau 20 phiên (60% đúng) — nhưng phụ thuộc thị trường, xem cảnh báo." },
    falling_three_methods: { pm: 1.1,  note: "Đo 4 năm: 56 lần, −0,78% sau 10 phiên (t −0,8) — 2 năm đúng chỉ 2026 (−9,8%), 2023–2024 sai chiều. Chưa ổn định." },
  };

  // Nến mẫu để vẽ glyph ở tab Cài đặt (o,h,l,c) — chỉ để nhận diện hình, không phải dữ liệu.
  const SAMPLES = {
    bull_engulfing: [[10, 10.3, 8.6, 9], [8.9, 11.4, 8.7, 11.2]],
    bear_engulfing: [[9, 10.3, 8.8, 10], [10.1, 10.3, 7.8, 8]],
    morning_star: [[11, 11.2, 8.9, 9.2], [9.1, 9.5, 8.5, 8.9], [9.3, 11.1, 9.2, 10.9]],
    evening_star: [[9, 11.2, 8.9, 10.9], [11, 11.5, 10.6, 11.2], [10.8, 10.9, 8.8, 9.1]],
    morning_doji_star: [[11, 11.2, 8.9, 9.2], [9.0, 9.5, 8.5, 9.02], [9.3, 11.1, 9.2, 10.9]],
    evening_doji_star: [[9, 11.2, 8.9, 10.9], [11.1, 11.5, 10.6, 11.08], [10.8, 10.9, 8.8, 9.1]],
    three_white_soldiers: [[8, 9.2, 7.9, 9], [8.6, 10.1, 8.5, 9.9], [9.4, 11, 9.3, 10.8]],
    three_black_crows: [[11, 11.1, 9.8, 10], [10.5, 10.6, 9.2, 9.4], [9.8, 9.9, 8.4, 8.6]],
    hammer_confirm: [[9.4, 9.65, 8.3, 9.6], [9.6, 10.6, 9.5, 10.5]],
    hanging_man_confirm: [[10.4, 10.65, 9.3, 10.6], [10.5, 10.6, 8.9, 9.1]],
    inv_hammer_confirm: [[9.4, 10.6, 9.35, 9.6], [9.7, 10.9, 9.6, 10.8]],
    shooting_star_confirm: [[10.4, 11.6, 10.35, 10.6], [10.5, 10.55, 9.4, 9.6]],
    piercing: [[11, 11.2, 9.3, 9.5], [9.4, 10.7, 9.2, 10.5]],
    dark_cloud: [[9.5, 11.2, 9.3, 11], [11.1, 11.3, 9.5, 10]],
    three_inside_down: [[9, 10.7, 8.9, 10.5], [10.2, 10.3, 9.5, 9.6], [9.6, 9.7, 8.6, 8.8]],
    limit_up_climax: [[9.6, 9.9, 9.4, 9.7], [9.7, 10.4, 9.6, 10.4]],
    limit_down_volume: [[10.4, 10.6, 10.1, 10.3], [10.3, 10.35, 9.55, 9.6]],
    falling_three_methods: [[10.8, 10.9, 9.4, 9.5], [9.6, 10.1, 9.5, 10.0], [10.0, 10.4, 9.9, 10.3], [10.3, 10.5, 10.1, 10.4], [10.3, 10.35, 8.9, 9.0]],
  };

  let D = null;

  // ---------------------------------------------------------------- mini-chart
  /* Vẽ n nến; `patBars` nến cuối tô màu (thuộc mẫu), nến cuối cùng khung vàng (nến xác nhận).
     W×H là kích thước SVG. Nến ngoài mẫu vẽ rỗng viền xám để mắt bám vào mẫu. */
  function miniChart(candles, patBars, W, H, thin) {
    const n = candles.length;
    if (!n) return "";
    const hi = Math.max(...candles.map((c) => c.h)), lo = Math.min(...candles.map((c) => c.l));
    const span = (hi - lo) || 1;
    const top = 6, bottom = H - 8;
    const y = (v) => bottom - (v - lo) / span * (bottom - top);
    const slot = W / n, bw = Math.max(6, Math.min(12, slot * 0.5));
    let out = `<line x1="0" y1="${H - 4}" x2="${W}" y2="${H - 4}" stroke="#D9D3C3" stroke-width="1"></line>`;
    candles.forEach((c, i) => {
      const cx = slot * i + slot / 2, inPat = i >= n - patBars, last = i === n - 1;
      const bull = c.c >= c.o, col = bull ? "#2E7D4F" : "#B84A3A";
      const yo = y(c.o), yc = y(c.c), bt = Math.min(yo, yc), bh = Math.max(1.5, Math.abs(yo - yc));
      const sw = thin ? 1.5 : 2;
      if (inPat) {
        out += `<line x1="${cx}" y1="${y(c.h)}" x2="${cx}" y2="${y(c.l)}" stroke="${col}" stroke-width="${sw}"></line>`;
        out += `<rect x="${cx - bw / 2}" y="${bt}" width="${bw}" height="${bh}" fill="${col}"></rect>`;
      } else {
        out += `<line x1="${cx}" y1="${y(c.h)}" x2="${cx}" y2="${y(c.l)}" stroke="#4B5A52" stroke-width="1.5"></line>`;
        out += `<rect x="${cx - bw / 2 + 1}" y="${bt}" width="${bw - 2}" height="${bh}" fill="#F7F4EC" stroke="#4B5A52" stroke-width="1.5"></rect>`;
      }
      if (last && !thin) out += `<rect x="${cx - bw / 2 - 3}" y="${y(c.h) - 3}" width="${bw + 6}" height="${y(c.l) - y(c.h) + 6}" rx="3" fill="none" stroke="#C99A2E" stroke-width="2"></rect>`;
    });
    return out;
  }
  const glyph = (pid, bars) => {
    const cs = (SAMPLES[pid] || []).map((a) => ({ o: a[0], h: a[1], l: a[2], c: a[3] }));
    return `<svg viewBox="0 0 56 36" aria-hidden="true">${miniChart(cs, bars || cs.length, 56, 36, true)}</svg>`;
  };

  // ---------------------------------------------------------------- tải dữ liệu
  async function load() {
    try {
      const r = await fetch("data/latest.json", { cache: "no-cache" });
      if (!r.ok) throw new Error("Chưa có data/latest.json — job sau phiên chưa chạy lần nào.");
      D = await r.json();
    } catch (err) {
      $("strip").innerHTML = `<span class="v">Chưa có dữ liệu</span><span class="note">${esc(err.message)}</span>`;
      renderSettings();
      return;
    }
    renderToday(); renderHistory(); renderSettings();
  }

  // ---------------------------------------------------------------- Hôm nay
  function renderToday() {
    const sig = D.signals || [], stale = D.stale || [], src = D.source || {};
    const nSym = new Set(sig.map((s) => s.symbol)).size;
    $("todaySub").textContent = `Mẫu hình nến đảo chiều trên nến đã chốt — ${D.watchlist ? D.watchlist.n : "?"} mã đang theo dõi.`;
    const gen = D.generated_at ? D.generated_at.slice(11, 16) : "";
    let note = `Nguồn DNSE chốt lúc ${gen}`;
    if (src.late) note += " · nguồn chốt muộn, chạy lại ở cron dự phòng";
    if (stale.length) note += ` · ${stale.length} mã chưa khớp lệnh hôm nay (${stale.slice(0, 4).map((s) => s.symbol).join(", ")}${stale.length > 4 ? "…" : ""})`;
    if (src.dnse_error) note += ` · <b>DNSE lỗi: ${esc(src.dnse_error)}</b>`;
    if (D.watchlist && D.watchlist.source === "cache") note += " · danh mục dùng bản chụp (KingStock không trả lời)";
    $("strip").innerHTML =
      `<span class="k">Phiên ${dmy(D.trade_date)}</span><svg aria-hidden="true"><use href="#i-arrow"/></svg>` +
      `<span class="v">${src.n_priced || 0} mã đã quét</span><svg aria-hidden="true"><use href="#i-arrow"/></svg>` +
      `<span class="v">${sig.length ? `${sig.length} mẫu hình · ${nSym} mã` : "không có mẫu hình"}</span>` +
      `<span class="note">${note}</span>`;

    if (!sig.length) {
      $("todayBody").innerHTML = `<div class="empty"><b>Không có mẫu hình nào hôm nay</b>Đã quét ${src.n_priced || 0} mã trên nến đã chốt phiên ${dmy(D.trade_date)}. Không có gì để làm — đó cũng là một câu trả lời.</div>`;
      return;
    }
    // Gộp theo mã: một thẻ một mã, nhiều mẫu thì liệt kê thêm
    const bySym = new Map();
    sig.forEach((s) => { if (!bySym.has(s.symbol)) bySym.set(s.symbol, []); bySym.get(s.symbol).push(s); });
    let i = 0;
    $("todayBody").innerHTML = `<div class="cards">` + [...bySym.entries()].map(([sym, list]) => {
      const s = list[0], buy = s.direction === "buy";
      const dirs = new Set(list.map((x) => x.direction));
      const chip = dirs.size > 1 ? `<span class="chip sell">TRÁI CHIỀU</span>` : `<span class="chip ${buy ? "buy" : "sell"}">${buy ? "MUA" : "BÁN"}</span>`;
      const chg = s.change_pct, ccls = chg > 0 ? "up" : chg < 0 ? "down" : "flat";
      const extra = list.length > 1 ? `<div class="more">Cùng phiên còn: <b>${list.slice(1).map((x) => esc(x.name)).join(", ")}</b></div>` : "";
      const rp = REPLAY[s.pattern] || {};
      i += 1;
      return `<div class="card ${dirs.size > 1 ? "sell" : buy ? "buy" : "sell"}">
        <div class="top"><div class="num">${pad2(i)}</div><h3>${esc(sym)} · ${esc(s.name)}</h3>${chip}</div>
        <div class="desc">${esc(s.hint)}${s.company_name ? ` <span class="mute">— ${esc(s.company_name)}</span>` : ""}</div>
        <div class="chart"><svg viewBox="0 0 132 72" aria-hidden="true">${miniChart(s.candles || [], s.bars || 2, 132, 72, false)}</svg>
          <div class="px"><div class="k">Đóng cửa</div><div class="v">${px(s.price)}</div><div class="c ${ccls}">${chg == null ? "—" : (chg > 0 ? "+" : "") + chg.toFixed(1) + "% hôm nay"}</div></div></div>
        <div class="kv"><div class="a"><span>Gợi ý</span><span>${esc(s.advice)}</span></div><div class="w"><span>Lưu ý</span><span>${esc(rp.note || "")}</span></div>${s.caution ? `<div class="c"><span>Cảnh báo</span><span>${esc(s.caution)}</span></div>` : ""}</div>
        ${extra}</div>`;
    }).join("") + `</div>`;
  }

  // ---------------------------------------------------------------- Lịch sử
  function renderHistory() {
    const hist = D.history || [];
    $("histKicker").textContent = `${hist.length} phiên gần nhất`;
    const nb = hist.reduce((a, h) => a + h.n_buy, 0), ns = hist.reduce((a, h) => a + h.n_sell, 0);
    const per = hist.length ? ((nb + ns) / hist.length).toFixed(1) : "—";
    $("totals").innerHTML =
      `<div class="tot" style="background:var(--sage);border-color:var(--sage-line)"><div class="k">Mua</div><div class="v">${nb}</div></div>` +
      `<div class="tot" style="background:var(--blush);border-color:var(--blush-line)"><div class="k">Bán</div><div class="v">${ns}</div></div>` +
      `<div class="tot" style="background:var(--peach);border-color:var(--peach-line)"><div class="k">Mỗi phiên</div><div class="v">${per}</div></div>`;
    if (!hist.length) { $("days").innerHTML = `<div class="empty"><b>Chưa có phiên nào</b>Job ghi lại đây sau mỗi phiên đã quét.</div>`; return; }
    $("days").innerHTML = hist.map((h) => {
      const chips = [];
      if (h.n_buy) chips.push(`<span class="chip buy">${h.n_buy} MUA</span>`);
      if (h.n_sell) chips.push(`<span class="chip sell">${h.n_sell} BÁN</span>`);
      if (!h.n_buy && !h.n_sell) chips.push(`<span class="chip soft">Không có</span>`);
      if (h.late) chips.push(`<span class="chip late">Nguồn chốt muộn</span>`);
      const list = h.items && h.items.length ? h.items.map(esc).join(" · ") : `Đã quét, không mẫu nào khớp.`;
      return `<div class="day"><div class="top"><b>${dow(h.date)} ${dmy(h.date)}</b>${chips.join("")}</div><div class="list">${list}</div></div>`;
    }).join("");
  }

  // ---------------------------------------------------------------- Cài đặt
  function renderSettings() {
    const pats = (D && D.patterns) || null;
    const disabled = new Set(((D && D.settings) || {}).patterns_disabled || []);
    const ids = pats ? Object.keys(pats) : Object.keys(SAMPLES);
    const row = (pid) => {
      const m = pats ? pats[pid] : { name: pid, hint: "" };
      const off = disabled.has(pid), rp = REPLAY[pid] || {};
      return `<div class="prow${off ? " off" : ""}">${glyph(pid, m.bars)}<div class="t"><div class="n">${esc(m.name)}</div><div class="h">${esc(m.hint)}</div></div><div class="f">${rp.pm != null ? rp.pm.toFixed(1) + "/th" : ""}</div><div class="tg ${off ? "off" : "on"}" title="${off ? "Đang tắt" : "Đang bật"}"></div></div>`;
    };
    const buys = ids.filter((p) => !pats || pats[p].direction === "buy"), sells = ids.filter((p) => pats && pats[p].direction === "sell");
    $("buyRows").innerHTML = buys.map(row).join(""); $("buyCount").textContent = `${buys.length} mẫu`;
    $("sellRows").innerHTML = sells.map(row).join(""); $("sellCount").textContent = `${sells.length} mẫu`;
    fetch("data/state.json", { cache: "no-cache" }).then((r) => r.ok ? r.json() : null).then((st) => {
      if (!st) return;
      const dv = st.devices || {}, p = st.push || {};
      let s = `Job chạy lần cuối ${st.last_run ? st.last_run.slice(0, 16).replace("T", " ") : "—"} · ${dv.n || 0} máy đã đăng ký (${dv.source || "—"}) · VAPID ${dv.vapid ? "OK" : "THIẾU"}`;
      if (p.mode) s += ` · lần báo gần nhất: ${p.mode === "digest" ? "tổng hợp" : p.mode === "per_symbol" ? p.n_symbols + " mã" : "không có mẫu"}, gửi ${p.sent || 0}`;
      if (st.push_gone_at) s += ` · <b style="color:var(--sell)">có máy đã huỷ đăng ký (${st.push_gone_at.slice(0, 10)}) — bấm Đăng ký lại</b>`;
      $("stateFoot").innerHTML = s;
    }).catch(() => {});
  }

  // ---------------------------------------------------------------- push (chép tudoanh-radar)
  const b64ToU8 = (s) => { const p = "=".repeat((4 - s.length % 4) % 4); const b = atob((s + p).replace(/-/g, "+").replace(/_/g, "/")); return Uint8Array.from(b, (c) => c.charCodeAt(0)); };
  const SW = "sw.js?v=1";
  async function pushStatus() {
    const st = $("pushState");
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) { st.textContent = "Trình duyệt này không hỗ trợ thông báo đẩy."; $("pushBtn").disabled = true; return; }
    if (!CFG.VAPID_PUBLIC) { st.textContent = "Chưa có VAPID_PUBLIC trong config.js."; $("pushBtn").disabled = true; return; }
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      st.textContent = CFG.WORKER_URL ? "Máy này đã đăng ký · máy chủ tạm của GitHub đánh thức được kể cả khi app đóng."
        : "Máy này đã tạo địa chỉ nhận · đảm bảo đoạn mã bên dưới đã được dán vào GitHub.";
      $("pushBtn").textContent = "Đăng ký lại"; $("testBtn").hidden = !CFG.WORKER_URL;
      if (!CFG.WORKER_URL) showSubCode(sub);
    } else { st.textContent = "Máy này chưa đăng ký nhận thông báo."; }
  }
  function showSubCode(sub) {
    const code = JSON.stringify([sub.toJSON()]);
    $("subCodeWrap").innerHTML = `<div class="subcode"><b>Đoạn mã đăng ký của máy này.</b> Dán vào GitHub → Settings → Secrets and variables → Actions → <span class="mono">PUSH_SUBS_FALLBACK</span> (nhiều máy thì nối các đoạn trong cùng một mảng JSON). Làm một lần mỗi máy.
      <textarea id="subTxt" readonly></textarea><div class="btns" style="margin-top:6px"><button type="button" class="btn" id="copySub">Sao chép</button></div></div>`;
    $("subTxt").value = code;
    $("copySub").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(code); toast("Đã sao chép", "Dán vào GitHub Secret PUSH_SUBS_FALLBACK."); }
      catch (_) { $("subTxt").select(); document.execCommand("copy"); toast("Đã sao chép", ""); }
    });
  }
  const swReady = () => Promise.race([
    navigator.serviceWorker.ready,
    new Promise((_, rej) => setTimeout(() => rej(new Error("Phần chạy nền chưa sẵn sàng — đóng hẳn app, mở lại rồi bấm lần nữa")), 8000)),
  ]);
  $("pushBtn").addEventListener("click", async () => {
    const st = $("pushState"), btn = $("pushBtn");
    btn.disabled = true;
    try {
      if (Notification.permission === "denied") { st.textContent = "Điện thoại đang CHẶN thông báo của trang này. Mở Cài đặt trình duyệt → Cài đặt trang web → Thông báo → bật, rồi bấm lại."; return; }
      st.textContent = "Đang xin quyền thông báo… (nếu hiện hộp thoại, bấm Cho phép)";
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { st.textContent = "Anh chưa cho phép. Bấm lại và chọn Cho phép."; return; }
      st.textContent = "Đang chuẩn bị phần chạy nền…";
      if (!navigator.serviceWorker.controller) { try { await navigator.serviceWorker.register(SW); } catch (_) { /* thử tiếp */ } }
      const reg = await swReady();
      st.textContent = "Đang tạo địa chỉ nhận với Google…";
      let sub = await reg.pushManager.getSubscription();
      if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToU8(CFG.VAPID_PUBLIC) });
      if (CFG.WORKER_URL) {
        const r = await fetch(CFG.WORKER_URL + "/subscribe", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.assign({ ua: navigator.userAgent.slice(0, 120) }, sub.toJSON())) });
        if (!r.ok) throw new Error("Worker trả lỗi " + r.status);
        toast("Đã đăng ký máy này", "Từ giờ cảnh báo sau phiên sẽ tới đây.");
      } else {
        toast("Đã tạo địa chỉ nhận", "Sao chép đoạn mã bên dưới và dán vào GitHub — một lần cho máy này.");
      }
      await pushStatus();
    } catch (err) {
      st.textContent = "Không đăng ký được: " + (err && err.message ? err.message : err) + " — chụp màn hình dòng này gửi lại.";
    } finally { btn.disabled = false; }
  });
  $("testBtn").addEventListener("click", async () => {
    try {
      const r = await fetch(CFG.WORKER_URL + "/test", { method: "POST" });
      toast(r.ok ? "Đã yêu cầu gửi thử" : "Gửi thử lỗi " + r.status, r.ok ? "Thông báo thật sẽ tới trong vài giây." : "");
    } catch (err) { alert(err.message); }
  });
  let toastTimer = null;
  function toast(t, b) { $("toastTitle").textContent = t; $("toastBody").textContent = b || ""; $("toast").classList.add("on"); clearTimeout(toastTimer); toastTimer = setTimeout(() => $("toast").classList.remove("on"), 5000); }
  $("toast").addEventListener("click", () => $("toast").classList.remove("on"));

  // ---------------------------------------------------------------- tab + boot
  const tabs = document.querySelectorAll('nav[role="tablist"] button');
  function switchTab(name) {
    tabs.forEach((x) => x.setAttribute("aria-selected", x.dataset.tab === name ? "true" : "false"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("on", p.id === "p-" + name));
    $("main").scrollTop = 0;
  }
  tabs.forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));
  function applyHash() { const m = /^#(today|history|settings)$/.exec(location.hash); if (m) switchTab(m[1]); }
  window.addEventListener("hashchange", applyHash);

  if ("serviceWorker" in navigator) navigator.serviceWorker.register(SW).catch(() => {});
  load().then(() => { applyHash(); pushStatus(); });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") load(); });
})();
