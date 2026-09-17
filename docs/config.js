/* Cấu hình giao diện — sửa sau khi sinh khoá VAPID (venv\Scripts\python -m job.gen_vapid).
   VAPID_PUBLIC phải trùng với Secret VAPID_PUBLIC_KEY trên GitHub.
   WORKER_URL là địa chỉ Cloudflare Worker (GĐ 2, tuỳ chọn) — để trống = dùng PUSH_SUBS_FALLBACK. */
window.CR_CONFIG = {
  VAPID_PUBLIC: "BJbVmDkj6ceEACMj80QinTC_-Xnn3ZNWWp_ojOJaWDtRVFLqTWC7KBIpnSYzelNU1C-fk8d6qy6V9WDiIwRqe90",
  WORKER_URL: "",
};
