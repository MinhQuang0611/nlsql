import { Spin } from 'antd';
import styled from 'styled-components';
import LoadingOutlined from '@ant-design/icons/LoadingOutlined';

const Wrapper = styled.div`
  --color-primary: #bc2626;
  position: absolute;
  top: 48px;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  background-color: white;
  display: none;

  &.isShow {
    display: flex;
  }

  .circle-loader {
    width: 50px;
    aspect-ratio: 1;
    --c: no-repeat radial-gradient(farthest-side, var(--color-primary) 92%, #0000);
    background:
      var(--c) 50% 0,
      var(--c) 50% 100%,
      var(--c) 100% 50%,
      var(--c) 0 50%;
    background-size: 10px 10px;
    animation: l18 1s infinite;
    position: relative;
  }

  .circle-loader::before {
    content: '';
    position: absolute;
    inset: 0;
    margin: 3px;
    background: repeating-conic-gradient(
      #0000 0 35deg,
      var(--color-primary) 0 90deg
    );
    -webkit-mask: radial-gradient(farthest-side, #0000 calc(100% - 3px), #000 0);
    border-radius: 50%;
  }

  @keyframes l18 {
    100% {
      transform: rotate(0.5turn);
    }
  }
`;

interface Props {
  visible?: boolean;
}

interface LoadingProps {
  children?: React.ReactNode | null;
  spinning?: boolean;
  loading?: boolean;
  tip?: string;
  size?: number;
  width?: number;
  height?: number;
  className?: string;
}

export const defaultIndicator = (
  <LoadingOutlined style={{ fontSize: 36 }} spin />
);

export const Spinner = ({ className = '', size = 36 }) => (
  <LoadingOutlined className={className} style={{ fontSize: size }} spin />
);

export default function PageLoading(props: Props) {
  const { visible } = props;
  return (
    <Wrapper
      className={`align-center justify-center${visible ? ' isShow' : ''}`}
    >
      <div className="text-center">
        <div className="circle-loader" />
        <div className="mt-2 geekblue-6">Loading...</div>
      </div>
    </Wrapper>
  );
}

export const FlexLoading = (props) => {
  const { height, tip } = props;
  return (
    <div
      className="d-flex align-center justify-center flex-column geekblue-6"
      style={{ height: height || '100%' }}
    >
      {defaultIndicator}
      {tip && <span className="mt-2">{tip}</span>}
    </div>
  );
};

export const Loading = ({
  children = null,
  spinning = false,
  loading = false,
  tip,
}: LoadingProps) => (
  <Spin indicator={defaultIndicator} spinning={spinning || loading} tip={tip}>
    {children}
  </Spin>
);

interface LoadingWrapperProps {
  loading: boolean;
  tip?: string;
  children: React.ReactElement;
}

export const LoadingWrapper = (props: LoadingWrapperProps) => {
  const { loading, tip, children } = props;
  if (loading) return <FlexLoading tip={tip} />;
  return children;
};
