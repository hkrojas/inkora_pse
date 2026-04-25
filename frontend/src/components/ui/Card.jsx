import { cn } from '../../lib/utils/cn';

export default function Card({ children, className }) {
  return (
    <section
      className={cn(
        'rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-soft)]',
        className
      )}
    >
      {children}
    </section>
  );
}
