import { useState, useCallback, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  Asterisk,
  BarChart3,
  ChevronRight,
  CreditCard,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Package,
  PanelLeftClose,
  Receipt,
  Settings,
  ShieldCheck,
  Sun,
  Truck,
  Warehouse,
  Users,
  XCircle,
  X,
  PlusCircle,
  ArrowLeftRight,
  RotateCcw,
  HandCoins,
  Eye,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { cn } from '../lib/utils/cn';
import { ENABLE_ADVANCED_FISCAL } from '../lib/utils/config';

const ADVANCED_FISCAL_GROUP = {
  id: 'fiscal',
  label: 'Fiscal',
  items: [
    { route: '/resumen-diario', label: 'Resumen diario', icon: BarChart3 },
    { route: '/bajas', label: 'Bajas', icon: XCircle },
    { route: '/reversiones', label: 'Reversiones', icon: RotateCcw },
    { route: '/retenciones', label: 'Retenciones', icon: HandCoins },
    { route: '/percepciones', label: 'Percepciones', icon: Eye },
  ],
};

const GROUPS = [
  {
    id: 'operativo',
    label: 'Operativo',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/clientes', label: 'Clientes', icon: Users },
      { to: '/cotizaciones', label: 'Cotizaciones', icon: FileText },
      { to: '/productos', label: 'Productos', icon: Package },
      { to: '/inventario', label: 'Inventario', icon: Warehouse },
      { to: '/cobranza', label: 'Cobranza', icon: CreditCard },
    ],
  },
  {
    id: 'comprobantes',
    label: 'Comprobantes',
    items: [
      { to: '/comprobantes/nuevo', label: 'Nuevo comprobante', icon: PlusCircle },
      { to: '/facturas', label: 'Facturas', icon: Receipt },
      { to: '/boletas', label: 'Boletas', icon: Receipt },
      { to: '/guias', label: 'Guías', icon: Truck },
      { to: '/notas', label: 'Notas créd./déb.', icon: ArrowLeftRight },
    ],
  },
  ...(ENABLE_ADVANCED_FISCAL ? [ADVANCED_FISCAL_GROUP] : []),
  {
    id: 'sistema',
    label: 'Sistema',
    items: [
      { to: '/configuracion', label: 'Configuración', icon: Settings },
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
    setTooltip({ label, x: rect.right + 10, y: rect.top + rect.height / 2 });
  }, []);

  const hideTooltip = useCallback(() => setTooltip(null), []);

  useEffect(() => {
    const sessionKey = user?.id || user?.email;
    if (!sessionKey || initializedSessionRef.current === sessionKey) return;
    initializedSessionRef.current = sessionKey;
    setCollapsed(false);
  }, [setCollapsed, user?.email, user?.id]);

  const handleToggle = () => {
    if (isMobile) setMobileOpen((value) => !value);
    else setCollapsed((value) => !value);
  };

  const isSuperadmin = Boolean(user?.is_superadmin);
  const roleLabel = isSuperadmin ? 'superadmin' : user?.rol;
  const showCollapsed = !isMobile && collapsed;

  const groups = GROUPS.map((group) => {
    if (group.id !== 'sistema' || !isSuperadmin) return group;
    return {
      ...group,
      items: [
        ...group.items,
        { to: '/superadmin', label: 'Superadmin', icon: ShieldCheck, accent: true },
      ],
    };
  });

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userInitial = (user?.nombre_completo || user?.email || 'U')[0].toUpperCase();

  return (
    <>
      {isMobile && !mobileOpen && (
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="fixed left-3 top-3 z-40 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-[#102b16] text-white shadow-[var(--shadow-floating)] lg:hidden"
          aria-label="Abrir menú"
        >
          <Menu size={18} />
        </button>
      )}

      {isMobile && mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={cn(
          'group/sidebar flex flex-shrink-0 flex-col bg-[linear-gradient(180deg,#102b16_0%,#0d2212_100%)] transition-[width,transform] duration-300',
          isMobile
            ? 'fixed inset-y-0 left-0 z-50 w-[264px] shadow-[var(--shadow-floating)] transition-transform duration-300'
            : 'sticky top-0 h-screen',
          isMobile && !mobileOpen && '-translate-x-full',
          !isMobile && (collapsed ? 'w-[62px]' : 'w-[244px]'),
        )}
      >
        <div className="flex items-center gap-3 px-4 pb-4 pt-5">
          <span className="inline-flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center text-[#a3e635]">
            <Asterisk size={22} strokeWidth={2.4} />
          </span>
          {!showCollapsed && (
            <span className="truncate text-[20px] font-black tracking-[-0.05em] text-white">
              Inkora
            </span>
          )}
          {isMobile && (
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="ml-auto inline-flex h-7 w-7 items-center justify-center rounded-lg text-white/60 hover:bg-white/5 hover:text-white"
              aria-label="Cerrar menú"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {!isMobile && (
          <button
            type="button"
            onClick={handleToggle}
            className={cn(
              'mx-3 mb-3 inline-flex h-9 items-center gap-2 rounded-xl border border-white/[0.08] px-3 text-[10px] font-black uppercase tracking-[0.1em] text-white/50 transition-colors hover:bg-white/[0.05] hover:text-white/70',
              showCollapsed && 'justify-center px-0',
            )}
          >
            {showCollapsed ? <ChevronRight size={12} /> : <PanelLeftClose size={12} />}
            {!showCollapsed && <span>Contraer</span>}
          </button>
        )}

        <nav className="ink-sidebar-scroll flex-1 overflow-y-auto overflow-x-hidden px-2 pb-2">
          {groups.map((group) => (
            <div key={group.id}>
              <div className={cn(
                'px-3 pb-1.5 pt-3 text-[9px] font-black uppercase tracking-[0.14em] text-white/25',
                showCollapsed && 'px-1 text-center',
              )}>
                {showCollapsed ? '·' : group.label}
              </div>

              {group.items.map((item) => {
                const { label, icon: Icon, accent } = item;
                const to = item.to || item.route;
                const isActive = location.pathname === to || location.pathname.startsWith(`${to}/`);
                return (
                  <NavLink
                    key={to}
                    to={to}
                    onMouseEnter={(event) => showCollapsed && showTooltip(event, label)}
                    onMouseLeave={hideTooltip}
                    className={cn(
                      'sidebar-item mb-0.5 flex items-center gap-2.5 rounded-[11px] px-3 py-[9px] text-[13px] transition-all duration-[150ms]',
                      showCollapsed && 'justify-center px-0',
                      isActive
                        ? 'is-active bg-[rgba(132,204,63,0.14)] font-bold text-white'
                        : 'font-medium text-white/55 hover:bg-white/[0.04] hover:text-white/80',
                    )}
                  >
                    <Icon
                      size={15}
                      className={cn('flex-shrink-0', isActive ? 'text-[#a3e635]' : 'text-white/40')}
                    />
                    {!showCollapsed && <span className="truncate">{label}</span>}
                    {!showCollapsed && accent && isActive && (
                      <span className="ml-auto flex-shrink-0 rounded-full bg-[#8DC63F]/20 px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wide text-[#8DC63F]">
                        SA
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="border-t border-white/[0.07] p-2.5 space-y-1.5">
          <button
            type="button"
            onClick={(event) => toggleTheme(event)}
            onMouseEnter={(event) =>
              showCollapsed &&
              showTooltip(event, resolvedTheme === 'dark' ? 'Modo claro' : 'Modo oscuro')
            }
            onMouseLeave={hideTooltip}
            className={cn(
              'flex w-full items-center gap-2 rounded-[11px] border border-white/[0.08] px-3 py-2 text-[10px] font-black uppercase tracking-[0.1em] text-white/40 transition-colors hover:bg-white/[0.05] hover:text-white/65',
              showCollapsed && 'justify-center px-0',
            )}
            aria-label="Cambiar tema"
          >
            {resolvedTheme === 'dark' ? <Sun size={12} /> : <Moon size={12} />}
            {!showCollapsed && (
              <span>{resolvedTheme === 'dark' ? 'Modo claro' : 'Modo oscuro'}</span>
            )}
          </button>

          <div
            className={cn(
              'flex items-center gap-2.5 rounded-[14px] bg-white/[0.06] px-2.5 py-2.5',
              showCollapsed && 'justify-center px-1',
            )}
            onMouseEnter={(event) => showCollapsed && showTooltip(event, 'Cerrar sesión')}
            onMouseLeave={hideTooltip}
          >
            <div className="grid h-[32px] w-[32px] flex-shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#e3e941] to-[#7cc63f] text-[11px] font-black text-white">
              {userInitial}
            </div>
            {!showCollapsed && (
              <>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12px] font-bold text-white leading-tight">
                    {user?.nombre_completo || user?.email}
                  </p>
                  <p className="truncate text-[10px] capitalize text-white/40 leading-tight">{roleLabel}</p>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg text-white/40 transition-colors hover:bg-white/5 hover:text-[#fca5a5]"
                  aria-label="Cerrar sesión"
                  title="Cerrar sesión"
                >
                  <LogOut size={13} />
                </button>
              </>
            )}
          </div>
        </div>
      </aside>

      {tooltip &&
        createPortal(
          <div
            className="pointer-events-none fixed z-[60] -translate-y-1/2 rounded-lg bg-[#102b16] px-2.5 py-1.5 text-xs font-bold text-white shadow-[var(--shadow-floating)]"
            style={{ top: tooltip.y, left: tooltip.x }}
          >
            {tooltip.label}
          </div>,
          document.body,
        )}
    </>
  );
}
