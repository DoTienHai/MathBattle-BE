## **1) Thông tin hiện tại của bạn**

- OS: **Windows 64-bit**
- Rclone bản bạn tải: **rclone-v1.74.0-windows-amd64**
- Remote Google Drive bạn đã tạo: **`google_driver`**
    - Vì vậy đường dẫn remote bắt đầu bằng: `google_driver:`
- Folder Drive bạn muốn đồng bộ: **`MathBattle`**
    - Đường dẫn remote: **`google_driver:MathBattle`**
- Folder local bạn muốn đồng bộ:
    - **`D:\3_CODING\MathBattle\doc`**

## **2) Các lựa chọn cấu hình quan trọng (bạn đã/ nên chọn)**

- `client_id` / `client_secret`: có thể **để trống** (vẫn sync 2 chiều được; chỉ có thể chậm/dễ limit hơn).
- `scope`: để sync 2 chiều phải chọn:
    - **Option 1: Full access (drive)**
- `service_account_file`: **để trống** (Enter)
- `auth_owner_only`: **false** (Enter)
- `metadata_owner`: **read** (Enter hoặc option 2)
- `metadata_permissions`: **off** (Enter)
- `Use web browser to authenticate`: **Y**

## **3) Lệnh kiểm tra hữu ích**

- Xem các remote:

bat

`rclone listremotes`

- Xem rclone đang dùng file config nào:

bat

`rclone config file`

- Xem thư mục cấp 1 trong Drive:

bat

`rclone lsd "google_driver:"`

## **4) Đồng bộ 2 chiều (bisync) — cách chạy đúng**

### **Lần đầu tiên / khi bị lỗi state / muốn tạo lại trạng thái:**

(kiểm tra trước)

bat

`rclone bisync "google_driver:MathBattle" "D:\3_CODING\MathBattle\doc" --resync --dry-run --progress`

(chạy thật)

bat

`rclone bisync "google_driver:MathBattle" "D:\3_CODING\MathBattle\doc" --resync --progress`

### **Những lần sau (đồng bộ bình thường):**

bat

`rclone bisync "google_driver:MathBattle" "D:\3_CODING\MathBattle\doc" --progress`

## **5) Ý nghĩa `-dry-run`**

- Có `-dry-run` = **chỉ mô phỏng**, KHÔNG upload/download thật.
- Muốn sync thật thì **bỏ `-dry-run`**.

## **6) Bisync không tự chạy nền**

- `rclone bisync` **chỉ sync khi bạn chạy lệnh**.
- Sau khi bạn sửa file, muốn nó upload lên Drive thì bạn phải:
    - chạy lại lệnh `rclone bisync ...`
- Muốn tự động: dùng **Task Scheduler** hoặc script loop.

## **7) Lưu ý an toàn**

- Trước khi chạy `-resync` thật, nên chắc chắn bạn trỏ đúng:
    - `google_driver:MathBattle`
    - `D:\3_CODING\MathBattle\doc`
- Nếu 2 bên đang khác nhau nhiều, `bisync` có thể copy nhiều file và có thể tạo tình huống conflict (tuỳ thay đổi).

Nếu bạn muốn, mình có thể viết sẵn cho bạn 1 file `.bat` “sync-now.bat” và 1 file `.bat` “sync-loop.bat”, dùng đúng đường dẫn của bạn để bạn bấm chạy là đồng bộ ngay.