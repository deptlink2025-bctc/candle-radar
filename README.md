# Candle Radar — cảnh báo 15 mẫu hình nến sau phiên

App thứ 7 trong bộ công cụ chứng khoán cá nhân. Mỗi chiều sau ATC, quét 39 mã trong danh mục
KingStock, nhận dạng 15 mẫu hình nến đảo chiều **trên nến đã chốt**, đẩy thông báo lên điện thoại
và ghi lại để xem trên giao diện tĩnh. Không máy chủ, 0 đồng.

- Giao diện: `https://deptlink2025-bctc.github.io/candle-radar/` (GitHub Pages từ `/docs`)
- Job: GitHub Actions 15:35 T2–T6 (dự phòng 16:05 / 16:45 / 18:10 nếu nguồn chốt muộn) — lệch 15 phút với TuDoanh Radar
- Nguồn giá: DNSE/Entrade (miễn phí, không token). Danh mục: API KingStock, có bản chụp dự phòng.
- Bản thiết kế giao diện + logo: https://claude.ai/artifact/GG1uq6fD3WtjGdGxr7T68k

Kiến trúc nhân bản từ `tudoanh-radar` (đang chạy thật từ 13/09/2026): `common/dnse.py`, `job/push.py`,
`docs/sw.js`, workflow cron dự phòng chép gần nguyên văn. Độc lập hoàn toàn với KingStock — chỉ **đọc**
`/api/watchlist` của nó.

## Đọc trước khi tin vào cảnh báo — kết quả đo lại

Trước khi bật push, `scripts/replay.py` đã tua 39 mã × 750 ngày (~509 phiên/mã) — bảng đầy đủ ở
[reports/replay-2026-09-16.md](reports/replay-2026-09-16.md). Tóm tắt:

- **Số lượng:** 4.382 lần xuất hiện ≈ **8,6 mẫu/phiên** cho cả danh mục. Vì thế job **gộp theo mã** (một
  thông báo/mã) và khi **quá 6 mã** cùng có mẫu thì gửi **một** thông báo tổng hợp (`digest_threshold`).
- **Mẫu MUA có giá trị thật** (so với mốc "mua đại rồi giữ" +0,18% / +0,41% sau 5 / 10 phiên):
  - Nhấn chìm tăng: +0,98% sau 10 phiên, t = 3,4 — nhưng 31,7 lần/tháng.
  - Sao mai Doji: +1,17% sau 5 phiên, t = 2,6 — 7,9 lần/tháng.
  - Sao mai yếu (t 1,7); Xuyên thấu, Búa, Búa ngược ≈ 0 hoặc âm.
- **Mẫu BÁN: không mẫu nào dự báo được giảm** trên dữ liệu 2024–2026 (thị trường đi lên). Ba con quạ
  đen còn +2% sau tín hiệu. Chỉ Mây đen che phủ có −0,89% sau 10 phiên (t −2,5).
- Siết "thân nến xác nhận ≥ 1,2× trung bình" giảm 25 % số lần, Nhấn chìm tăng vẫn giữ giá trị; các mẫu
  khác không khá lên.

Người dùng quyết định **bật cả 15** để xem thực tế. Muốn bớt ồn: thêm id mẫu vào `patterns_disabled`
trong `docs/data/settings.json` rồi push (job chạy ngay khi push). Muốn đo lại sau khi có thêm dữ liệu:

```
venv\Scripts\python -m scripts.replay --days 750 --md > reports/replay-<ngày>.md
```

Cách đọc số: MUA và BÁN tách riêng (VN không bán khống); với BÁN, lợi suất âm sau tín hiệu = đúng;
luôn so với mốc mua-đại trên cùng chuỗi; t > 2 mới đáng để ý; chưa trừ phí, chưa tính T+2.

## 15 mẫu hình (job/patterns.py)

Ký hiệu nến: `body=|c−o|`, `rng=h−l`, `up=h−max(o,c)`, `lo=min(o,c)−l`. `avg_body` = trung bình thân 10 nến
trước mẫu. Thân lớn = `body ≥ 0,8·avg_body`; thân nhỏ = `body ≤ 0,3·rng`; Doji = `body ≤ 0,1·rng`;
Búa = thân nhỏ, `lo ≥ 2·body`, `up ≤ 0,1·rng`; Búa ngược = đối xứng. Nến cuối luôn là nến xác nhận đã chốt.

| id | Tên | Hướng | Điều kiện (nến −3, −2, −1) |
|---|---|---|---|
| `bull_engulfing` | Nhấn chìm tăng | MUA | −2 giảm; −1 tăng thân lớn, `o₋₁ ≤ c₋₂`, `c₋₁ ≥ o₋₂` |
| `bear_engulfing` | Nhấn chìm giảm | BÁN | −2 tăng; −1 giảm thân lớn, `o₋₁ ≥ c₋₂`, `c₋₁ ≤ o₋₂` |
| `morning_star` | Sao mai | MUA | −3 giảm thân lớn; −2 `body ≤ 0,3·body₋₃`; −1 tăng, `c₋₁ > (o₋₃+c₋₃)/2` |
| `evening_star` | Sao hôm | BÁN | đối xứng Sao mai |
| `morning_doji_star` | Sao mai Doji | MUA | như Sao mai, −2 là Doji |
| `evening_doji_star` | Sao hôm Doji | BÁN | như Sao hôm, −2 là Doji |
| `three_white_soldiers` | Ba chàng lính trắng | MUA | 3 nến tăng `body/rng > 0,6`, đóng cửa tăng dần, mở cửa trong thân nến trước |
| `three_black_crows` | Ba con quạ đen | BÁN | đối xứng |
| `hammer_confirm` | Búa + xác nhận | MUA | −2 Búa; −1 tăng, `c₋₁ > h₋₂` |
| `hanging_man_confirm` | Người treo cổ + xác nhận | BÁN | −2 Búa (cùng hình); −1 giảm, `c₋₁ < l₋₂` |
| `inv_hammer_confirm` | Búa ngược + xác nhận | MUA | −2 Búa ngược; −1 tăng, `c₋₁ > h₋₂` |
| `shooting_star_confirm` | Sao băng + xác nhận | BÁN | −2 Búa ngược; −1 giảm, `c₋₁ < l₋₂` |
| `piercing` | Xuyên thấu | MUA | −2 giảm thân lớn; −1 tăng, `o₋₁ ≤ c₋₂`, `(o₋₂+c₋₂)/2 < c₋₁ < o₋₂` |
| `dark_cloud` | Mây đen che phủ | BÁN | đối xứng Xuyên thấu |
| `three_inside_down` | Ba nến trong giảm | BÁN | −3 tăng thân lớn; −2 giảm thân trong thân −3; −1 giảm, `c₋₁ < l₋₂` |

Ba chỗ cố ý khác với `vn-stock-app/backend/app/indicators/candlestick_patterns.py`:

1. **Không lọc xu hướng (MA), không lọc %K** — theo yêu cầu "mẫu xuất hiện là báo".
2. **Không đòi gap** ở Sao mai/Sao hôm: nến ngày VN hầu như không gap, điều kiện đó gần như không bao giờ
   thoả. Thay bằng điều kiện thân nến giữa.
3. **Mẫu 1 nến bắt buộc kèm nến xác nhận.** Theo Bulkowski, Búa/Búa ngược/Sao băng/Người treo cổ đứng
   một mình thiên về tiếp diễn hơn đảo chiều. Búa và Người treo cổ cùng hình → phân biệt bằng màu nến
   xác nhận. Một bộ nến có thể khớp nhiều mẫu (Sao hôm + Người treo cổ + xác nhận) — ghi cả, gộp theo mã.

Nến nào biên độ 0 (đứng giá, trần/sàn không khớp) → không nhận mẫu, không ném lỗi.

## Job sau phiên (job/run_daily.py)

1. `watchlist.load()`: GET KingStock `/api/watchlist` → ghi `docs/data/watchlist.json`; lỗi → dùng bản chụp.
2. `fetch_bars()`: nến ngày 120 phiên/mã + nến 1' hôm nay; ≥ 20 % mã thanh khoản (≥ 30 nến 1') thiếu nến
   ATC 14:45 → **nguồn chưa chốt**, ghi `state.unsettled`, không ghi file, cron sau thử lại.
3. `trade_date` = ngày nến cuối lớn nhất. Đã có `docs/data/daily/<ngày>.json` → thoát (idempotent).
4. Mã có nến cuối **cũ hơn** `trade_date` (không khớp lệnh hôm nay) → vào `stale`, **không xét mẫu**.
   Không có bước này, một mẫu cũ của mã kém thanh khoản sẽ được "phát hiện lại" mỗi ngày (bẫy IDP
   ở TuDoanh Radar 16/09/2026).
5. `detect_at(bars, -1)` cho từng mã → tín hiệu kèm 6 nến cuối để giao diện vẽ mini-chart.
6. Push: một thông báo/mã (`cr-<mã>`, gộp tên mẫu); > `digest_threshold` mã → một thông báo tổng hợp.
   Thứ Hai gửi thêm nhịp tim. Máy mới đăng ký → chào mừng ngay ở đầu job.
7. Ghi `latest.json` (giao diện đọc), `daily/<ngày>.json`, `state.json`.

Chạy tay: `run-daily-local.bat` (= `--force --no-push`), `--dry-run` chỉ in.

## Giao diện (docs/)

Ba tab: **Hôm nay** (thẻ theo mã, mini-chart 6 nến: nến thuộc mẫu tô màu, nến xác nhận khung vàng,
dòng GỢI Ý theo quy tắc cố định và LƯU Ý từ kết quả đo), **Lịch sử** (30 phiên, đếm MUA/BÁN), **Cài đặt**
(đăng ký thông báo, bảng 15 mẫu với glyph, số lần/tháng và trạng thái bật/tắt).

Không có Worker thì công tắc chỉ hiển thị; đổi trong `docs/data/settings.json` rồi push.
Đăng ký thông báo không Worker: bấm "Bật thông báo" → sao chép đoạn mã → dán vào GitHub Secret
`PUSH_SUBS_FALLBACK` (một lần mỗi máy). Cùng origin với tudoanh-radar nên quyền thông báo đã cấp;
service worker scope khác nên vẫn phải đăng ký mới.

Tông màu/chữ: nền kem `#F7F4EC`, xanh rêu `#1F3A2E`, thẻ pastel, Archivo + Source Serif 4 italic.
Logo B "Sao mai": `docs/icons/logo.svg`; PNG sinh bằng `scripts/make_icons.py` (cần Pillow).

## Deploy lần đầu

1. Tạo repo public `deptlink2025-bctc/candle-radar`, push toàn bộ (trừ `venv/`, `.env`).
2. Settings → Pages → Source: branch `main`, folder `/docs`.
3. `venv\Scripts\python -m job.gen_vapid` → 3 dòng. Dán `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
   `VAPID_SUBJECT` vào Settings → Secrets → Actions. Dán public key vào `docs/config.js` (`VAPID_PUBLIC`), push.
4. Mở app trên điện thoại → Cài đặt → Bật thông báo → Sao chép → dán vào Secret `PUSH_SUBS_FALLBACK`.
5. Actions → daily → Run workflow (`test_push=true`) → điện thoại nhận "Thông báo thử". Lần chạy kế
   sẽ gửi "Đã kết nối" cho máy mới.

Nghiệm thu: `docs/data/state.json` có `devices.n = 1`, `last_run`; 15:35 hôm sau `latest.json.trade_date`
đúng ngày; `workflow_dispatch force=true` vào tối chạy lại không gửi trùng (cùng `trade_date`).

## Bẫy đã gặp, đừng dẫm lại

- **DNSE trả nến hôm nay dừng giữa phiên, HTTP 200** (14/09/2026): job phải soi nến 1' có chạm ATC chưa.
- **Mã ít thanh khoản mang nến cũ nhiều ngày** → không xét mẫu, chỉ ghi `stale`.
- **DNSE trả giá đã điều chỉnh cổ tức** — cố ý giữ, mẫu hình dùng tỷ lệ nên không ảnh hưởng.
- **Giá theo nghìn đồng** (`PRICE_UNIT = 1.0`, khác tudoanh-radar nhân 1000).
- Console Windows cp1252 → script phải `reconfigure(encoding="utf-8")` trước khi in chữ có dấu.
- Chrome headless không cho cửa sổ hẹp dưới ~500px → muốn chụp 390px phải bọc trong iframe.
- **GitHub cron trễ 10–30 phút** là bình thường; đừng dựa vào đúng phút.
- Thiếu `VAPID_PUBLIC_KEY` thì thông báo im lặng không tới — `push.configured()` đòi cả hai khoá.

## Kiểm thử

```
venv\Scripts\python -m pytest tests -q      # 54 test: 15 mẫu dương/âm, bảo vệ, job idempotent, push gộp
node --check docs/app.js
```

## Không làm (đã cân nhắc)

- Không quét trong phiên (nến chưa chốt sẽ "vẽ lại"). Không lọc ADX/MA/%K (đã gỡ ở KingStock 11/09/2026).
- Không Fly.io (app không cần đúng phút). Không Cloudflare Worker ở GĐ 1 (tài khoản chỉ còn 1/5 suất cron).
