"""Mỗi mẫu một case dương + một case âm, dựng tay trên 10 nến nền thân = 1.0 (avg_body = 1)."""
from datetime import date, timedelta

import pytest

from job import patterns as P


def bar(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c, "v": 1000}


def series(*tail):
    """10 nến nền (thân 1.0, biên độ 2.0) rồi nối các nến của mẫu. Gán ngày tăng dần."""
    base = [bar(100, 101.5, 99.5, 101) for _ in range(10)]
    bars = base + list(tail)
    for k, b in enumerate(bars):
        b["d"] = date(2026, 1, 1) + timedelta(days=k)
    return bars


def last(bars, disabled=frozenset()):
    return P.detect_at(bars, len(bars) - 1, disabled)


# --- 2 nến ---------------------------------------------------------------------------------------
def test_bull_engulfing():
    s = series(bar(101, 101.3, 99.7, 100), bar(99.9, 101.5, 99.6, 101.2))
    assert last(s) == ["bull_engulfing"]


def test_bull_engulfing_khong_bao_het_than():
    s = series(bar(101, 101.3, 99.7, 100), bar(99.9, 101.5, 99.6, 100.8))
    assert "bull_engulfing" not in last(s)


def test_bear_engulfing():
    s = series(bar(100, 101.3, 99.7, 101), bar(101.1, 101.4, 99.5, 99.8))
    assert last(s) == ["bear_engulfing"]


def test_bear_engulfing_nen_xac_nhan_qua_nho():
    # thân 0.5 < 0.8 × avg_body → không phải nhấn chìm dù bao trọn? Không: thân 0.5 không thể bao 1.0.
    s = series(bar(100.2, 100.6, 99.9, 100.5), bar(100.6, 100.7, 100.0, 100.1))
    assert "bear_engulfing" not in last(s)


def test_hammer_confirm():
    s = series(bar(100.4, 100.65, 99.5, 100.6), bar(100.6, 101.4, 100.5, 101.3))
    assert last(s) == ["hammer_confirm"]


def test_hammer_khong_xac_nhan_thi_khong_bao():
    s = series(bar(100.4, 100.65, 99.5, 100.6), bar(100.6, 100.64, 100.3, 100.5))
    assert last(s) == []


def test_hanging_man_confirm_cung_hinh_bua_nhung_nen_giam():
    s = series(bar(100.4, 100.65, 99.5, 100.6), bar(100.5, 100.6, 99.2, 99.3))
    hits = last(s)
    # Sau nến nền tăng, bộ ba này đồng thời là Sao hôm — chồng mẫu là hợp lệ, job gộp theo mã.
    assert "hanging_man_confirm" in hits and "hammer_confirm" not in hits


def test_inv_hammer_confirm():
    s = series(bar(100.4, 101.5, 100.35, 100.6), bar(100.7, 101.9, 100.6, 101.8))
    assert last(s) == ["inv_hammer_confirm"]


def test_inv_hammer_xac_nhan_khong_vuot_dinh():
    s = series(bar(100.4, 101.5, 100.35, 100.6), bar(100.7, 101.4, 100.6, 101.3))
    assert last(s) == []


def test_shooting_star_confirm():
    s = series(bar(100.4, 101.5, 100.35, 100.6), bar(100.5, 100.55, 99.9, 100.0))
    hits = last(s)
    assert "shooting_star_confirm" in hits and "inv_hammer_confirm" not in hits


def test_piercing():
    s = series(bar(102, 102.2, 100.3, 100.5), bar(100.4, 101.7, 100.2, 101.5))
    assert last(s) == ["piercing"]


def test_piercing_dong_qua_cao_thanh_nhan_chim():
    s = series(bar(102, 102.2, 100.3, 100.5), bar(100.4, 102.5, 100.2, 102.3))
    hits = last(s)
    assert "piercing" not in hits and "bull_engulfing" in hits


def test_dark_cloud():
    s = series(bar(100.5, 102.2, 100.3, 102), bar(102.1, 102.3, 100.2, 101.0))
    assert last(s) == ["dark_cloud"]


def test_dark_cloud_dong_tren_giua_than():
    s = series(bar(100.5, 102.2, 100.3, 102), bar(102.1, 102.3, 100.2, 101.6))
    assert "dark_cloud" not in last(s)


# --- 3 nến ---------------------------------------------------------------------------------------
def test_morning_star():
    s = series(bar(102, 102.2, 100.3, 100.5), bar(100.4, 100.8, 99.9, 100.2), bar(100.5, 101.8, 100.4, 101.6))
    assert last(s) == ["morning_star"]


def test_morning_star_doi_nen_giua_la_doji_thi_bao_ca_hai():
    s = series(bar(102, 102.2, 100.3, 100.5), bar(100.4, 100.8, 99.9, 100.35), bar(100.5, 101.8, 100.4, 101.6))
    assert last(s) == ["morning_star", "morning_doji_star"]


def test_morning_star_xac_nhan_khong_qua_giua_than():
    s = series(bar(102, 102.2, 100.3, 100.5), bar(100.4, 100.8, 99.9, 100.2), bar(100.5, 101.1, 100.4, 101.0))
    assert last(s) == []


def test_evening_star():
    s = series(bar(100.5, 102.2, 100.3, 102), bar(102.1, 102.6, 101.7, 102.3), bar(102.0, 102.1, 100.5, 100.8))
    assert last(s) == ["evening_star"]


def test_evening_doji_star():
    s = series(bar(100.5, 102.2, 100.3, 102), bar(102.1, 102.6, 101.7, 102.13), bar(102.0, 102.1, 100.5, 100.8))
    assert last(s) == ["evening_star", "evening_doji_star"]


def test_evening_star_nen_dau_qua_nho():
    s = series(bar(100.5, 101.1, 100.3, 100.9), bar(100.9, 101.2, 100.7, 101.0), bar(100.9, 101.0, 100.2, 100.4))
    assert "evening_star" not in last(s)


def test_three_white_soldiers():
    s = series(bar(100, 101.2, 99.9, 101), bar(100.5, 101.8, 100.4, 101.6), bar(101.2, 102.6, 101.1, 102.4))
    assert last(s) == ["three_white_soldiers"]


def test_three_white_soldiers_nen_thu_ba_giam():
    s = series(bar(100, 101.2, 99.9, 101), bar(100.5, 101.8, 100.4, 101.6), bar(101.5, 101.7, 100.4, 100.6))
    assert "three_white_soldiers" not in last(s)


def test_three_black_crows():
    s = series(bar(101, 101.1, 99.8, 100), bar(100.5, 100.6, 99.2, 99.4), bar(99.8, 99.9, 98.4, 98.6))
    assert last(s) == ["three_black_crows"]


def test_three_black_crows_mo_cua_ngoai_than_truoc():
    s = series(bar(101, 101.1, 99.8, 100), bar(101.3, 101.4, 99.2, 99.4), bar(99.8, 99.9, 98.4, 98.6))
    assert "three_black_crows" not in last(s)


def test_three_inside_down():
    s = series(bar(100, 101.7, 99.9, 101.5), bar(101.2, 101.3, 100.5, 100.6), bar(100.6, 100.7, 99.9, 100.0))
    assert last(s) == ["three_inside_down"]


def test_three_inside_down_chua_thung_day_harami():
    s = series(bar(100, 101.7, 99.9, 101.5), bar(101.2, 101.3, 100.5, 100.6), bar(100.6, 100.7, 100.5, 100.55))
    assert last(s) == []


# --- bảo vệ --------------------------------------------------------------------------------------
def test_nen_bien_do_0_khong_nem_loi():
    s = series(bar(100, 100, 100, 100), bar(100, 101.5, 99.5, 101.2))
    assert last(s) == []


def test_qua_it_nen_thi_rong():
    bars = [bar(100, 101.5, 99.5, 101) for _ in range(5)]
    assert P.detect_at(bars, len(bars) - 1) == []
    assert P.detect_at(bars, 99) == []


def test_tat_mau_bang_disabled():
    s = series(bar(101, 101.3, 99.7, 100), bar(99.9, 101.5, 99.6, 101.2))
    assert last(s, {"bull_engulfing"}) == []


def test_scan_history_tra_dung_vi_tri():
    s = series(bar(101, 101.3, 99.7, 100), bar(99.9, 101.5, 99.6, 101.2))
    hits = P.scan_history(s)
    assert [(h["i"], h["pattern"], h["direction"]) for h in hits] == [(11, "bull_engulfing", "buy")]
    assert hits[0]["date"] == s[-1]["d"]


def test_bang_mau_du_15_va_can_mua_ban():
    assert len(P.PATTERNS) == 15
    assert len(P.BUY_PATTERNS) == 7 and len(P.SELL_PATTERNS) == 8
    for meta in P.PATTERNS.values():
        assert meta["bars"] in (2, 3) and meta["name"] and meta["hint"] and meta["advice"]


@pytest.mark.parametrize("pid", list(P.PATTERNS))
def test_moi_mau_deu_co_bo_nhan_dang(pid):
    assert pid in P._DETECTORS
