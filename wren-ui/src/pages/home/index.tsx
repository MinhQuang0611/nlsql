import { useState, useRef, useEffect } from 'react';
import { Layout, Input, Button, Typography, Space, Spin, Modal, message } from 'antd';
import styled from 'styled-components';
import { Logo } from '@/components/Logo';
import dynamic from 'next/dynamic';
import SiderLayout from '@/components/layouts/SiderLayout';
// Dynamically import ChatChartAnswer to avoid SSR issues with ESM vega-lite/vega-embed
import ChatChartAnswer from '@/components/chart/ChatChartAnswer';
import SendOutlined from '@ant-design/icons/SendOutlined';
import PlusOutlined from '@ant-design/icons/PlusOutlined';
import CopyOutlined from '@ant-design/icons/CopyOutlined';
import CheckOutlined from '@ant-design/icons/CheckOutlined';
import AudioOutlined from '@ant-design/icons/AudioOutlined';
import StopOutlined from '@ant-design/icons/StopOutlined';
import LoadingOutlined from '@ant-design/icons/LoadingOutlined';

const { Content } = Layout;
const { Text, Title, Paragraph } = Typography;

// --- Styled Components (ChatGPT Style) ---

const MainContent = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
`;

const ScrollableContainer = styled.div`
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 32px;
`;

const ChatWindow = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 40px 20px 150px 20px;
  display: flex;
  flex-direction: column;
`;

const MessageRow = styled.div<{ role: 'user' | 'assistant' }>`
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: ${(props) => (props.role === 'user' ? 'flex-end' : 'flex-start')};
`;

const AvatarCircle = styled.div`
  width: 30px;
  height: 30px;
  border-radius: 4px;
  background: var(--gray-3);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
`;

const MessageBubble = styled.div<{ role: 'user' | 'assistant' }>`
  max-width: 100%;
  padding: ${(props) => (props.role === 'user' ? '8px 16px' : '0')};
  background: ${(props) => (props.role === 'user' ? 'var(--gray-2)' : 'transparent')};
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
  color: var(--gray-9);
  white-space: pre-wrap;
`;

const InputStickyFooter = styled.div`
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px;
  background: linear-gradient(transparent, var(--gray-1) 20%);
`;

const InputContainer = styled.div`
  max-width: 800px;
  margin: 0 auto;
  background: var(--white);
  border: 1px solid var(--gray-4);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  padding: 8px 12px;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  transition: border-color 0.2s;

  &:focus-within {
    border-color: var(--red-5);
  }

  @keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.1); opacity: 0.7; }
    100% { transform: scale(1); opacity: 1; }
  }
`;

const CustomTextArea = styled(Input.TextArea)`
  border: none !important;
  box-shadow: none !important;
  resize: none;
  padding: 8px 4px !important;
  font-size: 15px;
`;

const SuggestedQuestionButton = styled(Button)`
  border: 1px solid var(--gray-4);
  font-size: 12px;
  transition: transform 0.2s ease, border-color 0.2s ease;

  &:hover,
  &:focus {
    border: 1px solid var(--red-5) !important;
    transform: translateY(-5px);
  }
`;

const SqlBlock = styled.pre`
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  padding: 16px;
  border-radius: 8px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
  color: #212529;
  margin-top: 12px;
  overflow-x: auto;
  position: relative;
  
  &::before {
    content: "SQL";
    position: absolute;
    top: 4px;
    right: 8px;
    font-size: 10px;
    color: #adb5bd;
    font-weight: bold;
  }
`;

const ThinkingText = styled(Text)`
  font-style: italic;
  color: var(--gray-6);
  
  &::after {
    content: '.';
    display: inline-block;
    animation: ellipsis 1.5s infinite;
    width: 12px;
    text-align: left;
  }

  @keyframes ellipsis {
    0% { content: '.'; }
    33% { content: '..'; }
    66% { content: '...'; }
  }
`;

const ExpandableSql = ({ sql }: { sql: string }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isOverflowing, setIsOverflowing] = useState(false);
  const [copied, setCopied] = useState(false);
  const contentRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (contentRef.current) {
      // Check if content is taller than 80px
      setIsOverflowing(contentRef.current.scrollHeight > 80);
    }
  }, [sql]);

  const onCopy = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    message.success({
      content: 'Đã sao chép SQL vào clipboard!',
      duration: 2,
    });
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ position: 'relative', marginTop: 12 }}>
      <div style={{ position: 'relative' }}>
        <SqlBlock
          ref={contentRef}
          style={{
            maxHeight: isExpanded ? 'none' : '80px',
            overflow: isExpanded ? 'auto' : 'hidden',
            marginBottom: 0,
            paddingRight: '44px', // Space for copy button
            maskImage: (!isExpanded && isOverflowing) ? 'linear-gradient(to bottom, rgba(0,0,0,1) 60%, rgba(0,0,0,0) 100%)' : 'none',
            WebkitMaskImage: (!isExpanded && isOverflowing) ? 'linear-gradient(to bottom, rgba(0,0,0,1) 60%, rgba(0,0,0,0) 100%)' : 'none'
          }}
        >
          {sql}
        </SqlBlock>
        <Button
          type="text"
          size="small"
          className="copy-sql-btn"
          icon={copied ? <CheckOutlined style={{ color: '#52c41a' }} /> : <CopyOutlined />}
          onClick={onCopy}
          style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            zIndex: 2,
            background: 'rgba(255, 255, 255, 0.8)',
            border: '1px solid var(--gray-4)',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s'
          }}
        />
      </div>
      {isOverflowing && (
        <div style={{ textAlign: 'center', marginTop: isExpanded ? 8 : -15, position: 'relative', zIndex: 1 }}>
          <Button
            type="default"
            size="small"
            shape="round"
            onClick={() => setIsExpanded(!isExpanded)}
            style={{
              fontSize: 10,
              background: 'white',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              border: '1px solid var(--gray-4)',
              height: '22px',
              padding: '0 10px',
              color: 'var(--gray-7)'
            }}
          >
            {isExpanded ? 'Thu gọn' : 'Xem toàn bộ SQL'}
          </Button>
        </div>
      )}
    </div>
  );
};




// --- Utility Functions ---

const STORAGE_KEY = 'chat_sessions';

const loadSessions = () => {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? JSON.parse(stored) : {};
};

const saveSessions = (sessions: any) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  window.dispatchEvent(new Event('chat_sessions_updated')); // Trigger sidebar reload
};

export default function Home() {
  const suggestedQuestions = [
    'Tổng số lượng sinh viên hiện tại?',
    'Thống kê sinh viên theo từng ngành học',
    'Danh sách sinh viên đang học',
    'Top 5 ngành học có đông sinh viên nhất'
  ];

  const [sessions, setSessions] = useState<any>({});
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [draftMessages, setDraftMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [availableTables, setAvailableTables] = useState<Record<string, string>>({});
  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [tableModalVisible, setTableModalVisible] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingSTT, setIsProcessingSTT] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Load history and tables on mount
  useEffect(() => {
    const s = loadSessions();
    setSessions(s);

    // Fetch tables
    fetch('/api/v1/tables').then(res => res.json()).then(setAvailableTables);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [sessions, activeSessionId]);

  const activeSession = activeSessionId ? sessions[activeSessionId] : null;
  const chatHistory = activeSession?.messages || draftMessages;

  const createNewChat = () => {
    setActiveSessionId(null);
    setDraftMessages([]);
    setInput('');
  };

  const selectSession = (id: string) => {
    setActiveSessionId(id);
    setDraftMessages([]);
    const s = loadSessions();
    setSessions(s);
  };

  const deleteSession = (id: string) => {
    const updated = { ...sessions };
    delete updated[id];
    setSessions(updated);
    saveSessions(updated);
    if (activeSessionId === id) {
      const keys = Object.keys(updated);
      if (keys.length > 0) setActiveSessionId(keys[0]);
      else {
        setActiveSessionId(null);
        setDraftMessages([]);
      }
    }
  };

  const updateSessionMessages = (id: string, messages: any[], title?: string) => {
    const currentSessions = loadSessions();
    if (!currentSessions[id]) return;

    currentSessions[id].messages = messages;
    currentSessions[id].updatedAt = Date.now();
    if (title) currentSessions[id].title = title;

    setSessions({ ...currentSessions });
    saveSessions(currentSessions);
  };

  // --- STT Logic ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        await uploadAudio();
      };
      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Microphone error:', err);
      message.error('Không thể truy cập micro. Vui lòng kiểm tra quyền trình duyệt.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setIsProcessingSTT(true);
  };

  const uploadAudio = async () => {
    const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
    const ext = mimeType.includes('ogg') ? 'ogg' : mimeType.includes('mp4') ? 'mp4' : 'webm';
    const blob = new Blob(audioChunksRef.current, { type: mimeType });
    const formData = new FormData();
    formData.append('file', blob, `recording.${ext}`);
    formData.append('webhook_url', 'http://localhost/noop');

    const STT_ENDPOINT = 'https://zenify-stt.ript.vn/api/v1/stt/zipformer';
    try {
      const res = await fetch(STT_ENDPOINT, { method: 'POST', body: formData });
      if (!res.ok) throw new Error(`STT upload failed: ${res.status}`);
      const data = await res.json();
      if (!data.job_id) throw new Error('No job_id in response');
      await pollSttStatus(data.job_id);
    } catch (err) {
      console.error('STT error:', err);
      message.error('Lỗi khi nhận dạng giọng nói. Vui lòng thử lại.');
      setIsProcessingSTT(false);
    }
  };

  const pollSttStatus = async (jobId: string) => {
    const POLL_INTERVAL_MS = 1500;
    const POLL_TIMEOUT_MS = 60000;
    const STT_STATUS_ENDPOINT = 'https://zenify-stt.ript.vn/api/v1/stt/zipformer/status';
    const deadline = Date.now() + POLL_TIMEOUT_MS;

    while (Date.now() < deadline) {
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
      try {
        const res = await fetch(`${STT_STATUS_ENDPOINT}/${jobId}`);
        if (!res.ok) throw new Error(`Status check failed: ${res.status}`);
        const data = await res.json();
        const status = (data.status || '').toLowerCase();
        if (status === 'success') {
          const transcript = data.transcription?.toLowerCase() || '';
          if (transcript) {
            setInput(prev => (prev ? `${prev} ${transcript}` : transcript));
            message.success('Đã nhận dạng giọng nói thành công!');
          } else {
            message.warning('Không nhận dạng được nội dung. Vui lòng thử lại.');
          }
          setIsProcessingSTT(false);
          return;
        } else if (status === 'failed' || status === 'error' || status === 'cancelled') {
          throw new Error(`STT job ${status}`);
        }
      } catch (pollErr) {
        console.error('Poll error:', pollErr);
        message.error('Lỗi khi kiểm tra kết quả nhận dạng.');
        setIsProcessingSTT(false);
        return;
      }
    }
    message.error('Hết thời gian chờ nhận dạng giọng nói. Vui lòng thử lại.');
    setIsProcessingSTT(false);
  };



  const sendMessage = async (text?: string) => {
    const query = text || input.trim();
    if (!query) return;
    if (!text) setInput('');

    const isDraftMode = !activeSessionId;
    const newMessages = [...chatHistory, { role: 'user', content: query }];

    // Auto-title if it's the first message
    let title = activeSession?.title || 'New Chat';
    if (chatHistory.length === 0) title = query.length > 30 ? query.substring(0, 30) + '...' : query;

    if (isDraftMode) {
      setDraftMessages(newMessages);
    } else {
      updateSessionMessages(activeSessionId, newMessages, title);
    }
    setLoading(true);

    const defaultEndpoint = typeof window !== 'undefined' ? localStorage.getItem('chat_api_endpoint') || '/api/v1/chat' : '/api/v1/chat';
    const endpoint = selectedTables.length > 0 ? defaultEndpoint.replace('/chat', '/chat_with_table') : defaultEndpoint;
    const requestSessionId = activeSessionId || `draft-${Date.now()}`;
    const body: any = {
      query: query,
      session_id: requestSessionId,
      history: newMessages.filter(m => m.role !== 'system'),
      num_recommend: 3
    };
    if (selectedTables.length > 0) {
      body.selected_tables = selectedTables;
    }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();

      const aiMsg = {
        role: 'assistant',
        content: data.error ? `❌ Error: ${data.error}` : data.answer,
        sql: data.sql,
        data: data.data,
        chart_config: data.chart_config,
        recommend_questions: data.recommend_questions,
        execution_time_ms: data.execution_time_ms,
        slowest_node: data.slowest_node,
        id: `ai-${Date.now()}`
      };

      if (!data.error && isDraftMode) {
        const newSessionId = `session-${Date.now()}`;
        const newSession = {
          id: newSessionId,
          title,
          messages: [...newMessages, aiMsg],
          updatedAt: Date.now(),
        };
        const updated = { ...loadSessions(), [newSessionId]: newSession };
        setSessions(updated);
        saveSessions(updated);
        setActiveSessionId(newSessionId);
        setDraftMessages([]);
      } else if (isDraftMode) {
        setDraftMessages([...newMessages, aiMsg]);
      } else {
        updateSessionMessages(activeSessionId, [...newMessages, aiMsg]);
      }
    } catch (e) {
      const errorMessage = {
        role: 'assistant',
        content: '❌ Connection error.',
      };
      if (isDraftMode) {
        setDraftMessages([...newMessages, errorMessage]);
      } else {
        updateSessionMessages(activeSessionId, [...newMessages, errorMessage]);
      }
    } finally {
      setLoading(false);
    }
  };

  const sidebarProps = {
    isHistoryMode: true,
    activeSessionId,
    onSelectSession: selectSession,
    onNewChat: createNewChat,
    onDeleteSession: deleteSession,
  } as any;

  return (
    <SiderLayout loading={false} sidebar={sidebarProps}>
      <MainContent>
        <ChatWindow>
          <ScrollableContainer>
            {chatHistory.length === 0 && (
              <div className="d-flex align-center justify-center flex-column" style={{ height: '70vh', marginTop: '10vh' }}>
                <Logo size={80} color="var(--gray-3)" />
                <Title level={3} className="mt-6">Xin chào! Tôi có thể giúp gì cho bạn</Title>
                <Space wrap size="small" style={{ marginTop: 12, justifyContent: 'center' }}>
                  {suggestedQuestions.map((question) => (
                    <SuggestedQuestionButton
                      key={question}
                      size="small"
                      shape="round"
                      disabled={loading}
                      onClick={() => sendMessage(question)}
                    >
                      {question}
                    </SuggestedQuestionButton>
                  ))}
                </Space>
              </div>
            )}

            {chatHistory.map((msg: any, idx: number) => (
              <MessageRow key={idx} role={msg.role}>
                {msg.role === 'assistant' && (
                  <AvatarCircle>
                    <Logo size={18} />
                  </AvatarCircle>
                )}
                <MessageBubble role={msg.role}>
                  {msg.role === 'assistant' ? (
                    <div dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>') }} />
                  ) : (
                    msg.content
                  )}

                  {msg.sql && (
                    <ExpandableSql sql={msg.sql} />
                  )}

                  {msg.data && msg.data.length > 0 && (
                    <ChatChartAnswer
                      chartConfig={msg.chart_config || {}}
                      data={msg.data}
                    />
                  )}

                  {msg.execution_time_ms !== undefined && (
                    <div style={{ marginTop: 8, fontSize: 11, color: 'var(--gray-6)', textAlign: 'right' }}>
                      ⚡ Execution: {msg.execution_time_ms.toFixed(0)}ms
                      {msg.slowest_node && ` | Slowest: ${msg.slowest_node}`}
                    </div>
                  )}

                  {msg.recommend_questions && (
                    <Space wrap className="mt-6" size="small">
                      {msg.recommend_questions.map((q: string, qidx: number) => (
                        <Button key={qidx} size="small" shape="round" onClick={() => sendMessage(q)} style={{ borderColor: 'var(--gray-4)', fontSize: 12 }}>{q}</Button>
                      ))}
                    </Space>
                  )}
                </MessageBubble>
              </MessageRow>
            ))}
            {loading && (
              <MessageRow role="assistant">
                <div className='chatbot-typing-dots' aria-label='Đang phản hồi'>
                  <span />
                  <span />
                  <span />
                </div>
                <ThinkingText>Thinking</ThinkingText>
              </MessageRow>
            )}
            <div ref={chatEndRef} />
          </ScrollableContainer>
        </ChatWindow>

        <InputStickyFooter>
          <InputContainer>
            <Button
              type="text"
              icon={<PlusOutlined style={{ color: "#000" }} />}
              onClick={() => setTableModalVisible(true)}
              style={{
                fontSize: 12,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {/* {selectedTables.length > 0 ? `${selectedTables.length} Tables` : 'Context'} */}
            </Button>
            <CustomTextArea
              placeholder="Ask anything..."
              style={{ color: "#000" }}
              autoSize={{ minRows: 1, maxRows: 6 }}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              disabled={loading}
            />
            <Button
              type="text"
              icon={isProcessingSTT ? <LoadingOutlined /> : (isRecording ? <StopOutlined style={{ color: 'var(--red-5)' }} /> : <AudioOutlined style={{ color: isRecording || isProcessingSTT ? 'var(--red-5)' : 'var(--red-5)', opacity: loading ? 0.5 : 1 }} />)}
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessingSTT || loading}
              style={{
                fontSize: 18,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '8px',
                padding: '4px',
                animation: isRecording ? 'pulse 1.5s infinite' : 'none',
                background: isRecording ? 'rgba(230, 57, 70, 0.1)' : 'transparent',
                color: 'var(--red-5)'
              }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => sendMessage()}
              loading={loading}
              disabled={!input.trim() || loading}
              style={{ borderRadius: '8px' }}
            />
          </InputContainer>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 12 }}>
            <img src="/images/ript-logo.png" style={{ height: 20, width: 'auto' }} alt="RIPT Logo" />
            <Text type="secondary" style={{ fontSize: 13, color: "#32057aff" }}>
              Powered by RIPT.
            </Text>
          </div>
        </InputStickyFooter>

        <Modal
          title="Select Database Context"
          visible={tableModalVisible}
          onOk={() => setTableModalVisible(false)}
          onCancel={() => setTableModalVisible(false)}
          width={600}
        >
          <div style={{ marginBottom: 12 }}>
            <Text type="secondary">Limit the AI's search to specific tables for more accurate results.</Text>
          </div>
          <div style={{ maxHeight: 400, overflowY: 'auto' }}>
            {Object.entries(availableTables).map(([name, desc]) => (
              <div
                key={name}
                onClick={() => {
                  setSelectedTables(prev =>
                    prev.includes(name) ? prev.filter(t => t !== name) : [...prev, name]
                  );
                }}
                style={{
                  padding: '10px 12px',
                  marginBottom: 4,
                  borderRadius: 8,
                  cursor: 'pointer',
                  border: '1px solid',
                  borderColor: selectedTables.includes(name) ? 'var(--blue-5)' : 'var(--gray-3)',
                  background: selectedTables.includes(name) ? 'var(--blue-1)' : 'transparent',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12
                }}
              >
                <input type="checkbox" checked={selectedTables.includes(name)} readOnly />
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{name}</div>
                  <div style={{ fontSize: 11, color: 'var(--gray-7)' }}>{desc || 'No description available'}</div>
                </div>
              </div>
            ))}
          </div>
        </Modal>
      </MainContent>
    </SiderLayout>
  );
}
