import React, { useState, useEffect } from 'react';
import { Form, Radio, Button, message } from 'antd';

export default function DataSourceSettings() {
  const [endpoint, setEndpoint] = useState('/api/v1/chat');

  useEffect(() => {
    const saved = localStorage.getItem('chat_api_endpoint');
    if (saved) {
      setEndpoint(saved);
    }
  }, []);

  const handleSave = () => {
    localStorage.setItem('chat_api_endpoint', endpoint);
    message.success('Cập nhật nguồn dữ liệu thành công!');
    // Tải lại cửa sổ (hoặc reload biến cục bộ) để reset session hiện tại (Tùy chọn)
  };

  return (
    <div className="py-3 px-4">
      <div className="mb-4 text-gray-7">
        Vui lòng chọn phạm vi dữ liệu mà Trợ lý ảo sẽ xem xét khi trả lời các câu lệnh truy vấn của bạn.
      </div>
      <Form layout="vertical">
        <Form.Item label="Chọn phạm vi dữ liệu:">
          <Radio.Group 
            value={endpoint} 
            onChange={(e) => setEndpoint(e.target.value)}
            style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
          >
            <Radio value="/api/v1/chat">
              <span className="text-bold">Toàn bộ dữ liệu</span> 
              <div className="gray-6 text-sm">Hỏi đáp đa lĩnh vực trên toàn bộ hệ thống (Mặc định).</div>
            </Radio>
            <Radio value="/api/v1/qldt/chat">
              <span className="text-bold">Dữ liệu Quản lý đào tạo</span>
              <div className="gray-6 text-sm">Giới hạn tìm kiếm chuyên sâu trong mảng đào tạo, sinh viên...</div>
            </Radio>
            <Radio value="/api/v1/tcns/chat">
              <span className="text-bold">Dữ liệu Tổ chức nhân sự</span>
              <div className="gray-6 text-sm">Giới hạn tìm kiếm kết quả cho cán bộ nhân sự, giảng viên.</div>
            </Radio>
          </Radio.Group>
        </Form.Item>
        <div className="py-2 text-right mt-6">
          <Button type="primary" onClick={handleSave} style={{ width: 120 }}>
            Lưu cài đặt
          </Button>
        </div>
      </Form>
    </div>
  );
}
