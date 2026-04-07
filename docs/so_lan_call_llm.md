Viewed builder.py:1-146
Searched for "\.ainvoke"
Searched for "ChatOpenAI"
Searched for "ainvoke"
Searched for "_llm"
Viewed knowledge_agent.py:1-196
Viewed chart_agent.py:1-178
Viewed answer_agent.py:1-123

Dựa trên việc kiểm tra toàn bộ pipeline LangGraph của hệ thống (`graph/builder.py` và các agent), mức độ sử dụng LLM phụ thuộc vào loại câu hỏi (`intent`). Dưới đây là số lần gọi API của LLM chi tiết cho từng tác vụ:

### 1. Luồng chính (Truy vấn Data / Vẽ biểu đồ): **6 Lần**
Đây là luồng tốn kém nhất và đầy đủ nhất (`intent == "data_query"` hoặc `"chart_request"`). Trật tự gọi LLM như sau:
1. **Intent Agent (1 lần):** Gọi LLM để gom nhóm câu hỏi thuộc thể loại nào.
2. **SQL Plan Agent (1 lần):** Dựa vào Schema và Kiến thức Nghiệp vụ để lập luận logic các mệnh đề (WHERE, GROUP BY,...).
3. **SQL Gen Agent (1 lần):** Sinh câu lệnh SQL thực tế dựa trên plan.
4. **SQL Check Agent (1 lần):** LLM làm nhiệm vụ Security/Syntax validator kiểm tra xem SQL có chuẩn Postgres/ClickHouse không. *(Lưu ý: Nếu có lỗi SQL và retry, sẽ tốn thêm 2 lần gọi / 1 vòng lặp)*.
5. **Chart Agent (1 lần):** Nhìn vào dữ liệu bảng kết quả từ Database và cấu hình biểu đồ (Trục X, trục Y, chart_type).
6. **Answer Agent (1 lần):** Đọc dữ liệu preview 10 dòng và sinh ra text giải thích thân thiện cho người dùng.

> 👉 **Kết luận:** Một câu query Data mượt mà hoàn hảo mất đúng **6 lượt LLM calls**. (Schema Agent và Executor Agent không gọi LLM).

--

### 2. Luồng truy vấn nghiệp vụ kết hợp số liệu (`domain_query`): **6 lần**
Cách đi đồ thị tương tự như luồng Data Query, nhưng nó rẽ qua `knowledge_agent` trước (node này lúc này đóng vai trò Vector Search DB tìm kiến thức, nên không tốn lượt gửi LLM nào), sau đó lại đẩy qua SQL Plan Agent để code. Do đó chi phí bằng **6 lần**.

--

### 3. Luồng hỏi đáp lý thuyết thuần tuý (`knowledge_query`): **Đang mất 3 lần ⚠️**
Luồng này thực chất không chọc xuống Database, ý định của kiến trúc là để trả lời chay. Tuy nhiên hiện tại có một chỗ lãng phí:
- **Intent Agent**: mất 1 lần.
- **Knowledge Agent**: mất 1 lần để LLM tổng hợp tài liệu từ Qdrant và ra câu trả lời.
- **Answer Agent**: Khi luồng chạy tới cuối, file `answer_agent.py` đang quên đoạn mã rẽ nhánh cho `knowledge_query` khiến nó ngầm gửi lại văn bản lên LLM 1 lần nữa để xin "tóm tắt".
> *(Đáng ra luồng này chỉ mất 2 lần gọi LLM)*

--

### 4. Bắt lỗi hoặc phân loại (`ambiguous` / Lạc đề / Chào hỏi)
- **Câu hỏi mập mờ thiếu ý (`ambiguous`)**: Mất **2 lần** (1 lần phân loại Intent, 1 lần ở Clarification Agent để hỏi vặn lại user).
- **Câu hỏi Rác/Lạc đề (`out_of_scope`), Chào hỏi (`greeting`), Hỏi cấu trúc CSDL (`schema_question`)**: Chỉ mất **1 lần** ở node Intent ban đầu, sau đó Answer Agent sẽ nhả ra text fix-cứng bằng if-else mà không gọi LLM nữa.