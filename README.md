# WorkFollow

Ứng dụng Flask + MySQL để theo dõi kế hoạch công việc theo ngày, tuần và tháng.

## Chạy ứng dụng

1. Tạo database MySQL:
```sql
CREATE DATABASE workfollow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Cài thư viện:
```bash
pip install -r requirements.txt
```

3. Cấu hình kết nối MySQL:
```bash
export DB_USER=root
export DB_PASS=mat_khau_mysql
export DB_HOST=localhost
export DB_NAME=workfollow
```

Trên Windows PowerShell:
```powershell
$env:DB_USER="root"
$env:DB_PASS="mat_khau_mysql"
$env:DB_HOST="localhost"
$env:DB_NAME="workfollow"
```

4. Chạy app:
```bash
python app.py
```

Mở trình duyệt: http://127.0.0.1:5000

App tự tạo bảng `task` và dữ liệu mẫu trong lần chạy đầu tiên.
