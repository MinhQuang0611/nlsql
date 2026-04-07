import { SETTINGS } from '@/utils/enum';
import DatabaseOutlined from '@ant-design/icons/DatabaseOutlined';
import ProjectOutlined from '@ant-design/icons/ProjectOutlined';
import MessageOutlined from '@ant-design/icons/MessageOutlined';

export const getSettingMenu = (menu: SETTINGS) =>
  ({
    [SETTINGS.DATA_SOURCE]: {
      icon: DatabaseOutlined,
      label: 'Cài đặt nguồn dữ liệu',
    },
    [SETTINGS.PROJECT]: {
      icon: ProjectOutlined,
      label: 'Cài đặt dự án',
    },
    [SETTINGS.CHAT]: {
      icon: MessageOutlined,
      label: 'Cài đặt Chat',
    },
  })[menu] || null;
