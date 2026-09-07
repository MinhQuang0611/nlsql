# Tài liệu API Chat Streaming (SSE)

Tài liệu này mô tả chi tiết các endpoint và luồng dữ liệu (data flow) mới nhất của tính năng Chat Streaming trong hệ thống NLSQL. Tính năng này cung cấp trải nghiệm theo thời gian thực (real-time) giúp giao diện người dùng hiển thị từng bước suy luận của AI và nội dung câu trả lời dưới dạng "typewriter" (gõ chữ) ngay lập tức.

## 1. Các Endpoints Hỗ trợ Streaming

| Endpoint | Giao thức | Chức năng | 
| :--- | :---: | :--- | 
| `POST /chat/stream` | SSE | Stream chung các nghiệp vụ (General) | 
| `POST /qldt/chat/stream` | SSE | Stream dành riêng cho luồng Quản lý đào tạo (QLDT) | 
| `POST /tcns/chat/stream` | SSE | Stream dành riêng cho luồng Tổ chức nhân sự (TCNS) | 

*Lưu ý: Header yêu cầu phía client cần chuẩn bị cơ chế đọc `text/event-stream`.*

## 2. Các Loại Sự Kiện (Events) Trả Về

Luồng Stream (Server-Sent Events) bao gồm 5 loại sự kiện theo đúng thứ tự chu kỳ sống của một quy trình truy vấn. Dưới đây là chi tiết luồng Data Pushed từ Backend ra Client:

### 2.1. Sự kiện `connected`
- **Thời điểm**: Được gửi trút xuống ngay lập tức trong 50ms đầu tiên khi kết nối được mở.
- **Mục đích**: Preamble bypass cơ chế đệm (buffering) của proxy (như Nginx, Next.js proxy), báo hiệu kết nối SSE đã sẵn sàng.
```json
{
  "event": "connected"
}
```

### 2.2. Sự kiện `node_finish`
- **Thời điểm**: Gửi liên tục mỗi khi một Agent (Node) trong LangGraph hoàn thành xong task của mình.
- **Mục đích**: Báo cáo tiến trình hệ thống để Client vẽ giao diện (ví dụ: hiển thị "Loading Schema...", "Generating SQL...", "Executing..."), kèm thời gian xử lý thực của node đó.
```json
{
  "event": "node_finish",
  "node": "schema",
  "execution_time_ms": 1250.5,
  "state_update": { "relevant_tables": "..." }
}
```

### 2.3. Sự kiện `answer_token`
- **Thời điểm**: Được gửi tự động sau khi tất cả các Node Graph đã chạy xong và hệ thống chốt xong biến text `answer`.
- **Mục đích**: Băm nhỏ text (bởi token hoặc khoảng trắng word-by-word) đẩy dần về client để tạo hiệu ứng "gõ phím" (Typewriter effect) trực tiếp trên Client thay vì đợi gom cả mảng lớn.
```json
{
  "event": "answer_token",
  "token": "Dưới "
}
```

### 2.4. Sự kiện `final_result`
- **Thời điểm**: Được gửi vào bước cuối cùng (Last chunk) trước khi luồng stream kết thúc mở ngỏ.
- **Mục đích**: Đóng gói toàn bộ đối tượng `ChatResponse` bản Final (Bao gồm nội dung chốt, lệnh SQL, mảng dữ liệu JSON Data thô, cấu hình biểu đồ `chart_config`, và `recommend_questions`). Đây là payload để client render Table và Biểu đồ.
```json
{
  "event": "final_result",
  "data": {
    "answer": "...",
    "sql": "SELECT * ...",
    "data": [...],
    "chart_config": {...},
    "recommend_questions": [...],
    "execution_time_ms": 4500
  }
}
```

### 2.5. Sự kiện `error`
- **Thời điểm**: Khi quá trình thực thi bị văng lỗi đứt gãy không mong muốn.
```json
{
  "event": "error",
  "detail": "Nội dung Exception chi tiết..."
}
```

## 3. Kiến Trúc Luồng Xử Lý Nội Bộ API

Hoạt động diễn ra bên trong luồng `_process_chat_stream` ở `chat.py` đi theo trình tự:
1. **Preamble Stream**: Trả trước `event: connected` nhanh để giữ luồng.
2. **Thiết lập DB (Sync)**: Lưu thông tin Context Session / User message object mới vào PostgreSQL ngay cho phiên lưu trữ. 
3. **Trigger LangGraph v2 Updates Stream**: Kích hoạt `graph.astream` với `stream_mode="updates"`. Lắng nghe và yield liên tục `node_finish` ra với độ trễ cực nhỏ ngay sau mỗi step hoàn tất thay vì buffer gom nhóm.
4. **Sinh Gợi Ý Song Song**: Chạy tác vụ (Background Asnyc Task) gọi LLM sinh và đoán `recommend_questions` ngay trong lúc luồng đang chuẩn bị nạp stream văn bản.
5. **Streaming Typewriter Text**: Băm nhỏ chuỗi văn bản (`response.answer.split(' ')`) và yield lên Client bằng sự kiện `event: answer_token`. Đạt được Real-time cho văn bản chữ.
6. **Đóng Gói & Push Final Response**: Render ra `event: final_result` chứa các cục metadata JSON to lớn (Chart, Table).
7. **Hậu Kỳ (Background Tasks)**: Lưu dòng tin nhắn kết quả vào DB nội bộ và gửi log report qua Google Sheets một cách âm thầm (Không can thiệp đến thời gian load của Client).

## 4. Ví dụ Code Tích Hợp (Client Implementation)

Dưới đây là đoạn code mẫu bằng **JavaScript/TypeScript** sử dụng Fetch API tiêu chuẩn để đọc mảng byte trả về. Bạn có thể sử dụng trực tiếp trong Frontend (React/Vue/Next.js) mà không cần dùng thêm thư viện bên ngoài:

```javascript
async function fetchChatStreaming(query, sessionId, history = []) {
  try {
    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream' // Bắt buộc cho SSE
      },
      body: JSON.stringify({
        query: query,
        session_id: sessionId,
        history: history,
        num_recommend: 3
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Khởi tạo Reader từ luồng
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      // Giải mã mảng byte thành chuỗi
      buffer += decoder.decode(value, { stream: true });
      
      // Các chunk SSE được phân tách bằng 2 dòng trống \n\n
      const lines = buffer.split('\n\n'); 
      buffer = lines.pop(); // Giữ lại luồng cut dở dang (nằm ở đuôi mảng) để dồn vào chunk kế

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const rawData = line.substring(6).trim(); // Cắt bỏ "data: "
          if (!rawData) continue;

          try {
            const parsed = JSON.parse(rawData);

            // Bắt sự kiện rẽ nhánh Logic
            switch (parsed.event) {
              case 'connected':
                console.log('🔗 Đã kết nối đến luồng suy luận của AI!');
                break;
              
              case 'node_finish':
                // Update UI: Ví dụ "Đang chạy Node: schema (123ms)"
                console.log(`⏳ [${parsed.node}] Hoàn tất xử lý (${parsed.execution_time_ms}ms)`);
                break;

              case 'answer_token':
                // Hiệu ứng Typewriter: Nối từng chữ một và render UI
                // document.getElementById('chat-box').innerHTML += parsed.token;
                process.stdout.write(parsed.token); 
                break;

              case 'final_result':
                console.log('\n\n✅ Đã nhận được toàn bộ gói Data Result:', parsed.data);
                // Update UI toàn diện: Parse Table, Vẽ Chart (parsed.data.chart_config)
                break;

              case 'error':
                console.error('❌ Lỗi từ luồng hệ thống:', parsed.detail);
                break;
            }
          } catch (e) {
            console.error('Có lỗi khi gỡ lỗi chunk JSON cục bộ:', e);
          }
        }
      }
    }
  } catch (error) {
    console.error('Lỗi khi fetch stream API:', error);
  }
}

// Bắt đầu chạy test thử
// fetchChatStreaming('Top 5 chi nhánh cao nhất', 'session-demo-123');
```

## 5. Ví dụ Code Kiến Trúc Luồng Backend (Python / FastAPI + LangGraph)

Dưới đây là phiên bản lược giản (pseudo-implementation) cách Backend thiết lập `FastAPI StreamingResponse` kết hợp hàm `astream` của LangGraph để đẩy từng sự kiện xuống luồng SSE:

```python
import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

async def _process_chat_stream(initial_state: dict):
    # 1. Preamble nhanh nhất để Bypass Buffering & Báo hiệu kết nối
    yield f"data: {json.dumps({'event': 'connected'})}\n\n"
    await asyncio.sleep(0.05)

    graph_app = get_graph_app() # Khai báo hệ thống luồng AI
    config = {"configurable": {"thread_id": initial_state.get("session_id")}}
    final_state = initial_state.copy()

    try:
        # 2. Async Loop đọc LangGraph Stream. Bật version="v2" để trả từng Node Update
        async for chunk in graph_app.astream(initial_state, config=config, stream_mode="updates", version="v2"):
            if chunk["type"] != "updates":
                continue

            for node_name, state_update in chunk["data"].items():
                final_state.update(state_update)

                # Emit sự kiện node_finish đẩy về Frontend kèm phần state được cập nhật
                yield f"data: {json.dumps({'event': 'node_finish', 'node': node_name})}\n\n"
                await asyncio.sleep(0.05)

        # 3. Khi Graph Done: Băm văn bản để mô phỏng Gõ Chữ (Typewriter)
        if final_state.get("answer"):
            words = final_state["answer"].split(" ")
            for i, word in enumerate(words):
                padding = ' ' if i < len(words) - 1 else ''
                yield f"data: {json.dumps({'event': 'answer_token', 'token': word + padding})}\n\n"
                await asyncio.sleep(0.03)

        # 4. Gắn các object nặng (Data, SQL, Config Bảng Biểu, Gợi ý Câu hỏi) vào Final_Result
        final_payload = {
            "answer": final_state.get("answer"),
            "sql": final_state.get("final_sql"),
            "data": final_state.get("query_result", []),
            "chart_config": final_state.get("chart_config")
        }
        
        yield f"data: {json.dumps({'event': 'final_result', 'data': final_payload})}\n\n"

        # (Phần hậu kỳ: Tiến hành Async Lưu DB / Logging ở Background)

    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'detail': str(e)})}\n\n"

@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    # Pass Data khởi tạo vào Stream Response
    initial_state = {"user_query": request.query, "session_id": request.session_id}
    
    return StreamingResponse(
        _process_chat_stream(initial_state),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )
```
