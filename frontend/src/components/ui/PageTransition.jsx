import { useLocation } from 'react-router-dom';

export default function PageTransition({ children, variant = 'fade' }) {
  const location = useLocation();
  const className = variant === 'slide'
    ? 'page-transition-wrapper--slide'
    : 'page-transition-wrapper';

  return (
    <div key={location.pathname} className={className}>
      {children}
    </div>
  );
}
