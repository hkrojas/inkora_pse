import { useState, useCallback, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  CreditCard,
  FileText,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Package,
  Receipt,
  Settings,
  ShieldCheck,
  Sun,
  Truck,
  Users,
  XCircle,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { cn } from '../lib/utils/cn';

const GROUPS = [
  {
    id: 'principal',
    label: 'Principal',
    icon: LayoutDashboard,
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/clientes', label: 'Clientes', icon: Users },
      { to: '/cotizaciones', label: 'Cotizaciones', icon: FileText },
      { to: '/facturas', label: 'Facturas', icon: Receipt },
      { to: '/boletas', label: 'Boletas', icon: Receipt },
      { to: '/guias', label: 'Guías', icon: Truck },
      { to: '/cobranza', label: 'Cobranza', icon: CreditCard },
      { to: '/productos', label: 'Productos', icon: Package },
    ],
  },
  {
    id: 'gestion',
    label: 'Gestión',
    icon: Settings,
    items: [
      { to: '/comprobantes/nuevo', label: 'Crear comprobante', icon: Receipt },
      { to: '/notas', label: 'Notas Créd/Déb', icon: Receipt },
      { to: '/resumen-diario', label: 'Resumen Diario', icon: BarChart3 },
      { to: '/bajas', label: 'Bajas', icon: XCircle },
      { to: '/reversiones', label: 'Reversiones', icon: Receipt },
      { to: '/retenciones', label: 'Retenciones', icon: ShieldCheck },
      { to: '/percepciones', label: 'Percepciones', icon: ShieldCheck },
      { to: '/configuracion', label: 'Configuración', icon: Settings },
      { to: '/cambiar-password', label: 'Seguridad', icon: KeyRound },
    ],
  },
];

function useLocalStorage(key, defaultValue) {
  const [value, setValue] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(key)) ?? defaultValue;
    } catch {
      return defaultValue;
    }
  });

  const set = (nextValue) => {
    const resolvedValue = typeof nextValue === 'function' ? nextValue(value) : nextValue;
    setValue(resolvedValue);
    localStorage.setItem(key, JSON.stringify(resolvedValue));
  };

  return [value, set];
}

export default function Sidebar() {
  const { user, logout } = useAuth();
  const { resolvedTheme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const [collapsed, setCollapsed] = useLocalStorage('sidebar-collapsed', false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openGroups, setOpenGroups] = useLocalStorage('sidebar-open-groups', ['principal']);
  const [tooltip, setTooltip] = useState(null);
  const initializedSessionRef = useRef(null);
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia('(max-width: 1023px)').matches : false,
  );

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const mq = window.matchMedia('(max-width: 1023px)');
    const sync = (event) => setIsMobile(event.matches);
    setIsMobile(mq.matches);
    if (mq.addEventListener) {
      mq.addEventListener('change', sync);
      return () => mq.removeEventListener('change', sync);
    }
    mq.addListener(sync);
    return () => mq.removeListener(sync);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const showTooltip = useCallback((event, label) => {
    if (!label) return;
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltip({ label, x: rect.right + 12, y: rect.top + rect.height / 2 });
  }, []);

  const hideTooltip = useCallback(() => setTooltip(null), []);

  useEffect(() => {
    const sessionKey = user?.id || user?.email;
    if (!sessionKey || initializedSessionRef.current === sessionKey) return;
    initializedSessionRef.current = sessionKey;
    setOpenGroups(['principal']);
    setCollapsed(false);
  }, [user?.id, user?.email, setCollapsed, setOpenGroups]);

  const handleToggle = () => {
    if (isMobile) setMobileOpen((v) => !v);
    else setCollapsed((v) => !v);
  };

  const isSuperadmin = user?.is_superadmin || user?.rol === 'superadmin';
  const roleLabel = isSuperadmin ? 'superadmin' : user?.rol;
  const showCollapsed = !isMobile && collapsed;

  const groups = GROUPS.map((group) => {
    if (group.id === 'gestion' && isSuperadmin) {
      return {
        ...group,
        items: [
          ...group.items,
          { to: '/superadmin', label: 'Superadmin', icon: ShieldCheck, accent: true },
        ],
      };
    }
    return group;
  });

  const toggleGroup = (id) => {
    setOpenGroups((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const isGroupActive = (group) =>
    group.items.some(
      (item) => location.pathname === item.to || location.pathname.startsWith(`${item.to}/`),
    );

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userInitial = (user?.nombre_completo || user?.email || 'U')[0].toUpperCase();

  return (
    <>
      {/* Mobile trigger */}
      {isMobile && !mobileOpen && (
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="fixed left-4 top-4 z-40 inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] shadow-[var(--shadow-soft)] lg:hidden"
          aria-label="Abrir menú"
        >
          <Menu size={20} />
        </button>
      )}

      {/* Mobile overlay */}
      {isMobile && mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={cn(
          'group/sidebar flex flex-col flex-shrink-0 bg-[var(--color-surface)] border-r border-[var(--color-border)] transition-[width] duration-300',
          isMobile
            ? 'fixed inset-y-0 left-0 z-50 w-72 shadow-[var(--shadow-floating)] transition-transform duration-300'
            : 'sticky top-0 h-screen',
          isMobile && !mobileOpen && '-translate-x-full',
          !isMobile && (collapsed ? 'w-[72px]' : 'w-[260px]'),
        )}
      >
        {/* Brand */}
        <div className="flex items-center justify-between px-4 pt-5 pb-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-3 min-w-0">
            <img
              src="/logo-icon.png"
              alt="Inkora"
              className="h-9 w-9 flex-shrink-0 object-contain"
            />
            {!showCollapsed && (
              <span className="truncate text-lg font-extrabold tracking-tight text-[var(--color-text)]">
                Inkora
              </span>
            )}
          </div>
          {isMobile && (
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)]"
              aria-label="Cerrar menú"
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* Collapse toggle (desktop) */}
        {!isMobile && (
          <button
            type="button"
            onClick={handleToggle}
            className={cn(
              'mx-3 mt-3 inline-flex items-center gap-2 rounded-lg border border-[var(--color-border)] px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-muted)] transition-colors',
              showCollapsed && 'justify-center px-0',
            )}
          >
            {showCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            {!showCollapsed && <span>Contraer</span>}
          </button>
        )}

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4 space-y-1">
          {groups.map((group) => {
            const isOpen = openGroups.includes(group.id);
            const groupActive = isGroupActive(group);
            const GroupIcon = group.icon;

            return (
              <div key={group.id}>
                <button
                  type="button"
                  onClick={() => !showCollapsed && toggleGroup(group.id)}
                  onMouseEnter={(e) => showCollapsed && showTooltip(e, group.label)}
                  onMouseLeave={hideTooltip}
                  className={cn(
                    'flex w-full items-center gap-3 rounded-xl px-3 py-2 text-[11px] font-bold uppercase tracking-[0.08em] transition-colors',
                    showCollapsed && 'justify-center px-0',
                    groupActive
                      ? 'text-[var(--color-text)]'
                      : 'text-[var(--color-text-soft)] hover:text-[var(--color-text)]',
                  )}
                >
                  <GroupIcon size={16} className="flex-shrink-0" />
                  {!showCollapsed && (
                    <>
                      <span className="flex-1 text-left">{group.label}</span>
                      <ChevronDown
                        size={14}
                        className={cn(
                          'transition-transform duration-200',
                          isOpen ? 'rotate-0' : '-rotate-90',
                        )}
                      />
                    </>
                  )}
                </button>

                {(isOpen || showCollapsed) && (
                  <div className={cn('mt-1 space-y-0.5', showCollapsed ? '' : 'pl-2')}>
                    {group.items.map(({ to, label, icon: Icon, accent }) => (
                      <NavLink
                        key={to}
                        to={to}
                        onMouseEnter={(e) => showCollapsed && showTooltip(e, label)}
                        onMouseLeave={hideTooltip}
                        className={({ isActive }) =>
                          cn(
                            'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors',
                            showCollapsed && 'justify-center px-0',
                            isActive
                              ? accent
                                ? 'bg-[var(--color-purple-soft)] text-[var(--color-purple-text)]'
                                : 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]'
                              : 'text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]',
                          )
                        }
                      >
                        <Icon size={16} className="flex-shrink-0" />
                        {!showCollapsed && <span className="truncate">{label}</span>}
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-[var(--color-border)] p-3 space-y-2">
          <button
            type="button"
            onClick={toggleTheme}
            onMouseEnter={(e) =>
              showCollapsed && showTooltip(e, resolvedTheme === 'dark' ? 'Modo claro' : 'Modo oscuro')
            }
            onMouseLeave={hideTooltip}
            className={cn(
              'flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)] transition-colors',
              showCollapsed && 'justify-center px-0',
            )}
            aria-label="Cambiar tema"
          >
            {resolvedTheme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            {!showCollapsed && (
              <span>{resolvedTheme === 'dark' ? 'Modo claro' : 'Modo oscuro'}</span>
            )}
          </button>

          <div
            className={cn(
              'flex items-center gap-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-soft)] p-2.5',
              showCollapsed && 'justify-center p-1.5',
            )}
            onMouseEnter={(e) => showCollapsed && showTooltip(e, 'Cerrar sesión')}
            onMouseLeave={hideTooltip}
          >
            <div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-[var(--color-primary-soft)] text-sm font-extrabold text-[var(--color-primary)]">
              {userInitial}
            </div>
            {!showCollapsed && (
              <>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-[var(--color-text)]">
                    {user?.nombre_completo || user?.email}
                  </p>
                  <p className="truncate text-[11px] text-[var(--color-text-muted)] capitalize">
                    {roleLabel}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-[var(--color-text-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-danger)] transition-colors"
                  aria-label="Cerrar sesión"
                  title="Cerrar sesión"
                >
                  <LogOut size={14} />
                </button>
              </>
            )}
          </div>
        </div>
      </aside>

      {/* Tooltip */}
      {tooltip &&
        createPortal(
          <div
            className="pointer-events-none fixed z-[60] -translate-y-1/2 rounded-lg bg-[var(--color-text)] px-2.5 py-1.5 text-xs font-bold text-[var(--color-surface)] shadow-[var(--shadow-floating)]"
            style={{ top: tooltip.y, left: tooltip.x }}
          >
            {tooltip.label}
          </div>,
          document.body,
        )}
    </>
  );
}
