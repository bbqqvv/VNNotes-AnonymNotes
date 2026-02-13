# 🍃 VNNotes: The Invisible Workspace

![Version](https://img.shields.io/badge/version-1.0.0-emerald?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-gray?style=flat-square)

**VNNotes** là không gian làm việc "tàng hình" chuyên nghiệp dành cho Windows. Ứng dụng giúp bạn ghi chú, lưu trữ ý tưởng và tra cứu thông tin mà **tuyệt đối không bị phát hiện** bởi các phần mềm quay màn hình, livestream hay chia sẻ màn hình (Zoom, Teams, Discord, OBS...).

> **"Nhìn thấy bởi bạn. Vô hình với thế giới."**

---

## 🌟 Tính Năng Nổi Bật

### 1. 👻 Ghost Mode (Công nghệ Anti-Capture)
Sử dụng **Windows Display Affinity API**, VNNotes có khả năng:
-   **Tàng hình 100%** trên các phần mềm quay/chụp màn hình.
-   Khi bạn share màn hình, người xem chỉ thấy... hình nền desktop của bạn, trong khi bạn vẫn đang đọc ghi chú bình thường.
-   Điều chỉnh độ trong suốt (Opacity) để hòa làm một với môi trường.

### 2. 📝 Power Notes (Ghi chú Mạnh mẽ)
Trình soạn thảo Markdown chuyên nghiệp với các tính năng cao cấp (Cập nhật **v1.0.0**):
-   **Kéo & Thả (Drag & Drop)**: Kéo ảnh, văn bản từ bên ngoài vào hoặc di chuyển tự do trong bài viết.
-   **Căn Chỉnh Ảnh**: Chuột phải vào ảnh -> Chọn **Align Left / Center / Right**.
-   **Resize Thông minh**: Double-click vào ảnh để nhập kích thước pixel chính xác.
-   **Code Blocks**: Viết code đẹp mắt với font Monospace.
-   **Checklists**: Quản lý việc cần làm nhanh chóng.

### 3. 🌐 Mini Browser (Trình duyệt Tích hợp)
-   Docking Browser ngay bên cạnh ghi chú.
-   Tra cứu tài liệu, Google Search, xem docs mà không cần Alt-Tab ra ngoài trình duyệt chính.
-   Luôn ở trạng thái "Always on Top" nếu cần.

### 4. 🔒 Local Privacy (Riêng tư Tuyệt đối)
-   Dữ liệu lưu cục bộ (**JSON**), không gửi lên Cloud.
-   Bạn hoàn toàn làm chủ dữ liệu của mình.

---

## 🚀 Tải về & Cài đặt

### Cách 1: Người dùng phổ thông (Khuyên dùng)
Tải bộ cài đặt `.exe` mới nhất tại trang **Releases**:

👉 **[Download VNNotes v1.0.0](https://github.com/bbqqvv/AnonymNotes/releases/latest)**

1.  Tải file `StealthAssist_Setup.exe`.
2.  Chạy file cài đặt.
3.  Mở app từ Shortcut ngoài Desktop.

### Cách 2: Chạy Portable (Không cần cài)
Trong thư mục cài đặt (`%LOCALAPPDATA%\StealthAssist`), bạn có thể copy file `.exe` đi bất cứ đâu.

---

## 💻 Dành cho Developer

Nếu bạn muốn phát triển thêm tính năng hoặc tự build từ source code:

### Yêu cầu
-   Python 3.10 trở lên.
-   Git.

### Cài đặt môi trường
```bash
# 1. Clone dự án về máy
git clone https://github.com/bbqqvv/AnonymNotes.git
cd AnonymNotes

# 2. Tạo môi trường ảo (Khuyên dùng)
python -m venv venv
.\venv\Scripts\activate

# 3. Cài đặt thư viện
pip install -r requirements.txt
```

### Chạy ứng dụng
```bash
python main.py
```

### Đóng gói (Build .exe)
Sử dụng script build tự động (đã tối ưu dung lượng):
```bash
python tools/build_installer.py
```
File cài đặt sẽ nằm trong thư mục `tools/dist/`.

---

## 🌐 Web Landing Page (SaaS)
Dự án bao gồm một Landing Page hiện đại (Next.js + TailwindCSS) nằm trong thư mục `/web`.
Để chạy website này:
1.  `cd web`
2.  Chạy `install_and_run.bat`.
3.  Truy cập `http://localhost:3000`.

---

## ⌨️ Phím tắt (Shortcuts)

| Phím tắt | Chức năng |
| :--- | :--- |
| `Ctrl + N` | Tạo ghi chú mới |
| `Ctrl + S` | Lưu thủ công (App tự lưu mỗi 5s) |
| `Ctrl + F` | Tìm kiếm trong ghi chú |
| `Ctrl + B/I/U` | In đậm / Nghiêng / Gạch chân |
| `Double-Click Ảnh` | Chỉnh kích thước ảnh |

---

**Phát triển bởi VTechStudio.**
*Privacy First. Always.*
