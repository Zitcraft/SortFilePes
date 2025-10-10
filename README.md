# Embroidery File Management System

Hệ thống quản lý file thêu tự động với đầy đủ quy trình từ tải xuống đến xuất DST và gắn nhãn.

## 📁 Cấu trúc thư mục

```
SORT FILE LEMIEX/
├── files/               # Thư mục chính chứa dữ liệu
│   ├── design/         # File .pes từ Dropbox
│   └── labels/         # File nhãn .png từ Dropbox
├── sorted/             # Kết quả phân loại (tự động tạo)
│   ├── A/              # Người A
│   │   ├── dst/        # File DST đã xuất
│   │   └── labels/     # Nhãn đã xử lý
│   ├── B/              # Người B
│   ├── C/              # Người C
│   └── output/         # File CSV/XLSX và log
├── download_from_dropbox.py    # Tải file từ Dropbox
├── export_dst.py       # Xuất file DST
├── map_dst_labels.py   # Gắn DST vào nhãn
├── workflow.py         # Quản lý quy trình (khuyến nghị)
└── README.md           # Hướng dẫn này
```

## 🚀 Quy trình sử dụng

### Cách khuyến nghị: Sử dụng workflow.py
```bash
python workflow.py
```
Chọn tùy chọn:
1. Chạy từng bước (có xác nhận)
2. Chạy tất cả tự động  
3. Chạy bước cụ thể
4. Hiển thị trạng thái thư mục

### Hoặc chạy từng bước thủ công:

### Bước 1: Tải file từ Dropbox
```bash
python download_from_dropbox.py
```
- Tải file .pes vào `files/design/`
- Tải file nhãn vào `files/labels/`
- Hiển thị báo cáo file bị thiếu

### Bước 2: Phân loại file
```bash
python sort_cli.py
```
- Đọc file từ `files/design/`
- Tạo thư mục `sorted/` với phân loại A/B/C
- Di chuyển file .pes vào folders (move, dùng --copy nếu muốn copy)
- Xuất CSV/XLSX với folder_order và unique_hashes
- Sao chép nhãn từ `files/labels/` vào `sorted/*/labels/`

### Bước 3: Xuất file DST
```bash
python export_dst.py
```
- Chuyển đổi file .pes thành .dst
- Tạo tên file theo định dạng XXXYLZMDD.dst
- Xử lý đúng multi-face items (front, sleeve_left, sleeve_right)
- Lưu vào `sorted/*/dst/`

### Bước 4: Gắn DST vào nhãn
```bash
python map_dst_labels.py           # Move labels (mặc định)
python map_dst_labels.py --copy    # Copy labels (nếu muốn giữ files/labels)
```
- Đọc log DST từ `sorted/output/dst_export_log.json`
- Di chuyển chỉ những label có DST mapping từ `files/labels/` vào `sorted/*/labels/`
- Gắn tên DST vào góc trên-trái của nhãn PNG
- Định vị lại nội dung nhãn xuống dưới
- Multi-face: "055A2F09j | 056A2L09j"
- Labels không có DST sẽ ở lại trong `files/labels/`

## 📋 Thông tin file DST

### Định dạng tên file: XXXYLZMDD.dst
- **XXX**: Folder order (3 chữ số)
- **Y**: Người (A/B/C)
- **L**: Tổng số mặt của item
- **Z**: Vị trí (F=front, L=sleeve_left, R=sleeve_right)
- **MM**: Ngày (01-31)
- **D**: Mã tháng (a=Jan, b=Feb, ..., j=Oct)

### Ví dụ:
- `055A2F09j.dst`: Folder 55, Người A, 2 mặt, Front, ngày 9, tháng 10
- `056A2L09j.dst`: Folder 56, Người A, 2 mặt, Left sleeve, ngày 9, tháng 10

## 🔧 Yêu cầu hệ thống

- Python 3.7+
- Thư viện: PIL (Pillow), pyembroidery, pandas, openpyxl
- Cài đặt: `pip install pillow pyembroidery pandas openpyxl`

## 📊 Kết quả

Sau khi hoàn thành quy trình:

1. **File phân loại**: `sorted/A/`, `sorted/B/`, `sorted/C/`
2. **File DST**: `sorted/*/dst/*.dst` (sẵn sàng cho máy thêu)
3. **Nhãn đã gắn**: `sorted/*/labels/*.png` (có tên DST)
4. **Báo cáo**: `sorted/output/` (CSV, XLSX, JSON logs)

## 💡 Lưu ý

- Chạy script theo thứ tự từ Bước 1 đến Bước 4
- Mỗi script có xác nhận trước khi thực hiện
- Multi-face items sẽ tạo nhiều file DST riêng biệt
- File log JSON chứa mapping chi tiết DST-to-label

## 🆘 Hỗ trợ

Nếu gặp lỗi:
1. Kiểm tra cấu trúc thư mục
2. Đảm bảo file nguồn tồn tại
3. Xem log chi tiết trong terminal
4. Kiểm tra quyền ghi file