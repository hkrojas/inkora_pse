import { useState, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  BarChart2,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  CreditCard,
  Eye,
  FileText,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Package,
  Palette,
  Receipt,
  RefreshCw,
  Settings,
  ShieldCheck,
  ShoppingBag,
  Truck,
  Users,
  XCircle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const GROUPS = [
  {
    id: 'panel',
    label: 'Dashboard',
    icon: LayoutDashboard,
    direct: '/dashboard',
  },
  {
    id: 'ventas',
    label: 'Ventas',
    icon: ShoppingBag,
    items: [
      { to: '/comprobantes/nuevo', label: 'Crear comprobante', icon: Receipt },
      { to: '/cotizaciones', label: 'Cotizaciones', icon: FileText },
      { to: '/facturas', label: 'Facturas', icon: Receipt },
      { to: '/boletas', label: 'Boletas de venta', icon: Receipt },
      { to: '/notas', label: 'Notas Cred/Deb', icon: RefreshCw },
      { to: '/cobranza', label: 'Cobranza', icon: CreditCard },
    ],
  },
  {
    id: 'sunat',
    label: 'Documentos SUNAT',
    icon: ShieldCheck,
    items: [
      { to: '/retenciones', label: 'Retenciones', icon: ShieldCheck },
      { to: '/percepciones', label: 'Percepciones', icon: Eye },
      { to: '/resumen-diario', label: 'Resumen Diario', icon: BarChart2 },
      { to: '/bajas', label: 'Bajas', icon: XCircle },
      { to: '/reversiones', label: 'Reversiones', icon: RefreshCw },
      { to: '/guias', label: 'Guias Remision', icon: Truck },
    ],
  },
  {
    id: 'maestros',
    label: 'Maestros',
    icon: BookOpen,
    items: [
      { to: '/clientes', label: 'Clientes', icon: Users },
      { to: '/productos', label: 'Productos', icon: Package },
    ],
  },
  {
    id: 'sistema',
    label: 'Configuracion',
    icon: Settings,
    items: [
      { to: '/configuracion', label: 'Perfil empresa', icon: Settings },
      { to: '/diseno-pdf', label: 'Diseno PDF', icon: Palette },
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
  const navigate = useNavigate();
  const location = useLocation();

  const [collapsed, setCollapsed] = useLocalStorage('sidebar-collapsed', false);
  const [mobileCollapsed, setMobileCollapsed] = useState(true);
  const [openGroups, setOpenGroups] = useLocalStorage('sidebar-open-groups', []);
  const [tooltip, setTooltip] = useState(null);
  const [isMobileViewport, setIsMobileViewport] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia('(max-width: 767px)').matches : false,
  );

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const mediaQuery = window.matchMedia('(max-width: 767px)');
    const sync = (event) => setIsMobileViewport(event.matches);

    setIsMobileViewport(mediaQuery.matches);

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', sync);
      return () => mediaQuery.removeEventListener('change', sync);
    }

    mediaQuery.addListener(sync);
    return () => mediaQuery.removeListener(sync);
  }, []);

  const showTooltip = useCallback((event, label) => {
    if (!label) return;
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltip({ label, x: rect.right + 12, y: rect.top + rect.height / 2 });
  }, []);

  const hideTooltip = useCallback(() => setTooltip(null), []);
  const handleSidebarToggle = useCallback(() => {
    if (isMobileViewport) {
      setMobileCollapsed((current) => !current);
      return;
    }
    setCollapsed((current) => !current);
  }, [isMobileViewport, setCollapsed]);

  const isSuperadmin = user?.is_superadmin || user?.rol === 'superadmin';
  const roleLabel = isSuperadmin ? 'superadmin' : user?.rol;
  const effectiveCollapsed = isMobileViewport ? mobileCollapsed : collapsed;

  const groups = GROUPS.map((group) => {
    if (group.id === 'sistema' && isSuperadmin) {
      return {
        ...group,
        label: 'Sistema',
        items: [
          { to: '/configuracion', label: 'Perfil empresa', icon: Settings },
          { to: '/diseno-pdf', label: 'Diseno PDF', icon: Palette },
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

  const isGroupActive = (group) => {
    if (group.direct) {
      return location.pathname === group.direct || location.pathname.startsWith(`${group.direct}/`);
    }
    return group.items.some(
      (item) => location.pathname === item.to || location.pathname.startsWith(`${item.to}/`),
    );
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const asideClassName = [
    'sidebar-shell',
    effectiveCollapsed ? 'sidebar-collapsed' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <>
      <aside className={asideClassName} id="sidebar-nav">
        <div className="sidebar-brand-wrap">
          <div className="sidebar-logo-row">
            <img src="/logo-icon.png" alt="Inkora" className="sidebar-logo-icon" />
            {!effectiveCollapsed && <span className="sidebar-brand">Inkora</span>}
          </div>

          {!effectiveCollapsed && (
            <div className="raw-lines" aria-hidden="true">
              <div />
              <div />
              <div />
            </div>
          )}
        </div>

        <button
          className="sidebar-toggle-btn"
          onClick={handleSidebarToggle}
          title={effectiveCollapsed ? 'Expandir panel' : 'Contraer panel'}
          type="button"
        >
          {effectiveCollapsed ? (
            <ChevronRight size={14} />
          ) : (
            <>
              <ChevronLeft size={14} />
              <span className="sidebar-toggle-label">Contraer</span>
            </>
          )}
        </button>

        <nav className="sidebar-nav">
          {groups.map((group) => {
            const groupActive = isGroupActive(group);
            const isOpen = openGroups.includes(group.id) || groupActive;
            const GroupIcon = group.icon;

            if (group.direct) {
              return (
                <div key={group.id} className="sidebar-group">
                  <NavLink
                    to={group.direct}
                    className={({ isActive }) =>
                      `sidebar-group-header${isActive ? ' sidebar-group-header-active' : ''}`
                    }
                    onMouseEnter={(event) => effectiveCollapsed && showTooltip(event, group.label)}
                    onMouseLeave={hideTooltip}
                  >
                    <GroupIcon size={16} className="sidebar-group-icon" />
                    {!effectiveCollapsed && <span className="sidebar-group-label">{group.label}</span>}
                  </NavLink>
                </div>
              );
            }

            return (
              <div key={group.id} className="sidebar-group">
                <button
                  className={`sidebar-group-header${groupActive ? ' sidebar-group-header-active' : ''}`}
                  onClick={() => toggleGroup(group.id)}
                  onMouseEnter={(event) => effectiveCollapsed && showTooltip(event, group.label)}
                  onMouseLeave={hideTooltip}
                  type="button"
                >
                  <GroupIcon size={16} className="sidebar-group-icon" />
                  {!effectiveCollapsed && (
                    <>
                      <span className="sidebar-group-label">{group.label}</span>
                      <ChevronDown
                        size={13}
                        className="sidebar-group-chevron"
                        style={{
                          transform: isOpen ? 'rotate(0deg)' : 'rotate(-90deg)',
                          transition: 'transform 200ms',
                        }}
                      />
                    </>
                  )}
                </button>

                {!effectiveCollapsed && (
                  <div className={`sidebar-group-items${isOpen ? ' sidebar-group-items-open' : ''}`}>
                    {group.items.map(({ to, label, icon: Icon, accent }) => (
                      <NavLink
                        key={to}
                        to={to}
                        className={({ isActive }) =>
                          `sidebar-navlink${isActive ? ' sidebar-navlink-active' : ''}${accent && isActive ? ' sidebar-navlink-accent' : ''}`
                        }
                      >
                        <Icon size={14} style={{ flexShrink: 0 }} />
                        <span>{label}</span>
                      </NavLink>
                    ))}
                  </div>
                )}

                {effectiveCollapsed && (
                  <div className={`sidebar-collapsed-items${isOpen ? ' sidebar-collapsed-items-open' : ''}`}>
                    {group.items.map(({ to, label, icon: Icon }) => (
                      <NavLink
                        key={to}
                        to={to}
                        className={({ isActive }) =>
                          `sidebar-collapsed-link${isActive ? ' sidebar-navlink-active' : ''}`
                        }
                        onMouseEnter={(event) => showTooltip(event, label)}
                        onMouseLeave={hideTooltip}
                      >
                        <Icon size={13} />
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div
            className="sidebar-user-card"
            onClick={handleLogout}
            onMouseEnter={(event) => effectiveCollapsed && showTooltip(event, 'Cerrar sesion')}
            onMouseLeave={hideTooltip}
          >
            <div className="sidebar-user-avatar">
              {(user?.nombre_completo || user?.email || 'U')[0].toUpperCase()}
            </div>
            {!effectiveCollapsed && (
              <div className="sidebar-user-info">
                <p className="sidebar-user-name">{user?.nombre_completo || user?.email}</p>
                <p className="sidebar-user-role">{roleLabel}</p>
              </div>
            )}
            {!effectiveCollapsed && (
              <div className="flex items-center gap-1">
                <NavLink
                  to="/cambiar-password"
                  className="sidebar-user-logout"
                  aria-label="Cambiar contraseña"
                  title="Cambiar contraseña"
                  onClick={(event) => event.stopPropagation()}
                >
                  <KeyRound size={14} />
                </NavLink>
                <button
                  className="sidebar-user-logout"
                  aria-label="Cerrar sesion"
                  onClick={(event) => {
                    event.stopPropagation();
                    handleLogout();
                  }}
                  type="button"
                >
                  <LogOut size={14} />
                </button>
              </div>
            )}
          </div>
        </div>

        {tooltip &&
          createPortal(
            <div className="sidebar-tooltip" style={{ top: tooltip.y, left: tooltip.x }}>
              {tooltip.label}
            </div>,
            document.body,
          )}
      </aside>
    </>
  );
}
