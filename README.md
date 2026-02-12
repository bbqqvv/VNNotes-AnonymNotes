# 🍃 Stealth Assist

**Stealth Assist** là một công cụ hỗ trợ ghi chú và duyệt web siêu ngụy trang, được thiết kế để hoạt động bí mật và hiệu quả trên Windows.

## ✨ Tính năng nổi bật

### 1. 🛡️ Super Stealth (Anti-Screen Capture)
Sử dụng công nghệ `SetWindowDisplayAffinity`, ứng dụng sẽ hoàn toàn **tàng hình** đối với các công cụ quay màn hình, chụp ảnh hoặc livestream (OBS, Discord, Zoom...). Bạn vẫn nhìn thấy app, nhưng người khác thì không.

### 2. 📝 Power Notes
-   Hỗ trợ đầy đủ định dạng văn bản (Bold, Italic, Underline).
-   Chèn hình ảnh trực tiếp từ Clipboard và kéo thả để thay đổi kích thước.
-   **Checkboxes (Todo list)**: Click trực tiếp để đánh dấu hoàn thành.
-   **Code Blocks**: Định dạng code chuyên nghiệp với font Monospace và nền tối.
-   **Highlighter**: Làm nổi bật các đoạn văn bản quan trọng.
-   **Internal Search**: Tìm kiếm nhanh nội dung trong note bằng `Ctrl+F`.

### 3. 🌐 Mini Browser
Trình duyệt web tích hợp nhỏ gọn dạng Docking, giúp bạn tra cứu nhanh mà không cần chuyển Tab rườm rà.

### 4. 🌓 Giao diện linh hoạt
-   Chế độ **Dark Mode** mặc định cực kỳ dịu mắt.
-   Chế độ **Light Mode** cho môi trường văn phòng truyền thống.
-   Tính năng **Always on Top** và điều chỉnh độ trong suốt.

### 5. 💾 Lưu trữ tin cậy
Tự động lưu lại toàn bộ trạng thái ghi chú, vị trí cửa sổ và lịch sử duyệt web khi thoát ứng dụng. Khôi phục y hệt khi mở lại.

## 🚀 Tải về & Cài đặt

Bạn có thể tải bản cài đặt sẵn `.exe` tại mục **[Releases](../../releases)**.

1.  Tải file `StealthAssist_Setup.exe`.
2.  Chạy bộ cài đặt và làm theo hướng dẫn (Next -> Install).
3.  Ứng dụng sẽ tự động tạo Shortcut ngoài Desktop.

## 🛠️ Yêu cầu hệ thống
-   Windows 10 hoặc Windows 11 (Cần thiết cho tính năng Super Stealth).
-   Python 3.8+ (Nếu bạn chạy từ mã nguồn).

## 👨‍💻 Phát triển
Nếu bạn muốn chạy từ mã nguồn:
```bash
# Clone repository
git clone https://github.com/[YOUR_USERNAME]/StealthAssist.git

# Cài đặt thư viện
pip install -r requirements.txt

# Chạy ứng dụng
python main.py
```

---
*Phát triển bởi VTechStudio.*
