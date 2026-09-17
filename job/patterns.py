"""15 mẫu hình nến đảo chiều — Python thuần, không numpy/pandas.

Nguồn: tổng hợp từ ảnh "Confirmation Candle" (forexsignalhub) và
vn-stock-app/backend/app/indicators/candlestick_patterns.py (bản pandas, có bối cảnh MA), đã loại
trùng. Khác bản vn-stock-app ở ba chỗ, đều có chủ đích:

1. KHÔNG lọc xu hướng (MA) và không lọc %K — người dùng chọn "mẫu xuất hiện là báo". Muốn bớt ồn
   thì tắt từng mẫu trong docs/data/settings.json (patterns_disabled).
2. KHÔNG đòi gap ở Sao mai / Sao hôm: nến ngày VN gần như không bao giờ gap (mở cửa ≈ đóng hôm
   trước), điều kiện gap của bản pandas trên dữ liệu VN hầu như không bao giờ thoả. Thay bằng
   "thân nến giữa ≤ 0,3 thân nến đầu".
3. Mẫu 1 nến (Búa, Búa ngược, Sao băng, Người treo cổ) BẮT BUỘC kèm nến xác nhận. Theo thống kê
   Bulkowski, đứng một mình chúng thiên về tiếp diễn hơn đảo chiều; chính vì thế ảnh gốc vẽ chúng
   kèm nến xác nhận. Hình Búa và Người treo cổ giống hệt nhau, phân biệt bằng MÀU nến xác nhận.

Ký hiệu: body=|c−o|, rng=h−l, up=h−max(o,c), lo=min(o,c)−l. Nến cuối của mẫu luôn là nến đã chốt.
"""
from __future__ import annotations

# Thân "lớn" so với trung bình thân 10 nến trước; thân "nhỏ" so với chính biên độ nến.
BIG_BODY_RATIO = 0.8
SMALL_BODY_RATIO = 0.30
DOJI_RATIO = 0.10
STAR_BODY_RATIO = 0.30      # thân nến giữa Sao mai/Sao hôm so với thân nến đầu
SHADOW_RATIO = 2.0          # râu dài ≥ 2 lần thân (Búa / Búa ngược)
OTHER_SHADOW_MAX = 0.10     # râu phía đối diện ≤ 10 % biên độ
SOLDIER_BODY_RATIO = 0.6    # 3 lính trắng / 3 quạ đen: thân ≥ 60 % biên độ
AVG_BODY_WINDOW = 10

# id → tên hiển thị, hướng, số nến của mẫu, mô tả 1 dòng, gợi ý hành động (quy tắc cố định).
# `bars` = số nến kể cả nến xác nhận; giao diện dùng để tô màu đúng các nến thuộc mẫu.
PATTERNS: dict[str, dict] = {
    "bull_engulfing": {
        "name": "Nhấn chìm tăng", "direction": "buy", "bars": 2,
        "hint": "Nến tăng bao trọn thân nến giảm hôm trước.",
        "advice": "Canh mua phiên sau; dừng lỗ dưới đáy nến nhấn chìm.",
    },
    "bear_engulfing": {
        "name": "Nhấn chìm giảm", "direction": "sell", "bars": 2,
        "hint": "Nến giảm bao trọn thân nến tăng hôm trước.",
        "advice": "Đang giữ thì cân nhắc hạ tỷ trọng đầu phiên sau.",
    },
    "morning_star": {
        "name": "Sao mai", "direction": "buy", "bars": 3,
        "hint": "Giảm mạnh → do dự → tăng, nến xác nhận đóng trên giữa thân nến giảm.",
        "advice": "Canh mua phiên sau; dừng lỗ dưới đáy nến giữa.",
    },
    "evening_star": {
        "name": "Sao hôm", "direction": "sell", "bars": 3,
        "hint": "Tăng mạnh → do dự → giảm, nến xác nhận đóng dưới giữa thân nến tăng.",
        "advice": "Đang giữ thì cân nhắc chốt bớt; đỉnh nến giữa là mốc vô hiệu.",
    },
    "morning_doji_star": {
        "name": "Sao mai Doji", "direction": "buy", "bars": 3,
        "hint": "Như Sao mai nhưng nến giữa là Doji thật.",
        "advice": "Canh mua phiên sau; dừng lỗ dưới đáy Doji.",
    },
    "evening_doji_star": {
        "name": "Sao hôm Doji", "direction": "sell", "bars": 3,
        "hint": "Như Sao hôm nhưng nến giữa là Doji thật.",
        "advice": "Đang giữ thì cân nhắc chốt bớt; đỉnh Doji là mốc vô hiệu.",
    },
    "three_white_soldiers": {
        "name": "Ba chàng lính trắng", "direction": "buy", "bars": 3,
        "hint": "Ba nến tăng thân đặc, đóng cửa cao dần, mở cửa trong thân nến trước.",
        "advice": "Đà tăng đã chạy 3 phiên — mua đuổi rủi ro, chờ nhịp lùi.",
    },
    "three_black_crows": {
        "name": "Ba con quạ đen", "direction": "sell", "bars": 3,
        "hint": "Ba nến giảm thân đặc, đóng cửa thấp dần, mở cửa trong thân nến trước.",
        "advice": "Đang giữ thì thoát; đừng bắt đáy khi chưa có nến tăng xác nhận.",
    },
    "hammer_confirm": {
        "name": "Búa + xác nhận", "direction": "buy", "bars": 2,
        "hint": "Nến búa hôm trước, hôm nay nến tăng đóng cửa vượt đỉnh búa.",
        "advice": "Canh mua phiên sau; điểm dừng lỗ tự nhiên là đáy râu búa.",
    },
    "hanging_man_confirm": {
        "name": "Người treo cổ + xác nhận", "direction": "sell", "bars": 2,
        "hint": "Nến râu dưới dài ở vùng cao, hôm nay nến giảm đóng cửa thủng đáy nó.",
        "advice": "Đang giữ thì cân nhắc thoát; đỉnh nến treo cổ là mốc vô hiệu.",
    },
    "inv_hammer_confirm": {
        "name": "Búa ngược + xác nhận", "direction": "buy", "bars": 2,
        "hint": "Nến râu trên dài hôm trước, hôm nay nến tăng đóng cửa vượt đỉnh nó.",
        "advice": "Canh mua phiên sau; dừng lỗ dưới đáy nến búa ngược.",
    },
    "shooting_star_confirm": {
        "name": "Sao băng + xác nhận", "direction": "sell", "bars": 2,
        "hint": "Nến râu trên dài ở vùng cao, hôm nay nến giảm đóng cửa thủng đáy nó.",
        "advice": "Đang giữ thì cân nhắc thoát; đỉnh râu sao băng là mốc vô hiệu.",
    },
    "piercing": {
        "name": "Xuyên thấu", "direction": "buy", "bars": 2,
        "hint": "Nến tăng mở thấp, đóng cửa trên giữa thân nến giảm hôm trước.",
        "advice": "Yếu hơn nhấn chìm — chờ thêm một nến tăng nữa rồi mới vào.",
    },
    "dark_cloud": {
        "name": "Mây đen che phủ", "direction": "sell", "bars": 2,
        "hint": "Nến giảm mở cao, đóng cửa dưới giữa thân nến tăng hôm trước.",
        "advice": "Yếu hơn nhấn chìm — đang giữ thì siết dừng lỗ lên dưới đáy nến này.",
    },
    "three_inside_down": {
        "name": "Ba nến trong giảm", "direction": "sell", "bars": 3,
        "hint": "Nến giảm nhỏ nằm trong thân nến tăng (harami), rồi nến giảm thủng đáy harami.",
        "advice": "Đang giữ thì thoát; đỉnh nến tăng đầu tiên là mốc vô hiệu.",
    },
}

BUY_PATTERNS = [k for k, v in PATTERNS.items() if v["direction"] == "buy"]
SELL_PATTERNS = [k for k, v in PATTERNS.items() if v["direction"] == "sell"]


# --- hình dạng một nến -------------------------------------------------------------------------
def _body(b: dict) -> float:
    return abs(b["c"] - b["o"])


def _rng(b: dict) -> float:
    return b["h"] - b["l"]


def _upper(b: dict) -> float:
    return b["h"] - max(b["o"], b["c"])


def _lower(b: dict) -> float:
    return min(b["o"], b["c"]) - b["l"]


def _bull(b: dict) -> bool:
    return b["c"] > b["o"]


def _bear(b: dict) -> bool:
    return b["c"] < b["o"]


def _mid(b: dict) -> float:
    return (b["o"] + b["c"]) / 2


def _small(b: dict) -> bool:
    r = _rng(b)
    return r > 0 and _body(b) <= SMALL_BODY_RATIO * r


def _is_doji(b: dict) -> bool:
    r = _rng(b)
    return r > 0 and _body(b) <= DOJI_RATIO * r


def _is_hammer(b: dict) -> bool:
    """Thân nhỏ, râu dưới ≥ 2 thân, râu trên gần như không có. Cùng hình với Người treo cổ."""
    r = _rng(b)
    return r > 0 and _small(b) and _lower(b) >= SHADOW_RATIO * _body(b) and _upper(b) <= OTHER_SHADOW_MAX * r


def _is_inv_hammer(b: dict) -> bool:
    """Thân nhỏ, râu trên ≥ 2 thân, râu dưới gần như không có. Cùng hình với Sao băng."""
    r = _rng(b)
    return r > 0 and _small(b) and _upper(b) >= SHADOW_RATIO * _body(b) and _lower(b) <= OTHER_SHADOW_MAX * r


def _solid(b: dict) -> bool:
    r = _rng(b)
    return r > 0 and _body(b) / r > SOLDIER_BODY_RATIO


def avg_body(bars: list[dict], i: int, n: int = AVG_BODY_WINDOW) -> float:
    """Trung bình thân của n nến TRƯỚC nến i (không tính i). Thiếu dữ liệu → 0 (không nhận mẫu)."""
    window = bars[max(0, i - n): i]
    if len(window) < n:
        return 0.0
    return sum(_body(b) for b in window) / n


def _big(b: dict, avg: float) -> bool:
    return avg > 0 and _body(b) >= BIG_BODY_RATIO * avg


# --- từng mẫu: nhận (bars, i, avg) với i là nến cuối (nến xác nhận) ------------------------------
def _bull_engulfing(bars, i, avg):
    p, c = bars[i - 1], bars[i]
    return _bear(p) and _bull(c) and _big(c, avg) and c["o"] <= p["c"] and c["c"] >= p["o"]


def _bear_engulfing(bars, i, avg):
    p, c = bars[i - 1], bars[i]
    return _bull(p) and _bear(c) and _big(c, avg) and c["o"] >= p["c"] and c["c"] <= p["o"]


def _star_shape(bars, i, avg, bearish_first: bool, doji_mid: bool):
    a, m, c = bars[i - 2], bars[i - 1], bars[i]
    first_ok = (_bear(a) if bearish_first else _bull(a)) and _big(a, avg)
    if not first_ok:
        return False
    mid_ok = _is_doji(m) if doji_mid else _body(m) <= STAR_BODY_RATIO * _body(a)
    if not mid_ok:
        return False
    if bearish_first:
        return _bull(c) and c["c"] > _mid(a)
    return _bear(c) and c["c"] < _mid(a)


def _morning_star(bars, i, avg):
    return _star_shape(bars, i, avg, bearish_first=True, doji_mid=False)


def _evening_star(bars, i, avg):
    return _star_shape(bars, i, avg, bearish_first=False, doji_mid=False)


def _morning_doji_star(bars, i, avg):
    return _star_shape(bars, i, avg, bearish_first=True, doji_mid=True)


def _evening_doji_star(bars, i, avg):
    return _star_shape(bars, i, avg, bearish_first=False, doji_mid=True)


def _three_white_soldiers(bars, i, avg):
    a, b, c = bars[i - 2], bars[i - 1], bars[i]
    return (
        _bull(a) and _bull(b) and _bull(c)
        and _solid(a) and _solid(b) and _solid(c)
        and b["c"] > a["c"] and c["c"] > b["c"]
        and a["o"] < b["o"] < a["c"] and b["o"] < c["o"] < b["c"]
    )


def _three_black_crows(bars, i, avg):
    a, b, c = bars[i - 2], bars[i - 1], bars[i]
    return (
        _bear(a) and _bear(b) and _bear(c)
        and _solid(a) and _solid(b) and _solid(c)
        and b["c"] < a["c"] and c["c"] < b["c"]
        and a["c"] < b["o"] < a["o"] and b["c"] < c["o"] < b["o"]
    )


def _hammer_confirm(bars, i, avg):
    p, c = bars[i - 1], bars[i]
    return _is_hammer(p) and _bull(c) and c["c"] > p["h"]


def _hanging_man_confirm(bars, i, avg):
    p, c = bars[i - 1], bars[i]
    return _is_hammer(p) and _bear(c) and c["c"] < p["l"]


def _inv_hammer_confirm(bars, i, avg):
    p, c = bars[i - 1], bars[i]
    return _is_inv_hammer(p) and _bull(c) and c["c"] > p["h"]


def _shooting_star_confirm(bars, i, avg):
    p, c = bars[i - 1], bars[i]
    return _is_inv_hammer(p) and _bear(c) and c["c"] < p["l"]


def _piercing(bars, i, avg):
    p, c = bars[i - 1], bars[i]
    return _bear(p) and _big(p, avg) and _bull(c) and c["o"] <= p["c"] and _mid(p) < c["c"] < p["o"]


def _dark_cloud(bars, i, avg):
    p, c = bars[i - 1], bars[i]
    return _bull(p) and _big(p, avg) and _bear(c) and c["o"] >= p["c"] and p["o"] < c["c"] < _mid(p)


def _three_inside_down(bars, i, avg):
    a, m, c = bars[i - 2], bars[i - 1], bars[i]
    harami = _bull(a) and _big(a, avg) and _bear(m) and a["o"] <= m["c"] and m["o"] <= a["c"]
    return harami and _bear(c) and c["c"] < m["l"]


_DETECTORS = {
    "bull_engulfing": _bull_engulfing,
    "bear_engulfing": _bear_engulfing,
    "morning_star": _morning_star,
    "evening_star": _evening_star,
    "morning_doji_star": _morning_doji_star,
    "evening_doji_star": _evening_doji_star,
    "three_white_soldiers": _three_white_soldiers,
    "three_black_crows": _three_black_crows,
    "hammer_confirm": _hammer_confirm,
    "hanging_man_confirm": _hanging_man_confirm,
    "inv_hammer_confirm": _inv_hammer_confirm,
    "shooting_star_confirm": _shooting_star_confirm,
    "piercing": _piercing,
    "dark_cloud": _dark_cloud,
    "three_inside_down": _three_inside_down,
}
assert set(_DETECTORS) == set(PATTERNS)

MIN_BARS = AVG_BODY_WINDOW + 2   # 10 nến nền + ít nhất 2 nến của mẫu


def detect_at(bars: list[dict], i: int, disabled: frozenset[str] | set[str] = frozenset()) -> list[str]:
    """Các mẫu KẾT THÚC tại nến i (i là nến xác nhận). Thứ tự trả về = thứ tự khai báo PATTERNS.

    Nến nào có biên độ 0 trong cửa sổ mẫu (mã đứng giá, trần/sàn không khớp) → bỏ, không ném lỗi.
    """
    if i < 0:
        i += len(bars)
    if i < MIN_BARS - 1 or i >= len(bars):
        return []
    avg = avg_body(bars, i)
    if avg <= 0:
        return []
    out: list[str] = []
    for pid, meta in PATTERNS.items():
        if pid in disabled or i - meta["bars"] + 1 < 0:
            continue
        window = bars[i - meta["bars"] + 1: i + 1]
        if any(_rng(b) <= 0 for b in window):
            continue
        if _DETECTORS[pid](bars, i, avg):
            out.append(pid)
    return out


def scan_history(bars: list[dict], disabled: frozenset[str] | set[str] = frozenset()) -> list[dict]:
    """Tua toàn bộ chuỗi — cho scripts/replay.py và test. Mỗi dòng: một (nến, mẫu)."""
    out: list[dict] = []
    for i in range(MIN_BARS - 1, len(bars)):
        for pid in detect_at(bars, i, disabled):
            out.append({
                "i": i, "date": bars[i]["d"], "pattern": pid,
                "direction": PATTERNS[pid]["direction"], "price": bars[i]["c"],
            })
    return out
