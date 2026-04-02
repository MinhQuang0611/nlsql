import { useState, useRef, useEffect } from 'react';
import { Layout, Input, Button, Typography, Space, Spin, Modal } from 'antd';
import styled from 'styled-components';
import { Logo } from '@/components/Logo';
import dynamic from 'next/dynamic';
import SiderLayout from '@/components/layouts/SiderLayout';
// Dynamically import ChatChartAnswer to avoid SSR issues with ESM vega-lite/vega-embed
const ChatChartAnswer = dynamic(() => import('@/components/chart/ChatChartAnswer'), { ssr: false });
import SendOutlined from '@ant-design/icons/SendOutlined';
import PlusOutlined from '@ant-design/icons/PlusOutlined';

const { Content } = Layout;
const { Text, Title, Paragraph } = Typography;

// --- Styled Components (ChatGPT Style) ---

const MainContent = styled.div`
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
`;

const ChatWindow = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 40px 20px 100px 20px;
  display: flex;
  flex-direction: column;
  gap: 32px;
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

    const endpoint = selectedTables.length > 0 ? '/api/v1/chat_with_table' : '/api/v1/chat';
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
          {chatHistory.length === 0 && (
            <div className="d-flex align-center justify-center flex-column" style={{ height: '100%', marginTop: '10vh' }}>
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
                  <SqlBlock>{msg.sql}</SqlBlock>
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
              <Text type="secondary" italic>Thinking...</Text>
            </MessageRow>
          )}
          <div ref={chatEndRef} />
        </ChatWindow>

        <InputStickyFooter>
          <InputContainer>
              <Button
                type="text"
                icon={<PlusOutlined style={{ color: "#000"}}/>}
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
              style={{ color: "#000"}}
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
              type="primary"
              icon={<SendOutlined />}
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              style={{ borderRadius: '8px' }}
            />
          </InputContainer>
          <div style={{ textAlign: 'center', marginTop: 12 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              Experimental AI. Check important info.
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
