import { useEffect } from 'react';
import { Button, Form, Input, Modal, Row, Col, Radio } from 'antd';
import DeleteOutlined from '@ant-design/icons/DeleteOutlined';
import PlusOutlined from '@ant-design/icons/PlusOutlined';
import { isEmpty } from 'lodash';
import { FORM_MODE } from '@/utils/enum';
import { ERROR_TEXTS } from '@/utils/error';
import { ModalAction } from '@/hooks/useModalAction';
import { Instruction } from '@/apollo/client/graphql/__types__';

const MAX_QUESTIONS = 100;

type Props = ModalAction<Instruction> & {
  loading?: boolean;
};

export default function InstructionModal(props: Props) {
  const { defaultValue, formMode, loading, onClose, onSubmit, visible } = props;

  const isCreateMode = formMode === FORM_MODE.CREATE;

  const [form] = Form.useForm();
  const isDefault = Form.useWatch('isDefault', form);

  useEffect(() => {
    if (visible) {
      form.setFieldsValue({
        isDefault: isEmpty(defaultValue) ? true : defaultValue.isDefault,
        instruction: defaultValue?.instruction,
        questions: defaultValue?.questions,
      });
    }
  }, [visible, defaultValue]);

  const onSubmitButton = () => {
    form
      .validateFields()
      .then(async (values) => {
        const data = {
          isDefault: values.isDefault,
          instruction: values.instruction,
          questions: values?.questions || [],
        };
        await onSubmit({ data, id: defaultValue?.id });
        onClose();
      })
      .catch(console.error);
  };

  return (
    <Modal
      title={`${isCreateMode ? 'Thêm' : 'Cập nhật'} hướng dẫn`}
      centered
      closable
      confirmLoading={loading}
      destroyOnClose
      maskClosable={false}
      onCancel={onClose}
      visible={visible}
      width={720}
      cancelButtonProps={{ disabled: loading }}
      okText="Gửi"
      onOk={onSubmitButton}
      afterClose={() => form.resetFields()}
    >
      <Form form={form} preserve={false} layout="vertical">
        <Form.Item
          label="Chi tiết hướng dẫn"
          name="instruction"
          rules={[
            {
              required: true,
              message: ERROR_TEXTS.INSTRUCTION.DETAILS.REQUIRED,
            },
          ]}
        >
          <Input.TextArea
            autoFocus
            placeholder="Nhập quy tắc mà Wren AI nên tuân theo khi tạo truy vấn SQL."
            maxLength={1000}
            rows={3}
            showCount
          />
        </Form.Item>
        <Form.Item
          label="Áp dụng hướng dẫn cho"
          name="isDefault"
          required={false}
          rules={[
            {
              required: true,
              message: ERROR_TEXTS.INSTRUCTION.IS_DEFAULT_GLOBAL.REQUIRED,
            },
          ]}
          extra={
            <>
              Chọn xem hướng dẫn này áp dụng cho{' '}
              <span className="gray-7">tất cả truy vấn</span> hoặc{' '}
              <span className="gray-7">
                chỉ khi phát hiện các câu hỏi người dùng tương tự
              </span>
              .
            </>
          }
        >
          <Radio.Group>
            <Radio.Button value={true}>
              Toàn cục (áp dụng cho tất cả câu hỏi)
            </Radio.Button>
            <Radio.Button value={false}>
              Khớp với các câu hỏi cụ thể
            </Radio.Button>
          </Radio.Group>
        </Form.Item>
        {!isDefault && (
          <Form.Item
            label="Các câu hỏi phù hợp"
            required
            extra="Wren AI sẽ khớp các truy vấn của người dùng dựa trên sự tương đồng và áp dụng hướng dẫn này khi phù hợp."
          >
            <Form.List name="questions" initialValue={['']}>
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Row key={key} wrap={false} gutter={8} className="my-2">
                      <Col flex="1 0">
                        <Form.Item
                          {...restField}
                          name={name}
                          required
                          className="mb-2"
                          style={{ width: '100%' }}
                          rules={[
                            {
                              required: true,
                              whitespace: true,
                              message:
                                ERROR_TEXTS.INSTRUCTION.QUESTIONS.REQUIRED,
                            },
                          ]}
                        >
                          <Input
                            placeholder="Nhập một câu hỏi ví dụ để kích hoạt hướng dẫn này."
                            maxLength={100}
                            showCount
                          />
                        </Form.Item>
                      </Col>
                      <Col flex="none" className="p-1">
                        <Button
                          onClick={() => remove(name)}
                          disabled={fields.length <= 1}
                          icon={<DeleteOutlined />}
                          size="small"
                          style={{ border: 'none' }}
                          className="bg-gray-1"
                        />
                      </Col>
                    </Row>
                  ))}
                  <Form.Item noStyle>
                    <Button
                      type="dashed"
                      onClick={() => add()}
                      block
                      icon={<PlusOutlined />}
                      disabled={fields.length >= MAX_QUESTIONS}
                      className="mb-1"
                    >
                      Thêm câu hỏi
                    </Button>
                  </Form.Item>
                </>
              )}
            </Form.List>
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}