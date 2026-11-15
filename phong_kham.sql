-- =====================================================================
-- BTL CSDL - PROJECT 1: HỆ THỐNG QUẢN LÝ PHÒNG KHÁM BỆNH TƯ NHÂN
-- Hệ quản trị: MySQL 8.0.16+ (cần CHECK và window function)
-- Chỉ chạy lần đầu khi database phong_kham chưa có bảng.
-- Chạy bằng MySQL Workbench hoặc: mysql -u root -p < phong_kham.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS phong_kham CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE phong_kham;

-- =====================================================================
-- PHẦN 1: TẠO BẢNG
-- =====================================================================

-- Siêu lớp NHAN_VIEN (chứa thuộc tính chung của bác sỹ và y tá)
CREATE TABLE nhan_vien (
    ma_nv      INT AUTO_INCREMENT PRIMARY KEY,
    ma_so      VARCHAR(10)  NOT NULL UNIQUE,          -- mã số BS / mã số NV
    cmt        VARCHAR(12)  NOT NULL UNIQUE,
    ho_ten     VARCHAR(100) NOT NULL,
    ngay_sinh  DATE         NOT NULL,
    dia_chi    VARCHAR(255),
    sdt        VARCHAR(15),
    tham_nien  TINYINT UNSIGNED NOT NULL DEFAULT 0,   -- số năm
    loai       CHAR(2)      NOT NULL CHECK (loai IN ('BS','YT')),
    UNIQUE KEY uq_nv_loai (ma_nv, loai)
) ENGINE=InnoDB;

-- Lớp con BAC_SY (chuyên biệt hoá rời nhau, toàn phần)
CREATE TABLE bac_sy (
    ma_nv            INT PRIMARY KEY,
    loai             CHAR(2) NOT NULL DEFAULT 'BS',
    bac_nghe         VARCHAR(50)  NOT NULL,
    trinh_do_dao_tao VARCHAR(100) NOT NULL,
    chuyen_mon       VARCHAR(100) NOT NULL,
    CHECK (loai = 'BS'),
    FOREIGN KEY (ma_nv, loai) REFERENCES nhan_vien (ma_nv, loai)
) ENGINE=InnoDB;

-- Lớp con Y_TA
CREATE TABLE y_ta (
    ma_nv    INT PRIMARY KEY,
    loai     CHAR(2) NOT NULL DEFAULT 'YT',
    trinh_do VARCHAR(100) NOT NULL,
    CHECK (loai = 'YT'),
    FOREIGN KEY (ma_nv, loai) REFERENCES nhan_vien (ma_nv, loai)
) ENGINE=InnoDB;

CREATE TABLE benh_nhan (
    ma_bn     INT AUTO_INCREMENT PRIMARY KEY,
    ma_so     VARCHAR(10)  NOT NULL UNIQUE,
    cmt       VARCHAR(12)  NOT NULL UNIQUE,
    ho_ten    VARCHAR(100) NOT NULL,
    ngay_sinh DATE         NOT NULL,
    dia_chi   VARCHAR(255),
    sdt       VARCHAR(15)
) ENGINE=InnoDB;

CREATE TABLE benh (
    ma_benh  INT AUTO_INCREMENT PRIMARY KEY,
    ten_benh VARCHAR(150) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE thuoc (
    ma_thuoc  INT AUTO_INCREMENT PRIMARY KEY,
    ten_thuoc VARCHAR(150) NOT NULL UNIQUE,
    don_vi    VARCHAR(20)  NOT NULL,
    don_gia   DECIMAL(12,0) NOT NULL CHECK (don_gia >= 0)
) ENGINE=InnoDB;

-- ĐỢT BỆNH: một lần mắc bệnh của bệnh nhân (chuỗi các lần khám liên tiếp cho
-- cùng một bệnh). Bệnh nhân khỏi rồi mắc lại => đợt mới.
-- ngay_ket_thuc IS NULL  <=> đang điều trị;  NOT NULL <=> đã chữa khỏi.
-- ma_bs NOT NULL => mỗi đợt bệnh được khám bởi duy nhất một bác sỹ.
CREATE TABLE dot_benh (
    ma_dot        INT AUTO_INCREMENT PRIMARY KEY,
    ma_bn         INT  NOT NULL,
    ma_benh       INT  NOT NULL,
    ma_bs         INT  NOT NULL,
    ngay_bat_dau  DATE NOT NULL,
    ngay_ket_thuc DATE NULL,
    CHECK (ngay_ket_thuc IS NULL OR ngay_ket_thuc >= ngay_bat_dau),
    FOREIGN KEY (ma_bn)   REFERENCES benh_nhan (ma_bn),
    FOREIGN KEY (ma_benh) REFERENCES benh (ma_benh),
    FOREIGN KEY (ma_bs)   REFERENCES bac_sy (ma_nv)
) ENGINE=InnoDB;

-- LẦN KHÁM: so_lan = lần khám thứ mấy trong đợt bệnh (tự động đánh số)
CREATE TABLE lan_kham (
    ma_lan_kham INT AUTO_INCREMENT PRIMARY KEY,
    ma_dot      INT  NOT NULL,
    so_lan      INT  NOT NULL DEFAULT 0,
    ngay_vao    DATE NOT NULL,
    ngay_ra     DATE NULL,
    phi_kham    DECIMAL(12,0) NOT NULL DEFAULT 0 CHECK (phi_kham >= 0),
    tong_tien   DECIMAL(12,0) NOT NULL DEFAULT 0,   -- = phi_kham + tiền thuốc (tự cập nhật)
    UNIQUE KEY uq_dot_solan (ma_dot, so_lan),
    CHECK (ngay_ra IS NULL OR ngay_ra >= ngay_vao),
    FOREIGN KEY (ma_dot) REFERENCES dot_benh (ma_dot) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ĐƠN THUỐC: thuốc kê trong mỗi lần khám (lưu giá tại thời điểm kê)
CREATE TABLE ke_don (
    ma_lan_kham INT NOT NULL,
    ma_thuoc    INT NOT NULL,
    so_luong    INT NOT NULL CHECK (so_luong > 0),
    don_gia     DECIMAL(12,0) NOT NULL DEFAULT 0,
    PRIMARY KEY (ma_lan_kham, ma_thuoc),
    FOREIGN KEY (ma_lan_kham) REFERENCES lan_kham (ma_lan_kham) ON DELETE CASCADE,
    FOREIGN KEY (ma_thuoc)    REFERENCES thuoc (ma_thuoc)
) ENGINE=InnoDB;

-- Y TÁ HỖ TRỢ: y tá làm việc gì trong mỗi lần khám
CREATE TABLE y_ta_ho_tro (
    ma_lan_kham INT NOT NULL,
    ma_yta      INT NOT NULL,
    vai_tro     ENUM('Tiếp đón','Cấp thuốc','Tiêm thuốc','Chăm sóc theo dõi') NOT NULL,
    PRIMARY KEY (ma_lan_kham, ma_yta, vai_tro),
    FOREIGN KEY (ma_lan_kham) REFERENCES lan_kham (ma_lan_kham) ON DELETE CASCADE,
    FOREIGN KEY (ma_yta)      REFERENCES y_ta (ma_nv)
) ENGINE=InnoDB;

-- =====================================================================
-- PHẦN 2: TRIGGER / PROCEDURE - RÀNG BUỘC VÀ TỰ ĐỘNG CẬP NHẬT
-- =====================================================================
--   RB1: Mỗi đợt bệnh có đúng 1 bác sỹ (NOT NULL + FK)
--   RB2: Một bệnh nhân chỉ có tối đa 1 đợt đang điều trị cho cùng 1 bệnh (trg_dot_bi, trg_dot_bu)
--   RB3: Một bác sỹ có tối đa 30 đợt bệnh đang điều trị cùng lúc (trg_dot_bi, trg_dot_bu)
--   RB4: Mỗi lần khám có tối đa 3 y tá hỗ trợ (trg_yta_ho_tro_bi, trg_yta_ho_tro_bu)
--   RB5: Ngày vào của lần khám phải nằm trong thời gian của đợt bệnh (trg_lan_kham_bi, trg_lan_kham_bu)
--   RB6: Mỗi lần khám có tối đa 1 dòng cho mỗi loại thuốc (PK ke_don)
--   Tự động cập nhật tổng tiền khi đổi phí khám hoặc thêm/sửa/xóa thuốc

DELIMITER $$

-- Thủ tục cập nhật tong_tien của lan_kham từ ke_don và phi_kham
CREATE PROCEDURE sp_cap_nhat_tong_tien (IN p_lan_kham INT)
BEGIN
    UPDATE lan_kham lk
    SET lk.tong_tien = lk.phi_kham + COALESCE(
        (SELECT SUM(k.so_luong * k.don_gia) FROM ke_don k WHERE k.ma_lan_kham = p_lan_kham), 0)
    WHERE lk.ma_lan_kham = p_lan_kham;
END$$

-- Trigger kiểm tra khi THÊM đợt bệnh mới (RB2, RB3)
CREATE TRIGGER trg_dot_bi BEFORE INSERT ON dot_benh
FOR EACH ROW
BEGIN
    IF NEW.ngay_ket_thuc IS NULL THEN
        -- RB2: Bệnh nhân không được có 2 đợt cùng bệnh đang điều trị song song
        IF EXISTS (SELECT 1 FROM dot_benh
                   WHERE ma_bn = NEW.ma_bn AND ma_benh = NEW.ma_benh AND ngay_ket_thuc IS NULL) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Bệnh nhân đang điều trị bệnh này, chưa thể mở đợt mới';
        END IF;

        -- RB3: Bác sỹ tối đa 30 đợt đang điều trị
        IF (SELECT COUNT(*) FROM dot_benh
            WHERE ma_bs = NEW.ma_bs AND ngay_ket_thuc IS NULL) >= 30 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Bác sỹ đã đủ 30 đợt bệnh đang điều trị';
        END IF;
    END IF;
END$$

-- Trigger kiểm tra khi CẬP NHẬT đợt bệnh (Đóng đợt, mở lại đợt, đổi bác sĩ)
CREATE TRIGGER trg_dot_bu BEFORE UPDATE ON dot_benh
FOR EACH ROW
BEGIN
    -- 1. Khi đóng đợt hoặc chỉnh sửa ngày kết thúc:
    -- Ngày kết thúc không được sớm hơn ngày vào của các lần khám đã có trong đợt
    IF NEW.ngay_ket_thuc IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM lan_kham
                   WHERE ma_dot = OLD.ma_dot AND ngay_vao > NEW.ngay_ket_thuc) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Ngày kết thúc sớm hơn ngày vào của lần khám trong đợt';
        END IF;
    END IF;

    -- 2. Khi sửa ngày bắt đầu đợt: không được muộn hơn ngày vào của lần khám đã có
    IF EXISTS (SELECT 1 FROM lan_kham
               WHERE ma_dot = OLD.ma_dot AND ngay_vao < NEW.ngay_bat_dau) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Ngày bắt đầu muộn hơn ngày vào của lần khám trong đợt';
    END IF;

    -- 3. Khi đợt đang mở (NEW.ngay_ket_thuc IS NULL), bao gồm:
    --    - Mở lại đợt đã đóng (OLD.ngay_ket_thuc IS NOT NULL -> NEW.ngay_ket_thuc IS NULL)
    --    - Đổi bác sĩ / bệnh nhân / bệnh khi đợt đang mở
    IF NEW.ngay_ket_thuc IS NULL THEN
        -- RB2: Bệnh nhân chỉ có tối đa 1 đợt đang điều trị cho cùng 1 bệnh
        IF EXISTS (SELECT 1 FROM dot_benh
                   WHERE ma_bn = NEW.ma_bn
                     AND ma_benh = NEW.ma_benh
                     AND ngay_ket_thuc IS NULL
                     AND ma_dot <> OLD.ma_dot) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Bệnh nhân đang điều trị bệnh này, chưa thể mở đợt mới';
        END IF;

        -- RB3: Bác sỹ có tối đa 30 đợt bệnh đang điều trị
        IF (SELECT COUNT(*) FROM dot_benh
            WHERE ma_bs = NEW.ma_bs
              AND ngay_ket_thuc IS NULL
              AND ma_dot <> OLD.ma_dot) >= 30 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Bác sỹ đã đủ 30 đợt bệnh đang điều trị';
        END IF;
    END IF;
END$$

-- Trigger kiểm tra khi THÊM lần khám mới (RB5, tự động tính số lần khám và tổng tiền)
CREATE TRIGGER trg_lan_kham_bi BEFORE INSERT ON lan_kham
FOR EACH ROW
BEGIN
    DECLARE v_bd DATE;
    DECLARE v_kt DATE;
    SELECT ngay_bat_dau, ngay_ket_thuc INTO v_bd, v_kt
    FROM dot_benh WHERE ma_dot = NEW.ma_dot;

    IF NEW.ngay_vao < v_bd OR (v_kt IS NOT NULL AND NEW.ngay_vao > v_kt) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Ngày vào nằm ngoài thời gian của đợt bệnh';
    END IF;
    SET NEW.so_lan    = (SELECT COUNT(*) FROM lan_kham WHERE ma_dot = NEW.ma_dot) + 1;
    SET NEW.tong_tien = NEW.phi_kham;
END$$

-- Trigger kiểm tra khi CẬP NHẬT lần khám (RB5, tự động cập nhật lại tổng tiền khi sửa phi_kham)
CREATE TRIGGER trg_lan_kham_bu BEFORE UPDATE ON lan_kham
FOR EACH ROW
BEGIN
    DECLARE v_bd DATE;
    DECLARE v_kt DATE;
    SELECT ngay_bat_dau, ngay_ket_thuc INTO v_bd, v_kt
    FROM dot_benh WHERE ma_dot = NEW.ma_dot;

    IF NEW.ngay_vao < v_bd OR (v_kt IS NOT NULL AND NEW.ngay_vao > v_kt) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Ngày vào nằm ngoài thời gian của đợt bệnh';
    END IF;

    -- Tự động tính lại tổng tiền = phi_kham + tổng tiền thuốc đã kê
    SET NEW.tong_tien = NEW.phi_kham + COALESCE(
        (SELECT SUM(so_luong * don_gia) FROM ke_don WHERE ma_lan_kham = NEW.ma_lan_kham), 0);
END$$

-- Trigger tự động điền đơn giá thuốc từ bảng thuoc nếu chưa nhập
CREATE TRIGGER trg_ke_don_bi BEFORE INSERT ON ke_don
FOR EACH ROW
BEGIN
    IF NEW.don_gia IS NULL OR NEW.don_gia = 0 THEN
        SET NEW.don_gia = (SELECT don_gia FROM thuoc WHERE ma_thuoc = NEW.ma_thuoc);
    END IF;
END$$

-- Triggers tự cập nhật tổng tiền lần khám khi kê đơn thay đổi
CREATE TRIGGER trg_ke_don_ai AFTER INSERT ON ke_don
FOR EACH ROW CALL sp_cap_nhat_tong_tien(NEW.ma_lan_kham)$$

CREATE TRIGGER trg_ke_don_au AFTER UPDATE ON ke_don
FOR EACH ROW CALL sp_cap_nhat_tong_tien(NEW.ma_lan_kham)$$

CREATE TRIGGER trg_ke_don_ad AFTER DELETE ON ke_don
FOR EACH ROW CALL sp_cap_nhat_tong_tien(OLD.ma_lan_kham)$$

-- Trigger kiểm tra khi THÊM y tá hỗ trợ (RB4: tối đa 3 y tá riêng biệt cho 1 lần khám)
CREATE TRIGGER trg_yta_ho_tro_bi BEFORE INSERT ON y_ta_ho_tro
FOR EACH ROW
BEGIN
    IF NOT EXISTS (SELECT 1 FROM y_ta_ho_tro
                   WHERE ma_lan_kham = NEW.ma_lan_kham AND ma_yta = NEW.ma_yta)
       AND (SELECT COUNT(DISTINCT ma_yta) FROM y_ta_ho_tro
            WHERE ma_lan_kham = NEW.ma_lan_kham) >= 3 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Mỗi lần khám chỉ có tối đa 3 y tá hỗ trợ';
    END IF;
END$$

-- Trigger kiểm tra khi CẬP NHẬT y tá hỗ trợ (RB4)
CREATE TRIGGER trg_yta_ho_tro_bu BEFORE UPDATE ON y_ta_ho_tro
FOR EACH ROW
BEGIN
    IF NEW.ma_yta <> OLD.ma_yta THEN
        IF NOT EXISTS (SELECT 1 FROM y_ta_ho_tro
                       WHERE ma_lan_kham = NEW.ma_lan_kham AND ma_yta = NEW.ma_yta)
           AND (SELECT COUNT(DISTINCT ma_yta) FROM y_ta_ho_tro
                WHERE ma_lan_kham = NEW.ma_lan_kham AND ma_yta <> OLD.ma_yta) >= 3 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Mỗi lần khám chỉ có tối đa 3 y tá hỗ trợ';
        END IF;
    END IF;
END$$

DELIMITER ;

-- =====================================================================
-- PHẦN 3: DỮ LIỆU MẪU
-- =====================================================================

-- Nhân viên phòng khám: 3 Bác sỹ (ma_nv 1, 2, 3) và 4 Y tá (ma_nv 4, 5, 6, 7)
INSERT INTO nhan_vien (ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt, tham_nien, loai) VALUES
('BS001','001080012345','Nguyễn Văn An', '1980-03-15','12 Bạch Mai, Hai Bà Trưng, Hà Nội','0901000001',15,'BS'),
('BS002','001085023456','Trần Thị Bình', '1985-07-22','45 Giải Phóng, Hoàng Mai, Hà Nội','0901000002',10,'BS'),
('BS003','001078034567','Lê Quốc Cường', '1978-11-05','8 Láng Hạ, Đống Đa, Hà Nội','0901000003',18,'BS'),
('YT001','001092045678','Phạm Thu Hà',   '1992-01-30','21 Kim Mã, Ba Đình, Hà Nội','0912000001',6,'YT'),
('YT002','001095056789','Hoàng Minh Tuấn','1995-09-12','5 Xã Đàn, Đống Đa, Hà Nội','0912000002',3,'YT'),
('YT003','001097067890','Vũ Lan Anh',    '1997-05-18','77 Nguyễn Trãi, Thanh Xuân, Hà Nội','0912000003',2,'YT'),
('YT004','001099078901','Đỗ Mỹ Linh',    '1999-08-20','18 Tam Trinh, Hoàng Mai, Hà Nội','0912000004',1,'YT');

INSERT INTO bac_sy (ma_nv, bac_nghe, trinh_do_dao_tao, chuyen_mon) VALUES
(1,'Bác sỹ chuyên khoa II','Tiến sỹ','Tim mạch'),
(2,'Bác sỹ chuyên khoa I','Thạc sỹ','Hô hấp'),
(3,'Bác sỹ chuyên khoa II','Thạc sỹ','Tiêu hoá');

INSERT INTO y_ta (ma_nv, trinh_do) VALUES
(4,'Đại học Điều dưỡng'),
(5,'Cao đẳng Điều dưỡng'),
(6,'Cao đẳng Điều dưỡng'),
(7,'Cao đẳng Điều dưỡng');

INSERT INTO benh_nhan (ma_so, cmt, ho_ten, ngay_sinh, dia_chi, sdt) VALUES
('BN001','001200111111','Đỗ Thị Mai',   '2000-04-10','3 Trương Định, Hai Bà Trưng, Hà Nội','0987000001'),
('BN002','001195222222','Bùi Văn Hùng', '1995-08-25','90 Minh Khai, Hai Bà Trưng, Hà Nội','0987000002'),
('BN003','001188333333','Ngô Thị Lan',  '1988-12-02','15 Đại Cồ Việt, Hai Bà Trưng, Hà Nội','0987000003'),
('BN004','001965444444','Phan Văn Thắng','1965-06-30','60 Lê Thanh Nghị, Hai Bà Trưng, Hà Nội','0987000004');

INSERT INTO benh (ten_benh) VALUES
('Viêm phổi'),        -- 1
('Tăng huyết áp'),    -- 2
('Viêm dạ dày'),      -- 3
('Cảm cúm');          -- 4

INSERT INTO thuoc (ten_thuoc, don_vi, don_gia) VALUES
('Paracetamol 500mg','viên',2000),   -- 1
('Amoxicillin 500mg','viên',5000),   -- 2
('Amlodipin 5mg','viên',3000),       -- 3
('Omeprazol 20mg','viên',4000),      -- 4
('Vitamin C 500mg','viên',1000);     -- 5

-- Đợt bệnh (ma_dot tự tăng từ 1). NULL ở ngày kết thúc = đang điều trị.
INSERT INTO dot_benh (ma_bn, ma_benh, ma_bs, ngay_bat_dau, ngay_ket_thuc) VALUES
(1,4,2,'2026-08-10','2026-08-14'),  -- 1: BN1 cảm cúm lần 1 (khỏi)
(1,4,2,'2026-09-20','2026-09-24'),  -- 2: BN1 MẮC LẠI cảm cúm (khỏi)
(1,2,1,'2026-09-25',NULL),          -- 3: BN1 tăng huyết áp (đang điều trị, có tái khám tháng 11)
(2,1,2,'2026-09-28','2026-10-05'),  -- 4: BN2 viêm phổi (khỏi)
(3,3,3,'2026-10-01','2026-10-03'),  -- 5: BN3 viêm dạ dày (khỏi)
(3,4,2,'2026-10-12','2026-11-02'),  -- 6: BN3 cảm cúm (chữa khỏi ngày 02/11/2026 -> BS2 được thưởng tháng 11)
(4,2,1,'2026-10-02',NULL),          -- 7: BN4 tăng huyết áp (đang điều trị)
(2,4,2,'2026-10-06','2026-10-08'),  -- 8: BN2 cảm cúm (khỏi)
(2,3,3,'2026-11-01','2026-11-05'),  -- 9: BN2 viêm dạ dày (chữa khỏi ngày 05/11/2026 -> BS3 được thưởng tháng 11)
(4,1,2,'2026-11-04',NULL);          -- 10: BN4 viêm phổi đợt mới tháng 11 (đang điều trị)

-- Lần khám (so_lan và tong_tien do trigger tự tính)
INSERT INTO lan_kham (ma_dot, ngay_vao, ngay_ra, phi_kham) VALUES
-- Dữ liệu tháng 8, 9, 10/2026
(1,'2026-08-10','2026-08-10',150000),  -- 1
(1,'2026-08-14','2026-08-14',100000),  -- 2
(2,'2026-09-20','2026-09-20',150000),  -- 3
(2,'2026-09-22','2026-09-22',100000),  -- 4
(2,'2026-09-24','2026-09-24',100000),  -- 5
(3,'2026-09-25','2026-09-25',200000),  -- 6
(3,'2026-10-09','2026-10-09',150000),  -- 7
(4,'2026-09-28','2026-09-30',400000),  -- 8
(4,'2026-10-02','2026-10-05',300000),  -- 9
(5,'2026-10-01','2026-10-01',200000),  -- 10
(5,'2026-10-03','2026-10-03',150000),  -- 11
(6,'2026-10-12','2026-10-12',150000),  -- 12
(7,'2026-10-02','2026-10-02',200000),  -- 13
(8,'2026-10-06','2026-10-06',150000),  -- 14
(8,'2026-10-08','2026-10-08',100000),  -- 15
-- Dữ liệu mẫu tháng 11/2026 (từ 01/11/2026 đến 05/11/2026)
(6,'2026-11-02','2026-11-02',100000),  -- 16: BN3 tái khám cảm cúm (khỏi bệnh, đợt 6)
(3,'2026-11-03','2026-11-03',150000),  -- 17: BN1 tái khám định kỳ tăng huyết áp (đợt 3)
(9,'2026-11-01','2026-11-01',200000),  -- 18: BN2 khám viêm dạ dày lần 1 (đợt 9)
(9,'2026-11-05','2026-11-05',150000),  -- 19: BN2 khám viêm dạ dày lần 2 (khỏi bệnh, đợt 9)
(10,'2026-11-04','2026-11-04',250000); -- 20: BN4 khám viêm phổi đợt mới (đợt 10)

-- Đơn thuốc (don_gia tự lấy từ bảng thuoc)
INSERT INTO ke_don (ma_lan_kham, ma_thuoc, so_luong) VALUES
(1,1,10),(1,5,5),(2,1,6),
(3,1,10),(3,5,5),(4,1,6),(5,1,6),
(6,3,30),(7,3,30),
(8,2,21),(8,1,10),(9,2,14),
(10,4,14),(11,4,14),
(12,1,10),
(13,3,30),
(14,1,10),(15,1,6),
-- Đơn thuốc cho các lần khám tháng 11/2026
(16,1,6),(16,5,5),
(17,3,30),
(18,4,14),
(19,4,14),
(20,1,10),(20,2,21);

-- Y tá hỗ trợ
INSERT INTO y_ta_ho_tro (ma_lan_kham, ma_yta, vai_tro) VALUES
(1,4,'Tiếp đón'),(1,4,'Cấp thuốc'),
(2,5,'Tiếp đón'),
(3,4,'Tiếp đón'),
(4,5,'Tiếp đón'),
(5,6,'Tiếp đón'),(5,6,'Cấp thuốc'),
(6,4,'Tiếp đón'),
(7,5,'Cấp thuốc'),
-- Lần khám 8 chuẩn bị sẵn 3 y tá khác nhau: YT001 (4), YT002 (5), YT003 (6) để sẵn sàng test RB4
(8,6,'Tiếp đón'),(8,6,'Tiêm thuốc'),(8,4,'Chăm sóc theo dõi'),(8,5,'Tiếp đón'),
(9,5,'Tiêm thuốc'),
(10,4,'Tiếp đón'),
(11,6,'Cấp thuốc'),
(12,5,'Tiếp đón'),
(13,4,'Tiếp đón'),
(14,6,'Tiếp đón'),
(15,5,'Cấp thuốc'),
-- Phân công y tá cho các lần khám tháng 11/2026 (cả 4 y tá đều có lượt hỗ trợ để demo tính lương)
(16,4,'Tiếp đón'),(16,5,'Cấp thuốc'),
(17,4,'Tiếp đón'),(17,6,'Cấp thuốc'),
(18,5,'Tiếp đón'),(18,7,'Cấp thuốc'),
(19,6,'Tiếp đón'),(19,5,'Cấp thuốc'),
(20,4,'Tiếp đón'),(20,6,'Tiêm thuốc'),(20,7,'Cấp thuốc');

-- =====================================================================
-- PHẦN 4: CÁC TRUY VẤN YÊU CẦU
-- =====================================================================
DELIMITER $$

-- ---------------------------------------------------------------------
-- TRUY VẤN 1: Các đợt bệnh bắt đầu trong tháng, sắp xếp theo số đợt giảm dần.
-- Một đợt tái khám sang tháng khác không bị tính lại; mắc lại sau khi khỏi là đợt mới.
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_benh_theo_thang (IN p_thang INT, IN p_nam INT)
BEGIN
    DECLARE d1 DATE;
    SET d1 = MAKEDATE(p_nam, 1) + INTERVAL (p_thang - 1) MONTH;
    SELECT b.ma_benh, b.ten_benh,
           COUNT(d.ma_dot) AS so_benh_nhan_mac
    FROM dot_benh d
    JOIN benh b     ON b.ma_benh = d.ma_benh
    WHERE d.ngay_bat_dau >= d1 AND d.ngay_bat_dau < d1 + INTERVAL 1 MONTH
    GROUP BY b.ma_benh, b.ten_benh
    ORDER BY so_benh_nhan_mac DESC, b.ten_benh;
END$$

-- ---------------------------------------------------------------------
-- TRUY VẤN 2: Lương bác sỹ và y tá trong 1 tháng (NULL = tháng hiện tại).
-- Chỉ tính các lần chữa khỏi / hỗ trợ đến hết ngày hôm nay.
--   BS : 7.000.000 + 1.000.000 / đợt bệnh được chữa khỏi trong tháng
--   YT : 5.000.000 +   200.000 / lần khám hỗ trợ trong tháng
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_tinh_luong (IN p_thang INT, IN p_nam INT)
BEGIN
    DECLARE d1 DATE;
    DECLARE d2 DATE;
    SET p_thang = IFNULL(p_thang, MONTH(CURDATE()));
    SET p_nam   = IFNULL(p_nam,   YEAR(CURDATE()));
    SET d1 = MAKEDATE(p_nam, 1) + INTERVAL (p_thang - 1) MONTH;
    SET d2 = LEAST(d1 + INTERVAL 1 MONTH, CURDATE() + INTERVAL 1 DAY);

    SELECT nv.ma_so, nv.ho_ten, 'Bác sỹ' AS chuc_vu,
           7000000 AS luong_co_ban,
           COUNT(dd.ma_dot) AS so_luot_tinh_thuong,
           COUNT(dd.ma_dot) * 1000000 AS thuong,
           7000000 + COUNT(dd.ma_dot) * 1000000 AS tong_luong
    FROM bac_sy bs
    JOIN nhan_vien nv ON nv.ma_nv = bs.ma_nv
    LEFT JOIN dot_benh dd ON dd.ma_bs = bs.ma_nv
         AND dd.ngay_ket_thuc >= d1 AND dd.ngay_ket_thuc < d2
    GROUP BY nv.ma_nv, nv.ma_so, nv.ho_ten

    UNION ALL

    SELECT nv.ma_so, nv.ho_ten, 'Y tá',
           5000000,
           COUNT(x.ma_lan_kham),
           COUNT(x.ma_lan_kham) * 200000,
           5000000 + COUNT(x.ma_lan_kham) * 200000
    FROM y_ta yt
    JOIN nhan_vien nv ON nv.ma_nv = yt.ma_nv
    LEFT JOIN (
        SELECT DISTINCT h.ma_yta, h.ma_lan_kham
        FROM y_ta_ho_tro h
        JOIN lan_kham lk ON lk.ma_lan_kham = h.ma_lan_kham
        WHERE lk.ngay_vao >= d1 AND lk.ngay_vao < d2
    ) x ON x.ma_yta = yt.ma_nv
    GROUP BY nv.ma_nv, nv.ma_so, nv.ho_ten;
END$$

-- ---------------------------------------------------------------------
-- TRUY VẤN 3: Thông tin 1 bệnh nhân + toàn bộ lịch sử khám + tình trạng hiện tại
-- Đã sửa: Dùng DENSE_RANK() để đếm lần mắc theo từng đợt bệnh (thay vì ROW_NUMBER() đếm theo lần khám)
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_thong_tin_benh_nhan (IN p_ma_bn INT)
BEGIN
    -- (a) Thông tin cá nhân
    SELECT * FROM benh_nhan WHERE ma_bn = p_ma_bn;

    -- (b) Toàn bộ lịch sử khám chữa bệnh
    SELECT b.ten_benh,
           DENSE_RANK() OVER (PARTITION BY d.ma_bn, d.ma_benh
                              ORDER BY d.ngay_bat_dau, d.ma_dot) AS lan_mac_thu,
           lk.so_lan   AS lan_kham_thu,
           lk.ngay_vao, lk.ngay_ra,
           nv.ho_ten   AS bac_sy_phu_trach,
           lk.phi_kham, lk.tong_tien
    FROM dot_benh d
    JOIN benh b       ON b.ma_benh = d.ma_benh
    JOIN nhan_vien nv ON nv.ma_nv  = d.ma_bs
    JOIN lan_kham lk  ON lk.ma_dot = d.ma_dot
    WHERE d.ma_bn = p_ma_bn
    ORDER BY lk.ngay_vao, lk.ma_lan_kham;

    -- (c) Tình trạng hiện tại: các bệnh đang mắc, đã khám lần thứ mấy
    SELECT b.ten_benh, d.ngay_bat_dau,
           COUNT(lk.ma_lan_kham) AS da_kham_lan_thu,
           nv.ho_ten AS bac_sy_phu_trach
    FROM dot_benh d
    JOIN benh b       ON b.ma_benh = d.ma_benh
    JOIN nhan_vien nv ON nv.ma_nv  = d.ma_bs
    LEFT JOIN lan_kham lk ON lk.ma_dot = d.ma_dot
    WHERE d.ma_bn = p_ma_bn AND d.ngay_ket_thuc IS NULL
    GROUP BY d.ma_dot, b.ten_benh, d.ngay_bat_dau, nv.ho_ten;
END$$

-- ---------------------------------------------------------------------
-- TRUY VẤN 4: Doanh thu phòng khám = tiền khám + tiền thuốc (theo khoảng ngày)
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_doanh_thu (IN p_tu DATE, IN p_den DATE)
BEGIN
    SELECT COUNT(*)                       AS so_luot_kham,
           COALESCE(SUM(phi_kham), 0)     AS doanh_thu_kham,
           COALESCE(SUM(tong_tien - phi_kham), 0) AS doanh_thu_thuoc,
           COALESCE(SUM(tong_tien), 0)    AS tong_doanh_thu
    FROM lan_kham
    WHERE ngay_vao BETWEEN p_tu AND p_den;
END$$

DELIMITER ;

-- Doanh thu theo từng tháng
CREATE VIEW v_doanh_thu_theo_thang AS
SELECT YEAR(ngay_vao) AS nam, MONTH(ngay_vao) AS thang,
       SUM(phi_kham) AS doanh_thu_kham,
       SUM(tong_tien - phi_kham) AS doanh_thu_thuoc,
       SUM(tong_tien) AS tong_doanh_thu
FROM lan_kham
GROUP BY YEAR(ngay_vao), MONTH(ngay_vao);

-- =====================================================================
-- PHẦN 5: GỌI THỬ CÁC TRUY VẤN (DEMO THÁNG 10 VÀ THÁNG 11/2026 HIỆN TẠI)
-- =====================================================================
CALL sp_benh_theo_thang(10, 2026);            -- TV1 tháng 10
CALL sp_benh_theo_thang(11, 2026);            -- TV1 tháng 11
CALL sp_tinh_luong(10, 2026);                 -- TV2 tháng 10
CALL sp_tinh_luong(NULL, NULL);               -- TV2 tháng hiện tại, chỉ tính đến hôm nay
CALL sp_thong_tin_benh_nhan(1);               -- TV3 (Kiểm chứng lan_mac_thu: 1, 1, 2, 2, 2)
CALL sp_doanh_thu('2026-11-01', '2026-11-06');-- TV4 doanh thu tháng 11
SELECT * FROM v_doanh_thu_theo_thang;

-- =====================================================================
-- PHẦN 6: BỘ THỦ TỤC & CÂU LỆNH KIỂM CHỨNG CÁC RÀNG BUỘC (RB2 -> RB5, UPDATE)
-- =====================================================================

DELIMITER $$

-- Thủ tục setup nhanh 30 đợt bệnh đang điều trị cho BS003 (để test RB3)
CREATE PROCEDURE sp_test_setup_rb3 ()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE v_ms VARCHAR(10);
    DECLARE v_cmt VARCHAR(12);
    DECLARE v_new_bn INT;

    -- Xoá dữ liệu test cũ nếu có
    DELETE d FROM dot_benh d JOIN benh_nhan b ON b.ma_bn = d.ma_bn WHERE b.ma_so LIKE 'BN9%';
    DELETE FROM benh_nhan WHERE ma_so LIKE 'BN9%';

    WHILE i <= 30 DO
        SET v_ms = CONCAT('BN9', LPAD(i, 2, '0'));
        SET v_cmt = CONCAT('9990000000', LPAD(i, 2, '0'));
        INSERT INTO benh_nhan (ma_so, cmt, ho_ten, ngay_sinh)
        VALUES (v_ms, v_cmt, CONCAT('Bệnh nhân Test ', i), '1990-01-01');
        SET v_new_bn = LAST_INSERT_ID();

        INSERT INTO dot_benh (ma_bn, ma_benh, ma_bs, ngay_bat_dau, ngay_ket_thuc)
        VALUES (v_new_bn, 1, 3, '2026-11-01', NULL);

        SET i = i + 1;
    END WHILE;
END$$

-- Thủ tục dọn dẹp dữ liệu test RB3
CREATE PROCEDURE sp_test_cleanup_rb3 ()
BEGIN
    DELETE d FROM dot_benh d JOIN benh_nhan b ON b.ma_bn = d.ma_bn WHERE b.ma_so LIKE 'BN9%';
    DELETE FROM benh_nhan WHERE ma_so LIKE 'BN9%';
END$$

-- ---------------------------------------------------------------------
-- THỦ TỤC CHẠY TOÀN BỘ BỘ TEST VÀ XUẤT BẢNG TỔNG KẾT TỰ ĐỘNG
-- (Tự động bắt lỗi SIGNAL bằng Exception Handler và in bảng báo cáo chi tiết)
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_chay_tat_ca_test ()
BEGIN
    DECLARE v_msg VARCHAR(255);
    DECLARE v_status VARCHAR(20);

    DROP TEMPORARY TABLE IF EXISTS tmp_ket_qua_test;
    CREATE TEMPORARY TABLE tmp_ket_qua_test (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ten_test VARCHAR(120),
        loai_thao_tac VARCHAR(40),
        ket_qua_mong_doi VARCHAR(255),
        thong_bao_thuc_te VARCHAR(255),
        trang_thai VARCHAR(20)
    );

    -- TEST 1: RB2 (INSERT) - BN1 đang điều trị Tăng huyết áp, mở thêm đợt cùng bệnh
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_msg = MESSAGE_TEXT;
        END;
        SET v_msg = 'KHÔNG PHÁT HIỆN LỖI';
        INSERT INTO dot_benh (ma_bn, ma_benh, ma_bs, ngay_bat_dau) VALUES (1, 2, 1, '2026-11-06');
        IF v_msg LIKE '%Bệnh nhân đang điều trị bệnh này%' THEN
            SET v_status = 'PASSED';
        ELSE
            SET v_status = 'FAILED';
        END IF;
        INSERT INTO tmp_ket_qua_test (ten_test, loai_thao_tac, ket_qua_mong_doi, thong_bao_thuc_te, trang_thai)
        VALUES ('RB2: BN trùng bệnh đang điều trị', 'INSERT dot_benh', 'Chặn mở đợt trùng bệnh', v_msg, v_status);
    END;

    -- TEST 2: RB3 (INSERT) - BS003 đã có 30 đợt điều trị, thêm đợt thứ 31
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_msg = MESSAGE_TEXT;
        END;
        CALL sp_test_setup_rb3();
        SET v_msg = 'KHÔNG PHÁT HIỆN LỖI';
        INSERT INTO dot_benh (ma_bn, ma_benh, ma_bs, ngay_bat_dau) VALUES (1, 1, 3, '2026-11-06');
        IF v_msg LIKE '%Bác sỹ đã đủ 30 đợt%' THEN
            SET v_status = 'PASSED';
        ELSE
            SET v_status = 'FAILED';
        END IF;
        CALL sp_test_cleanup_rb3();
        INSERT INTO tmp_ket_qua_test (ten_test, loai_thao_tac, ket_qua_mong_doi, thong_bao_thuc_te, trang_thai)
        VALUES ('RB3: Bác sỹ tối đa 30 đợt đang điều trị', 'INSERT dot_benh (đợt thứ 31)', 'Chặn khi BS đủ 30 đợt', v_msg, v_status);
    END;

    -- TEST 3: RB4 (INSERT) - Lần khám 8 đã có 3 y tá, thêm y tá thứ 4
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_msg = MESSAGE_TEXT;
        END;
        SET v_msg = 'KHÔNG PHÁT HIỆN LỖI';
        INSERT INTO y_ta_ho_tro (ma_lan_kham, ma_yta, vai_tro) VALUES (8, 7, 'Tiếp đón');
        IF v_msg LIKE '%Mỗi lần khám chỉ có tối đa 3 y tá%' THEN
            SET v_status = 'PASSED';
        ELSE
            SET v_status = 'FAILED';
        END IF;
        INSERT INTO tmp_ket_qua_test (ten_test, loai_thao_tac, ket_qua_mong_doi, thong_bao_thuc_te, trang_thai)
        VALUES ('RB4: Tối đa 3 y tá / lần khám', 'INSERT y_ta_ho_tro (y tá thứ 4)', 'Chặn y tá thứ 4', v_msg, v_status);
    END;

    -- TEST 4: RB5 (INSERT) - Thêm lần khám có ngày vào trước ngày bắt đầu đợt
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_msg = MESSAGE_TEXT;
        END;
        SET v_msg = 'KHÔNG PHÁT HIỆN LỖI';
        INSERT INTO lan_kham (ma_dot, ngay_vao, phi_kham) VALUES (6, '2026-10-01', 100000);
        IF v_msg LIKE '%Ngày vào nằm ngoài thời gian%' THEN
            SET v_status = 'PASSED';
        ELSE
            SET v_status = 'FAILED';
        END IF;
        INSERT INTO tmp_ket_qua_test (ten_test, loai_thao_tac, ket_qua_mong_doi, thong_bao_thuc_te, trang_thai)
        VALUES ('RB5: Ngày khám nằm trong đợt bệnh', 'INSERT lan_kham', 'Chặn ngày vào trước đợt', v_msg, v_status);
    END;

    -- TEST 5: UPDATE phi_kham -> tong_tien tự cập nhật
    BEGIN
        DECLARE v_old_tong DECIMAL(12,0);
        DECLARE v_new_tong DECIMAL(12,0);
        SELECT tong_tien INTO v_old_tong FROM lan_kham WHERE ma_lan_kham = 1;
        UPDATE lan_kham SET phi_kham = 250000 WHERE ma_lan_kham = 1;
        SELECT tong_tien INTO v_new_tong FROM lan_kham WHERE ma_lan_kham = 1;
        -- Khôi phục lại giá trị cũ
        UPDATE lan_kham SET phi_kham = 150000 WHERE ma_lan_kham = 1;
        IF v_new_tong = 275000 THEN
            SET v_status = 'PASSED';
            SET v_msg = CONCAT('Tổng tiền tự cập nhật từ ', v_old_tong, ' lên ', v_new_tong);
        ELSE
            SET v_status = 'FAILED';
            SET v_msg = CONCAT('Tổng tiền thực tế: ', v_new_tong, ' (kỳ vọng 275000)');
        END IF;
        INSERT INTO tmp_ket_qua_test (ten_test, loai_thao_tac, ket_qua_mong_doi, thong_bao_thuc_te, trang_thai)
        VALUES ('UPDATE phi_kham tự cập nhật tong_tien', 'UPDATE lan_kham', 'tong_tien = phi_kham + thuốc', v_msg, v_status);
    END;

    -- TEST 6: UPDATE đóng đợt sớm hơn ngày vào của lần khám cuối
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_msg = MESSAGE_TEXT;
        END;
        SET v_msg = 'KHÔNG PHÁT HIỆN LỖI';
        UPDATE dot_benh SET ngay_ket_thuc = '2026-08-12' WHERE ma_dot = 1;
        IF v_msg LIKE '%Ngày kết thúc sớm hơn%' THEN
            SET v_status = 'PASSED';
        ELSE
            SET v_status = 'FAILED';
        END IF;
        INSERT INTO tmp_ket_qua_test (ten_test, loai_thao_tac, ket_qua_mong_doi, thong_bao_thuc_te, trang_thai)
        VALUES ('UPDATE đóng đợt sớm hơn lần khám cuối', 'UPDATE dot_benh (ngay_ket_thuc)', 'Chặn ngày kết thúc sớm', v_msg, v_status);
    END;

    -- TEST 7: UPDATE mở lại đợt (ngay_ket_thuc=NULL) vi phạm RB2
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_msg = MESSAGE_TEXT;
        END;
        -- BN1 đang có đợt 2 (Cảm cúm) đã kết thúc. Tạo tạm 1 đợt cảm cúm đang mở cho BN1, sau đó mở lại đợt 2
        INSERT INTO dot_benh (ma_bn, ma_benh, ma_bs, ngay_bat_dau, ngay_ket_thuc) VALUES (1, 4, 2, '2026-11-06', NULL);
        SET v_msg = 'KHÔNG PHÁT HIỆN LỖI';
        UPDATE dot_benh SET ngay_ket_thuc = NULL WHERE ma_dot = 2;
        IF v_msg LIKE '%Bệnh nhân đang điều trị bệnh này%' THEN
            SET v_status = 'PASSED';
        ELSE
            SET v_status = 'FAILED';
        END IF;
        -- Dọn đợt vừa tạm tạo
        DELETE FROM dot_benh WHERE ma_bn = 1 AND ma_benh = 4 AND ngay_bat_dau = '2026-11-06';
        INSERT INTO tmp_ket_qua_test (ten_test, loai_thao_tac, ket_qua_mong_doi, thong_bao_thuc_te, trang_thai)
        VALUES ('UPDATE mở lại đợt vi phạm RB2', 'UPDATE dot_benh (ngay_ket_thuc=NULL)', 'Chặn mở lại đợt trùng bệnh', v_msg, v_status);
    END;

    -- TEST 8: UPDATE đổi bác sĩ sang BS đã đủ 30 đợt vi phạm RB3
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 v_msg = MESSAGE_TEXT;
        END;
        CALL sp_test_setup_rb3();
        SET v_msg = 'KHÔNG PHÁT HIỆN LỖI';
        -- Đợt 3 đang mở (thuộc BS 1), thử đổi sang BS 3 (đã đủ 30 đợt)
        UPDATE dot_benh SET ma_bs = 3 WHERE ma_dot = 3;
        IF v_msg LIKE '%Bác sỹ đã đủ 30 đợt%' THEN
            SET v_status = 'PASSED';
        ELSE
            SET v_status = 'FAILED';
        END IF;
        CALL sp_test_cleanup_rb3();
        INSERT INTO tmp_ket_qua_test (ten_test, loai_thao_tac, ket_qua_mong_doi, thong_bao_thuc_te, trang_thai)
        VALUES ('UPDATE đổi bác sĩ đủ 30 đợt vi phạm RB3', 'UPDATE dot_benh (ma_bs)', 'Chặn gán BS đã đủ 30 đợt', v_msg, v_status);
    END;

    -- Hiển thị kết quả tổng hợp
    SELECT id AS `STT`,
           ten_test AS `Tên kiểm thử`,
           loai_thao_tac AS `Thao tác`,
           ket_qua_mong_doi AS `Kỳ vọng`,
           thong_bao_thuc_te AS `Thông báo thực tế`,
           trang_thai AS `Kết quả`
    FROM tmp_ket_qua_test;

    DROP TEMPORARY TABLE IF EXISTS tmp_ket_qua_test;
END$$

DELIMITER ;

-- =====================================================================
-- CHẠY KIỂM THỬ TỰ ĐỘNG KHI NẠP FILE
-- =====================================================================
CALL sp_chay_tat_ca_test();

-- =====================================================================
-- HƯỚNG DẪN TEST THỦ CÔNG TỪNG LỆNH TRÊN MYSQL WORKBENCH:
-- (Bôi đen từng dòng dưới đây và bấm nút Sấm sét (Ctrl+Enter) để thấy mã lỗi SIGNAL 45000 đỏ trực tiếp)
-- =====================================================================

-- [Test RB2 - INSERT]: BN1 đang điều trị Tăng huyết áp (đợt 3). Thử mở đợt mới cùng bệnh 2:
-- -> Lỗi mong đợi: Error Code: 1644. Bệnh nhân đang điều trị bệnh này, chưa thể mở đợt mới
-- INSERT INTO dot_benh (ma_bn, ma_benh, ma_bs, ngay_bat_dau) VALUES (1, 2, 1, '2026-11-06');

-- [Test RB3 - INSERT]: BS 3 đã đủ 30 đợt bệnh đang điều trị. Thử mở đợt thứ 31 cho BS 3:
-- Bước 1: Setup 30 đợt test cho BS 3:
-- CALL sp_test_setup_rb3();
-- Bước 2: Thử mở đợt thứ 31 cho BS 3 -> Lỗi mong đợi: Error Code: 1644. Bác sỹ đã đủ 30 đợt bệnh đang điều trị
-- INSERT INTO dot_benh (ma_bn, ma_benh, ma_bs, ngay_bat_dau) VALUES (1, 1, 3, '2026-11-06');
-- Bước 3: Dọn dẹp dữ liệu test RB3:
-- CALL sp_test_cleanup_rb3();

-- [Test RB4 - INSERT]: Lần khám 8 đã có đủ 3 y tá (4, 5, 6). Thêm y tá thứ 4 (ma_yta = 7):
-- -> Lỗi mong đợi: Error Code: 1644. Mỗi lần khám chỉ có tối đa 3 y tá hỗ trợ
-- INSERT INTO y_ta_ho_tro (ma_lan_kham, ma_yta, vai_tro) VALUES (8, 7, 'Tiếp đón');

-- [Test RB5 - INSERT]: Đợt bệnh 6 bắt đầu 2026-10-12. Thêm lần khám ngày 2026-10-01 (sớm hơn đợt):
-- -> Lỗi mong đợi: Error Code: 1644. Ngày vào nằm ngoài thời gian của đợt bệnh
-- INSERT INTO lan_kham (ma_dot, ngay_vao, phi_kham) VALUES (6, '2026-10-01', 100000);

-- [Test UPDATE phi_kham]: Sửa phí khám lần khám 1 -> tong_tien tự nhảy từ 175.000 lên 275.000:
-- SELECT ma_lan_kham, phi_kham, tong_tien FROM lan_kham WHERE ma_lan_kham = 1;
-- UPDATE lan_kham SET phi_kham = 250000 WHERE ma_lan_kham = 1;
-- SELECT ma_lan_kham, phi_kham, tong_tien FROM lan_kham WHERE ma_lan_kham = 1;

-- [Test UPDATE ngay_ket_thuc]: Đợt 1 có lần khám cuối ngày 2026-08-14. Đóng đợt với ngày 2026-08-12:
-- -> Lỗi mong đợi: Error Code: 1644. Ngày kết thúc sớm hơn ngày vào của lần khám trong đợt
-- UPDATE dot_benh SET ngay_ket_thuc = '2026-08-12' WHERE ma_dot = 1;

-- [Test UPDATE mở lại đợt vi phạm RB2]:
-- INSERT INTO dot_benh (ma_bn, ma_benh, ma_bs, ngay_bat_dau, ngay_ket_thuc) VALUES (1, 4, 2, '2026-11-06', NULL);
-- -> Thử mở lại đợt 2 (Cảm cúm của BN1) khi đang có đợt cảm cúm khác mở:
-- UPDATE dot_benh SET ngay_ket_thuc = NULL WHERE ma_dot = 2;
-- -> Dọn đợt vừa tạo:
-- DELETE FROM dot_benh WHERE ma_bn = 1 AND ma_benh = 4 AND ngay_bat_dau = '2026-11-06';
