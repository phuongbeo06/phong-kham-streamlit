import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

# Tải cấu hình từ file .env
load_dotenv()

def get_connection():
    """Tạo kết nối mới tới MySQL database phong_kham."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "phong_kham"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def test_connection():
    """Kiểm tra trạng thái kết nối tới cơ sở dữ liệu."""
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
                return True, "Kết nối thành công tới CSDL phong_kham!"
    except pymysql.MySQLError as e:
        err_code = e.args[0] if len(e.args) > 0 else 0
        err_msg = e.args[1] if len(e.args) > 1 else str(e)
        if err_code == 1045:
            return False, "Không thể đăng nhập MySQL. Vui lòng kiểm tra lại DB_USER và DB_PASSWORD trong file .env."
        elif err_code == 2003:
            return False, "Không thể kết nối đến MySQL Server (Host/Port không đúng hoặc MySQL chưa chạy)."
        elif err_code == 1049:
            return False, "CSDL 'phong_kham' không tồn tại. Vui lòng nạp file phong_kham.sql vào MySQL trước."
        return False, f"Lỗi MySQL ({err_code}): {err_msg}"
    except Exception as e:
        return False, f"Lỗi không xác định: {str(e)}"

def call_procedure(proc_name, args=()):
    """
    Gọi Stored Procedure trong MySQL.
    Xử lý tự động mọi kết quả (kể cả procedure trả về nhiều Result Sets).
    Bắt lỗi SIGNAL 45000 (Mã lỗi 1644) và chuyển thành thông báo tiếng Việt dễ hiểu.
    """
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.callproc(proc_name, args)
                results = []
                while True:
                    rows = cursor.fetchall()
                    results.append(rows)
                    if not cursor.nextset():
                        break
                return True, results, None
    except pymysql.MySQLError as e:
        err_code = e.args[0] if len(e.args) > 0 else 0
        err_msg = e.args[1] if len(e.args) > 1 else str(e)
        if err_code == 1644:
            # Lỗi do SIGNAL SQLSTATE '45000' ném ra từ Trigger/Procedure
            return False, None, err_msg
        elif err_code == 1045:
            return False, None, "Lỗi đăng nhập MySQL (sai tài khoản hoặc mật khẩu trong file .env)."
        elif err_code == 2003:
            return False, None, "Không thể kết nối tới MySQL Server."
        elif err_code == 1049:
            return False, None, "Database 'phong_kham' chưa được tạo. Hãy chạy phong_kham.sql trước."
        elif err_code == 1062:
            return False, None, "Dữ liệu bị trùng lặp khóa chính hoặc ràng buộc UNIQUE."
        return False, None, f"Lỗi MySQL ({err_code}): {err_msg}"
    except Exception as e:
        return False, None, f"Lỗi hệ thống: {str(e)}"

def execute_query(sql, args=()):
    """Thực thi câu lệnh SELECT."""
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, args)
                rows = cursor.fetchall()
                return True, rows, None
    except pymysql.MySQLError as e:
        err_code = e.args[0] if len(e.args) > 0 else 0
        err_msg = e.args[1] if len(e.args) > 1 else str(e)
        if err_code == 1644:
            return False, None, err_msg
        return False, None, f"Lỗi MySQL ({err_code}): {err_msg}"
    except Exception as e:
        return False, None, f"Lỗi: {str(e)}"

def execute_statement(sql, args=()):
    """Thực thi câu lệnh INSERT / UPDATE / DELETE."""
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, args)
                return True, cursor.rowcount, None
    except pymysql.MySQLError as e:
        err_code = e.args[0] if len(e.args) > 0 else 0
        err_msg = e.args[1] if len(e.args) > 1 else str(e)
        if err_code == 1644:
            return False, None, err_msg
        elif err_code == 1062:
            return False, None, "Dữ liệu bị trùng lặp (Mã số, CMT hoặc tên đã tồn tại trong hệ thống)."
        elif err_code == 1451:
            return False, None, "Không thể xóa bản ghi này vì đang có dữ liệu liên quan ở bảng khác."
        return False, None, f"Lỗi MySQL ({err_code}): {err_msg}"
    except Exception as e:
        return False, None, f"Lỗi: {str(e)}"

def execute_insert(sql, args=()):
    """Thực thi câu lệnh INSERT và trả về lastrowid (ID vừa được tạo)."""
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, args)
                return True, cursor.lastrowid, None
    except pymysql.MySQLError as e:
        err_code = e.args[0] if len(e.args) > 0 else 0
        err_msg = e.args[1] if len(e.args) > 1 else str(e)
        if err_code == 1644:
            return False, None, err_msg
        elif err_code == 1062:
            return False, None, "Dữ liệu bị trùng lặp (Mã số, CMT hoặc tên đã tồn tại trong hệ thống)."
        return False, None, f"Lỗi MySQL ({err_code}): {err_msg}"
    except Exception as e:
        return False, None, f"Lỗi: {str(e)}"

def add_doctor(ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt, tham_nien, bac_nghe, trinh_do_dao_tao, chuyen_mon):
    """Thêm Bác sỹ mới vào đồng thời 2 bảng nhan_vien và bac_sy."""
    try:
        conn = get_connection()
        with conn:
            conn.begin()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO nhan_vien (ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt, tham_nien, loai)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, 'BS')""",
                        (ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt, tham_nien)
                    )
                    ma_nv = cursor.lastrowid
                    cursor.execute(
                        """INSERT INTO bac_sy (ma_nv, loai, bac_nghe, trinh_do_dao_tao, chuyen_mon)
                           VALUES (%s, 'BS', %s, %s, %s)""",
                        (ma_nv, bac_nghe, trinh_do_dao_tao, chuyen_mon)
                    )
                conn.commit()
                return True, ma_nv, None
            except Exception:
                conn.rollback()
                raise
    except pymysql.MySQLError as e:
        err_code = e.args[0] if len(e.args) > 0 else 0
        err_msg = e.args[1] if len(e.args) > 1 else str(e)
        if err_code == 1062:
            return False, None, "Mã số BS hoặc số CMT đã tồn tại trong hệ thống."
        elif err_code == 1644:
            return False, None, err_msg
        return False, None, f"Lỗi MySQL ({err_code}): {err_msg}"
    except Exception as e:
        return False, None, f"Lỗi: {str(e)}"

def add_nurse(ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt, tham_nien, trinh_do):
    """Thêm Y tá mới vào đồng thời 2 bảng nhan_vien và y_ta."""
    try:
        conn = get_connection()
        with conn:
            conn.begin()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO nhan_vien (ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt, tham_nien, loai)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, 'YT')""",
                        (ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt, tham_nien)
                    )
                    ma_nv = cursor.lastrowid
                    cursor.execute(
                        """INSERT INTO y_ta (ma_nv, loai, trinh_do)
                           VALUES (%s, 'YT', %s)""",
                        (ma_nv, trinh_do)
                    )
                conn.commit()
                return True, ma_nv, None
            except Exception:
                conn.rollback()
                raise
    except pymysql.MySQLError as e:
        err_code = e.args[0] if len(e.args) > 0 else 0
        err_msg = e.args[1] if len(e.args) > 1 else str(e)
        if err_code == 1062:
            return False, None, "Mã số NV hoặc số CMT đã tồn tại trong hệ thống."
        elif err_code == 1644:
            return False, None, err_msg
        return False, None, f"Lỗi MySQL ({err_code}): {err_msg}"
    except Exception as e:
        return False, None, f"Lỗi: {str(e)}"


def _change_staff(statements):
    """Ghi các thay đổi liên quan đến nhân viên như một giao dịch."""
    try:
        conn = get_connection()
        with conn:
            conn.begin()
            try:
                with conn.cursor() as cursor:
                    for sql, args in statements:
                        cursor.execute(sql, args)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return True, None
    except pymysql.MySQLError as e:
        if e.args and e.args[0] == 1451:
            return False, "Không thể xóa nhân viên vì đã có hồ sơ khám liên quan."
        if e.args and e.args[0] == 1062:
            return False, "Thông tin nhân viên bị trùng."
        return False, f"Lỗi MySQL: {e}"
    except Exception as e:
        return False, f"Lỗi: {e}"


def update_staff(ma_nv, loai, ho_ten, ngay_sinh, dia_chi, sdt, tham_nien, *details):
    """Cập nhật thông tin chung và thông tin chuyên môn của bác sĩ/y tá."""
    if loai == "BS" and len(details) == 3:
        child = (
            "UPDATE bac_sy SET bac_nghe=%s, trinh_do_dao_tao=%s, chuyen_mon=%s WHERE ma_nv=%s",
            (*details, ma_nv),
        )
    elif loai == "YT" and len(details) == 1:
        child = ("UPDATE y_ta SET trinh_do=%s WHERE ma_nv=%s", (details[0], ma_nv))
    else:
        return False, "Loại nhân viên không hợp lệ."
    common = (
        "UPDATE nhan_vien SET ho_ten=%s, ngay_sinh=%s, dia_chi=%s, sdt=%s, tham_nien=%s WHERE ma_nv=%s AND loai=%s",
        (ho_ten, ngay_sinh, dia_chi, sdt, tham_nien, ma_nv, loai),
    )
    return _change_staff((common, child))


def delete_staff(ma_nv, loai):
    """Xóa lớp con rồi xóa nhân viên; khóa ngoại chặn hồ sơ đã được sử dụng."""
    table = {"BS": "bac_sy", "YT": "y_ta"}.get(loai)
    if table is None:
        return False, "Loại nhân viên không hợp lệ."
    return _change_staff((
        (f"DELETE FROM {table} WHERE ma_nv=%s", (ma_nv,)),
        ("DELETE FROM nhan_vien WHERE ma_nv=%s AND loai=%s", (ma_nv, loai)),
    ))
