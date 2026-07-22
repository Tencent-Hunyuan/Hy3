interface GraceAvatarProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

// Heights in px — SVG natural ratio is 1175:2001 ≈ 0.587
const heights: Record<NonNullable<GraceAvatarProps['size']>, number> = {
  xs:  28,
  sm:  40,
  md:  80,
  lg: 160,
  xl: 260,   // More prominent in onboarding
};

export default function GraceAvatar({ size = 'md', className = '' }: GraceAvatarProps) {
  const h = heights[size];
  return (
    <div className={`shrink-0 flex items-end justify-center ${className}`} style={{ height: h }}>
      <img
        src="/assets/grace-avatar.svg"
        alt="Grace"
        draggable={false}
        style={{ height: h, width: 'auto', display: 'block', userSelect: 'none' }}
      />
    </div>
  );
}
