import React, { useEffect, useState } from 'react';
import { Row, Col, Form, Switch, Typography } from 'antd';

const { Text } = Typography;

export default function ChatSettings() {
  const [form] = Form.useForm();
  const [streamingMode, setStreamingMode] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('streaming_mode') === 'true';
    setStreamingMode(stored);
    form.setFieldsValue({ streamingMode: stored });
  }, [form]);

  const onSwitchChange = (checked: boolean) => {
    localStorage.setItem('streaming_mode', checked ? 'true' : 'false');
    setStreamingMode(checked);
    // Dispatch event to notify other components if needed
    window.dispatchEvent(new Event('storage_settings_updated'));
  };

  return (
    <div className="py-3 px-4">
      <Form
        form={form}
        layout="vertical"
        initialValues={{ streamingMode }}
      >
        <Form.Item
          label="Chế độ Streaming"
          extra="Khi bật, AI sẽ trả về kết quả từng bước một cách trực quan hơn thay vì đợi toàn bộ câu trả lời hoàn tất."
        >
          <Row gutter={16} align="middle" wrap={false}>
            <Col className="flex-grow-1">
              <Text type="secondary">Sử dụng API streaming (SSE)</Text>
            </Col>
            <Col>
              <Form.Item name="streamingMode" valuePropName="checked" noStyle>
                <Switch onChange={onSwitchChange} />
              </Form.Item>
            </Col>
          </Row>
        </Form.Item>
      </Form>
    </div>
  );
}
