# Tài liệu Vận hành: Cẩm nang LangGraph Streaming v2

Tài liệu này giải thích chuyên sâu về cơ chế Streaming của kiến trúc LangGraph, đối chiếu với tài liệu gốc của thư viện Langchain và hướng dẫn các kỹ thuật xử lý luồng sự kiện (bao gồm hệ thống kết nối SSE và kỹ thuật xử lý đệm Proxy) đang được ứng dụng trực tiếp tại nhánh Backend dự án NLSQL.

## 1. Bản chất Streaming của LangGraph

Trong các ứng dụng LLM đơn thuần, "streaming" thường đồng nghĩa với "token streaming" (gửi cụm văn bản được sinh ra dưới dạng từng token/chữ một).

Tuy nhiên, cấu trúc ứng dụng LangGraph phức tạp hơn rất nhiều. Việc streaming ở đây đồng nghĩa rông hơn, đó là sự **phân phối quá trình biến đổi trạng thái dự án (State Streaming)** một cách liền mạch từ vô số tiến trình nhỏ (Nodes, Subgraphs, External Tools, LLM Calls). 

LangGraph cho phép phát ra (emit) cả State Streaming và Token Streaming trên cùng một đường ống duy nhất, giúp giao diện Frontend UI có được góc nhìn thời gian thực:
- Hiển thị được quá trình hệ thống suy nghĩ minh bạch: "Đang phân tích ý định...", "Đang viết SQL..."
- Nhận luồng câu trả lời trực tiếp từ API dưới dạng "Gõ chữ" (Typewriter effect).

## 2. Định dạng Chuẩn hóa Version V2 (v2 output format)

Với bộ LangGraph >= 1.1, cú pháp bắt buộc là truyền `version="v2"` vào hàm gọi `astream()`. 

**Lợi ích lớn nhất:** Trong v1, kiểu dữ liệu trả về biến đổi hỗn độn tùy thuộc vào việc bạn gọi 1 mode, nhiều mode, hay gọi từ subgraph. Nhưng ở **v2**, dữ liệu xuất ra bao giờ cũng định dạng cấu trúc Từ điển (Dict) cố định mang tên `StreamPart`:

```python
for chunk in graph.stream(inputs, stream_mode="updates", version="v2"):
    print(chunk["type"])  # Ví dụ: "updates"
    print(chunk["ns"])    # ()
    print(chunk["data"])  # Dữ liệu thật chứa bên trong
```

Cấu trúc đồng nhất của `StreamPart` v2 bao gồm:
- **`type`**: Loại luồng stream (thuộc 1 trong 7 dạng: `"values"`, `"updates"`, `"messages"`, `"custom"`, `"checkpoints"`, `"tasks"`, `"debug"`).
- **`ns`**: (Namespace Tuple), cực kỳ hữu dụng để truy vết nếu truy vấn gọi sâu từ Subgraph (vd: `("node_name:<task_id>",)`). Nếu ở nhánh graph gốc thì là `()`.
- **`data`**: Payload nội dung trần. Định dạng payload biến đổi linh hoạt và ánh xạ cực chặt với từ khóa khai báo của `type`.

Nhờ có cấu trúc cờ `chunk["type"]`, vòng lặp Backend API có thể thoải mái thiết lập rẽ nhánh `if / elif` để routing luồng dữ liệu an toàn và dễ Type Check.

## 3. Các Chế độ Phân Luồng (Stream Modes) Tiêu Chuẩn

Bạn có thể truyền một chuỗi chuẩn (String) hoặc kết hợp hàng loạt chế độ dưới dạng Mảng (List) vào thuộc tính `stream_mode` (Ví dụ: `["updates", "messages", "custom"]`). Dưới đây là ý nghĩa cốt lõi của từng chế độ:

### 3.1. Chế độ `updates` (Chế độ thiết yếu của hệ thống NLSQL)
- **Hành vi**: Chỉ trả về **những gì vừa được thay đổi (delta)** trên Global State sau khi một Node / Bước hoàn thành (State updates after each step). Nếu một node thay đổi nhiều lần thì sẽ bị ngắt làm các block riêng biệt.
- **Payload (`chunk["data"]`)**: Là một dict, có format `{"tên_node": {"biến_cập_nhật": "giá_trị"}}`.
- **Ưu điểm**: Tuyệt đối tối ưu về băng thông. Backend nhận được gói dữ liệu này đồng nghĩa xác thực = "Node đó vừa làm xong task!".

### 3.2. Chế độ `values`
- **Hành vi**: Gửi lại Toàn Bộ biến của State hiện hành (Full state snapshot after each step) mỗi khi 1 step khép lại.
- **Nhược điểm**: Rất cồng kềnh. Nếu trong phiên làm việc, DB load lên mảng JSON 50.000 dòng Data gán vào biến `query_result`, qua mỗi một Node phụ, LangGraph lại phát Stream cả 50.000 dòng Data đó liên tục gây thắt nút cổ chai (Bottleneck) mạng socket.

### 3.3. Chế độ `messages` (Dành cho Streaming Token Nội Tại)
- **Hành vi**: Tuôn các luồng token (ký tự LLM) được sinh ra trực tiếp từ bên trong các node/tools đang gọi OpenAI.
- **Payload (`chunk["data"]`)**: Là một tuple chứa 2 thành phần `(message_chunk, metadata)`.
- **Lọc thông minh (Filter by node/tags)**: Bạn có thể bắt `metadata["langgraph_node"] == "answer_agent"` để nhận riêng Text từ một Node chỉ định, hoặc chèn thêm thẻ tags (vd `{"tags": ["nostream"]}`) vào Chat Models để ẩn chặn hoàn toàn các token gọi nháp, không để nó tràn dội xuống Client UI.

### 3.4. Chế độ `custom` (Custom Data Emitter)
Khắc phục nhược điểm "Node phải chạy xong mới hiện status", LangGraph cung cấp hàm `get_stream_writer()` để một Node đang chạy có thể bắn trực tiếp metadata, status, % tiến trình chạy của nó ra luồng bên ngoài ngay lập tức!
```python
from langgraph.config import get_stream_writer

def schema_agent(state: State):
    writer = get_stream_writer()
    # Bắn tín hiệu custom báo trạng thái
    writer({"status": "Đang đọc cấu trúc Postgres (20%)"})
    
    # ... Process lâu dài ...
    
    return {"schema_context": [...]}
```

### 3.5. Một số chế độ phụ trợ
- `checkpoints`, `tasks`: Lưu giữ và in ra tiến trình Vòng Đời Node (Bắt đầu chạy khi nào, kết thúc có lỗi không, mã lỗi...). Cần cắm Checkpointer SQL/Memory.
- `debug`: Cổng xả toàn bộ mọi thể loại Logs (Kết hợp tổng hợp từ checkpoint + tasks + metadata) ra ngoại cảnh.

## 4. Hiện trạng Tích hợp Stream vào SSE tại dự án NLSQL

Dưới tầng Backend (`api/routers/chat.py`), chuỗi tiến trình `astream` được tiêu thụ và format ngược trở lại thành giao thức HTTP Server-Sent Events tuần tự:

1. **Khởi tạo Async Iterator** với mode `updates` và version v2 chuẩn:
   ```python
   async for chunk in graph_app.astream(state, config=config, stream_mode="updates", version="v2"):
   ```
2. **Định Tuyến & Loại bỏ rác**: 
   ```python
   if chunk["type"] == "updates":
       for node_name, state_update in chunk["data"].items():
           # Phát sinh sự kiện event: node_finish ra SSE
   ```
3. **Parse và Tính Toán Thời Gian Vi Mô Tính Từng Node**: 
   Mỗi vòng nhảy Loop For cập nhật tiến độ, hệ thống sẽ chốt Timestamp để tính Delta Duration. Nhờ đó Backend báo về Client con số chính xác để UI in lên log màn hình (Node `schema_agent` tốn `1200ms`, Node `sql_gen_agent` tốn `2400ms`).
4. **Cơ Chế Phun Chữ (Typewriter)**:
   - Hiện tại Backend NLSQL đang kết hợp Mode `updates` chờ Node hoàn tất, lấy toàn bộ Cục Text Answer ra băm thủ công `split(" ")` và xả ngược vào các gói SSE với Event `answer_token`.
   - Cải tiến mở rộng theo Version v2 cho phép sau này chúng ta nhúng mảng `stream_mode=["updates", "messages"]` để hứng chuỗi token tinh tế hơn bắt trực tiếp luồng stream do lõi Models API của Langchain tạo ra.

## 5. Thách thức "Hố Đen Đệm Proxy" (Proxy Buffering Blackhole)

Trong môi trường Backend tiêu chuẩn khi dùng load balancers Docker + Nginx proxy phía trước, giao thức Streaming thường xuyên bị "Nuốt" bởi Middleware:
- **Biểu hiện**: Rõ ràng hệ thống xử lý từng node một, Backend log hoạt động nhảy lách cách từng chút. NHƯNG ở Client Frontend lại im lìm chờ đợi, phải đợi 5 giây mới bụp ra trọn vẹn cả cục Text khổng lồ. (Làm hỏng Real-time UX).
- **Tại sao**: Nginx hay WSGI buffer mặc định 4KB-8KB (cơ chế `proxy_buffering on;` trong Nginx). Nếu dữ liệu nhả ra ít hơn 50 byte, nó ém hàng đóng gói chờ bao giờ tuôn đủ lớn mới Flush đẩy xuống Browser để tiết kiệm gói TCP Network.
- **Biện pháp can thiệp của NLSQL**:
  Tại Router Stream, chúng ta đã hack neo điểm giả bằng `yield event: connected` ở ngay hàng dữ liệu đầu tiên và kích hoạt ép ngắt Sleep bằng `asyncio.sleep(0.05)` bên trong luồng Async của uVicorn. Hành vi này cưỡng bức Kernel TCP xả bộ đệm (Flush Buffer Layer 7 chuncked data block), xé phá tường bảo vệ ngầm của Nginx đẩy dữ liệu thoát ngay ra luồng Browser để duy trì kết nối Stream liên tục.
