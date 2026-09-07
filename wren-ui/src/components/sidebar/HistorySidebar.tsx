import React, { useEffect, useState } from 'react';
import { Button, Space, Typography, Popconfirm, Empty } from 'antd';
import styled from 'styled-components';
import PlusOutlined from '@ant-design/icons/PlusOutlined';
import MessageOutlined from '@ant-design/icons/MessageOutlined';
import DeleteOutlined from '@ant-design/icons/DeleteOutlined';

const { Text } = Typography;

const SidebarContainer = styled.div<{ collapsed?: boolean }>`
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: ${(props) => (props.collapsed ? '12px 8px' : '12px')};
  color: #fff;
  background: #f9f9f9;
`;

const PanelIcon = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    style={{ display: 'block' }}
  >
    <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
    <line x1="9" x2="9" y1="3" y2="21" />
  </svg>
);

const NewChatButton = styled(Button)<{ collapsed?: boolean }>`
  margin-bottom: 20px;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: ${(props) => (props.collapsed ? 'center' : 'flex-start')};
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

const HistoryItem = styled.div<{ active: boolean; collapsed?: boolean }>`
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: ${(props) => (props.collapsed ? 'center' : 'space-between')};
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
  collapsed?: boolean;
  onToggle?: () => void;
}

export default function HistorySidebar({ activeSessionId, onSelectSession, onNewChat, onDeleteSession, collapsed, onToggle }: Props) {
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
    <SidebarContainer collapsed={collapsed}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20, justifyContent: collapsed ? 'center' : 'flex-start', flexDirection: collapsed ? 'column-reverse' : 'row' }}>
        <NewChatButton 
          icon={<PlusOutlined />} 
          onClick={onNewChat}
          collapsed={collapsed}
          style={{ flex: collapsed ? 'none' : 1, marginBottom: 0 }}
        >
          {!collapsed && "New Chat"}
        </NewChatButton>
        <Button
          type="text"
          icon={<PanelIcon />}
          onClick={onToggle}
          style={{
            color: 'var(--gray-7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 0,
            width: 32,
            height: collapsed ? 32 : 48,
            borderRadius: '8px',
            border: collapsed ? 'none' : '1px solid var(--gray-4)',
            background: collapsed ? 'transparent' : 'white'
          }}
        />
      </div>
      
      {!collapsed && (
        <Text strong className="mb-2 px-2" style={{ fontSize: 12, color: '#8e8ea0' }}>
          Lịch sử trò chuyện
        </Text>
      )}
      
      <HistoryList>
        {sessions.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: '#8e8ea0' }}>No history yet</span>} />
        ) : (
          sessions.map((session) => (
            <HistoryItem 
              key={session.id} 
              active={activeSessionId === session.id}
              onClick={() => onSelectSession(session.id)}
              collapsed={collapsed}
              title={collapsed ? session.title : undefined}
            >
              <Space style={{ overflow: 'hidden' }}>
                <MessageOutlined style={{ fontSize: 14, color: activeSessionId === session.id ? 'var(--red-5)' : 'inherit' }} />
                {!collapsed && (
                  <Text ellipsis style={{ width: 140, fontSize: 13, color: 'inherit' }}>
                    {session.title}
                  </Text>
                )}
              </Space>
              
              {!collapsed && (
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
              )}
            </HistoryItem>
          ))
        )}
      </HistoryList>
    </SidebarContainer>
  );
}
