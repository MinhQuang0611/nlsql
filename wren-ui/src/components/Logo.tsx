interface Props {
  size?: number;
  color?: string;
}

export const Logo = (props: Props) => {
  const { size = 30 } = props;
  return (
    <img
      src="/images/ptit-logo.png"
      alt="PTIT AI"
      style={{
        width: size,
        height: size,
        objectFit: 'contain',
      }}
    />
  );
};
