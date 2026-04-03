import { useRouter } from 'next/router';
import { Button } from 'antd';
import styled from 'styled-components';
import { Path } from '@/utils/enum';
import SettingOutlined from '@ant-design/icons/SettingOutlined';
import Home, { Props as HomeSidebarProps } from './Home';
import Modeling, { Props as ModelingSidebarProps } from './Modeling';
import Knowledge from './Knowledge';
import APIManagement from './APIManagement';
import HistorySidebar from './HistorySidebar';

const Layout = styled.div`
  position: relative;
  height: 100%;
  background-color: var(--white);
  color: var(--gray-8);
  padding-bottom: 12px;
  overflow-x: hidden;
`;

const Content = styled.div`
  flex-grow: 1;
  overflow-y: auto;
`;

const StyledButton = styled(Button)`
  cursor: pointer;
  display: flex;
  align-items: center;
  padding-left: 16px;
  padding-right: 16px;
  color: var(--gray-8) !important;
  border-radius: 0;

  &:hover,
  &:focus {
    background-color: var(--gray-4);
  }
`;

export type HistorySidebarProps = {
  isHistoryMode?: boolean;
  activeSessionId?: string | null;
  onSelectSession?: (id: string) => void;
  onNewChat?: () => void;
  onDeleteSession?: (id: string) => void;
  onToggle?: () => void;
};

type Props = (ModelingSidebarProps | HomeSidebarProps | HistorySidebarProps) & {
  onOpenSettings?: () => void;
  collapsed?: boolean;
  onToggle?: () => void;
};

const DynamicSidebar = (
  props: Props & {
    pathname: string;
  },
) => {
  const { pathname, collapsed, onToggle, ...restProps } = props;

  const getContent = () => {
    if (pathname.startsWith(Path.Home)) {
      if ((restProps as HistorySidebarProps).isHistoryMode) {
        return (
          <HistorySidebar
            activeSessionId={(restProps as HistorySidebarProps).activeSessionId}
            onSelectSession={(restProps as HistorySidebarProps).onSelectSession}
            onNewChat={(restProps as HistorySidebarProps).onNewChat}
            onDeleteSession={(restProps as HistorySidebarProps).onDeleteSession}
            collapsed={collapsed}
            onToggle={onToggle}
          />
        );
      }
      return <Home {...(restProps as HomeSidebarProps)} collapsed={collapsed} />;
    }

    if (pathname.startsWith(Path.Modeling)) {
      return <Modeling {...(restProps as ModelingSidebarProps)} collapsed={collapsed} />;
    }

    if (pathname.startsWith(Path.Knowledge)) {
      return <Knowledge />;
    }

    if (pathname.startsWith(Path.APIManagement)) {
      return <APIManagement />;
    }

    return null;
  };

  return <Content>{getContent()}</Content>;
};

export default function Sidebar(props: Props) {
  const { onOpenSettings, onToggle, collapsed } = props;
  const router = useRouter();

  const onSettingsClick = (event) => {
    onOpenSettings && onOpenSettings();
    event.target.blur();
  };

  return (
    <Layout className="d-flex flex-column">
      <DynamicSidebar {...props} pathname={router.pathname} onToggle={onToggle} collapsed={collapsed} />
      <div className={`border-t border-gray-4 pt-2 ${collapsed ? 'd-flex justify-center' : ''}`}>
        <StyledButton type="text" block onClick={onSettingsClick} style={{ padding: collapsed ? 0 : '4px 16px', justifyContent: collapsed ? 'center' : 'flex-start' }}>
          <SettingOutlined className="text-md" />
          {!collapsed && <span className="ml-2">Cài đặt</span>}
        </StyledButton>
      </div>
    </Layout>
  );
}
