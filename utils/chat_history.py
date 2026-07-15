def format_history(history: list[dict], max_len: int = 8) -> str:
    """
    Chuyển list history [{"role": ..., "content": ...}] thành chuỗi dễ đọc cho LLM.
    Sử dụng Sliding Window để chỉ lấy `max_len` tin nhắn gần nhất.
    Hỗ trợ thêm SQL và Intent để AI bám sát ngữ cảnh.
    """
    if not history:
        return "(Không có lịch sử hội thoại)"
    
    # Sliding window: lấy 8 tin nhắn gần nhất
    truncated_history = history[-max_len:]
    
    lines = []
    for msg in truncated_history:
        role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
        content = msg.get("content", "")
        sql = msg.get("sql")
        intent = msg.get("intent")
        
        # Tạo dòng cơ bản: Người dùng: nội dung
        line = f"{role}: {content}"
        
        # Nếu là trợ lý, bổ sung thêm ý định và SQL (nếu có) để AI hiểu ngữ cảnh cũ
        if role == "Trợ lý":
            extra_info = []
            if intent:
                extra_info.append(f"Ý định: {intent}")
            if sql:
                extra_info.append(f"SQL đã dùng:\n```sql\n{sql}\n```")
            
            if extra_info:
                line += "\n  " + "\n  ".join(extra_info)
        
        lines.append(line)
        
    return "\n\n".join(lines)
