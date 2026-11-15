# HỆ THỐNG QUẢN LÝ PHÒNG KHÁM BỆNH TƯ NHÂN
> **Bài tập lớn môn Cơ sở dữ liệu – Project 1 (MySQL 8 + Python Streamlit)**

Ứng dụng web trực quan, thân thiện cho người không biết lập trình, kết nối trực tiếp với MySQL 8 để thực thi các nghiệp vụ phòng khám qua các Stored Procedure, Trigger và View.

---

## 📁 Cấu trúc thư mục

```text
phongkham-main/
├── phong_kham.sql      # Script tạo CSDL MySQL 8, trigger, procedure, dữ liệu mẫu
├── app.py              # Giao diện Streamlit với 5 mục công việc
├── db.py               # Module kết nối MySQL, gọi Stored Procedure, xử lý lỗi hệ thống
├── static/style.css     # Kiểu hiển thị bổ sung
├── .streamlit/config.toml # Màu sắc và kiểu chữ của ứng dụng
├── requirements.txt    # Danh sách thư viện Python cần cài đặt
├── .env.example        # File mẫu cấu hình kết nối CSDL
├── .env                # File cấu hình kết nối thực tế (không commit lên Git)
├── .gitignore          # Cấu hình bỏ qua file nhạy cảm (.env, cache)
├── tests/              # Kiểm thử thao tác ghi dữ liệu nhân viên
└── README.md           # Hướng dẫn cài đặt và sử dụng chi tiết
```

---

## 🛠️ Yêu cầu hệ thống

* **Hệ điều hành:** Windows, macOS hoặc Linux.
* **Hệ quản trị CSDL:** **MySQL 8.0.16+** (yêu cầu hỗ trợ CHECK constraint, Trigger và Window Functions).
* **Python:** Phiên bản **3.10 trở lên** (đã kiểm thử tốt trên Python 3.13).

---

## 🚀 Hướng dẫn cài đặt & Khởi chạy (Từng bước)

### Bước 1: Nạp cơ sở dữ liệu `phong_kham.sql` vào MySQL

> **Chỉ nạp `phong_kham.sql` khi database chưa có bảng.** Có thể database `phong_kham` đã tồn tại nhưng còn trống; script vẫn tạo các bảng và dữ liệu mẫu. Nếu database đã có bảng, không chạy lại toàn bộ script để tránh nạp trùng dữ liệu.

Mở **MySQL Workbench** hoặc **Command Prompt / Terminal** và thực hiện:

* **Cách 1: Sử dụng MySQL Workbench**
  1. Mở MySQL Workbench, kết nối vào tài khoản `root`.
  2. Chọn menu `File` $\rightarrow$ `Open SQL Script...` $\rightarrow$ chọn file `phong_kham.sql`.
  3. Bấm nút biểu tượng tia sét ⚡ (**Execute All**) để chạy toàn bộ file.

* **Cách 2: Sử dụng dòng lệnh Terminal**
  ```bash
  mysql -u root -p < phong_kham.sql
  ```
  *(Nhập mật khẩu MySQL khi được hỏi)*.

---

### Bước 2: Cài đặt các thư viện Python

Trên Windows, mở PowerShell trong thư mục dự án (nơi có `app.py`) và chạy từng lệnh:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

### Bước 3: Cấu hình file `.env`

1. Tạo file `.env` dựa trên file mẫu `.env.example`:
   * Nếu dùng lệnh terminal:
     ```powershell
     Copy-Item .env.example .env
     ```
2. Mở file `.env` và điền thông tin tài khoản MySQL của bạn:
   ```env
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=mat_khau_mysql_cua_ban
   DB_NAME=phong_kham
   ```
   *(Nếu tài khoản `root` không đặt mật khẩu, để trống `DB_PASSWORD=`)*.

Sau khi sửa `.env`, khởi động lại ứng dụng để kết nối bằng thông tin mới.

---

### Bước 4: Khởi chạy ứng dụng Web

Chạy lệnh sau trong thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Ứng dụng sẽ tự động mở trên trình duyệt tại địa chỉ: **http://localhost:8501** 🎉

---

## Hướng dẫn dùng giao diện

Thanh bên trái có 5 mục theo công việc:

| Mục | Dùng khi nào |
| --- | --- |
| **Trang chủ** | Chọn công việc cần làm và xem số liệu tổng quan. |
| **Bệnh nhân** | Xem lịch sử khám; thêm, sửa hoặc xóa hồ sơ bệnh nhân. |
| **Nhân viên & danh mục** | Xem và quản lý bác sĩ, y tá, thuốc và loại bệnh. |
| **Khám chữa bệnh** | Ghi nhận một ca điều trị theo 5 bước được đánh số trên màn hình. |
| **Báo cáo** | Xem bệnh theo tháng, bảng lương và doanh thu. |

**Quy trình khám:** Thêm bệnh nhân → Mở đợt bệnh → Thêm lần khám → Kê thuốc và phân công y tá → Đóng đợt khi đã khỏi.

---

## ❓ Xử lý sự cố thường gặp (Troubleshooting)

Để kiểm tra các thao tác ghi dữ liệu nhân viên, chạy `python -m unittest discover -s tests -v` trong thư mục dự án.

1. **Lỗi `Access denied for user 'root'@'localhost'`:**
   * Mật khẩu trong file `.env` chưa khớp với mật khẩu MySQL của bạn.
   * Cách khắc phục: Sửa `DB_PASSWORD` trong `.env` rồi khởi động lại ứng dụng.
2. **Lỗi `Can't connect to MySQL server on 'localhost'`:**
   * Dịch vụ MySQL chưa được khởi động. Hãy mở `services.msc` trên Windows và đảm bảo dịch vụ `MySQL80` đang ở trạng thái `Running`.
3. **Lỗi `Unknown database 'phong_kham'`:**
   * Bạn chưa nạp file `phong_kham.sql` vào MySQL. Hãy thực hiện Bước 1 ở trên.
