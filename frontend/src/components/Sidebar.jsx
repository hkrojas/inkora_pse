import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Users, Package, FileText, CreditCard,
  Truck, Settings, LogOut, ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const nav = [
  { to: '/dashboard',    label: 'Dashboard',     icon: LayoutDashboard },
  { to: '/clientes',     label: 'Clientes',       icon: Users },
  { to: '/productos',    label: 'Productos',      icon: Package },
  { to: '/cotizaciones', label: 'Cotizaciones',   icon: FileText },
  { to: '/cobranza',     label: 'Cobranza',       icon: CreditCard },
  { to: '/guias',        label: 'Guías',          icon: Truck },
  { to: '/configuracion',label: 'Configuración',  icon: Settings },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isSuperadmin = user?.is_superadmin || user?.rol === 'superadmin';
  const roleLabel = isSuperadmin ? 'superadmin' : user?.rol;

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-gray-200 bg-white">
      {/* Logo */}
      <div className="flex h-14 items-center px-5 border-b border-gray-100">
        <span className="text-sm font-bold tracking-tight text-gray-900">PrintFlow</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}

        {isSuperadmin && (
          <NavLink
            to="/superadmin"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-purple-50 text-purple-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <ShieldCheck className="h-4 w-4 shrink-0" />
            Superadmin
          </NavLink>
        )}
      </nav>

      {/* User */}
      <div className="border-t border-gray-100 p-3">
        <div className="mb-2 px-3 py-1">
          <p className="truncate text-xs font-medium text-gray-900">{user?.nombre_completo || user?.email}</p>
          <p className="truncate text-xs text-gray-400 capitalize">{roleLabel}</p>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900"
        >
          <LogOut className="h-4 w-4" />
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
