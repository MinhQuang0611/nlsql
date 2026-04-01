import React, { useEffect, useState } from 'react';
import { Button, Space, Typography, Popconfirm, Empty } from 'antd';
import styled from 'styled-components';
import PlusOutlined from '@ant-design/icons/PlusOutlined';
import MessageOutlined from '@ant-design/icons/MessageOutlined';
import DeleteOutlined from '@ant-design/icons/DeleteOutlined';

const { Text } = Typography;

const SidebarContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 12px;
  color: #fff;
  background: #f9f9f9;
  border-right: 2px solid #0d0d0d0d;
`;

const NewChatButton = styled(Button)`
  margin-bottom: 20px;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  height: 48px;
  border-radius: 8px;
  transition: background 0.2s;
`;

const HistoryList = styled.div`
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const HistoryItem = styled.div<{ active: boolean }>`
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #1f1f1f;
  background: ${(props) => (props.active ? '#0000000f' : 'transparent')};
  transition: background 0.2s;

  &:hover {
    background: #00000014;

    .delete-btn {
      opacity: 1;
      color: #595959;
    }
  }

  .delete-btn {
    opacity: 0;
    color: #595959;
    transition: opacity 0.2s;
  }
`;

interface ChatSession {
  id: string;
  title: string;
  updatedAt: number;
}

interface Props {
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
}

export default function HistorySidebar({ activeSessionId, onSelectSession, onNewChat, onDeleteSession }: Props) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  useEffect(() => {
    const loadSessions = () => {
      const stored = localStorage.getItem('chat_sessions');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          const list = Object.values(parsed).map((s: any) => ({
            id: s.id,
            title: s.title || 'New Chat',
            updatedAt: s.updatedAt || Date.now()
          })).sort((a, b) => b.updatedAt - a.updatedAt);
          setSessions(list as ChatSession[]);
        } catch (e) {
          console.error('Failed to parse sessions', e);
        }
      }
    };

    loadSessions();
    window.addEventListener('storage', loadSessions);
    // Custom event to update from within the same window
    window.addEventListener('chat_sessions_updated', loadSessions);
    return () => {
      window.removeEventListener('storage', loadSessions);
      window.removeEventListener('chat_sessions_updated', loadSessions);
    };
  }, []);

  return (
    <SidebarContainer>
      <NewChatButton icon={<PlusOutlined />} onClick={onNewChat}>
        New Chat
      </NewChatButton>
      
      <Text strong className="mb-2 px-2" style={{ fontSize: 12, color: '#8e8ea0' }}>
        Lịch sử trò chuyện
      </Text>
      
      <HistoryList>
        {sessions.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: '#8e8ea0' }}>No history yet</span>} />
        ) : (
          sessions.map((session) => (
            <HistoryItem 
              key={session.id} 
              active={activeSessionId === session.id}
              onClick={() => onSelectSession(session.id)}
            >
              <Space style={{ overflow: 'hidden' }}>
                <Text ellipsis style={{ width: 140, fontSize: 13, color: 'inherit' }}>
                  {session.title}
                </Text>
              </Space>
              
              <Button 
                type="text" 
                size="small"
                className="delete-btn"
                icon={<DeleteOutlined style={{ fontSize: 12 }} />}
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(session.id);
                }}
              />
            </HistoryItem>
          ))
        )}
      </HistoryList>
    </SidebarContainer>
  );
}
