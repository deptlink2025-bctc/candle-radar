"""Job sau phiên — chạy trong GitHub Actions 15:35 T2–T6 (hoặc local: python -m job.run_daily).

Luồng: danh mục KingStock → nến ngày DNSE cho từng mã → nhận dạng 15 mẫu trên NẾN CUỐI ĐÃ CHỐT
→ Web Push (gộp theo mã) → ghi docs/data/latest.json, state.json, daily/<ngày>.json.

Idempotent: nếu hôm nay đã có file daily và không có --force thì thoát (các cron dự phòng chạy
lại chỉ khi lần trước bị GitHub trễ/bỏ hoặc nguồn chưa chốt). Không có CSDL: file daily theo
ngày chính là chốt chống bắn trùng.

Nguồn chưa chốt (bẫy 14/09/2026, chép cơ chế từ tudoanh-radar): mỗi mã có nến hôm nay phải có
nến 1' chạm ATC 14:45 mới được tin; ≥ 20 % mã thanh khoản thiếu → KHÔNG ghi file hôm nay, cron
sau thử lại. Mã ít khớp lệnh (IDP, TDM…) mang nến cũ nhiều ngày → ghi vào `stale`, KHÔNG xét
mẫu — nếu xét thì một mẫu cũ sẽ được "phát hiện lại" mỗi ngày.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta

from common import dnse
from common.config import SITE_DATA, TZ

from . import patterns, push, settings, watchlist

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("job")

LATEST = SITE_DATA / "latest.json"
STATE = SITE_DATA / "state.json"
DAILY = SITE_DATA / "daily"

# Số nến gửi kèm mỗi tín hiệu để giao diện vẽ mini-chart (≥ 2 nến nền + tối đa 5 nến của mẫu)
CANDLES_IN_CARD = 7
# Mã có ít nhất ngần này nến 1' trong ngày mới đủ thanh khoản để "bỏ phiếu" nguồn đã chốt chưa.
LIQUID_MIN_BARS = 30
# Tỷ lệ mã thanh khoản thiếu nến ATC từ mức này trở lên → coi nguồn chưa chốt.
UNSETTLED_RATIO = 0.2
# Nhiều hơn ngần này mã cùng có mẫu → gửi MỘT thông báo tổng hợp thay vì mỗi mã một cái.
DIGEST_THRESHOLD_DEFAULT = 6


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _dump(path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def fetch_bars(tickers: list[str], client=None, days: int = 120) -> tuple[dict[str, list[dict]], list[str]]:
    """Nến ngày cho từng mã + danh sách mã thanh khoản mà nến HÔM NAY chưa chốt (rỗng = nguồn ổn).
    Chép từ tudoanh-radar/job/run_daily.py::fetch_bars."""
    bars: dict[str, list[dict]] = {}
    voters: list[str] = []
    lacking: list[str] = []
    today = dnse.today_vn()
    with (client or dnse.DnseClient(days=days)) as c:
        for i, t in enumerate(sorted(tickers), 1):
            b = c.daily(t)
            if not b:
                continue
            if b[-1]["d"] == today:
                minutes = c.today_minutes(t)
                if len(minutes) >= LIQUID_MIN_BARS:
                    voters.append(t)
                    if not dnse.session_settled(minutes):
                        lacking.append(t)
                b[-1] = dnse.merge_today(b[-1], minutes)
            bars[t] = b
            if i % 10 == 0:
                log.info("giá: %d/%d mã", i, len(tickers))
    unsettled = lacking if voters and len(lacking) / len(voters) >= UNSETTLED_RATIO else []
    if lacking and not unsettled:
        log.info("Mã thiếu nến ATC nhưng nguồn nhìn chung đã chốt (%d/%d): %s",
                 len(lacking), len(voters), ", ".join(lacking))
    return bars, unsettled


def _candles_for_card(bars: list[dict], n: int = CANDLES_IN_CARD) -> list[dict]:
    return [{"d": b["d"].isoformat(), "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]}
            for b in bars[-n:]]


def detect_signals(bars_by_symbol: dict[str, list[dict]], names: dict[str, str], trade_date,
                   disabled: set[str]) -> tuple[list[dict], list[dict]]:
    """(tín hiệu của phiên trade_date, danh sách mã có nến cuối cũ hơn trade_date)."""
    signals: list[dict] = []
    stale: list[dict] = []
    for sym in sorted(bars_by_symbol):
        b = bars_by_symbol[sym]
        if b[-1]["d"] != trade_date:
            stale.append({"symbol": sym, "last_date": b[-1]["d"].isoformat()})
            continue
        hits = patterns.detect_at(b, len(b) - 1, disabled)
        if not hits:
            continue
        prev = b[-2]["c"] if len(b) > 1 and b[-2]["c"] else None
        chg = (b[-1]["c"] / prev - 1) * 100 if prev else None
        for pid in hits:
            meta = patterns.PATTERNS[pid]
            signals.append({
                "symbol": sym, "company_name": names.get(sym, ""),
                "pattern": pid, "name": meta["name"], "direction": meta["direction"],
                "bars": meta["bars"], "hint": meta["hint"], "advice": meta["advice"],
                "caution": meta.get("caution", ""),
                "price": b[-1]["c"], "change_pct": round(chg, 2) if chg is not None else None,
                "volume": b[-1]["v"], "candles": _candles_for_card(b),
            })
    # MUA trước BÁN, trong mỗi nhóm theo mã — thứ tự này là thứ tự thẻ trên giao diện
    signals.sort(key=lambda s: (s["direction"] != "buy", s["symbol"]))
    return signals, stale


def _history(days: int) -> list[dict]:
    """Đếm MUA/BÁN của các phiên gần nhất từ file daily — giao diện tab Lịch sử đọc ở đây."""
    out: list[dict] = []
    if not DAILY.exists():
        return out
    for f in sorted(DAILY.glob("*.json"), reverse=True)[:days]:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        sig = d.get("signals") or []
        out.append({
            "date": d.get("trade_date") or f.stem,
            "n_buy": sum(1 for s in sig if s["direction"] == "buy"),
            "n_sell": sum(1 for s in sig if s["direction"] == "sell"),
            "items": [f"{s['symbol']} {s['name']}" for s in sig],
            "late": bool(d.get("late")),
        })
    return out


def _send_alerts(signals: list[dict], trade_iso: str, subs: list[dict], digest_threshold: int) -> dict:
    res = {"sent": 0, "gone": 0, "failed": 0, "errors": [], "mode": "none", "n_symbols": 0}
    by_sym: dict[str, list[dict]] = {}
    for s in signals:
        by_sym.setdefault(s["symbol"], []).append(s)
    res["n_symbols"] = len(by_sym)
    if not by_sym:
        return res
    if len(by_sym) > digest_threshold:
        res["mode"] = "digest"
        payloads = [push.digest_payload(by_sym, trade_iso)]
    else:
        res["mode"] = "per_symbol"
        payloads = [push.symbol_payload(sym, sigs, trade_iso) for sym, sigs in by_sym.items()]
    for p in payloads:
        r = push.send(p, subs)
        for k in ("sent", "gone", "failed"):
            res[k] += r[k]
        res["errors"] += r["errors"]
    return res


def run(force: bool = False, dry_run: bool = False, no_push: bool = False) -> int:
    now = datetime.now(TZ)
    st = _load(STATE, {})

    if not dry_run and not no_push:
        _welcome_new_devices(st, now)

    cfg = settings.load()
    disabled = set(cfg.get("patterns_disabled") or [])
    digest_threshold = int(cfg.get("digest_threshold") or DIGEST_THRESHOLD_DEFAULT)

    items, wl_source = watchlist.load()
    if not items:
        log.error("Không có danh mục: KingStock không trả lời và chưa có docs/data/watchlist.json")
        st.update({"last_run": now.isoformat(timespec="seconds"), "watchlist_error": "không có danh mục"})
        _dump(STATE, st)
        return 2
    names = {it["symbol"]: it.get("company_name", "") for it in items}
    tickers = sorted(names)
    log.info("Danh mục %d mã (nguồn %s)", len(tickers), wl_source)

    bars, unsettled = fetch_bars(tickers)
    if not bars:
        log.error("DNSE không trả về gì: %s", dnse.last_error)
        st.update({"dnse_error": dnse.last_error, "last_run": now.isoformat(timespec="seconds")})
        _dump(STATE, st)
        return 3
    trade_date = max(b[-1]["d"] for b in bars.values())
    trade_iso = trade_date.isoformat()
    daily_file = DAILY / f"{trade_iso}.json"
    if daily_file.exists() and not force:
        log.info("Đã có %s — không chạy lại (dùng --force nếu muốn)", daily_file.name)
        return 0
    if unsettled and not force:
        msg = (f"Nguồn chưa chốt phiên {trade_iso}: {len(unsettled)}/{len(bars)} mã chưa có nến ATC "
               f"({', '.join(unsettled[:8])}{'…' if len(unsettled) > 8 else ''}) — chờ cron sau")
        log.warning(msg)
        st.update({"last_run": now.isoformat(timespec="seconds"),
                   "unsettled": {"trade_date": trade_iso, "tickers": unsettled,
                                 "at": now.isoformat(timespec="seconds")}})
        _dump(STATE, st)
        return 0
    late = bool(st.pop("unsettled", None))   # lần trước phải chờ → ghi nhớ để tab Lịch sử hiện "nguồn chốt muộn"
    if (now.date() - trade_date).days > 4:
        log.warning("Phiên gần nhất %s cách hôm nay quá 4 ngày — DNSE có thể chưa cập nhật", trade_iso)

    signals, stale = detect_signals(bars, names, trade_date, disabled)
    log.info("Phiên %s: %d tín hiệu trên %d mã, %d mã nến cũ", trade_iso, len(signals),
             len({s["symbol"] for s in signals}), len(stale))

    push_res: dict = {"skipped": True}
    if not dry_run and not no_push:
        subs, src = push.subscriptions()
        push_res = {"source": src, "n_devices": len(subs)}
        if subs and push.configured():
            push_res.update(_send_alerts(signals, trade_iso, subs, digest_threshold))
            if now.weekday() == 0:  # thứ Hai: nhịp tim để biết đường dây còn sống
                week_n = _signals_last_week(now) + len(signals)
                push_res["heartbeat"] = push.send(push.heartbeat_payload(week_n, trade_iso), subs)["sent"]
            if push.test_requested():
                push_res["test"] = push.send(push.test_payload(), subs)["sent"]
        elif not push.configured():
            push_res["errors"] = ["Thiếu khoá VAPID"]
        if push_res.get("gone"):
            st["push_gone_at"] = now.isoformat(timespec="seconds")

    latest = {
        "generated_at": now.isoformat(timespec="seconds"), "trade_date": trade_iso,
        "watchlist": {"n": len(tickers), "source": wl_source},
        "source": {"dnse_ok": bool(dnse.last_ok), "dnse_error": dnse.last_error,
                   "n_priced": len(bars), "unsettled": unsettled, "late": late},
        "settings": {k: v for k, v in cfg.items() if not k.startswith("_")},
        "patterns": {pid: {"name": m["name"], "direction": m["direction"], "bars": m["bars"], "hint": m["hint"],
                           "caution": m.get("caution", "")}
                     for pid, m in patterns.PATTERNS.items()},
        "stale": stale, "signals": signals, "push": push_res,
    }

    if dry_run:
        print(json.dumps({k: v for k, v in latest.items() if k not in ("signals", "patterns")},
                         ensure_ascii=False, indent=1, default=str))
        for s in signals:
            print(f"  {'▲' if s['direction'] == 'buy' else '▼'} {s['symbol']:<5} {s['name']:<26} "
                  f"giá {s['price']:.2f} ({s['change_pct']:+.1f}%)" if s["change_pct"] is not None
                  else f"  {s['symbol']} {s['name']}")
        return 0

    _dump(daily_file, {"trade_date": trade_iso, "generated_at": latest["generated_at"], "late": late,
                       "signals": signals, "stale": stale})
    latest["history"] = _history(int(cfg.get("history_days") or 30))
    _dump(LATEST, latest)
    st.update({"last_run": now.isoformat(timespec="seconds"), "last_trade_date": trade_iso,
               "dnse_error": dnse.last_error, "push": push_res,
               "watchlist": {"n": len(tickers), "source": wl_source}})
    _dump(STATE, st)
    log.info("Xong: %d mã, %d tín hiệu, push %s", len(bars), len(signals), push_res)
    return 0


def _welcome_new_devices(st: dict, now: datetime) -> None:
    """Máy mới đăng ký → gửi ngay một thông báo chào mừng, TRƯỚC bước idempotent, để người dùng
    chỉ cần Re-run là biết đường dây thông. Chép từ tudoanh-radar."""
    subs, src = push.subscriptions()
    st["devices"] = {"n": len(subs), "source": src, "vapid": push.configured(),
                     "checked_at": now.isoformat(timespec="seconds")}
    if not subs or not push.configured():
        _dump(STATE, st)
        return
    known = set(st.get("known_subs") or [])
    new = [s for s in subs if push._sub_id(s) not in known]
    if new:
        payload = {"kind": "welcome", "title": "Đã kết nối — máy này sẽ nhận cảnh báo",
                   "body": "Mẫu hình nến sau phiên 15:35 các ngày T2–T6, nhịp tim mỗi thứ Hai.",
                   "url": "./#today", "tag": "cr-welcome"}
        r = push.send(payload, new)
        log.info("Chào mừng %d máy mới (nguồn %s): %s", len(new), src, r)
        st["welcome"] = {"at": now.isoformat(timespec="seconds"), **r}
    st["known_subs"] = sorted(known | {push._sub_id(s) for s in subs})
    _dump(STATE, st)


def _signals_last_week(now: datetime) -> int:
    n = 0
    for i in range(1, 8):
        f = DAILY / f"{(now - timedelta(days=i)).date().isoformat()}.json"
        if f.exists():
            try:
                n += len(json.loads(f.read_text(encoding="utf-8")).get("signals") or [])
            except Exception:  # noqa: BLE001
                pass
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="chạy lại dù hôm nay đã có file")
    ap.add_argument("--dry-run", action="store_true", help="in kết quả, không ghi file, không push")
    ap.add_argument("--no-push", action="store_true", help="ghi file nhưng không gửi thông báo")
    a = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(run(force=a.force, dry_run=a.dry_run, no_push=a.no_push))


if __name__ == "__main__":
    main()
