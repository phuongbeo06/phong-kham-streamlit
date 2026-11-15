import os
import re
import streamlit as st
import pandas as pd
import datetime
from dotenv import load_dotenv

import db

# Cấu hình trang giao diện
st.set_page_config(
    page_title="Phòng khám An Tâm | Quản lý",
    page_icon="✚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tải cấu hình từ .env
load_dotenv()


def fmt_vnd(amount):
    try:
        val = float(amount or 0)
        return f"{val:,.0f} đ".replace(",", ".")
    except Exception:
        return f"{amount} đ"


# Helper kiểm tra định dạng CMT/CCCD (đúng 12 chữ số)
def validate_cmt(cmt: str) -> tuple[bool, str]:
    s = (cmt or "").strip()
    if not s:
        return False, "Số CMT/CCCD không được để trống."
    if not re.fullmatch(r"\d{12}", s):
        return False, "Số CMT/CCCD phải gồm đúng 12 chữ số (ví dụ: 001080012345)."
    return True, ""


# Helper kiểm tra định dạng SĐT (chỉ gồm chữ số, 10-11 số)
def validate_sdt(sdt: str, allow_empty: bool = True) -> tuple[bool, str]:
    s = (sdt or "").strip()
    if not s:
        if allow_empty:
            return True, ""
        return False, "Số điện thoại không được để trống."
    if not re.fullmatch(r"\d{10,11}", s):
        return False, "Số điện thoại chỉ gồm chữ số và phải có từ 10 đến 11 số (ví dụ: 0901234567)."
    return True, ""


def show_staff_actions(loai, rows):
    if not rows:
        return
    title = "bác sỹ" if loai == "BS" else "y tá"
    options = {f"{row['ma_so']} - {row['ho_ten']}": row for row in rows}

    with st.expander(f"✏️ Sửa thông tin {title}"):
        selected = options[st.selectbox(f"Chọn {title} cần sửa", list(options), key=f"edit_{loai}")]
        staff_id = selected["ma_nv"]
        with st.form(f"edit_staff_{loai}_{staff_id}"):
            name = st.text_input("Họ và tên", value=selected["ho_ten"])
            birthday = st.date_input("Ngày sinh", value=selected["ngay_sinh"],
                                     min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today())
            address = st.text_input("Địa chỉ", value=selected["dia_chi"] or "")
            phone = st.text_input("Số điện thoại", value=selected["sdt"] or "")
            seniority = st.number_input("Thâm niên (năm)", min_value=0, max_value=255,
                                        value=int(selected["tham_nien"]))
            if loai == "BS":
                grade = st.text_input("Bậc nghề", value=selected["bac_nghe"])
                training = st.text_input("Trình độ đào tạo", value=selected["trinh_do_dao_tao"])
                specialty = st.text_input("Chuyên môn", value=selected["chuyen_mon"])
                details = (grade.strip(), training.strip(), specialty.strip())
            else:
                training = st.text_input("Trình độ", value=selected["trinh_do"])
                details = (training.strip(),)
            save = st.form_submit_button("Lưu thay đổi", type="primary")
        if save:
            valid_phone, phone_error = validate_sdt(phone)
            if not name.strip() or any(not value for value in details):
                st.error("Họ tên và thông tin chuyên môn không được để trống.")
            elif not valid_phone:
                st.error(phone_error)
            else:
                ok, error = db.update_staff(staff_id, loai, name.strip(), str(birthday),
                                            address.strip(), phone.strip(), seniority, *details)
                if ok:
                    st.success("Đã cập nhật nhân viên.")
                    st.rerun()
                else:
                    st.error(error)

    with st.expander(f"🗑️ Xóa {title}"):
        selected = options[st.selectbox(f"Chọn {title} cần xóa", list(options), key=f"delete_{loai}")]
        with st.form(f"delete_staff_{loai}_{selected['ma_nv']}"):
            confirm = st.checkbox(f"Tôi xác nhận xóa {selected['ho_ten']} ({selected['ma_so']})")
            delete = st.form_submit_button("Xóa nhân viên")
        if delete:
            if not confirm:
                st.warning("Hãy đánh dấu xác nhận trước khi xóa.")
            else:
                ok, error = db.delete_staff(selected["ma_nv"], loai)
                if ok:
                    st.success("Đã xóa nhân viên.")
                    st.rerun()
                else:
                    st.error(error)


def inject_css():
    style_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
    with open(style_path, encoding="utf-8") as stylesheet:
        st.markdown(f"<style>{stylesheet.read()}</style>", unsafe_allow_html=True)


# Kích hoạt style giao diện
inject_css()

# Kiểm tra trạng thái kết nối CSDL
is_connected, _ = db.test_connection()

NAV_ITEMS = {
    "Trang chủ": "Tổng quan",
    "Bệnh nhân": "Bệnh nhân",
    "Nhân viên & danh mục": "Danh sách",
    "Khám chữa bệnh": "Nhập dữ liệu",
    "Báo cáo": "Báo cáo",
}


def go_to(page):
    st.session_state["main_nav"] = page


if st.session_state.get("main_nav") not in NAV_ITEMS:
    st.session_state["main_nav"] = "Trang chủ"

with st.sidebar:
    st.markdown(
        '<div class="app-brand"><span class="brand-mark" aria-hidden="true">+</span>'
        '<div><div class="brand-name">Phòng khám An Tâm</div>'
        '<div class="brand-subtitle">Quản lý khám chữa bệnh</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<p class="nav-label">ĐIỀU HƯỚNG</p>', unsafe_allow_html=True)
    for page in NAV_ITEMS:
        st.button(
            page,
            key=f"nav_{page}",
            type="primary" if st.session_state["main_nav"] == page else "secondary",
            use_container_width=True,
            on_click=go_to,
            args=(page,),
        )
    st.markdown('<div class="sidebar-help"><strong>Cần bắt đầu?</strong><br>Chọn Bệnh nhân để tiếp nhận, sau đó vào Khám chữa bệnh.</div>', unsafe_allow_html=True)

current_page = st.session_state["main_nav"]
nav = NAV_ITEMS[current_page]

if not is_connected:
    st.markdown('<div class="empty-state"><span class="empty-state-label">TẠM THỜI GIÁN ĐOẠN</span><h1>Chưa thể mở hồ sơ phòng khám</h1><p>Ứng dụng chưa sẵn sàng. Vui lòng thử lại sau hoặc liên hệ người quản lý hệ thống.</p></div>', unsafe_allow_html=True)
    if st.button("Thử kết nối lại", type="primary"):
        st.rerun()
    st.stop()

# =====================================================================
# MENU 1: TỔNG QUAN
# =====================================================================
if nav == "Tổng quan":
    st.markdown(
        '<section class="home-hero"><p class="hero-eyebrow">PHÒNG KHÁM AN TÂM</p>'
        '<h1>Quản lý phòng khám, rõ từng bước.</h1>'
        '<p>Tiếp nhận bệnh nhân, theo dõi điều trị và xem tình hình hoạt động tại một nơi.</p>'
        '</section>', unsafe_allow_html=True,
    )

    st.subheader("Tổng quan hôm nay")
    m1, m2, m3, m4 = st.columns(4)
    ok_cnt_bn, rows_cnt_bn, _ = db.execute_query("SELECT COUNT(*) AS cnt FROM benh_nhan")
    ok_cnt_bs, rows_cnt_bs, _ = db.execute_query("SELECT COUNT(*) AS cnt FROM bac_sy")
    ok_cnt_yt, rows_cnt_yt, _ = db.execute_query("SELECT COUNT(*) AS cnt FROM y_ta")
    ok_cnt_dot, rows_cnt_dot, _ = db.execute_query("SELECT COUNT(*) AS cnt FROM dot_benh WHERE ngay_ket_thuc IS NULL")

    with m1:
        cnt_bn = rows_cnt_bn[0]["cnt"] if ok_cnt_bn and rows_cnt_bn else 0
        st.metric("Bệnh nhân", cnt_bn)
    with m2:
        cnt_bs = rows_cnt_bs[0]["cnt"] if ok_cnt_bs and rows_cnt_bs else 0
        st.metric("Bác sĩ", cnt_bs)
    with m3:
        cnt_yt = rows_cnt_yt[0]["cnt"] if ok_cnt_yt and rows_cnt_yt else 0
        st.metric("Y tá", cnt_yt)
    with m4:
        cnt_dot = rows_cnt_dot[0]["cnt"] if ok_cnt_dot and rows_cnt_dot else 0
        st.metric("Đang điều trị", cnt_dot)

    st.subheader("Bắt đầu công việc")
    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown('<div class="action-kicker">01 · TIẾP NHẬN</div><h3 class="action-title">Bệnh nhân</h3><p class="action-copy">Tìm hồ sơ, tiếp nhận người mới hoặc sửa thông tin.</p>', unsafe_allow_html=True)
            st.button("Mở hồ sơ bệnh nhân", key="home_patients", use_container_width=True,
                      on_click=go_to, args=("Bệnh nhân",))
        with st.container(border=True):
            st.markdown('<div class="action-kicker">03 · QUẢN LÝ</div><h3 class="action-title">Nhân viên và danh mục</h3><p class="action-copy">Xem bác sĩ, y tá, thuốc và các loại bệnh.</p>', unsafe_allow_html=True)
            st.button("Xem nhân viên và danh mục", key="home_catalog", use_container_width=True,
                      on_click=go_to, args=("Nhân viên & danh mục",))
    with right:
        with st.container(border=True):
            st.markdown('<div class="action-kicker">02 · ĐIỀU TRỊ</div><h3 class="action-title">Khám chữa bệnh</h3><p class="action-copy">Mở đợt bệnh, ghi lần khám, kê thuốc và phân công y tá.</p>', unsafe_allow_html=True)
            st.button("Bắt đầu khám bệnh", key="home_care", use_container_width=True,
                      on_click=go_to, args=("Khám chữa bệnh",))
        with st.container(border=True):
            st.markdown('<div class="action-kicker">04 · THEO DÕI</div><h3 class="action-title">Báo cáo hoạt động</h3><p class="action-copy">Xem tình hình bệnh, lương nhân viên và doanh thu.</p>', unsafe_allow_html=True)
            st.button("Mở báo cáo", key="home_reports", use_container_width=True,
                      on_click=go_to, args=("Báo cáo",))

    st.subheader("Hoạt động gần đây")
    recent_col, doctor_col = st.columns([1.7, 1], gap="large")

    # Lần khám gần đây
    with recent_col:
        st.markdown("**Các lần khám mới nhất**")
        ok_lk, lk_recent, _ = db.execute_query("""
            SELECT lk.ma_lan_kham, lk.ngay_vao, lk.ngay_ra, bn.ho_ten, b.ten_benh,
                   nv.ho_ten AS ten_bs, lk.tong_tien
            FROM lan_kham lk
            JOIN dot_benh d ON d.ma_dot = lk.ma_dot
            JOIN benh_nhan bn ON bn.ma_bn = d.ma_bn
            JOIN benh b ON b.ma_benh = d.ma_benh
            JOIN nhan_vien nv ON nv.ma_nv = d.ma_bs
            ORDER BY lk.ngay_vao DESC, lk.ma_lan_kham DESC
            LIMIT 8
        """)
        if ok_lk and lk_recent:
            df_lk_recent = pd.DataFrame(lk_recent)
            df_lk_recent["tong_tien"] = df_lk_recent["tong_tien"].apply(fmt_vnd)
            df_lk_recent.columns = ["Mã", "Ngày vào", "Ngày ra", "Bệnh nhân", "Bệnh", "Bác sĩ", "Tổng tiền"]
            st.dataframe(df_lk_recent, use_container_width=True, hide_index=True, height=300)
        else:
            st.info("Chưa có lần khám nào.")

    # Tải trọng bác sỹ
    with doctor_col:
        st.markdown("**Bác sĩ đang phụ trách**")
        ok_wl, wl_rows, _ = db.execute_query("""
            SELECT nv.ho_ten, COUNT(d.ma_dot) AS so_dot_hien_tai
            FROM bac_sy bs
            JOIN nhan_vien nv ON nv.ma_nv = bs.ma_nv
            LEFT JOIN dot_benh d ON d.ma_bs = bs.ma_nv AND d.ngay_ket_thuc IS NULL
            GROUP BY bs.ma_nv, nv.ho_ten
            ORDER BY so_dot_hien_tai DESC
        """)
        if ok_wl and wl_rows:
            df_wl = pd.DataFrame(wl_rows)
            df_wl.columns = ["Bác sĩ", "Đợt đang điều trị"]
            st.dataframe(df_wl, use_container_width=True, hide_index=True, height=300)
        else:
            st.info("Chưa có bác sĩ nào.")
        st.caption("Mỗi bác sĩ phụ trách tối đa 30 đợt đang điều trị.")

# =====================================================================
# MENU 2: BỆNH NHÂN
# =====================================================================
elif nav == "Bệnh nhân":
    st.title("Bệnh nhân")
    st.markdown("<p class='page-desc'>Tìm hồ sơ để xem lịch sử khám, hoặc thêm và cập nhật thông tin bệnh nhân.</p>", unsafe_allow_html=True)
    tab_tracuu, tab_quanly = st.tabs(["Xem hồ sơ", "Thêm, sửa hoặc xóa"])

    # ---- Tab 1: Tra cứu hồ sơ (old menu 3) ----
    with tab_tracuu:
        st.subheader("Tra cứu hồ sơ")
        st.markdown("<p class='page-desc'>Xem thông tin cá nhân, tình trạng bệnh hiện tại và toàn bộ lịch sử khám chữa bệnh của bệnh nhân.</p>", unsafe_allow_html=True)

        ok_bn, bn_list, _ = db.execute_query("SELECT ma_bn, ma_so, ho_ten, cmt FROM benh_nhan ORDER BY ma_bn")

        if ok_bn and bn_list:
            bn_options = {f"{b['ma_so']} - {b['ho_ten']} (CMT: {b['cmt']})": b["ma_bn"] for b in bn_list}
            selected_label = st.selectbox("Chọn bệnh nhân để tra cứu:", options=list(bn_options.keys()), key="tracuu_sel")
            ma_bn = bn_options[selected_label]
        else:
            ma_bn = None
            st.info("Chưa có bệnh nhân nào. Chọn mục ‘Thêm, sửa hoặc xóa’ để tạo hồ sơ đầu tiên.")

        success, results, err = db.call_procedure("sp_thong_tin_benh_nhan", (ma_bn,)) if ma_bn else (True, [], None)

        if not success:
            st.error(f"❌ Lỗi khi tra cứu: {err}")
        elif results and len(results) >= 3:
            info_rows = results[0]
            history_rows = results[1]
            active_rows = results[2]

            if not info_rows:
                st.warning("Không tìm thấy thông tin bệnh nhân này.")
            else:
                bn = info_rows[0]
                st.subheader("Thông tin bệnh nhân")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.write(f"**Mã số:** `{bn['ma_so']}`")
                    st.write(f"**Họ tên:** **{bn['ho_ten']}**")
                with c2:
                    st.write(f"**Số CMT/CCCD:** `{bn['cmt']}`")
                    st.write(f"**Ngày sinh:** {bn['ngay_sinh']}")
                with c3:
                    st.write(f"**Số điện thoại:** {bn['sdt']}")
                    st.write(f"**Địa chỉ:** {bn['dia_chi']}")
                with c4:
                    st.write(f"**Số loại bệnh từng mắc:** {len(set(r['ten_benh'] for r in history_rows)) if history_rows else 0}")
                    st.write(f"**Tổng số lần khám:** {len(history_rows) if history_rows else 0}")

                st.markdown("---")

                st.subheader("Bệnh đang điều trị")
                if not active_rows:
                    st.success("✅ Hiện tại bệnh nhân không có bệnh nào đang điều trị (đã chữa khỏi hoặc chưa có đợt mới).")
                else:
                    df_active = pd.DataFrame(active_rows)
                    df_active.columns = ["Tên Bệnh Đang Mắc", "Ngày Bắt Đầu Đợt", "Đã Khám Lần Thứ Mấy", "Bác Sỹ Phụ Trách"]
                    st.dataframe(df_active, use_container_width=True, hide_index=True)

                st.subheader("Lịch sử khám chữa bệnh")
                if not history_rows:
                    st.info("Bệnh nhân chưa có lịch sử khám chữa bệnh nào.")
                else:
                    df_hist = pd.DataFrame(history_rows)
                    df_hist["phi_kham"] = df_hist["phi_kham"].apply(fmt_vnd)
                    df_hist["tong_tien"] = df_hist["tong_tien"].apply(fmt_vnd)
                    df_hist.columns = [
                        "Tên Bệnh", "Lần Mắc Thứ (Đợt)", "Lần Khám Thứ (Trong đợt)",
                        "Ngày Vào", "Ngày Ra", "Bác Sỹ Phụ Trách", "Phí Khám", "Tổng Tiền (Kèm thuốc)"
                    ]
                    st.dataframe(df_hist, use_container_width=True, hide_index=True)

    # ---- Tab 2: Quản lý bệnh nhân (old menu 5) ----
    with tab_quanly:
        st.subheader("Quản lý hồ sơ")
        st.markdown("<p class='page-desc'>Tra cứu, thêm mới, chỉnh sửa thông tin hoặc xóa hồ sơ bệnh nhân.</p>", unsafe_allow_html=True)

        keyword = st.text_input("🔍 Tìm kiếm theo tên, mã số (BN...) hoặc số CMT/CCCD:", value="", key="quanly_kw")

        if keyword.strip():
            kw = f"%{keyword.strip()}%"
            ok_bn, bn_list, err = db.execute_query(
                "SELECT ma_bn, ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt FROM benh_nhan WHERE ho_ten LIKE %s OR ma_so LIKE %s OR cmt LIKE %s ORDER BY ma_bn DESC",
                (kw, kw, kw)
            )
        else:
            ok_bn, bn_list, err = db.execute_query(
                "SELECT ma_bn, ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt FROM benh_nhan ORDER BY ma_bn DESC"
            )

        if ok_bn and bn_list:
            df_bn = pd.DataFrame(bn_list)
            df_bn.columns = ["Mã BN", "Mã Số", "Số CMT/CCCD", "Họ Tên", "Ngày Sinh", "Địa Chỉ", "Số Điện Thoại"]
            st.dataframe(df_bn, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có bệnh nhân nào hoặc không tìm thấy kết quả phù hợp.")

        st.markdown("---")
        tab_add, tab_edit, tab_del = st.tabs(["Thêm bệnh nhân", "Sửa thông tin", "Xóa hồ sơ"])

        # Thêm bệnh nhân
        with tab_add:
            st.subheader("Nhập thông tin bệnh nhân mới")
            with st.form("form_add_bn", clear_on_submit=True):
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    new_ms = st.text_input("Mã số bệnh nhân (*)", placeholder="Ví dụ: BN005").strip()
                    new_cmt = st.text_input("Số CMT / CCCD (*)", placeholder="12 chữ số").strip()
                    new_ten = st.text_input("Họ và tên (*)", placeholder="Nguyễn Văn A").strip()
                with f_col2:
                    new_ns = st.date_input("Ngày sinh (*)", value=datetime.date(1995, 1, 1), min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today())
                    new_sdt = st.text_input("Số điện thoại", placeholder="0901234567").strip()
                    new_dc = st.text_input("Địa chỉ", placeholder="Số nhà, đường, quận/huyện, tỉnh/thành").strip()

                btn_submit_add = st.form_submit_button("Lưu bệnh nhân", type="primary")

            if btn_submit_add:
                if not new_ms or not new_cmt or not new_ten:
                    st.error("❌ Vui lòng điền đầy đủ các thông tin bắt buộc (*): Mã số, CMT, Họ tên.")
                else:
                    ok_cmt, msg_cmt = validate_cmt(new_cmt)
                    if not ok_cmt:
                        st.error(f"❌ {msg_cmt}")
                    else:
                        ok_sdt, msg_sdt = validate_sdt(new_sdt, allow_empty=True)
                        if not ok_sdt:
                            st.error(f"❌ {msg_sdt}")
                        else:
                            sql_insert = "INSERT INTO benh_nhan (ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt) VALUES (%s, %s, %s, %s, %s, %s)"
                            ok, _, err_msg = db.execute_statement(sql_insert, (new_ms, new_cmt, new_ten, str(new_ns), new_dc, new_sdt))
                            if not ok:
                                st.error(f"❌ {err_msg}")
                            else:
                                st.success(f"✅ Đã thêm bệnh nhân **{new_ten}** ({new_ms}) thành công!")
                                st.rerun()

        # Sửa bệnh nhân
        with tab_edit:
            st.subheader("Cập nhật thông tin bệnh nhân")
            if ok_bn and bn_list:
                options_edit = {f"{b['ma_so']} - {b['ho_ten']} (CMT: {b['cmt']})": b for b in bn_list}
                sel_label = st.selectbox("Chọn bệnh nhân cần sửa:", options=list(options_edit.keys()), key="sel_edit_bn")
                cur_bn = options_edit[sel_label]

                with st.form("form_edit_bn"):
                    e_col1, e_col2 = st.columns(2)
                    with e_col1:
                        st.text_input("Mã số (Không đổi)", value=cur_bn["ma_so"], disabled=True)
                        st.text_input("Số CMT (Không đổi)", value=cur_bn["cmt"], disabled=True)
                        e_ten = st.text_input("Họ và tên (*)", value=cur_bn["ho_ten"]).strip()
                    with e_col2:
                        default_ns = cur_bn["ngay_sinh"] if isinstance(cur_bn["ngay_sinh"], datetime.date) else datetime.date(1995, 1, 1)
                        e_ns = st.date_input("Ngày sinh (*)", value=default_ns, min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today())
                        e_sdt = st.text_input("Số điện thoại", value=cur_bn["sdt"] or "").strip()
                        e_dc = st.text_input("Địa chỉ", value=cur_bn["dia_chi"] or "").strip()

                    btn_submit_edit = st.form_submit_button("Lưu thay đổi", type="primary")

                if btn_submit_edit:
                    if not e_ten:
                        st.error("❌ Họ và tên không được để trống!")
                    else:
                        ok_sdt, msg_sdt = validate_sdt(e_sdt, allow_empty=True)
                        if not ok_sdt:
                            st.error(f"❌ {msg_sdt}")
                        else:
                            sql_update = "UPDATE benh_nhan SET ho_ten = %s, ngay_sinh = %s, dia_chi = %s, sdt = %s WHERE ma_bn = %s"
                            ok, _, err_msg = db.execute_statement(sql_update, (e_ten, str(e_ns), e_dc, e_sdt, cur_bn["ma_bn"]))
                            if not ok:
                                st.error(f"❌ {err_msg}")
                            else:
                                st.success(f"✅ Đã cập nhật thông tin bệnh nhân **{e_ten}** thành công!")
                                st.rerun()
            else:
                st.info("Không có dữ liệu bệnh nhân để sửa.")

        # Xóa bệnh nhân
        with tab_del:
            st.subheader("Xóa hồ sơ bệnh nhân")
            if ok_bn and bn_list:
                options_del = {f"{b['ma_so']} - {b['ho_ten']} (CMT: {b['cmt']})": b for b in bn_list}
                sel_del_label = st.selectbox("Chọn bệnh nhân cần xóa:", options=list(options_del.keys()), key="sel_del_bn")
                bn_to_del = options_del[sel_del_label]

                st.warning(f"⚠️ Bạn có chắc chắn muốn xóa bệnh nhân **{bn_to_del['ho_ten']}** ({bn_to_del['ma_so']})?")
                st.write("Lưu ý: Nếu bệnh nhân đã có lịch sử khám bệnh trong hệ thống, dữ liệu sẽ được giữ lại để đảm bảo tính toàn vẹn.")

                if st.button("🗑️ Xác nhận xóa", type="primary"):
                    sql_delete = "DELETE FROM benh_nhan WHERE ma_bn = %s"
                    ok, _, err_msg = db.execute_statement(sql_delete, (bn_to_del["ma_bn"],))
                    if not ok:
                        st.error(f"❌ {err_msg}")
                    else:
                        st.success(f"✅ Đã xóa bệnh nhân **{bn_to_del['ho_ten']}** thành công!")
                        st.rerun()
            else:
                st.info("Không có dữ liệu bệnh nhân để xóa.")

# =====================================================================
# MENU 3: DANH SÁCH
# =====================================================================
elif nav == "Danh sách":
    st.title("Nhân viên và danh mục")
    st.markdown("<p class='page-desc'>Xem và quản lý bác sĩ, y tá, thuốc và các loại bệnh. Hồ sơ bệnh nhân nằm ở mục Bệnh nhân.</p>", unsafe_allow_html=True)
    tab_bs, tab_yt, tab_thuoc, tab_benh = st.tabs([
        "Bác sĩ", "Y tá", "Thuốc", "Loại bệnh"
    ])

    # ---- Tab Bác sỹ ----
    with tab_bs:
        st.subheader("Danh sách bác sĩ")
        ok_bs_all, all_bs, _ = db.execute_query("""
            SELECT nv.ma_nv, nv.ma_so, nv.cmt, nv.ho_ten, nv.ngay_sinh, nv.dia_chi, nv.sdt, nv.tham_nien,
                   bs.bac_nghe, bs.trinh_do_dao_tao, bs.chuyen_mon
            FROM bac_sy bs
            JOIN nhan_vien nv ON nv.ma_nv = bs.ma_nv
            ORDER BY nv.ma_so
        """)
        if ok_bs_all and all_bs:
            df_all_bs = pd.DataFrame(all_bs)[["ma_so", "cmt", "ho_ten", "ngay_sinh", "sdt", "tham_nien",
                                            "bac_nghe", "trinh_do_dao_tao", "chuyen_mon"]]
            df_all_bs.columns = ["Mã BS", "Số CMT", "Họ Tên", "Ngày Sinh", "Số ĐT", "Thâm Niên (Năm)", "Bậc Nghề", "Trình Độ", "Chuyên Môn"]
            st.dataframe(df_all_bs, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có bác sỹ nào trong hệ thống.")

        st.markdown("---")
        st.subheader("Thêm bác sĩ")
        with st.form("form_add_bs", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                bs_ma_so = st.text_input("Mã số BS (*):", placeholder="Ví dụ: BS004").strip()
                bs_cmt = st.text_input("Số CMT/CCCD (*):", placeholder="12 chữ số").strip()
                bs_ten = st.text_input("Họ và tên Bác sỹ (*):", placeholder="Ví dụ: Hoàng Quốc Huy").strip()
                bs_ns = st.date_input("Ngày sinh (*):", value=datetime.date(1985, 5, 20), min_value=datetime.date(1940, 1, 1), max_value=datetime.date.today())
                bs_tham_nien = st.number_input("Thâm niên (năm):", min_value=0, max_value=60, value=5)
            with c2:
                bs_sdt = st.text_input("Số điện thoại:", placeholder="0901xxxxxx").strip()
                bs_dc = st.text_input("Địa chỉ:", placeholder="Hà Nội...").strip()
                bs_bac_nghe = st.selectbox("Bậc nghề (*):", options=["Bác sỹ chuyên khoa I", "Bác sỹ chuyên khoa II", "Bác sỹ đa khoa", "Bác sỹ nội trú"])
                bs_trinh_do = st.selectbox("Trình độ đào tạo (*):", options=["Tiến sỹ", "Thạc sỹ", "Bác sỹ"])
                bs_chuyen_mon = st.text_input("Chuyên môn (*):", placeholder="Ví dụ: Tai Mũi Họng, Răng Hàm Mặt, Mắt...").strip()

            btn_submit_bs = st.form_submit_button("Lưu Bác sỹ", type="primary")

        if btn_submit_bs:
            if not bs_ma_so or not bs_cmt or not bs_ten or not bs_chuyen_mon:
                st.error("❌ Vui lòng nhập đầy đủ các thông tin bắt buộc (*): Mã số, CMT, Họ tên, Chuyên môn!")
            else:
                ok_cmt, msg_cmt = validate_cmt(bs_cmt)
                if not ok_cmt:
                    st.error(f"❌ {msg_cmt}")
                else:
                    ok_sdt, msg_sdt = validate_sdt(bs_sdt, allow_empty=True)
                    if not ok_sdt:
                        st.error(f"❌ {msg_sdt}")
                    else:
                        ok_bs, new_bs_id, err_msg = db.add_doctor(
                            bs_ma_so, bs_cmt, bs_ten, str(bs_ns), bs_dc, bs_sdt, bs_tham_nien,
                            bs_bac_nghe, bs_trinh_do, bs_chuyen_mon
                        )
                        if not ok_bs:
                            st.error(f"❌ {err_msg}")
                        else:
                            st.success(f"🎉 Đã thêm Bác sỹ **{bs_ten}** ({bs_ma_so}) thành công!")
                            st.rerun()

        show_staff_actions("BS", all_bs if ok_bs_all else [])

    # ---- Tab Y tá ----
    with tab_yt:
        st.subheader("Danh sách y tá")
        ok_yt_all, all_yt, _ = db.execute_query("""
            SELECT nv.ma_nv, nv.ma_so, nv.cmt, nv.ho_ten, nv.ngay_sinh, nv.dia_chi, nv.sdt, nv.tham_nien, yt.trinh_do
            FROM y_ta yt
            JOIN nhan_vien nv ON nv.ma_nv = yt.ma_nv
            ORDER BY nv.ma_so
        """)
        if ok_yt_all and all_yt:
            df_all_yt = pd.DataFrame(all_yt)[["ma_so", "cmt", "ho_ten", "ngay_sinh", "sdt", "tham_nien", "trinh_do"]]
            df_all_yt.columns = ["Mã YT", "Số CMT", "Họ Tên", "Ngày Sinh", "Số ĐT", "Thâm Niên (Năm)", "Trình Độ Đào Tạo"]
            st.dataframe(df_all_yt, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có y tá nào trong hệ thống.")

        st.markdown("---")
        st.subheader("Thêm y tá")
        with st.form("form_add_yt", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                yt_ma_so = st.text_input("Mã số Y tá (*):", placeholder="Ví dụ: YT005").strip()
                yt_cmt = st.text_input("Số CMT/CCCD (*):", placeholder="12 chữ số").strip()
                yt_ten = st.text_input("Họ và tên Y tá (*):", placeholder="Ví dụ: Lê Thị Hoa").strip()
                yt_ns = st.date_input("Ngày sinh (*):", value=datetime.date(1996, 8, 15), min_value=datetime.date(1940, 1, 1), max_value=datetime.date.today(), key="ns_yt")
            with c2:
                yt_sdt = st.text_input("Số điện thoại:", placeholder="0912xxxxxx", key="sdt_yt").strip()
                yt_dc = st.text_input("Địa chỉ:", placeholder="Hà Nội...", key="dc_yt").strip()
                yt_tham_nien = st.number_input("Thâm niên (năm):", min_value=0, max_value=60, value=2, key="tn_yt")
                yt_trinh_do = st.selectbox("Trình độ đào tạo (*):", options=["Đại học Điều dưỡng", "Cao đẳng Điều dưỡng", "Trung cấp Y tế"])

            btn_submit_yt = st.form_submit_button("Lưu Y tá", type="primary")

        if btn_submit_yt:
            if not yt_ma_so or not yt_cmt or not yt_ten:
                st.error("❌ Vui lòng nhập đầy đủ các thông tin bắt buộc (*): Mã số, CMT, Họ tên!")
            else:
                ok_cmt, msg_cmt = validate_cmt(yt_cmt)
                if not ok_cmt:
                    st.error(f"❌ {msg_cmt}")
                else:
                    ok_sdt, msg_sdt = validate_sdt(yt_sdt, allow_empty=True)
                    if not ok_sdt:
                        st.error(f"❌ {msg_sdt}")
                    else:
                        ok_yt, new_yt_id, err_msg = db.add_nurse(
                            yt_ma_so, yt_cmt, yt_ten, str(yt_ns), yt_dc, yt_sdt, yt_tham_nien, yt_trinh_do
                        )
                        if not ok_yt:
                            st.error(f"❌ {err_msg}")
                        else:
                            st.success(f"🎉 Đã thêm Y tá **{yt_ten}** ({yt_ma_so}) thành công!")
                            st.rerun()

        show_staff_actions("YT", all_yt if ok_yt_all else [])

    # ---- Tab Thuốc ----
    with tab_thuoc:
        st.subheader("Danh sách thuốc")
        ok_t, thuoc_list, _ = db.execute_query("SELECT ma_thuoc, ten_thuoc, don_vi, don_gia FROM thuoc ORDER BY ma_thuoc")
        if ok_t and thuoc_list:
            df_t = pd.DataFrame(thuoc_list)
            df_t["don_gia_fmt"] = df_t["don_gia"].apply(fmt_vnd)
            disp_t = df_t[["ma_thuoc", "ten_thuoc", "don_vi", "don_gia_fmt"]].copy()
            disp_t.columns = ["Mã Thuốc", "Tên Thuốc", "Đơn Vị Tính", "Đơn Giá Hiện Tại"]
            st.dataframe(disp_t, use_container_width=True, hide_index=True)

        st.markdown("---")
        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.subheader("Thêm thuốc")
            with st.form("form_add_thuoc", clear_on_submit=True):
                new_ten_thuoc = st.text_input("Tên thuốc (*):", placeholder="Ví dụ: Cefixim 200mg").strip()
                new_don_vi = st.text_input("Đơn vị tính (*):", placeholder="viên, chai, vỉ, gói...").strip()
                new_don_gia = st.number_input("Đơn giá (VNĐ) (*):", min_value=0, value=5000, step=1000)
                btn_add_thuoc = st.form_submit_button("Lưu thuốc mới", type="primary")

            if btn_add_thuoc:
                if not new_ten_thuoc or not new_don_vi:
                    st.error("❌ Tên thuốc và đơn vị tính không được để trống!")
                else:
                    sql_add_t = "INSERT INTO thuoc (ten_thuoc, don_vi, don_gia) VALUES (%s, %s, %s)"
                    ok_t_ins, _, err_msg = db.execute_statement(sql_add_t, (new_ten_thuoc, new_don_vi, new_don_gia))
                    if not ok_t_ins:
                        st.error(f"❌ {err_msg}")
                    else:
                        st.success(f"✅ Đã thêm thuốc **{new_ten_thuoc}** vào danh mục thành công!")
                        st.rerun()

        with col_t2:
            st.subheader("Điều chỉnh giá thuốc")
            if ok_t and thuoc_list:
                dict_up_t = {f"{t['ten_thuoc']} ({t['don_vi']}) - Hiện tại: {fmt_vnd(t['don_gia'])}": t for t in thuoc_list}
                sel_up_key = st.selectbox("Chọn thuốc cần đổi giá:", options=list(dict_up_t.keys()))
                t_to_update = dict_up_t[sel_up_key]

                with st.form("form_update_gia_thuoc"):
                    cur_price = int(t_to_update["don_gia"])
                    updated_price = st.number_input("Nhập đơn giá mới (VNĐ) (*):", min_value=0, value=cur_price, step=1000)
                    btn_up_price = st.form_submit_button("Cập nhật đơn giá", type="primary")

                if btn_up_price:
                    sql_up_p = "UPDATE thuoc SET don_gia = %s WHERE ma_thuoc = %s"
                    ok_up, _, err_msg = db.execute_statement(sql_up_p, (updated_price, t_to_update["ma_thuoc"]))
                    if not ok_up:
                        st.error(f"❌ {err_msg}")
                    else:
                        st.success(f"✅ Đã cập nhật giá thuốc **{t_to_update['ten_thuoc']}** thành {fmt_vnd(updated_price)}!")
                        st.rerun()

    # ---- Tab Bệnh ----
    with tab_benh:
        st.subheader("Danh sách bệnh")
        ok_b, benh_list, _ = db.execute_query("SELECT ma_benh, ten_benh FROM benh ORDER BY ma_benh")
        if ok_b and benh_list:
            df_b = pd.DataFrame(benh_list)
            df_b.columns = ["Mã Bệnh", "Tên Bệnh"]
            st.dataframe(df_b, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Thêm loại bệnh")
        with st.form("form_add_benh", clear_on_submit=True):
            new_ten_benh = st.text_input("Tên bệnh (*):", placeholder="Ví dụ: Viêm xoang, Đau mắt đỏ...").strip()
            btn_add_benh = st.form_submit_button("Lưu bệnh mới", type="primary")

        if btn_add_benh:
            if not new_ten_benh:
                st.error("❌ Tên bệnh không được để trống!")
            else:
                sql_add_b = "INSERT INTO benh (ten_benh) VALUES (%s)"
                ok_b_ins, _, err_msg = db.execute_statement(sql_add_b, (new_ten_benh,))
                if not ok_b_ins:
                    st.error(f"❌ {err_msg}")
                else:
                    st.success(f"✅ Đã thêm bệnh **{new_ten_benh}** vào danh mục thành công!")
                    st.rerun()

# =====================================================================
# MENU 4: BÁO CÁO
# =====================================================================
elif nav == "Báo cáo":
    st.title("Báo cáo")
    st.markdown("<p class='page-desc'>Theo dõi tình hình khám chữa bệnh, lương nhân viên và doanh thu phòng khám.</p>", unsafe_allow_html=True)
    tab_bc1, tab_bc2, tab_bc3 = st.tabs(["Bệnh theo tháng", "Bảng lương", "Doanh thu"])

    # ---- Tab 1: Bệnh theo tháng (old menu 1) ----
    with tab_bc1:
        st.subheader("Bệnh theo tháng")
        st.markdown("<p class='page-desc'>Danh sách các loại bệnh trong tháng, sắp xếp theo số lượng bệnh nhân mắc giảm dần.</p>", unsafe_allow_html=True)
        st.markdown("Một bệnh nhân khám nhiều lần liên tiếp cho cùng một bệnh chỉ tính là một lần mắc.")
        ok_latest, latest_rows, _ = db.execute_query("SELECT MAX(ngay_bat_dau) AS latest FROM dot_benh")
        latest = latest_rows[0].get("latest") if ok_latest and latest_rows else None
        latest_date = datetime.date.fromisoformat(str(latest)[:10]) if latest else datetime.date.today()

        col1, col2 = st.columns(2)
        with col1:
            thang = st.selectbox("Chọn tháng", options=list(range(1, 13)), index=latest_date.month - 1)
        with col2:
            nam = st.number_input("Chọn năm", min_value=2000, max_value=2100, value=latest_date.year)

        success, results, err = db.call_procedure("sp_benh_theo_thang", (thang, nam))

        if not success:
            st.error(f"❌ Không thể lấy dữ liệu: {err}")
        else:
            rows = results[0] if results else []
            if not rows:
                st.info(f"Chưa ghi nhận đợt bệnh nào bắt đầu trong tháng {thang}/{nam}. Hãy chọn tháng khác để xem.")
            else:
                df = pd.DataFrame(rows)
                df.columns = ["Mã Bệnh", "Tên Bệnh", "Số Bệnh Nhân Mắc (Đợt)"]

                m1, m2 = st.columns(2)
                with m1:
                    st.metric("Tổng số loại bệnh ghi nhận trong tháng", f"{len(df)} bệnh")
                with m2:
                    top_benh = df.iloc[0]["Tên Bệnh"]
                    top_so = df.iloc[0]["Số Bệnh Nhân Mắc (Đợt)"]
                    st.metric("Bệnh có nhiều bệnh nhân nhất", f"{top_benh} ({top_so} BN)")

                c_table, c_chart = st.columns([1, 1])
                with c_table:
                    st.subheader("Bảng dữ liệu chi tiết")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                with c_chart:
                    st.subheader("Biểu đồ phân bố bệnh nhân")
                    chart_data = df.set_index("Tên Bệnh")["Số Bệnh Nhân Mắc (Đợt)"]
                    st.bar_chart(chart_data, color="#087C76", alt="Số đợt bệnh theo từng loại bệnh trong tháng")

    # ---- Tab 2: Bảng lương (old menu 2) ----
    with tab_bc2:
        st.subheader("Lương bác sĩ và y tá")
        st.markdown("<p class='page-desc'>Bảng tính chi tiết tiền lương hàng tháng của Bác sỹ và Y tá dựa trên kết quả hoạt động.</p>", unsafe_allow_html=True)
        st.markdown("""
        **Cách tính lương:**
        * **Bác sỹ:** Lương cơ bản **7.000.000 đ** + **1.000.000 đ** cho mỗi đợt bệnh nhân được chữa khỏi trong tháng.
        * **Y tá:** Lương cơ bản **5.000.000 đ** + **200.000 đ** cho mỗi lần khám bệnh mà y tá tham gia hỗ trợ trong tháng.
        """)

        col_opt, col_m, col_y = st.columns([2, 1, 1])
        with col_opt:
            is_current_month = st.checkbox("Lấy tháng hiện tại (mặc định)", value=True)
        with col_m:
            thang_input = st.selectbox("Tháng", options=list(range(1, 13)), index=datetime.date.today().month - 1, disabled=is_current_month)
        with col_y:
            nam_input = st.number_input("Năm", min_value=2000, max_value=2100, value=datetime.date.today().year, disabled=is_current_month)

        p_thang = None if is_current_month else thang_input
        p_nam = None if is_current_month else nam_input

        success, results, err = db.call_procedure("sp_tinh_luong", (p_thang, p_nam))

        if not success:
            st.error(f"❌ Lỗi khi tính lương: {err}")
        else:
            rows = results[0] if results else []
            if not rows:
                st.info("Chưa có dữ liệu nhân viên để tính lương.")
            else:
                df = pd.DataFrame(rows)
                total_payroll = df["tong_luong"].sum()
                total_bonus = df["thuong"].sum()
                num_staff = len(df)

                kpi1, kpi2, kpi3 = st.columns(3)
                with kpi1:
                    st.metric("Tổng chi trả lương tháng", fmt_vnd(total_payroll))
                with kpi2:
                    st.metric("Tổng tiền thưởng", fmt_vnd(total_bonus))
                with kpi3:
                    st.metric("Tổng số nhân sự", f"{num_staff} người")

                df_bs = df[df["chuc_vu"] == "Bác sỹ"].copy()
                df_yt = df[df["chuc_vu"] == "Y tá"].copy()

                for d in [df_bs, df_yt]:
                    d["luong_co_ban_fmt"] = d["luong_co_ban"].apply(fmt_vnd)
                    d["thuong_fmt"] = d["thuong"].apply(fmt_vnd)
                    d["tong_luong_fmt"] = d["tong_luong"].apply(fmt_vnd)

                tab_bs_l, tab_yt_l, tab_all = st.tabs(["Bác sĩ", "Y tá", "Toàn bộ nhân viên"])

                with tab_bs_l:
                    st.write("Bác sỹ được cộng thêm 1.000.000 đ cho mỗi đợt bệnh nhân được chữa khỏi trong tháng.")
                    disp_bs = df_bs[["ma_so", "ho_ten", "luong_co_ban_fmt", "so_luot_tinh_thuong", "thuong_fmt", "tong_luong_fmt"]]
                    disp_bs.columns = ["Mã BS", "Họ Tên", "Lương Cơ Bản", "Số Đợt Chữa Khỏi", "Tiền Thưởng", "Tổng Lương"]
                    st.dataframe(disp_bs, use_container_width=True, hide_index=True)

                with tab_yt_l:
                    st.write("Y tá được cộng thêm 200.000 đ cho mỗi lần khám bệnh tham gia hỗ trợ trong tháng.")
                    disp_yt = df_yt[["ma_so", "ho_ten", "luong_co_ban_fmt", "so_luot_tinh_thuong", "thuong_fmt", "tong_luong_fmt"]]
                    disp_yt.columns = ["Mã YT", "Họ Tên", "Lương Cơ Bản", "Số Lần Khám Hỗ Trợ", "Tiền Thưởng", "Tổng Lương"]
                    st.dataframe(disp_yt, use_container_width=True, hide_index=True)

                with tab_all:
                    disp_all = df.copy()
                    disp_all["luong_co_ban"] = disp_all["luong_co_ban"].apply(fmt_vnd)
                    disp_all["thuong"] = disp_all["thuong"].apply(fmt_vnd)
                    disp_all["tong_luong"] = disp_all["tong_luong"].apply(fmt_vnd)
                    disp_all.columns = ["Mã Số", "Họ Tên", "Chức Vụ", "Lương Cơ Bản", "Số Lượt Thưởng", "Tiền Thưởng", "Tổng Lương"]
                    st.dataframe(disp_all, use_container_width=True, hide_index=True)

    # ---- Tab 3: Doanh thu (old menu 4) ----
    with tab_bc3:
        st.subheader("Doanh thu phòng khám")
        st.markdown("<p class='page-desc'>Doanh thu phòng khám bao gồm tiền khám chữa bệnh và tiền bán thuốc trên các đơn thuốc.</p>", unsafe_allow_html=True)

        tab_range, tab_monthly = st.tabs(["Theo khoảng ngày", "Theo từng tháng"])

        with tab_range:
            st.subheader("Doanh thu trong khoảng thời gian")
            today = datetime.date.today()
            first_day_of_month = today.replace(day=1)
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                d_from = st.date_input("Từ ngày", value=first_day_of_month)
            with col_d2:
                d_to = st.date_input("Đến ngày", value=today)

            if d_from > d_to:
                st.error("Ngày bắt đầu không được lớn hơn ngày kết thúc!")
            else:
                success, results, err = db.call_procedure("sp_doanh_thu", (str(d_from), str(d_to)))
                if not success:
                    st.error(f"❌ Lỗi: {err}")
                elif results and results[0]:
                    data = results[0][0]
                    luot_kham = data.get("so_luot_kham", 0)
                    dt_kham = data.get("doanh_thu_kham", 0)
                    dt_thuoc = data.get("doanh_thu_thuoc", 0)
                    tong_dt = data.get("tong_doanh_thu", 0)

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Tổng lượt khám", f"{luot_kham} lượt")
                    m2.metric("Doanh thu tiền khám", fmt_vnd(dt_kham))
                    m3.metric("Doanh thu tiền thuốc", fmt_vnd(dt_thuoc))
                    m4.metric("Tổng doanh thu", fmt_vnd(tong_dt))

                    if tong_dt > 0:
                        st.write("---")
                        st.write("**Cơ cấu doanh thu:**")
                        df_pie = pd.DataFrame({
                            "Khoản thu": ["Tiền khám chữa", "Tiền thuốc"],
                            "Doanh thu": [float(dt_kham), float(dt_thuoc)]
                        }).set_index("Khoản thu")
                        st.bar_chart(df_pie, color="#087C76", alt="So sánh doanh thu khám và doanh thu thuốc")

        with tab_monthly:
            st.subheader("Doanh thu tổng hợp theo từng tháng")
            ok, rows, err = db.execute_query("SELECT nam, thang, doanh_thu_kham, doanh_thu_thuoc, tong_doanh_thu FROM v_doanh_thu_theo_thang ORDER BY nam DESC, thang DESC")
            if not ok:
                st.error(f"❌ Lỗi đọc doanh thu: {err}")
            elif not rows:
                st.info("Chưa có dữ liệu doanh thu tháng.")
            else:
                df_m = pd.DataFrame(rows)
                df_m["Tháng/Năm"] = df_m.apply(lambda r: f"Tháng {r['thang']:02d}/{r['nam']}", axis=1)

                disp_m = df_m.copy()
                disp_m["doanh_thu_kham"] = disp_m["doanh_thu_kham"].apply(fmt_vnd)
                disp_m["doanh_thu_thuoc"] = disp_m["doanh_thu_thuoc"].apply(fmt_vnd)
                disp_m["tong_doanh_thu"] = disp_m["tong_doanh_thu"].apply(fmt_vnd)
                disp_m = disp_m[["Tháng/Năm", "doanh_thu_kham", "doanh_thu_thuoc", "tong_doanh_thu"]]
                disp_m.columns = ["Tháng/Năm", "Doanh Thu Khám", "Doanh Thu Thuốc", "Tổng Doanh Thu"]

                st.dataframe(disp_m, use_container_width=True, hide_index=True)

                st.write("**Biểu đồ doanh thu các tháng:**")
                chart_df = df_m.set_index("Tháng/Năm")[["doanh_thu_kham", "doanh_thu_thuoc"]]
                chart_df.columns = ["Tiền Khám", "Tiền Thuốc"]
                st.bar_chart(chart_df, color=["#087C76", "#D89A47"], alt="Doanh thu khám và tiền thuốc theo từng tháng")

# =====================================================================
# MENU 5: NHẬP DỮ LIỆU
# =====================================================================
elif nav == "Nhập dữ liệu":
    st.title("Khám chữa bệnh")
    st.markdown("<p class='page-desc'>Thực hiện lần lượt các bước bên dưới để ghi nhận một quá trình điều trị. Bạn có thể quay lại bất kỳ bước nào khi cần.</p>", unsafe_allow_html=True)
    st.markdown('<div class="workflow-note"><strong>Thứ tự thực hiện:</strong> 1. Mở đợt bệnh → 2. Thêm lần khám → 3. Kê thuốc → 4. Phân công y tá → 5. Đóng đợt khi đã khỏi.</div>', unsafe_allow_html=True)
    tab_nd1, tab_nd2, tab_nd3, tab_nd4, tab_nd5 = st.tabs([
        "1. Mở đợt bệnh", "2. Thêm lần khám", "3. Kê thuốc",
        "4. Phân công y tá", "5. Đóng đợt"
    ])

    # ---- Tab 1: Mở đợt bệnh (old menu 6) ----
    with tab_nd1:
        st.subheader("Mở đợt điều trị")
        st.markdown("<p class='page-desc'>Tiếp nhận bệnh nhân đến khám bệnh. Mỗi đợt bệnh được chỉ định một bác sỹ phụ trách.</p>", unsafe_allow_html=True)
        st.caption("Mỗi bệnh nhân chỉ có một đợt đang điều trị cho cùng một bệnh.")

        ok_bn, bn_list, _ = db.execute_query("SELECT ma_bn, ma_so, ho_ten, cmt FROM benh_nhan ORDER BY ma_so")
        ok_b, b_list, _ = db.execute_query("SELECT ma_benh, ten_benh FROM benh ORDER BY ten_benh")
        ok_bs, bs_list, _ = db.execute_query("""
            SELECT bs.ma_nv, nv.ma_so, nv.ho_ten, bs.chuyen_mon, bs.bac_nghe
            FROM bac_sy bs
            JOIN nhan_vien nv ON nv.ma_nv = bs.ma_nv
            ORDER BY nv.ma_so
        """)

        with st.form("form_mo_dot"):
            c1, c2 = st.columns(2)
            with c1:
                dict_bn = {f"{b['ma_so']} - {b['ho_ten']} (CMT: {b['cmt']})": b["ma_bn"] for b in (bn_list or [])}
                sel_bn = st.selectbox("1. Chọn Bệnh nhân (*):", options=list(dict_bn.keys())) if dict_bn else None

                dict_b = {f"{b['ten_benh']}": b["ma_benh"] for b in (b_list or [])}
                sel_b = st.selectbox("2. Chọn Bệnh mắc phải (*):", options=list(dict_b.keys())) if dict_b else None

            with c2:
                dict_bs = {f"{b['ma_so']} - BS. {b['ho_ten']} ({b['chuyen_mon']})": b["ma_nv"] for b in (bs_list or [])}
                sel_bs = st.selectbox("3. Chỉ định Bác sỹ phụ trách (*):", options=list(dict_bs.keys())) if dict_bs else None

                ngay_bd = st.date_input("4. Ngày bắt đầu khám/điều trị (*):", value=datetime.date.today())

            btn_mo_dot = st.form_submit_button("🚀 Mở đợt bệnh mới", type="primary")

        if btn_mo_dot:
            if not sel_bn or not sel_b or not sel_bs:
                st.error("❌ Vui lòng chọn đầy đủ Bệnh nhân, Bệnh và Bác sỹ!")
            else:
                p_ma_bn = dict_bn[sel_bn]
                p_ma_benh = dict_b[sel_b]
                p_ma_bs = dict_bs[sel_bs]

                sql_insert_dot = "INSERT INTO dot_benh (ma_bn, ma_benh, ma_bs, ngay_bat_dau, ngay_ket_thuc) VALUES (%s, %s, %s, %s, NULL)"
                ok, new_id, err_msg = db.execute_insert(sql_insert_dot, (p_ma_bn, p_ma_benh, p_ma_bs, str(ngay_bd)))

                if not ok:
                    st.error(f"❌ {err_msg}")
                else:
                    st.success(f"🎉 Mở đợt bệnh mới thành công! (Mã đợt: `{new_id}`). Hãy tiếp tục thêm lần khám đầu tiên cho bệnh nhân.")
                    st.rerun()

        st.markdown("---")
        st.subheader("Đợt đang điều trị")
        ok_cur, cur_dots, _ = db.execute_query("""
            SELECT d.ma_dot, bn.ma_so AS ma_bn, bn.ho_ten AS ten_bn, b.ten_benh,
                   nv.ho_ten AS ten_bs, d.ngay_bat_dau,
                   (SELECT COUNT(*) FROM lan_kham WHERE ma_dot = d.ma_dot) AS so_lan_da_kham
            FROM dot_benh d
            JOIN benh_nhan bn ON bn.ma_bn = d.ma_bn
            JOIN benh b ON b.ma_benh = d.ma_benh
            JOIN nhan_vien nv ON nv.ma_nv = d.ma_bs
            WHERE d.ngay_ket_thuc IS NULL
            ORDER BY d.ma_dot DESC
        """)
        if ok_cur and cur_dots:
            df_cur = pd.DataFrame(cur_dots)
            df_cur.columns = ["Mã Đợt", "Mã BN", "Tên Bệnh Nhân", "Bệnh Đang Điều Trị", "Bác Sỹ Phụ Trách", "Ngày Bắt Đầu", "Số Lần Đã Khám"]
            st.dataframe(df_cur, use_container_width=True, hide_index=True)
        else:
            st.info("Hiện không có đợt bệnh nào đang điều trị.")

    # ---- Tab 2: Thêm lần khám (old menu 7) ----
    with tab_nd2:
        st.subheader("Ghi nhận lần khám")
        st.markdown("<p class='page-desc'>Ghi nhận một lần đến khám/chữa bệnh của bệnh nhân trong đợt điều trị.</p>", unsafe_allow_html=True)
        st.caption("Ngày vào khám phải nằm trong khoảng thời gian điều trị của đợt bệnh.")

        ok_dot, dot_active, _ = db.execute_query("""
            SELECT d.ma_dot, d.ngay_bat_dau, bn.ma_so, bn.ho_ten AS ten_bn, b.ten_benh, nv.ho_ten AS ten_bs
            FROM dot_benh d
            JOIN benh_nhan bn ON bn.ma_bn = d.ma_bn
            JOIN benh b ON b.ma_benh = d.ma_benh
            JOIN nhan_vien nv ON nv.ma_nv = d.ma_bs
            WHERE d.ngay_ket_thuc IS NULL
            ORDER BY d.ma_dot DESC
        """)

        if not dot_active:
            st.warning("⚠️ Hiện tại không có đợt bệnh nào đang điều trị. Vui lòng mở đợt bệnh mới trước.")
        else:
            dict_dot = {
                f"Đợt {d['ma_dot']}: {d['ten_bn']} ({d['ma_so']}) - Bệnh: {d['ten_benh']} | Bắt đầu: {d['ngay_bat_dau']}": d
                for d in dot_active
            }

            with st.form("form_add_lan_kham"):
                sel_dot_key = st.selectbox("1. Chọn Đợt bệnh đang điều trị (*):", options=list(dict_dot.keys()))
                dot_info = dict_dot[sel_dot_key]

                st.write(f"Đợt bệnh bắt đầu từ ngày **{dot_info['ngay_bat_dau']}**, do BS. **{dot_info['ten_bs']}** phụ trách.")

                c1, c2, c3 = st.columns(3)
                with c1:
                    ngay_vao = st.date_input("2. Ngày vào khám (*):", value=datetime.date.today())
                with c2:
                    co_ngay_ra = st.checkbox("Có ngày ra viện ngay?")
                    ngay_ra = st.date_input("Ngày ra viện:", value=datetime.date.today()) if co_ngay_ra else None
                with c3:
                    phi_kham = st.number_input("3. Phí khám/chữa bệnh (VNĐ) (*):", min_value=0, value=150000, step=10000)

                btn_submit_lk = st.form_submit_button("Thêm lần khám", type="primary")

            if btn_submit_lk:
                p_ma_dot = dot_info["ma_dot"]
                p_ngay_ra = str(ngay_ra) if co_ngay_ra and ngay_ra else None

                sql_lk = "INSERT INTO lan_kham (ma_dot, ngay_vao, ngay_ra, phi_kham) VALUES (%s, %s, %s, %s)"
                ok, new_lk_id, err_msg = db.execute_insert(sql_lk, (p_ma_dot, str(ngay_vao), p_ngay_ra, phi_kham))

                if not ok:
                    st.error(f"❌ {err_msg}")
                else:
                    st.success(f"✅ Thêm lần khám thành công! (Mã lần khám: `{new_lk_id}`). Số lần khám và tổng tiền ban đầu đã được ghi nhận.")
                    st.rerun()

        st.markdown("---")
        st.subheader("Lần khám gần đây")
        ok_lks, lk_list, _ = db.execute_query("""
            SELECT lk.ma_lan_kham, lk.ma_dot, bn.ho_ten AS ten_bn, b.ten_benh,
                   lk.so_lan AS lan_thu, lk.ngay_vao, lk.ngay_ra, lk.phi_kham, lk.tong_tien
            FROM lan_kham lk
            JOIN dot_benh d ON d.ma_dot = lk.ma_dot
            JOIN benh_nhan bn ON bn.ma_bn = d.ma_bn
            JOIN benh b ON b.ma_benh = d.ma_benh
            ORDER BY lk.ma_lan_kham DESC
            LIMIT 10
        """)
        if ok_lks and lk_list:
            df_lks = pd.DataFrame(lk_list)
            df_lks["phi_kham"] = df_lks["phi_kham"].apply(fmt_vnd)
            df_lks["tong_tien"] = df_lks["tong_tien"].apply(fmt_vnd)
            df_lks.columns = ["Mã LK", "Mã Đợt", "Bệnh Nhân", "Bệnh", "Lần Khám Thứ", "Ngày Vào", "Ngày Ra", "Phí Khám", "Tổng Tiền (Kèm thuốc)"]
            st.dataframe(df_lks, use_container_width=True, hide_index=True)

    # ---- Tab 3: Kê đơn thuốc (old menu 8) ----
    with tab_nd3:
        st.subheader("Kê đơn thuốc")
        st.markdown("<p class='page-desc'>Thêm các loại thuốc được kê đơn cho bệnh nhân trong một lần khám.</p>", unsafe_allow_html=True)
        st.caption("Tổng chi phí lần khám gồm phí khám và tiền thuốc đã kê.")

        ok_lks, lk_list, _ = db.execute_query("""
            SELECT lk.ma_lan_kham, lk.ma_dot, lk.so_lan, lk.ngay_vao, lk.phi_kham, lk.tong_tien,
                   bn.ho_ten AS ten_bn, bn.ma_so AS ma_bn, b.ten_benh
            FROM lan_kham lk
            JOIN dot_benh d ON d.ma_dot = lk.ma_dot
            JOIN benh_nhan bn ON bn.ma_bn = d.ma_bn
            JOIN benh b ON b.ma_benh = d.ma_benh
            ORDER BY lk.ma_lan_kham DESC
        """)

        ok_t, thuoc_list, _ = db.execute_query("SELECT ma_thuoc, ten_thuoc, don_vi, don_gia FROM thuoc ORDER BY ten_thuoc")

        if not ok_lks or not lk_list:
            st.warning("Chưa có lần khám nào trong hệ thống. Vui lòng thêm lần khám trước.")
        else:
            dict_lk = {
                f"LK {lk['ma_lan_kham']} (Lần {lk['so_lan']} - {lk['ngay_vao']}): {lk['ten_bn']} ({lk['ten_benh']}) | Tổng tiền: {fmt_vnd(lk['tong_tien'])}": lk
                for lk in lk_list
            }
            sel_lk_key = st.selectbox("1. Chọn Lần khám cần kê đơn:", options=list(dict_lk.keys()))
            selected_lk = dict_lk[sel_lk_key]
            ma_lk = selected_lk["ma_lan_kham"]

            st.markdown("---")
            c_form, c_cur = st.columns([1, 1])

            with c_form:
                st.subheader("Thêm thuốc vào đơn")
                dict_t = {
                    f"{t['ten_thuoc']} ({t['don_vi']}) - Đơn giá: {fmt_vnd(t['don_gia'])}": t
                    for t in (thuoc_list or [])
                }
                with st.form("form_ke_thuoc", clear_on_submit=True):
                    sel_t_key = st.selectbox("Chọn loại thuốc (*):", options=list(dict_t.keys())) if dict_t else None
                    so_luong = st.number_input("Số lượng kê đơn (*):", min_value=1, value=10, step=1)
                    btn_ke = st.form_submit_button("Kê thuốc vào đơn", type="primary")

                if btn_ke and sel_t_key:
                    t_obj = dict_t[sel_t_key]
                    p_ma_thuoc = t_obj["ma_thuoc"]

                    sql_ke = "INSERT INTO ke_don (ma_lan_kham, ma_thuoc, so_luong) VALUES (%s, %s, %s)"
                    ok_ins, _, err_msg = db.execute_statement(sql_ke, (ma_lk, p_ma_thuoc, so_luong))

                    if not ok_ins:
                        st.error(f"❌ {err_msg}")
                    else:
                        st.success(f"✅ Đã kê **{so_luong} {t_obj['don_vi']} {t_obj['ten_thuoc']}**! Tổng tiền lần khám đã được cập nhật.")
                        st.rerun()

            with c_cur:
                st.subheader(f"Thuốc đã kê cho lần khám {ma_lk}")
                ok_kd, don_thuoc, _ = db.execute_query("""
                    SELECT t.ten_thuoc, t.don_vi, kd.don_gia, kd.so_luong, (kd.so_luong * kd.don_gia) AS thanh_tien
                    FROM ke_don kd
                    JOIN thuoc t ON t.ma_thuoc = kd.ma_thuoc
                    WHERE kd.ma_lan_kham = %s
                """, (ma_lk,))

                _, lk_now, _ = db.execute_query("SELECT phi_kham, tong_tien FROM lan_kham WHERE ma_lan_kham = %s", (ma_lk,))
                phi_kham_val = lk_now[0]["phi_kham"] if lk_now else 0
                tong_tien_val = lk_now[0]["tong_tien"] if lk_now else 0

                if not don_thuoc:
                    st.info("Lần khám này chưa được kê loại thuốc nào.")
                else:
                    df_kd = pd.DataFrame(don_thuoc)
                    tong_tien_thuoc = df_kd["thanh_tien"].sum()
                    df_kd["don_gia"] = df_kd["don_gia"].apply(fmt_vnd)
                    df_kd["thanh_tien"] = df_kd["thanh_tien"].apply(fmt_vnd)
                    df_kd.columns = ["Tên Thuốc", "Đơn Vị", "Đơn Giá", "Số Lượng", "Thành Tiền"]
                    st.dataframe(df_kd, use_container_width=True, hide_index=True)

                    st.write(f"🔹 **Phí khám:** `{fmt_vnd(phi_kham_val)}`")
                    st.write(f"🔹 **Tiền thuốc:** `{fmt_vnd(tong_tien_thuoc)}`")
                    st.markdown(f"### 👉 **Tổng Tiền Viện Phí:** `{fmt_vnd(tong_tien_val)}`")

    # ---- Tab 4: Phân công y tá (old menu 9) ----
    with tab_nd4:
        st.subheader("Phân công y tá hỗ trợ")
        st.markdown("<p class='page-desc'>Phân công các y tá hỗ trợ bệnh nhân trong một lần khám (tiếp đón, cấp thuốc, tiêm thuốc, theo dõi).</p>", unsafe_allow_html=True)
        st.caption("Mỗi lần khám có tối đa 3 y tá tham gia hỗ trợ.")

        ok_lks, lk_list, _ = db.execute_query("""
            SELECT lk.ma_lan_kham, lk.ma_dot, lk.so_lan, lk.ngay_vao,
                   bn.ho_ten AS ten_bn, b.ten_benh
            FROM lan_kham lk
            JOIN dot_benh d ON d.ma_dot = lk.ma_dot
            JOIN benh_nhan bn ON bn.ma_bn = d.ma_bn
            JOIN benh b ON b.ma_benh = d.ma_benh
            ORDER BY lk.ma_lan_kham DESC
        """)

        ok_yt, yt_list, _ = db.execute_query("""
            SELECT yt.ma_nv, nv.ma_so, nv.ho_ten, yt.trinh_do
            FROM y_ta yt
            JOIN nhan_vien nv ON nv.ma_nv = yt.ma_nv
            ORDER BY nv.ma_so
        """)

        if not ok_lks or not lk_list:
            st.warning("Chưa có lần khám nào trong hệ thống. Vui lòng thêm lần khám trước.")
        else:
            dict_lk = {
                f"Lần khám #{lk['ma_lan_kham']} (Lần {lk['so_lan']} - {lk['ngay_vao']}): {lk['ten_bn']} ({lk['ten_benh']})": lk
                for lk in lk_list
            }
            sel_lk_key = st.selectbox("1. Chọn Lần khám cần phân công:", options=list(dict_lk.keys()))
            selected_lk = dict_lk[sel_lk_key]
            ma_lk = selected_lk["ma_lan_kham"]

            st.markdown("---")
            col_assign, col_view = st.columns([1, 1])

            with col_assign:
                st.subheader("Thêm y tá hỗ trợ")
                dict_yt = {
                    f"{y['ma_so']} - {y['ho_ten']} ({y['trinh_do']})": y["ma_nv"]
                    for y in (yt_list or [])
                }
                with st.form("form_assign_yt"):
                    sel_yt_key = st.selectbox("Chọn y tá (*):", options=list(dict_yt.keys())) if dict_yt else None
                    vai_tro = st.selectbox(
                        "Chọn vai trò hỗ trợ (*):",
                        options=["Tiếp đón", "Cấp thuốc", "Tiêm thuốc", "Chăm sóc theo dõi"]
                    )
                    btn_assign = st.form_submit_button("Phân công y tá", type="primary")

                if btn_assign and sel_yt_key:
                    p_ma_yta = dict_yt[sel_yt_key]
                    sql_assign = "INSERT INTO y_ta_ho_tro (ma_lan_kham, ma_yta, vai_tro) VALUES (%s, %s, %s)"
                    ok_as, _, err_msg = db.execute_statement(sql_assign, (ma_lk, p_ma_yta, vai_tro))

                    if not ok_as:
                        st.error(f"❌ {err_msg}")
                    else:
                        st.success(f"✅ Phân công y tá thành công với vai trò **{vai_tro}**!")
                        st.rerun()

            with col_view:
                st.subheader(f"Y tá hỗ trợ lần khám {ma_lk}")
                ok_cur_yt, cur_yts, _ = db.execute_query("""
                    SELECT nv.ma_so, nv.ho_ten, yt.trinh_do, h.vai_tro
                    FROM y_ta_ho_tro h
                    JOIN y_ta yt ON yt.ma_nv = h.ma_yta
                    JOIN nhan_vien nv ON nv.ma_nv = yt.ma_nv
                    WHERE h.ma_lan_kham = %s
                """, (ma_lk,))

                if not cur_yts:
                    st.info("Lần khám này chưa có y tá nào được phân công.")
                else:
                    df_cur_yt = pd.DataFrame(cur_yts)
                    df_cur_yt.columns = ["Mã Số", "Họ Tên Y Tá", "Trình Độ", "Vai Trò"]
                    st.dataframe(df_cur_yt, use_container_width=True, hide_index=True)

                    distinct_cnt = len(set(r["ma_so"] for r in cur_yts))
                    st.write(f"Lần khám này hiện có **{distinct_cnt}/3** y tá khác nhau tham gia hỗ trợ.")

    # ---- Tab 5: Ghi nhận chữa khỏi (old menu 10) ----
    with tab_nd5:
        st.subheader("Kết thúc đợt điều trị")
        st.markdown("<p class='page-desc'>Ghi nhận ngày chữa khỏi bệnh và kết thúc đợt điều trị của bệnh nhân.</p>", unsafe_allow_html=True)
        st.caption("Ngày kết thúc đợt bệnh không được sớm hơn ngày vào của lần khám cuối cùng.")

        ok_dot, dot_active, _ = db.execute_query("""
            SELECT d.ma_dot, d.ngay_bat_dau, bn.ma_so, bn.ho_ten AS ten_bn, b.ten_benh, nv.ho_ten AS ten_bs,
                   (SELECT MAX(ngay_vao) FROM lan_kham WHERE ma_dot = d.ma_dot) AS ngay_kham_cuoi,
                   (SELECT COUNT(*) FROM lan_kham WHERE ma_dot = d.ma_dot) AS tong_so_lan_kham
            FROM dot_benh d
            JOIN benh_nhan bn ON bn.ma_bn = d.ma_bn
            JOIN benh b ON b.ma_benh = d.ma_benh
            JOIN nhan_vien nv ON nv.ma_nv = d.ma_bs
            WHERE d.ngay_ket_thuc IS NULL
            ORDER BY d.ma_dot DESC
        """)

        if not dot_active:
            st.success("✅ Tuyệt vời! Hiện tại không còn đợt bệnh nào đang điều trị (tất cả các đợt đều đã chữa khỏi).")
        else:
            dict_dot = {
                f"Đợt #{d['ma_dot']}: {d['ten_bn']} - Bệnh: {d['ten_benh']} | BS: {d['ten_bs']} (Bắt đầu: {d['ngay_bat_dau']})": d
                for d in dot_active
            }
            sel_dot_key = st.selectbox("1. Chọn Đợt bệnh cần ghi nhận chữa khỏi (*):", options=list(dict_dot.keys()))
            selected_dot = dict_dot[sel_dot_key]

            c_info1, c_info2 = st.columns(2)
            with c_info1:
                st.write(f"👤 **Bệnh nhân:** {selected_dot['ten_bn']} ({selected_dot['ma_so']})")
                st.write(f"🩺 **Bệnh:** **{selected_dot['ten_benh']}**")
                st.write(f"👨‍⚕️ **Bác sỹ điều trị:** {selected_dot['ten_bs']}")
            with c_info2:
                st.write(f"📅 **Ngày bắt đầu đợt:** `{selected_dot['ngay_bat_dau']}`")
                st.write(f"🏥 **Lần khám cuối cùng vào ngày:** `{selected_dot['ngay_kham_cuoi'] or 'Chưa có lần khám nào'}`")
                st.write(f"🔢 **Tổng số lần đã khám:** {selected_dot['tong_so_lan_kham']} lần")

            with st.form("form_dong_dot"):
                def_end_date = selected_dot["ngay_kham_cuoi"] if selected_dot["ngay_kham_cuoi"] else datetime.date.today()
                ngay_kt = st.date_input("2. Chọn Ngày kết thúc / Ngày chữa khỏi (*):", value=def_end_date)
                btn_dong = st.form_submit_button("Xác nhận đã chữa khỏi bệnh", type="primary")

            if btn_dong:
                sql_close = "UPDATE dot_benh SET ngay_ket_thuc = %s WHERE ma_dot = %s"
                ok_cl, _, err_msg = db.execute_statement(sql_close, (str(ngay_kt), selected_dot["ma_dot"]))

                if not ok_cl:
                    st.error(f"❌ {err_msg}")
                else:
                    st.success(f"🎉 Chúc mừng! Đã ghi nhận chữa khỏi đợt bệnh #{selected_dot['ma_dot']} thành công vào ngày {ngay_kt}!")
                    st.rerun()

        st.markdown("---")
        st.subheader("Đợt điều trị đã kết thúc")
        ok_done, done_dots, _ = db.execute_query("""
            SELECT d.ma_dot, bn.ho_ten AS ten_bn, b.ten_benh, nv.ho_ten AS ten_bs,
                   d.ngay_bat_dau, d.ngay_ket_thuc,
                   (SELECT COUNT(*) FROM lan_kham WHERE ma_dot = d.ma_dot) AS tong_lan_kham
            FROM dot_benh d
            JOIN benh_nhan bn ON bn.ma_bn = d.ma_bn
            JOIN benh b ON b.ma_benh = d.ma_benh
            JOIN nhan_vien nv ON nv.ma_nv = d.ma_bs
            WHERE d.ngay_ket_thuc IS NOT NULL
            ORDER BY d.ngay_ket_thuc DESC
            LIMIT 10
        """)
        if ok_done and done_dots:
            df_done = pd.DataFrame(done_dots)
            df_done.columns = ["Mã Đợt", "Bệnh Nhân", "Tên Bệnh", "Bác Sỹ Phụ Trách", "Ngày Bắt Đầu", "Ngày Khỏi Bệnh", "Tổng Số Lần Khám"]
            st.dataframe(df_done, use_container_width=True, hide_index=True)
