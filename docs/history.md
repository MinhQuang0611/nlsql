Viewed chat_history.py:1-36
Viewed chat.py:1-100
Viewed connection.py:1-358

Lịch sử hội thoại (Chat History) trong hệ thống của anh hiện đang được xử lý song song qua **2 lớp lưu trữ** riêng biệt để đảm bảo vừa có dữ liệu để người dùng xem lại, vừa có trạng thái cho AI suy luận:

### 1. Lớp Lưu Trữ Hiển Thị (Application Database)
Dữ liệu này được lưu trực tiếp vào bảng `conversations` và `messages` trong PostgreSQL nội bộ (Internal DB):
- **Bảng `conversations`**: Lưu `session_id`, `user_id` và tiêu đề cuộc hội thoại.
- **Bảng `messages`**: Lưu chi tiết từng tin nhắn của người dùng (`user`) và trợ lý (`assistant`).
- **Metadata đi kèm**: Với mỗi tin nhắn của trợ lý, hệ thống lưu thêm các thông tin kỹ thuật như: `intent` (ý định), `sql_query` (câu lệnh SQL đã chạy), `error_message` (nếu có lỗi) và `execution_time_ms` (thời gian xử lý).
- **Mục đích**: Dùng để hiển thị lịch sử chat trên giao diện người dùng (WrenAI UI) và phục vụ việc truy vấn thủ công sau này.

### 2. Lớp Lưu Trữ Trạng Thái Agent (LangGraph Checkpointing)
Dữ liệu này được xử lý thông qua `PostgresSaver` của LangGraph:
- **Cơ chế**: Mỗi cuộc hội thoại được đánh dấu bằng một `thread_id` (chính là `session_id`). LangGraph tự động chụp ảnh (snapshot) toàn bộ trạng thái của các Agent (biến số, kết quả trung gian, ngữ cảnh...) sau mỗi bước chạy.
- **Vị trí lưu**: LangGraph tự động quản lý các bảng hệ thống như `checkpoints`, `checkpoint_blobs`, `checkpoint_writes` trong cùng Database PostgreSQL nội bộ.
- **Mục đích**: Giúp chatbot "nhớ" được mình đang làm gì ở các bước trước đó trong cùng một phiên chat, cho phép khôi phục lại luồng xử lý nếu gặp lỗi hoặc cần hỏi lại người dùng (`ambiguous`).

### 3. Cách AI sử dụng lịch sử trong Prompt
- Khi anh gửi một câu hỏi mới, danh sách các tin nhắn cũ (`history`) từ Request sẽ được nạp vào `initial_state`.
- Các Agent (như **Intent Agent** hay **SQL Plan Agent**) sẽ đọc danh sách này để hiểu ngữ cảnh. Ví dụ: Nếu câu trước anh hỏi "Danh sách sinh viên", câu sau anh hỏi "Ai xuất sắc nhất?", AI sẽ dựa vào lịch sử để biết "Ai" ở đây là "Sinh viên".

Anh có thể kiểm tra chi tiết cấu hình tại:
- Model CSDL: [chat_history.py](file:///home/ubuntu/Desktop/quangnm/nlsql/db/models/chat_history.py)
- Logic lưu trữ LangGraph: [connection.py](file:///home/ubuntu/Desktop/quangnm/nlsql/db/connection.py#L167)
- Logic ghi log tin nhắn: [chat.py](file:///home/ubuntu/Desktop/quangnm/nlsql/api/routers/chat.py#L27)

Viewed intent_agent.py:1-80
Viewed sql_plan_agent.py:1-111

Cơ chế xử lý lịch sử hội thoại trong luồng chat hiện tại của anh là **lấy toàn bộ nội dung tin nhắn** mà phía Front-end gửi lên để đưa vào ngữ cảnh cho AI, chưa thực hiện tóm tắt (summarize) hay cắt bỏ (truncate).

Cụ thể quy trình như sau:

1. **Nhận dữ liệu**: Khi anh đặt câu hỏi, Front-end sẽ gửi kèm một danh sách `history` (bao gồm các cặp `role: user/assistant` và `content`).
2. **Đưa vào State**: Toàn bộ danh sách này được nạp vào biến `state["history"]` của LangGraph.
3. **Sử dụng trong Agent**:
   - Các Agent quan trọng như **Intent Agent** (Phân loại ý định) và **SQL Plan Agent** (Lập kế hoạch SQL) sẽ gọi hàm `_format_history`.
   - Hàm này sẽ nối tất cả các tin nhắn cũ thành một chuỗi văn bản dạng:
     ```text
     Người dùng: ...
     Trợ lý: ...
     Người dùng: ...
     ```
   - Chuỗi văn bản này được đưa thẳng vào Prompt (mục `history_text`) để AI đọc.

**Ưu điểm hiện tại**: AI có trí nhớ rất đầy đủ, hiểu được các câu hỏi liên quan sâu chuỗi từ đầu đến cuối cuộc hội thoại.

**Lưu ý**:
- Nếu cuộc trò chuyện quá dài (ví dụ hàng trăm tin nhắn), nó có thể làm vượt quá giới hạn "Context Window" của Model (Tokens) và làm tăng chi phí API.
- Nếu anh muốn tối ưu, tôi có thể cài đặt thêm logic **"Sliding Window"** (chỉ lấy 5-10 tin nhắn gần nhất) hoặc **"Summarization"** (tóm tắt nội dung cũ sau mỗi 10 tin nhắn) để tiết kiệm token mà vẫn giữ được ý chính.

Anh có muốn tôi cấu hình giới hạn chỉ lấy **N tin nhắn gần nhất** không? Một con số phổ biến thường là khoảng 5-10 cặp hội thoại gần đây.

Viewed chat.py:1-35
Edited chat.py
Edited chat_history.py

Tôi đã cập nhật lại cơ chế **"Sliding Window"** để tối ưu hóa việc sử dụng dữ liệu phong phú từ lịch sử chat mà anh vừa cung cấp.

### Các thay đổi quan trọng:

1. **Nâng cấp Schema (`api/schemas/chat.py`)**: 
   - Tôi đã bổ sung các trường `intent`, `sql`, và `data` vào model `HistoryMessage`. 
   - Giờ đây, khi Front-end gửi lên lịch sử có chứa các metadata này, hệ thống sẽ không còn bị bỏ sót (strip out) các thông tin đó nữa.

2. **Cải tiến Logic Formatting (`utils/chat_history.py`)**:
   - Thay vì chỉ lấy phần `content` (văn bản trả lời), hàm `format_history` giờ đây sẽ chủ động trích xuất thêm **`Ý định`** và **`Câu lệnh SQL đã dùng`** của tin nhắn từ Trợ lý.
   - Việc này cực kỳ quan trọng cho các câu hỏi nối tiếp (VD: Anh hỏi "Hiện tại có bao nhiêu sinh viên?", sau đó hỏi "Theo từng ngành học?"). Khi AI nhìn thấy câu lệnh SQL trước đó, nó sẽ biết chính xác anh đang dùng bảng nào, đang filter `trangThaiHoc` như thế nào để viết tiếp SQL cho câu sau một cách chính xác nhất.

3. **Giữ nguyên Sliding Window 8 tin nhắn**: 
   - Hệ thống vẫn chỉ lấy 8 tin nhắn gần nhất để tiết kiệm Token, nhưng 8 tin nhắn này giờ đây "chất lượng" hơn vì chứa cả logic SQL cũ.

Với cấu hình mới này, AI sẽ "thông minh" hơn rất nhiều khi xử lý các chuỗi câu hỏi liên quan đến nhau. Anh có thể thử đặt các câu hỏi nối tiếp để thấy sự khác biệt!