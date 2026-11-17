import { useState, useEffect, createContext, useContext } from 'react';
import axios from 'axios';
import {
  LayoutDashboard, Wallet, FileText, CalendarDays, Lock,
  BarChart3, CheckSquare, Bell, ArrowUpRight, ArrowDownRight,
  CheckCircle2, XCircle, Download, AlertCircle, TrendingDown,
  FileSpreadsheet, ShieldAlert, LogOut, User as UserIcon,
  Clock, Eye, MessageSquare, CreditCard, X, Loader2,
  ClipboardCheck, Banknote, Users, ScrollText,
} from 'lucide-react';
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const API_URL = 'http://127.0.0.1:8000/api';

// ============================================================
// TOAST CONTEXT
// ============================================================
const ToastContext = createContext(null);
const useToast = () => useContext(ToastContext);

const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);
  const push = (message, type = 'success') => {
    const id = Date.now() + Math.random();
    setToasts(t => [...t, { id, message, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000);
  };
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="fixed top-6 right-6 z-50 space-y-3">
        {toasts.map(t => (
          <div key={t.id} className={`px-6 py-4 rounded-2xl shadow-2xl font-bold text-white animate-fade-in ${
            t.type === 'success' ? 'bg-emerald-600' :
            t.type === 'error' ? 'bg-rose-600' : 'bg-slate-800'
          }`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

// ============================================================
// MAIN APP
// ============================================================
function App() {
  return (
    <ToastProvider>
      <AppInner />
    </ToastProvider>
  );
}

function AppInner() {
  const toast = useToast();

  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [page, setPage] = useState(null);
  const [me, setMe] = useState(null);

  const [dashboardData, setDashboardData] = useState(null);
  const [contributions, setContributions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [showNotifPanel, setShowNotifPanel] = useState(false);

  const api = axios.create({
    baseURL: API_URL,
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });

  api.interceptors.response.use(
    res => res,
    err => {
      if (err.response?.status === 401) handleLogout();
      return Promise.reject(err);
    }
  );

  useEffect(() => {
    if (!token) return;
    api.get('/auth/me/').then(res => {
      setMe(res.data);
      if (!page) setPage(defaultPageForRole(res.data));
    }).catch(handleLogout);
    fetchNotifications();
  }, [token]);

  useEffect(() => {
    if (!token || !me) return;
    if (me.role_code === 'MEMBER') {
      if (page === 'member-dashboard') fetchDashboard();
      if (page === 'member-contributions') fetchContributions();
    }
  }, [token, page, me]);

  const defaultPageForRole = (profile) => {
    const role = profile?.role_code;
    if (role === 'MEMBER') return 'member-dashboard';
    if (role === 'TELLER') return 'teller-station';
    if (role === 'ACCOUNTANT') return 'accountant-queue';
    if (role === 'LOAN_OFFICER') return 'loanofficer-queue';
    if (role === 'MANAGER') return 'admin-dashboard';
    if (role === 'CREDIT_COMMITTEE') return 'committee-queue';
    if (role === 'SUPERVISOR') return 'admin-audit';
    if (role === 'BOARD_MEMBER') return 'admin-dashboard';
    if (role === 'SYSTEM_ADMIN') return 'admin-dashboard';
    return 'member-dashboard';
  };

  const fetchDashboard = async () => {
    try {
      const res = await api.get('/member/dashboard/');
      setDashboardData(res.data);
    } catch (err) { console.error(err); }
  };

  const fetchContributions = async () => {
    try {
      const res = await api.get('/member/contributions/');
      setContributions(res.data);
    } catch (err) { setContributions([]); }
  };

  const fetchNotifications = async () => {
    try {
      const res = await api.get('/member/notifications/');
      setNotifications(Array.isArray(res.data) ? res.data : []);
    } catch (err) { setNotifications([]); }
  };

  const handleLogin = async (username, password) => {
    try {
      const res = await axios.post(`${API_URL}/auth/login/`, { username, password });
      localStorage.setItem('token', res.data.access);
      setToken(res.data.access);
      setPage(null);
      setMe(null);
    } catch (err) {
      toast('Invalid credentials', 'error');
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    setToken(null);
    setMe(null);
    setPage(null);
    setDashboardData(null);
    setContributions([]);
    setNotifications([]);
    setShowNotifPanel(false);
  };

  if (!token) return <LoginView onLogin={handleLogin} />;
  if (!me) return <LoadingScreen />;

  return (
    <div className="flex h-screen overflow-hidden text-slate-800">
      <Sidebar me={me} page={page} setPage={setPage} onLogout={handleLogout} />

      <main className="flex-1 overflow-y-auto bg-slate-50 custom-scrollbar relative">
        <TopBar
          notifications={notifications}
          showPanel={showNotifPanel}
          setShowPanel={setShowNotifPanel}
          api={api}
          refresh={fetchNotifications}
        />

        <div className="p-10 max-w-7xl mx-auto">
          <PageRouter
            page={page}
            me={me}
            api={api}
            toast={toast}
            dashboardData={dashboardData}
            contributions={contributions}
            setPage={setPage}
            refreshDashboard={fetchDashboard}
            refreshContributions={fetchContributions}
          />
        </div>
      </main>
    </div>
  );
}

// ============================================================
// PAGE ROUTER
// ============================================================
const PageRouter = ({ page, me, api, toast, dashboardData, contributions, setPage, refreshDashboard, refreshContributions }) => {
  const role = me.role_code;

  if (role === 'MEMBER') {
    if (page === 'member-dashboard') return <MemberDashboard data={dashboardData} setPage={setPage} />;
    if (page === 'member-contributions') return <ContributionsView contributions={contributions} api={api} refresh={refreshContributions} />;
    if (page === 'member-loan-app') return <LoanApplication data={dashboardData} api={api} setPage={setPage} />;
    if (page === 'member-repayments') return <RepaymentSchedule api={api} />;
  }

  if (role === 'TELLER') {
    if (page === 'teller-station') return <TellerStation api={api} toast={toast} />;
    if (page === 'teller-disburse') return <TellerDisburseQueue api={api} toast={toast} />;
  }

  if (role === 'ACCOUNTANT') {
    if (page === 'accountant-queue') return <AccountantQueue api={api} toast={toast} />;
    if (page === 'admin-reports') return <FinancialReports api={api} />;
  }

  if (role === 'LOAN_OFFICER') {
    if (page === 'loanofficer-queue') return <LoanOfficerQueue api={api} toast={toast} />;
    if (page === 'admin-arrears') return <ArrearsTracker api={api} />;
  }

  if (role === 'MANAGER' || role === 'BOARD_MEMBER') {
    if (page === 'admin-dashboard') return <AdminDashboard api={api} />;
    if (page === 'admin-approval') return <ManagerApprovalQueue api={api} toast={toast} />;
    if (page === 'admin-contributions') return <AccountantQueue api={api} toast={toast} />;
    if (page === 'admin-reports') return <FinancialReports api={api} />;
    if (page === 'admin-arrears') return <ArrearsTracker api={api} />;
    if (page === 'admin-members') return <MemberDirectory api={api} />;
  }

  if (role === 'CREDIT_COMMITTEE') {
    if (page === 'committee-queue') return <ManagerApprovalQueue api={api} toast={toast} committeeOnly />;
    if (page === 'admin-dashboard') return <AdminDashboard api={api} />;
    if (page === 'admin-reports') return <FinancialReports api={api} />;
  }

  if (role === 'SUPERVISOR') {
    if (page === 'admin-audit') return <AuditLogViewer api={api} />;
    if (page === 'admin-dashboard') return <AdminDashboard api={api} />;
    if (page === 'admin-reports') return <FinancialReports api={api} />;
  }

  if (role === 'SYSTEM_ADMIN') {
    if (page === 'admin-dashboard') return <AdminDashboard api={api} />;
    if (page === 'admin-approval') return <ManagerApprovalQueue api={api} toast={toast} />;
    if (page === 'admin-contributions') return <AccountantQueue api={api} toast={toast} />;
    if (page === 'admin-reports') return <FinancialReports api={api} />;
    if (page === 'admin-arrears') return <ArrearsTracker api={api} />;
    if (page === 'admin-audit') return <AuditLogViewer api={api} />;
    if (page === 'admin-members') return <MemberDirectory api={api} />;
    if (page === 'admin-users') return <UserManagement api={api} toast={toast} />;
  }

  return <div className="text-slate-400 font-bold">Page not found — {page}</div>;
};

// ============================================================
// SIDEBAR
// ============================================================
const Sidebar = ({ me, page, setPage, onLogout }) => {
  const role = me.role_code;

  const navConfig = {
    MEMBER: {
      label: 'Member Portal',
      items: [
        { id: 'member-dashboard', icon: <LayoutDashboard size={20} />, label: 'Dashboard' },
        { id: 'member-contributions', icon: <Wallet size={20} />, label: 'Contributions' },
        { id: 'member-loan-app', icon: <FileText size={20} />, label: 'Loan Application' },
        { id: 'member-repayments', icon: <CalendarDays size={20} />, label: 'Repayment Schedule' },
      ],
    },
    TELLER: {
      label: 'Teller Station',
      items: [
        { id: 'teller-station', icon: <Wallet size={20} />, label: 'Record Deposit' },
        { id: 'teller-disburse', icon: <CreditCard size={20} />, label: 'Disburse Loans' },
      ],
    },
    ACCOUNTANT: {
      label: 'Accounting',
      items: [
        { id: 'accountant-queue', icon: <CheckSquare size={20} />, label: 'Verify Contributions' },
        { id: 'admin-reports', icon: <FileSpreadsheet size={20} />, label: 'Financial Reports' },
      ],
    },
    LOAN_OFFICER: {
      label: 'Loan Desk',
      items: [
        { id: 'loanofficer-queue', icon: <ClipboardCheck size={20} />, label: 'Review Queue' },
        { id: 'admin-arrears', icon: <ShieldAlert size={20} />, label: 'Arrears' },
      ],
    },
    MANAGER: {
      label: 'Management',
      items: [
        { id: 'admin-dashboard', icon: <BarChart3 size={20} />, label: 'Analytics' },
        { id: 'admin-approval', icon: <CheckSquare size={20} />, label: 'Loan Approvals' },
        { id: 'admin-contributions', icon: <Wallet size={20} />, label: 'Contributions' },
        { id: 'admin-reports', icon: <FileSpreadsheet size={20} />, label: 'Reports' },
        { id: 'admin-arrears', icon: <ShieldAlert size={20} />, label: 'Arrears' },
        { id: 'admin-members', icon: <Users size={20} />, label: 'Members' },
      ],
    },
    CREDIT_COMMITTEE: {
      label: 'Credit Committee',
      items: [
        { id: 'committee-queue', icon: <CheckSquare size={20} />, label: 'Committee Queue' },
        { id: 'admin-dashboard', icon: <BarChart3 size={20} />, label: 'Analytics' },
        { id: 'admin-reports', icon: <FileSpreadsheet size={20} />, label: 'Reports' },
      ],
    },
    BOARD_MEMBER: {
      label: 'Board Oversight',
      items: [
        { id: 'admin-dashboard', icon: <BarChart3 size={20} />, label: 'Analytics' },
        { id: 'admin-reports', icon: <FileSpreadsheet size={20} />, label: 'Reports' },
        { id: 'admin-members', icon: <Users size={20} />, label: 'Members' },
      ],
    },
    SUPERVISOR: {
      label: 'Supervisory',
      items: [
        { id: 'admin-audit', icon: <ScrollText size={20} />, label: 'Audit Log' },
        { id: 'admin-dashboard', icon: <BarChart3 size={20} />, label: 'Analytics' },
        { id: 'admin-reports', icon: <FileSpreadsheet size={20} />, label: 'Reports' },
      ],
    },
    SYSTEM_ADMIN: {
      label: 'System Admin',
      items: [
        { id: 'admin-dashboard', icon: <BarChart3 size={20} />, label: 'Analytics' },
        { id: 'admin-approval', icon: <CheckSquare size={20} />, label: 'Loan Approvals' },
        { id: 'admin-contributions', icon: <Wallet size={20} />, label: 'Contributions' },
        { id: 'admin-reports', icon: <FileSpreadsheet size={20} />, label: 'Reports' },
        { id: 'admin-arrears', icon: <ShieldAlert size={20} />, label: 'Arrears' },
        { id: 'admin-audit', icon: <ScrollText size={20} />, label: 'Audit Log' },
        { id: 'admin-members', icon: <Users size={20} />, label: 'Members' },
        { id: 'admin-users', icon: <UserIcon size={20} />, label: 'User Management' },
      ],
    },
  };

  const config = navConfig[role] || navConfig.MEMBER;

  return (
    <aside className="w-72 bg-gradient-to-b from-slate-900 to-slate-800 text-slate-300 flex flex-col shadow-2xl z-20">
      <div className="p-8 border-b border-slate-700/50 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-indigo-500/30">
          M
        </div>
        <div>
          <h1 className="text-xl font-extrabold text-white tracking-tight">
            MUHAZI <span className="text-indigo-400">SACCO</span>
          </h1>
          <p className="text-xs text-slate-400 font-medium">{me.branch || 'Financial Portal'}</p>
        </div>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto custom-scrollbar">
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3 ml-4">
          {config.label}
        </p>
        {config.items.map(item => (
          <NavBtn
            key={item.id}
            icon={item.icon}
            label={item.label}
            active={page === item.id}
            onClick={() => setPage(item.id)}
          />
        ))}
      </nav>

      <div className="p-6 bg-slate-900/50 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold">
          {(me.display_name || 'U').charAt(0)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-slate-400 font-medium">Logged in as</p>
          <p className="text-sm font-bold text-white truncate">{me.display_name}</p>
          <p className="text-[10px] text-indigo-400 font-bold mt-0.5">{me.role}</p>
        </div>
        <button
          onClick={onLogout}
          className="text-rose-400 hover:text-rose-300 p-2 rounded-lg hover:bg-rose-500/10 transition-colors"
          title="Logout"
        >
          <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
};

const NavBtn = ({ icon, label, active, onClick }) => (
  <button onClick={onClick} className={`w-full flex items-center gap-3 text-left px-4 py-3 rounded-xl transition-all duration-200 group ${
    active ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30' : 'hover:bg-white/10 hover:text-white'
  }`}>
    <span className={active ? 'text-white' : 'text-slate-400 group-hover:text-indigo-400 transition-colors'}>{icon}</span>
    <span className="font-medium">{label}</span>
  </button>
);

// ============================================================
// TOP BAR
// ============================================================
const TopBar = ({ notifications, showPanel, setShowPanel, api, refresh }) => (
  <>
    <div className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200 px-10 py-4 flex justify-between items-center">
      <div className="text-sm text-slate-500 font-medium">
        {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
      </div>
      <button onClick={() => setShowPanel(!showPanel)} className="relative p-2 rounded-full hover:bg-slate-100 transition-colors">
        <Bell size={22} className="text-slate-500" />
        {notifications.filter(n => !n.is_read).length > 0 && (
          <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center">
            {notifications.filter(n => !n.is_read).length}
          </span>
        )}
      </button>
    </div>
    {showPanel && (
      <NotificationPanel
        notifications={notifications}
        api={api}
        onClose={() => setShowPanel(false)}
        refresh={refresh}
      />
    )}
  </>
);

const NotificationPanel = ({ notifications, api, onClose, refresh }) => {
  const markRead = async (id) => {
    try {
      await api.patch('/member/notifications/', { id });
      refresh();
    } catch (err) { console.error(err); }
  };

  return (
    <div className="absolute top-16 right-10 w-96 bg-white rounded-2xl shadow-2xl border border-slate-100 z-30 animate-fade-in max-h-[70vh] flex flex-col">
      <div className="p-5 border-b border-slate-100 flex justify-between items-center">
        <h3 className="font-bold text-slate-800">Notifications</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-sm font-bold">Close</button>
      </div>
      <div className="overflow-y-auto custom-scrollbar flex-1">
        {notifications.length === 0 ? (
          <p className="p-8 text-center text-slate-400 text-sm font-medium">No notifications yet</p>
        ) : notifications.map(n => (
          <div key={n.id} onClick={() => !n.is_read && markRead(n.id)}
            className={`p-4 border-b border-slate-50 cursor-pointer hover:bg-slate-50 transition-colors ${!n.is_read ? 'bg-indigo-50/40' : ''}`}>
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg shrink-0 ${
                n.notification_type === 'LOAN_STATUS' ? 'bg-indigo-100 text-indigo-600' :
                n.notification_type === 'ARREARS' ? 'bg-rose-100 text-rose-600' :
                n.notification_type === 'CONTRIBUTION' ? 'bg-emerald-100 text-emerald-600' :
                'bg-slate-100 text-slate-600'
              }`}>
                <Bell size={16} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-slate-800">{n.title}</p>
                <p className="text-xs text-slate-500 mt-0.5">{n.message}</p>
                <p className="text-[10px] text-slate-400 mt-1">{n.time_ago || new Date(n.created_at).toLocaleString()}</p>
              </div>
              {!n.is_read && <div className="w-2 h-2 rounded-full bg-indigo-500 mt-1"></div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================
// UTILITIES
// ============================================================
const LoadingScreen = () => (
  <div className="h-screen flex items-center justify-center bg-slate-50">
    <div className="text-center">
      <Loader2 size={48} className="animate-spin text-indigo-600 mx-auto mb-4" />
      <p className="text-slate-500 font-bold">Loading MUHAZI SACCO...</p>
    </div>
  </div>
);

const SkeletonLoader = () => (
  <div className="space-y-6 animate-pulse">
    <div className="h-10 bg-slate-200 rounded-xl w-1/3"></div>
    <div className="grid grid-cols-3 gap-6">
      <div className="h-40 bg-slate-200 rounded-3xl"></div>
      <div className="h-40 bg-slate-200 rounded-3xl"></div>
      <div className="h-40 bg-slate-200 rounded-3xl"></div>
    </div>
  </div>
);

const Modal = ({ title, children, onClose }) => (
  <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-40 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full p-8 animate-fade-in" onClick={e => e.stopPropagation()}>
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-2xl font-extrabold text-slate-900">{title}</h3>
        <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100"><X size={20} /></button>
      </div>
      {children}
    </div>
  </div>
);

const StatCard = ({ title, amount, color, trend, icon }) => {
  const colorMap = {
    emerald: { text: 'text-emerald-500', bg: 'bg-emerald-50', textDark: 'text-emerald-700' },
    rose: { text: 'text-rose-500', bg: 'bg-rose-50', textDark: 'text-rose-700' },
  };
  const c = colorMap[color] || colorMap.emerald;
  return (
    <div className="bg-white p-8 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 hover:-translate-y-1 transition-transform duration-300 relative overflow-hidden group">
      <div className={`absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity ${c.text}`}>{icon}</div>
      <p className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-2">{title}</p>
      <p className="text-4xl font-extrabold text-slate-800">{amount}</p>
      <div className={`mt-6 inline-flex items-center gap-1.5 ${c.bg} ${c.textDark} px-3 py-1 rounded-full text-sm font-semibold`}>{trend}</div>
    </div>
  );
};

const AdminStat = ({ title, amount, color }) => {
  const colorMap = { blue: 'bg-blue-500', emerald: 'bg-emerald-500', purple: 'bg-purple-500', amber: 'bg-amber-500', rose: 'bg-rose-500' };
  return (
    <div className="bg-white p-6 rounded-3xl shadow-lg shadow-slate-200/50 border border-slate-100 relative overflow-hidden">
      <div className={`w-2 h-full absolute left-0 top-0 ${colorMap[color] || 'bg-blue-500'}`}></div>
      <p className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-1 ml-4">{title}</p>
      <p className="text-3xl font-extrabold text-slate-800 ml-4">{amount}</p>
    </div>
  );
};

const NoDataOverlay = ({ message = 'No data yet' }) => (
  <div className="absolute inset-0 flex items-center justify-center bg-white/70 backdrop-blur-sm rounded-3xl z-10">
    <div className="text-center">
      <BarChart3 size={48} className="mx-auto text-slate-300 mb-3" />
      <p className="text-slate-400 font-bold">{message}</p>
    </div>
  </div>
);

// ============================================================
// LOGIN
// ============================================================
const LoginView = ({ onLogin }) => {
  const [username, setUsername] = useState('gentil');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);

  const quickLogins = [
    { label: 'Member', username: 'gentil', password: 'password123', color: 'bg-indigo-50 text-indigo-700' },
    { label: 'Teller', username: 'teller', password: 'password123', color: 'bg-emerald-50 text-emerald-700' },
    { label: 'Accountant', username: 'accountant', password: 'password123', color: 'bg-blue-50 text-blue-700' },
    { label: 'Loan Officer', username: 'loanofficer', password: 'password123', color: 'bg-amber-50 text-amber-700' },
    { label: 'Manager', username: 'manager', password: 'password123', color: 'bg-purple-50 text-purple-700' },
    { label: 'Supervisor', username: 'supervisor', password: 'password123', color: 'bg-slate-100 text-slate-700' },
    { label: 'Admin', username: 'admin', password: 'admin123', color: 'bg-rose-50 text-rose-700' },
  ];

  return (
    <div className="h-screen flex flex-col items-center justify-center bg-slate-50 animate-fade-in p-4">
      <div className="mb-8 text-center">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center text-white font-bold text-3xl shadow-lg shadow-indigo-500/30 mb-4">M</div>
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">MUHAZI SACCO Portal</h2>
        <p className="text-slate-500 font-medium mt-1">Secure Access</p>
      </div>
      <div className="bg-white p-10 rounded-3xl shadow-2xl shadow-slate-200/80 border border-slate-100 w-full max-w-md">
        <form onSubmit={async (e) => { e.preventDefault(); setLoading(true); await onLogin(username, password); setLoading(false); }}>
          <div className="mb-5">
            <label className="block text-sm font-bold text-slate-700 mb-2">Username</label>
            <input type="text" value={username} onChange={e => setUsername(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-900 rounded-xl p-4 focus:ring-2 focus:ring-slate-900 outline-none font-semibold" required />
          </div>
          <div className="mb-8">
            <label className="block text-sm font-bold text-slate-700 mb-2">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-900 rounded-xl p-4 focus:ring-2 focus:ring-slate-900 outline-none font-semibold" required />
          </div>
          <button type="submit" disabled={loading}
            className="w-full bg-slate-900 text-white font-bold px-6 py-4 rounded-xl shadow-lg shadow-slate-900/30 hover:bg-slate-800 transition-colors flex justify-center items-center gap-2 disabled:opacity-50">
            {loading ? <Loader2 size={20} className="animate-spin" /> : <Lock size={20} />}
            {loading ? 'Authenticating...' : 'Secure Authenticate'}
          </button>
        </form>
        <div className="mt-6 p-4 bg-slate-50 rounded-xl">
          <p className="text-xs font-bold text-slate-600 uppercase mb-2">Quick Login</p>
          <div className="grid grid-cols-2 gap-2">
            {quickLogins.map(q => (
              <button key={q.label} onClick={() => { setUsername(q.username); setPassword(q.password); }}
                className={`text-xs font-bold px-3 py-2 rounded-lg ${q.color} hover:opacity-80 transition-opacity`}>
                {q.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// MEMBER PAGES
// ============================================================
const MemberDashboard = ({ data, setPage }) => {
  if (!data) return <SkeletonLoader />;
  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Welcome back, {(data.member_name || 'Member').split(' ').slice(-1)[0]} 👋
        </h2>
        <p className="text-slate-500 mt-2 font-medium">Here is your financial overview.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <StatCard title="Total Savings Balance" amount={`RWF ${(data.total_savings / 1000000).toFixed(2)}M`} color="emerald" trend="Verified contributions" icon={<Wallet size={96} />} />
        <StatCard title="Active Loan Balance" amount={`RWF ${(data.active_loan_balance / 1000).toFixed(0)}K`} color="rose" trend={data.outstanding_repayments ? 'Outstanding repayments' : 'No active loan'} icon={<FileText size={96} />} />
        <div className="bg-gradient-to-br from-indigo-600 to-blue-700 p-8 rounded-3xl shadow-xl shadow-indigo-500/30 text-white hover:-translate-y-1 transition-transform duration-300 relative overflow-hidden">
          <div className="absolute -bottom-10 -right-10 opacity-20"><ArrowUpRight size={160} /></div>
          <p className="text-sm font-bold text-indigo-200 uppercase tracking-wider mb-2">Max Loan Eligibility</p>
          <p className="text-4xl font-extrabold text-white">RWF {(data.max_loan_eligibility / 1000000).toFixed(2)}M</p>
          <div className="mt-6 inline-flex items-center gap-1.5 bg-white/20 backdrop-blur-sm text-white px-3 py-1 rounded-full text-sm font-semibold">
            <ArrowUpRight size={16} /> 3x savings − loans
          </div>
        </div>
      </div>

      <div className="bg-white p-8 rounded-3xl shadow-lg border border-slate-100 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-gradient-to-r from-white to-slate-50">
        <div>
          <h3 className="text-xl font-bold text-slate-800">Ready to make a move?</h3>
          <p className="text-slate-500 font-medium mt-1">Manage your contributions or request new financial support.</p>
        </div>
        <div className="flex gap-4">
          <button onClick={() => setPage('member-contributions')} className="bg-indigo-600 text-white font-bold px-8 py-3 rounded-xl shadow-lg shadow-indigo-500/30 hover:bg-indigo-700 transition-colors">Deposit Funds</button>
          <button onClick={() => setPage('member-loan-app')} className="bg-white text-indigo-600 font-bold border-2 border-indigo-100 px-8 py-3 rounded-xl hover:border-indigo-600 hover:bg-indigo-50 transition-colors">Apply for Loan</button>
        </div>
      </div>
    </div>
  );
};

const ContributionsView = ({ contributions, api, refresh }) => {
  const toast = useToast();
  const [amount, setAmount] = useState('');
  const [refCode, setRefCode] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/member/contributions/', { amount, reference_code: refCode });
      refresh();
      setAmount(''); setRefCode('');
      toast('Deposit submitted — awaiting accountant verification', 'success');
    } catch (err) {
      const msg = err.response?.data?.reference_code?.[0] || err.response?.data?.error || 'Error logging deposit';
      toast(msg, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const statusBadge = (status) => {
    const map = {
      VERIFIED: 'bg-emerald-100 text-emerald-700',
      PENDING_VERIFICATION: 'bg-amber-100 text-amber-700',
      REJECTED: 'bg-rose-100 text-rose-700',
    };
    return (
      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold ${map[status] || 'bg-slate-100 text-slate-600'}`}>
        {status.replace('_', ' ')}
      </span>
    );
  };

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Contributions & History</h2>
        <p className="text-slate-500 mt-2 font-medium">Log new deposits and review your past savings transactions.</p>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="bg-white p-8 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 lg:col-span-1 h-fit">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-emerald-100 rounded-lg text-emerald-600"><ArrowDownRight size={24} /></div>
            <h3 className="text-xl font-bold text-slate-800">Log Deposit</h3>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="mb-5">
              <label className="block text-sm font-bold text-slate-700 mb-2">Amount (RWF)</label>
              <input type="number" value={amount} onChange={e => setAmount(e.target.value)} min="1"
                className="w-full bg-slate-50 border border-slate-200 text-slate-900 rounded-xl p-3 focus:ring-2 focus:ring-indigo-500 outline-none font-semibold" placeholder="0.00" required />
            </div>
            <div className="mb-8">
              <label className="block text-sm font-bold text-slate-700 mb-2">MoMo Reference Code</label>
              <input type="text" value={refCode} onChange={e => setRefCode(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 text-slate-900 rounded-xl p-3 focus:ring-2 focus:ring-indigo-500 outline-none font-semibold" placeholder="e.g. 123456789" required />
            </div>
            <button type="submit" disabled={submitting}
              className="w-full bg-indigo-600 text-white font-bold px-4 py-3.5 rounded-xl shadow-lg shadow-indigo-500/30 hover:bg-indigo-700 transition-colors disabled:opacity-50">
              {submitting ? 'Submitting...' : 'Submit for Verification'}
            </button>
            <p className="text-xs text-slate-400 mt-3 text-center">Accountant will verify your deposit shortly.</p>
          </form>
        </div>

        <div className="bg-white rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 lg:col-span-2 overflow-hidden">
          <div className="p-8 border-b border-slate-100 bg-slate-50/50">
            <h3 className="text-xl font-bold text-slate-800">Transaction Ledger</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Date</th>
                  <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Amount</th>
                  <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Reference</th>
                  <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {contributions.length === 0 ? (
                  <tr><td colSpan="4" className="px-8 py-8 text-center text-slate-400 font-medium">No contributions yet.</td></tr>
                ) : contributions.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-8 py-5 text-sm font-semibold text-slate-600">{new Date(c.payment_date).toLocaleDateString()}</td>
                    <td className="px-8 py-5 text-sm font-extrabold text-slate-900">{parseFloat(c.amount).toLocaleString()}</td>
                    <td className="px-8 py-5 text-sm font-medium text-slate-400">{c.reference_code}</td>
                    <td className="px-8 py-5">{statusBadge(c.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

const LoanApplication = ({ data, api, setPage }) => {
  const toast = useToast();
  const [amount, setAmount] = useState('');
  const [purpose, setPurpose] = useState('');
  const [term, setTerm] = useState(3);
  const [message, setMessage] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await api.post('/member/loan/apply/', { requested_amount: amount, purpose, term_months: term });
      setMessage({ type: 'success', text: res.data.reply });
      toast('Application submitted', 'success');
      setTimeout(() => setPage('member-dashboard'), 2500);
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.reply || 'Error submitting application' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Apply for a Loan</h2>
        <p className="text-slate-500 mt-2 font-medium">Request financial support based on your savings multiplier.</p>
      </header>
      <div className="bg-white p-10 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 max-w-3xl mx-auto">
        <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-6 mb-8 flex gap-4 items-start">
          <div className="p-3 bg-indigo-100 rounded-full text-indigo-600 shrink-0"><AlertCircle size={24} /></div>
          <div>
            <h4 className="font-bold text-indigo-900">Eligibility Notice</h4>
            <p className="text-sm text-indigo-700 mt-1 font-medium">
              Your max loan is <strong className="text-indigo-900">RWF {parseFloat(data?.max_loan_eligibility || 0).toLocaleString()}</strong>. Interest rate: 5%.
            </p>
          </div>
        </div>
        {message && (
          <div className={`mb-6 p-4 rounded-xl font-bold ${message.type === 'success' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
            {message.text}
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Requested Amount (RWF)</label>
              <input type="number" value={amount} onChange={e => setAmount(e.target.value)} max={data?.max_loan_eligibility} min="1"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3.5 focus:ring-2 focus:ring-indigo-500 outline-none font-semibold" placeholder="Enter amount..." required />
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Repayment Period</label>
              <select value={term} onChange={e => setTerm(Number(e.target.value))}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3.5 focus:ring-2 focus:ring-indigo-500 outline-none font-semibold cursor-pointer">
                <option value={3}>3 Months</option>
                <option value={6}>6 Months</option>
                <option value={12}>12 Months</option>
                <option value={24}>24 Months</option>
              </select>
            </div>
          </div>
          <div className="mb-8">
            <label className="block text-sm font-bold text-slate-700 mb-2">Purpose of Loan</label>
            <textarea value={purpose} onChange={e => setPurpose(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 h-32 focus:ring-2 focus:ring-indigo-500 outline-none font-semibold resize-none"
              placeholder="Briefly describe the purpose..."></textarea>
          </div>
          <button type="submit" disabled={submitting}
            className="w-full bg-indigo-600 text-white text-lg font-bold px-6 py-4 rounded-xl shadow-lg shadow-indigo-500/30 hover:bg-indigo-700 transition-colors disabled:opacity-50">
            {submitting ? 'Submitting...' : 'Submit Application'}
          </button>
        </form>
      </div>
    </div>
  );
};

const RepaymentSchedule = ({ api }) => {
  const toast = useToast();
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showPayModal, setShowPayModal] = useState(false);
  const [payAmount, setPayAmount] = useState('');

  const fetchSchedule = () => {
    setLoading(true);
    api.get('/member/repayments/')
      .then(res => setSchedule(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchSchedule(); }, []);

  const handlePayment = async () => {
    try {
      await api.post('/member/pay-installment/', { loan_id: schedule.loan_id, amount: payAmount });
      toast(`Payment of RWF ${Number(payAmount).toLocaleString()} received`, 'success');
      setShowPayModal(false);
      setPayAmount('');
      fetchSchedule();
    } catch (err) {
      toast(err.response?.data?.error || 'Payment failed', 'error');
    }
  };

  if (loading) return <SkeletonLoader />;
  if (!schedule) return <div className="text-slate-400 font-bold">Loading...</div>;
  if (schedule.message) {
    return (
      <div className="animate-fade-in">
        <header className="mb-10">
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Repayment Schedule</h2>
        </header>
        <div className="bg-white rounded-3xl p-16 shadow-xl border border-slate-100 text-center">
          <CheckCircle2 size={48} className="mx-auto text-emerald-400 mb-4" />
          <p className="text-slate-600 font-bold text-lg">{schedule.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Repayment Schedule</h2>
        <p className="text-slate-500 mt-2 font-medium">Track your active loans and upcoming payment deadlines.</p>
      </header>

      <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden max-w-4xl">
        <div className="p-8 bg-gradient-to-r from-slate-900 to-slate-800 text-white flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-4">
            <div className="p-4 bg-white/10 rounded-2xl backdrop-blur-sm border border-white/20"><FileText size={32} className="text-indigo-400" /></div>
            <div>
              <p className="text-sm font-medium text-slate-400">Active Loan <span className="text-white font-bold tracking-widest ml-1">#LN-{schedule.loan_id}</span></p>
              <p className="text-2xl font-extrabold mt-1">Remaining: RWF {parseFloat(schedule.remaining_balance).toLocaleString()}</p>
              <p className="text-xs text-slate-400 mt-1">Paid: RWF {parseFloat(schedule.total_paid).toLocaleString()} ({schedule.progress_percent}%)</p>
            </div>
          </div>
          <button onClick={() => setShowPayModal(true)}
            className="bg-indigo-500 text-white font-bold px-6 py-3 rounded-xl shadow-lg shadow-indigo-500/30 hover:bg-indigo-400 transition-colors whitespace-nowrap flex items-center gap-2">
            <CreditCard size={18} /> Pay Installment
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Due Date</th>
                <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Principal</th>
                <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Interest</th>
                <th className="px-8 py-4 text-xs font-bold text-slate-800 uppercase">Total Due</th>
                <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {schedule.schedule.map((s, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className={`px-8 py-5 text-sm font-semibold ${s.status === 'Overdue' ? 'text-rose-600' : 'text-slate-700'}`}>{s.due_date}</td>
                  <td className="px-8 py-5 text-sm font-semibold text-slate-700">{Number(s.principal).toLocaleString()}</td>
                  <td className="px-8 py-5 text-sm font-semibold text-slate-700">{Number(s.interest).toLocaleString()}</td>
                  <td className="px-8 py-5 text-sm font-extrabold text-slate-900">{Number(s.total_due).toLocaleString()}</td>
                  <td className="px-8 py-5">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold ${
                      s.status === 'Overdue' ? 'bg-rose-100 text-rose-700' :
                      s.status === 'Pending' ? 'bg-amber-100 text-amber-700' :
                      s.status === 'Cleared' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'
                    }`}>{s.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showPayModal && (
        <Modal title="Pay Installment" onClose={() => setShowPayModal(false)}>
          <p className="text-slate-500 mb-4 font-medium">
            Remaining: <strong className="text-slate-900">RWF {parseFloat(schedule.remaining_balance).toLocaleString()}</strong>
          </p>
          <div className="mb-6">
            <label className="block text-sm font-bold text-slate-700 mb-2">Amount to Pay (RWF)</label>
            <input type="number" value={payAmount} onChange={e => setPayAmount(e.target.value)} min="1"
              className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-lg" placeholder="0" />
          </div>
          <div className="flex gap-3">
            <button onClick={() => setShowPayModal(false)} className="flex-1 bg-slate-100 text-slate-700 font-bold py-3 rounded-xl hover:bg-slate-200">Cancel</button>
            <button onClick={handlePayment} disabled={!payAmount || Number(payAmount) <= 0}
              className="flex-1 bg-indigo-600 text-white font-bold py-3 rounded-xl hover:bg-indigo-700 disabled:opacity-50">Confirm Payment</button>
          </div>
        </Modal>
      )}
    </div>
  );
};

// ============================================================
// TELLER PAGES
// ============================================================
const TellerStation = ({ api, toast }) => {
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedMember, setSelectedMember] = useState(null);
  const [amount, setAmount] = useState('');
  const [refCode, setRefCode] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get('/admin/members/').then(res => setMembers(res.data)).catch(console.error);
  }, []);

  const filtered = members.filter(m =>
    m.full_name.toLowerCase().includes(search.toLowerCase()) ||
    m.national_id.includes(search) ||
    m.phone_number.includes(search)
  );

  const handleRecord = async (e) => {
    e.preventDefault();
    if (!selectedMember) return toast('Select a member first', 'error');
    setSubmitting(true);
    try {
      await api.post('/admin/contributions/record/', {
        member_id: selectedMember.id,
        amount,
        reference_code: refCode,
      });
      toast(`Deposit of RWF ${Number(amount).toLocaleString()} recorded for ${selectedMember.full_name}`, 'success');
      setAmount(''); setRefCode(''); setSelectedMember(null);
    } catch (err) {
      toast(err.response?.data?.error || 'Failed to record', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Teller Station</h2>
        <p className="text-slate-500 mt-2 font-medium">Record member deposits at the counter.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-8 rounded-3xl shadow-xl border border-slate-100">
          <h3 className="text-xl font-bold text-slate-800 mb-4">1. Find Member</h3>
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 mb-4 focus:ring-2 focus:ring-indigo-500 outline-none font-semibold"
            placeholder="Search name, ID, or phone..." />
          <div className="max-h-96 overflow-y-auto custom-scrollbar space-y-2">
            {filtered.slice(0, 20).map(m => (
              <button key={m.id} onClick={() => setSelectedMember(m)}
                className={`w-full text-left p-4 rounded-xl transition-all ${
                  selectedMember?.id === m.id ? 'bg-indigo-600 text-white shadow-lg' : 'bg-slate-50 hover:bg-slate-100'
                }`}>
                <p className="font-bold">{m.full_name}</p>
                <p className={`text-xs ${selectedMember?.id === m.id ? 'text-indigo-200' : 'text-slate-500'}`}>
                  {m.national_id} • {m.phone_number} • Savings: RWF {parseFloat(m.total_savings).toLocaleString()}
                </p>
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white p-8 rounded-3xl shadow-xl border border-slate-100">
          <h3 className="text-xl font-bold text-slate-800 mb-4">2. Record Deposit</h3>
          {selectedMember ? (
            <form onSubmit={handleRecord}>
              <div className="p-4 bg-indigo-50 rounded-xl mb-6">
                <p className="text-sm text-indigo-700 font-medium">Recording for:</p>
                <p className="text-lg font-bold text-indigo-900">{selectedMember.full_name}</p>
                <p className="text-xs text-indigo-600">Current savings: RWF {parseFloat(selectedMember.total_savings).toLocaleString()}</p>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-bold text-slate-700 mb-2">Amount (RWF)</label>
                <input type="number" value={amount} onChange={e => setAmount(e.target.value)} min="1"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 focus:ring-2 focus:ring-indigo-500 outline-none font-semibold" required />
              </div>
              <div className="mb-6">
                <label className="block text-sm font-bold text-slate-700 mb-2">MoMo Reference</label>
                <input type="text" value={refCode} onChange={e => setRefCode(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 focus:ring-2 focus:ring-indigo-500 outline-none font-semibold" required />
              </div>
              <button type="submit" disabled={submitting}
                className="w-full bg-emerald-600 text-white font-bold py-3 rounded-xl hover:bg-emerald-700 disabled:opacity-50">
                {submitting ? 'Recording...' : 'Record Deposit'}
              </button>
            </form>
          ) : (
            <div className="text-center py-10 text-slate-400 font-bold">
              <UserIcon size={48} className="mx-auto mb-3 text-slate-300" />
              Select a member from the left
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const TellerDisburseQueue = ({ api, toast }) => {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    setLoading(true);
    api.get('/admin/loans/approval-queue/')
      .then(res => {
        setLoans(res.data.filter(l => l.status === 'APPROVED' || l.status === 'UNDER_REVIEW'));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const disburse = async (loanId) => {
    try {
      await api.patch('/admin/loans/workflow/', { loan_id: loanId, action: 'disburse' });
      toast('Loan disbursed', 'success');
      fetch();
    } catch (err) {
      toast(err.response?.data?.error || 'Disbursement failed', 'error');
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Disbursement Queue</h2>
        <p className="text-slate-500 mt-2 font-medium">Loans approved by management — ready to disburse.</p>
      </header>
      <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Member</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Amount</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Term</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Approved By</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loans.length === 0 ? (
              <tr><td colSpan="5" className="px-8 py-10 text-center text-slate-400 font-bold">
                <CheckCircle2 size={32} className="mx-auto text-emerald-400 mb-2" />
                No approved loans awaiting disbursement
              </td></tr>
            ) : loans.map(l => (
              <tr key={l.id} className="hover:bg-slate-50">
                <td className="px-8 py-5 font-bold text-slate-800">{l.member_name}</td>
                <td className="px-8 py-5 font-extrabold">RWF {parseFloat(l.principal_amount).toLocaleString()}</td>
                <td className="px-8 py-5">{l.term_months} months</td>
                <td className="px-8 py-5 text-sm text-slate-500">{l.approved_by_name || '—'}</td>
                <td className="px-8 py-5 text-right">
                  <button onClick={() => disburse(l.id)}
                    className="bg-emerald-600 text-white font-bold px-4 py-2 rounded-lg text-xs hover:bg-emerald-700">
                    Disburse
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================
// ACCOUNTANT PAGE
// ============================================================
const AccountantQueue = ({ api, toast }) => {
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    setLoading(true);
    api.get('/admin/contributions/pending/')
      .then(res => setPending(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const verify = async (id, action, reason = '') => {
    try {
      await api.patch('/admin/contributions/verify/', { contribution_id: id, action, reason });
      toast(`Contribution ${action}d`, 'success');
      fetch();
    } catch (err) {
      toast(err.response?.data?.error || 'Action failed', 'error');
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Contribution Verification</h2>
        <p className="text-slate-500 mt-2 font-medium">Verify MoMo references against your statement before approving.</p>
      </header>
      {pending.length === 0 ? (
        <div className="bg-white rounded-3xl p-16 shadow-xl border text-center">
          <CheckCircle2 size={48} className="mx-auto text-emerald-400 mb-4" />
          <p className="text-slate-600 font-bold text-lg">No pending contributions</p>
        </div>
      ) : (
        <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Member</th>
                <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Amount</th>
                <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Reference</th>
                <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Recorded By</th>
                <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {pending.map(c => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="px-8 py-5 font-bold text-slate-800">{c.member_name}</td>
                  <td className="px-8 py-5 font-extrabold">RWF {c.amount.toLocaleString()}</td>
                  <td className="px-8 py-5 font-mono text-sm text-slate-600">{c.reference_code}</td>
                  <td className="px-8 py-5 text-xs text-slate-500">{c.recorded_by}</td>
                  <td className="px-8 py-5 text-right">
                    <div className="flex justify-end gap-2">
                      <button onClick={() => verify(c.id, 'verify')}
                        className="bg-emerald-600 text-white font-bold px-4 py-2 rounded-lg text-xs hover:bg-emerald-700">Verify</button>
                      <button onClick={() => {
                        const reason = window.prompt('Rejection reason:');
                        if (reason) verify(c.id, 'reject', reason);
                      }}
                        className="bg-white border border-rose-200 text-rose-600 font-bold px-4 py-2 rounded-lg text-xs hover:bg-rose-50">Reject</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// ============================================================
// LOAN OFFICER PAGE
// ============================================================
const LoanOfficerQueue = ({ api, toast }) => {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    setLoading(true);
    api.get('/admin/loans/review-queue/')
      .then(res => setLoans(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const review = async (loanId) => {
    try {
      await api.patch('/admin/loans/workflow/', { loan_id: loanId, action: 'review' });
      toast('Loan marked as reviewed — sent to Manager queue', 'success');
      fetch();
    } catch (err) {
      toast(err.response?.data?.error || 'Review failed', 'error');
    }
  };

  const reject = async (loanId) => {
    const reason = window.prompt('Rejection reason:');
    if (!reason) return;
    try {
      await api.patch('/admin/loans/workflow/', { loan_id: loanId, action: 'reject', reason });
      toast('Loan rejected', 'success');
      fetch();
    } catch (err) {
      toast(err.response?.data?.error || 'Rejection failed', 'error');
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Loan Review Queue</h2>
        <p className="text-slate-500 mt-2 font-medium">Review new applications and forward to management.</p>
      </header>
      <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Applicant</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Amount</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Savings</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Purpose</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Eligibility</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loans.length === 0 ? (
              <tr><td colSpan="6" className="px-8 py-10 text-center text-slate-400 font-bold">
                <CheckCircle2 size={32} className="mx-auto text-emerald-400 mb-2" />
                Queue is clear
              </td></tr>
            ) : loans.map(l => (
              <tr key={l.id} className="hover:bg-slate-50">
                <td className="px-8 py-5 font-bold text-slate-800">{l.member_name}</td>
                <td className="px-8 py-5 font-extrabold">RWF {l.principal_amount.toLocaleString()}</td>
                <td className="px-8 py-5 text-sm text-slate-500">RWF {l.current_savings.toLocaleString()}</td>
                <td className="px-8 py-5 text-sm text-slate-500 max-w-xs truncate">{l.purpose || '—'}</td>
                <td className="px-8 py-5">
                  {l.is_valid ? (
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-emerald-100 text-emerald-700 rounded-lg text-xs font-bold">
                      <CheckCircle2 size={12} /> Valid
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-rose-100 text-rose-700 rounded-lg text-xs font-bold">
                      <XCircle size={12} /> Exceeds
                    </span>
                  )}
                </td>
                <td className="px-8 py-5 text-right">
                  <div className="flex justify-end gap-2">
                    <button onClick={() => review(l.id)} disabled={!l.is_valid}
                      className={`font-bold px-3 py-2 rounded-lg text-xs ${
                        l.is_valid ? 'bg-slate-900 text-white hover:bg-slate-800' : 'bg-slate-300 text-white cursor-not-allowed'
                      }`}>Review</button>
                    <button onClick={() => reject(l.id)}
                      className="bg-white border border-rose-200 text-rose-600 font-bold px-3 py-2 rounded-lg text-xs hover:bg-rose-50">Reject</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================
// MANAGER / COMMITTEE APPROVAL QUEUE
// ============================================================
const ManagerApprovalQueue = ({ api, toast, committeeOnly = false }) => {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    setLoading(true);
    api.get('/admin/loans/approval-queue/')
      .then(res => {
        let filtered = res.data;
        if (committeeOnly) filtered = filtered.filter(l => l.requires_committee);
        setLoans(filtered);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const approve = async (loanId) => {
    try {
      await api.patch('/admin/loans/workflow/', { loan_id: loanId, action: 'approve' });
      toast('Loan approved', 'success');
      fetch();
    } catch (err) {
      toast(err.response?.data?.error || 'Approval failed', 'error');
    }
  };

  const reject = async (loanId) => {
    const reason = window.prompt('Rejection reason:');
    if (!reason) return;
    try {
      await api.patch('/admin/loans/workflow/', { loan_id: loanId, action: 'reject', reason });
      toast('Loan rejected', 'success');
      fetch();
    } catch (err) {
      toast(err.response?.data?.error || 'Rejection failed', 'error');
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          {committeeOnly ? 'Committee Approval Queue' : 'Loan Approval Queue'}
        </h2>
        <p className="text-slate-500 mt-2 font-medium">
          {committeeOnly ? 'Loans ≥ RWF 2,000,000 requiring committee sign-off.' : 'Loans reviewed by Loan Officers, awaiting final approval.'}
        </p>
      </header>
      <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Applicant</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Amount</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Reviewed By</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Type</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loans.length === 0 ? (
              <tr><td colSpan="5" className="px-8 py-10 text-center text-slate-400 font-bold">
                <CheckCircle2 size={32} className="mx-auto text-emerald-400 mb-2" />
                No loans awaiting approval
              </td></tr>
            ) : loans.map(l => (
              <tr key={l.id} className="hover:bg-slate-50">
                <td className="px-8 py-5 font-bold text-slate-800">{l.member_name}</td>
                <td className="px-8 py-5 font-extrabold">RWF {l.principal_amount.toLocaleString()}</td>
                <td className="px-8 py-5 text-sm text-slate-500">{l.reviewed_by || '—'}</td>
                <td className="px-8 py-5">
                  {l.requires_committee ? (
                    <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-lg text-xs font-bold">Committee</span>
                  ) : (
                    <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-lg text-xs font-bold">Standard</span>
                  )}
                </td>
                <td className="px-8 py-5 text-right">
                  <div className="flex justify-end gap-2">
                    <button onClick={() => approve(l.id)}
                      className="bg-emerald-600 text-white font-bold px-4 py-2 rounded-lg text-xs hover:bg-emerald-700">Approve</button>
                    <button onClick={() => reject(l.id)}
                      className="bg-white border border-rose-200 text-rose-600 font-bold px-4 py-2 rounded-lg text-xs hover:bg-rose-50">Reject</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================
// ADMIN DASHBOARD — WITH INTERACTIVE CHARTS
// ============================================================
const AdminDashboard = ({ api }) => {
  const [data, setData] = useState(null);
  const [charts, setCharts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [chartError, setChartError] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get('/admin/analytics/'),
      api.get('/admin/analytics/charts/'),
    ])
      .then(([analyticsRes, chartsRes]) => {
        setData(analyticsRes.data);
        setCharts(chartsRes.data);
      })
      .catch(err => {
        console.error(err);
        setChartError('Failed to load chart data');
        // Still try to load basic analytics
        api.get('/admin/analytics/').then(r => setData(r.data)).catch(console.error);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) return <SkeletonLoader />;

  const CHART_COLORS = {
    PENDING: '#f59e0b',
    UNDER_REVIEW: '#3b82f6',
    APPROVED: '#8b5cf6',
    DISBURSED: '#10b981',
    CLOSED: '#64748b',
    REJECTED: '#ef4444',
  };

  return (
    <div className="animate-fade-in">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Financial Analytics</h2>
          <p className="text-slate-500 mt-2 font-medium">Cooperative performance overview.</p>
        </div>
        <div className="bg-indigo-100 text-indigo-800 px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 border border-indigo-200">
          <CalendarDays size={16} /> {new Date().toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}
        </div>
      </header>

      {/* KPI CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <AdminStat title="Total Liquidity" amount={`RWF ${(data.total_liquidity / 1000000).toFixed(2)}M`} color="blue" />
        <AdminStat title="Disbursed Loans" amount={`RWF ${(data.disbursed_loans / 1000000).toFixed(2)}M`} color="emerald" />
        <AdminStat title="Interest Revenue" amount={`RWF ${(data.interest_revenue / 1000).toFixed(1)}K`} color="purple" />
        <AdminStat title="Pending Loans" amount={data.pending_loans} color="amber" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-3xl shadow-lg border">
          <p className="text-sm font-bold text-slate-400 uppercase mb-1">Total Members</p>
          <p className="text-3xl font-extrabold">{data.total_members}</p>
        </div>
        <div className="bg-white p-6 rounded-3xl shadow-lg border">
          <p className="text-sm font-bold text-slate-400 uppercase mb-1">Active Members</p>
          <p className="text-3xl font-extrabold">{data.active_members}</p>
        </div>
        <div className="bg-amber-50 p-6 rounded-3xl shadow-lg border border-amber-200">
          <p className="text-sm font-bold text-amber-700 uppercase mb-1">Pending Contributions</p>
          <p className="text-3xl font-extrabold text-amber-900">{data.pending_contributions}</p>
        </div>
      </div>

      {chartError && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-6 text-amber-800 font-bold text-sm">
          ⚠ {chartError} — stats above are still accurate.
        </div>
      )}

      {charts && (
        <>
          {/* CHART 1: Member Growth vs Loan Disbursements */}
          <div className="bg-white p-8 rounded-3xl shadow-xl border border-slate-100 mb-8 relative">
            <div className="flex justify-between items-start mb-6 flex-wrap gap-4">
              <div>
                <h3 className="text-xl font-bold text-slate-800">Member Growth vs Loan Disbursements</h3>
                <p className="text-slate-500 text-sm font-medium mt-1">Last 12 months</p>
              </div>
              <div className="flex gap-4 text-xs font-bold">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-indigo-500"></div>
                  <span className="text-slate-600">Members</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                  <span className="text-slate-600">Disbursed (RWF)</span>
                </div>
              </div>
            </div>
            {charts.member_growth.every(d => d.count === 0) &&
             charts.loan_disbursements.every(d => d.amount === 0) && (
              <NoDataOverlay message="No data in the last 12 months" />
            )}
            <ResponsiveContainer width="100%" height={340}>
              <LineChart
                data={charts.member_growth.map((m, i) => ({
                  label: m.label,
                  members: m.count,
                  disbursed: charts.loan_disbursements[i]?.amount || 0,
                }))}
                margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="label"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  angle={-30}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  label={{ value: 'Members', angle: -90, position: 'insideLeft', fill: '#6366f1', fontSize: 12 }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`}
                  label={{ value: 'RWF', angle: 90, position: 'insideRight', fill: '#10b981', fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                  formatter={(value, name) => {
                    if (name === 'disbursed') return [`RWF ${value.toLocaleString()}`, 'Disbursed'];
                    return [value, 'Members'];
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="members"
                  name="Members"
                  stroke="#6366f1"
                  strokeWidth={3}
                  dot={{ fill: '#6366f1', r: 4 }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="disbursed"
                  name="Disbursed (RWF)"
                  stroke="#10b981"
                  strokeWidth={3}
                  dot={{ fill: '#10b981', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* CHART 2 & 3 SIDE BY SIDE */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            {/* Contribution Inflow */}
            <div className="bg-white p-8 rounded-3xl shadow-xl border border-slate-100 relative">
              <h3 className="text-lg font-bold text-slate-800 mb-1">Contribution Inflow</h3>
              <p className="text-slate-500 text-xs font-medium mb-6">Monthly verified contributions</p>
              {charts.contributions_by_month.every(d => d.amount === 0) && (
                <NoDataOverlay message="No contributions yet" />
              )}
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart
                  data={charts.contributions_by_month}
                  margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
                >
                  <defs>
                    <linearGradient id="contribGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                    angle={-30}
                    textAnchor="end"
                    height={50}
                  />
                  <YAxis
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                    tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                    formatter={(value) => [`RWF ${value.toLocaleString()}`, 'Contributions']}
                  />
                  <Area
                    type="monotone"
                    dataKey="amount"
                    stroke="#6366f1"
                    strokeWidth={3}
                    fill="url(#contribGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Loan Status Distribution */}
            <div className="bg-white p-8 rounded-3xl shadow-xl border border-slate-100 relative">
              <h3 className="text-lg font-bold text-slate-800 mb-1">Loan Status Distribution</h3>
              <p className="text-slate-500 text-xs font-medium mb-6">All loans by workflow state</p>
              {charts.loan_status_distribution.length === 0 && (
                <NoDataOverlay message="No loans yet" />
              )}
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={charts.loan_status_distribution}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    innerRadius={50}
                    paddingAngle={3}
                    label={({ label, count }) => `${label}: ${count}`}
                    labelLine={{ stroke: '#94a3b8' }}
                  >
                    {charts.loan_status_distribution.map((entry, i) => (
                      <Cell key={i} fill={CHART_COLORS[entry.status] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                    formatter={(value, name) => [`${value} loans`, name]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* CHART 4: Top Members by Savings */}
          <div className="bg-white p-8 rounded-3xl shadow-xl border border-slate-100 mb-8 relative">
            <h3 className="text-lg font-bold text-slate-800 mb-1">Top 10 Members by Savings</h3>
            <p className="text-slate-500 text-xs font-medium mb-6">Highest verified savings balances</p>
            {charts.top_members.length === 0 && <NoDataOverlay message="No savings recorded yet" />}
            <ResponsiveContainer width="100%" height={340}>
              <BarChart
                data={charts.top_members}
                layout="vertical"
                margin={{ top: 5, right: 40, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={180}
                  tick={{ fill: '#475569', fontSize: 11, fontWeight: 'bold' }}
                />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                  formatter={(value) => [`RWF ${value.toLocaleString()}`, 'Savings']}
                />
                <Bar dataKey="savings" fill="#6366f1" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
};

// ============================================================
// FINANCIAL REPORTS
// ============================================================
const FinancialReports = ({ api }) => {
  const toast = useToast();
  const [report, setReport] = useState(null);
  const [period, setPeriod] = useState('monthly');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/admin/reports/?period=${period}`)
      .then(res => setReport(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [period]);

  const handleExport = async () => {
    try {
      const res = await api.get('/admin/reports/export/', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'muhazi_financial_statement.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast('Statement exported', 'success');
    } catch (err) {
      toast('Export failed', 'error');
    }
  };

  if (loading || !report) return <SkeletonLoader />;

  return (
    <div className="animate-fade-in">
      <header className="mb-10 flex justify-between items-end flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Financial Reports</h2>
          <p className="text-slate-500 mt-2 font-medium">Generate & export official cooperative statements.</p>
        </div>
        <div className="flex gap-3">
          <select value={period} onChange={e => setPeriod(e.target.value)}
            className="bg-white border border-slate-200 rounded-xl px-4 py-2 font-bold text-sm">
            <option value="daily">Daily</option>
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
          </select>
          <button onClick={handleExport}
            className="bg-emerald-600 text-white font-bold px-6 py-2 rounded-xl shadow-lg hover:bg-emerald-700 flex items-center gap-2">
            <Download size={16} /> Export CSV
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <AdminStat title="Total Contributions" amount={`RWF ${(report.summary.total_contributions / 1000000).toFixed(2)}M`} color="blue" />
        <AdminStat title="Total Disbursed" amount={`RWF ${(report.summary.total_disbursed_loans / 1000000).toFixed(2)}M`} color="emerald" />
        <AdminStat title="Interest Revenue" amount={`RWF ${(report.summary.interest_revenue / 1000).toFixed(1)}K`} color="purple" />
        <AdminStat title="Net Position" amount={`RWF ${(report.summary.net_position / 1000000).toFixed(2)}M`} color="amber" />
      </div>

      <div className="bg-white rounded-3xl shadow-xl border overflow-hidden mb-6">
        <div className="p-6 border-b bg-slate-50">
          <h3 className="font-bold text-slate-800">Loan Status Breakdown</h3>
          <p className="text-xs text-slate-500">Generated: {new Date(report.generated_at).toLocaleString()}</p>
        </div>
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Status</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Count</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {report.loan_breakdown.map((row, i) => (
              <tr key={i} className="hover:bg-slate-50">
                <td className="px-8 py-4 font-bold text-slate-700">{row.status}</td>
                <td className="px-8 py-4 font-extrabold">{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-6">
          <p className="text-sm font-bold text-emerald-700 uppercase mb-1">Loans Approved</p>
          <p className="text-3xl font-extrabold text-emerald-800">{report.summary.total_loans_approved}</p>
        </div>
        <div className="bg-rose-50 border border-rose-100 rounded-2xl p-6">
          <p className="text-sm font-bold text-rose-700 uppercase mb-1">Loans Rejected</p>
          <p className="text-3xl font-extrabold text-rose-800">{report.summary.total_loans_rejected}</p>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// ARREARS TRACKER
// ============================================================
const ArrearsTracker = ({ api }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/arrears/')
      .then(res => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) return <SkeletonLoader />;

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Arrears Tracker</h2>
        <p className="text-slate-500 mt-2 font-medium">Monitor overdue loans and outstanding balances.</p>
      </header>

      <div className="bg-rose-50 border border-rose-200 rounded-3xl p-8 mb-8 flex items-center gap-4">
        <div className="p-4 bg-rose-500 text-white rounded-2xl"><TrendingDown size={32} /></div>
        <div>
          <p className="text-sm font-bold text-rose-700 uppercase">Loans in Arrears</p>
          <p className="text-4xl font-extrabold text-rose-900">{data.total_arrears}</p>
          <p className="text-sm text-rose-600 mt-1">Total outstanding: RWF {data.total_outstanding?.toLocaleString() || 0}</p>
        </div>
      </div>

      <div className="bg-white rounded-3xl shadow-xl border overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Loan</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Member</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Expected</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Paid</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Outstanding</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Days Overdue</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {data.arrears.length === 0 ? (
              <tr><td colSpan="6" className="px-8 py-10 text-center text-slate-400 font-bold">
                <CheckCircle2 size={32} className="mx-auto text-emerald-400 mb-2" />
                No arrears — all loans current!
              </td></tr>
            ) : data.arrears.map(a => (
              <tr key={a.loan_id} className="hover:bg-slate-50">
                <td className="px-8 py-5 font-bold">#LN-{a.loan_id}</td>
                <td className="px-8 py-5 font-bold">{a.member_name}</td>
                <td className="px-8 py-5">RWF {a.amount_expected.toLocaleString()}</td>
                <td className="px-8 py-5">RWF {a.amount_paid.toLocaleString()}</td>
                <td className="px-8 py-5 font-extrabold text-rose-600">RWF {a.outstanding.toLocaleString()}</td>
                <td className="px-8 py-5">
                  <span className="bg-rose-100 text-rose-700 px-3 py-1 rounded-lg text-xs font-bold">{a.days_overdue} days</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================
// MEMBER DIRECTORY
// ============================================================
const MemberDirectory = ({ api }) => {
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/members/')
      .then(res => setMembers(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = members.filter(m =>
    m.full_name.toLowerCase().includes(search.toLowerCase()) ||
    m.national_id.includes(search) ||
    m.phone_number.includes(search)
  );

  if (loading) return <SkeletonLoader />;

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Member Directory</h2>
        <p className="text-slate-500 mt-2 font-medium">{members.length} registered members</p>
      </header>

      <input type="text" value={search} onChange={e => setSearch(e.target.value)}
        className="w-full bg-white border border-slate-200 rounded-xl p-4 mb-6 focus:ring-2 focus:ring-indigo-500 outline-none font-semibold"
        placeholder="Search by name, ID, or phone..." />

      <div className="bg-white rounded-3xl shadow-xl border overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Name</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">National ID</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Phone</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Branch</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Savings</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Loans</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filtered.map(m => (
              <tr key={m.id} className="hover:bg-slate-50">
                <td className="px-8 py-5 font-bold text-slate-800">{m.full_name}</td>
                <td className="px-8 py-5 font-mono text-xs text-slate-600">{m.national_id}</td>
                <td className="px-8 py-5 text-sm">{m.phone_number}</td>
                <td className="px-8 py-5 text-sm text-slate-500">{m.branch}</td>
                <td className="px-8 py-5 font-bold">RWF {parseFloat(m.total_savings).toLocaleString()}</td>
                <td className="px-8 py-5 text-sm">{m.loan_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================
// AUDIT LOG VIEWER
// ============================================================
const AuditLogViewer = ({ api }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/audit-log/')
      .then(res => setLogs(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <SkeletonLoader />;

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Audit Log</h2>
        <p className="text-slate-500 mt-2 font-medium">Immutable trail of all system actions (BNR compliance).</p>
      </header>

      <div className="bg-white rounded-3xl shadow-xl border overflow-hidden">
        <div className="max-h-[70vh] overflow-y-auto custom-scrollbar">
          <table className="w-full text-left">
            <thead className="bg-slate-50 border-b sticky top-0">
              <tr>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Time</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Actor</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Role</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Action</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Target</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {logs.map(log => (
                <tr key={log.id} className="hover:bg-slate-50 text-xs">
                  <td className="px-6 py-3 text-slate-500 whitespace-nowrap">{new Date(log.timestamp).toLocaleString()}</td>
                  <td className="px-6 py-3 font-bold text-slate-800">{log.actor_name}</td>
                  <td className="px-6 py-3">
                    <span className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded font-bold text-[10px]">{log.actor_role}</span>
                  </td>
                  <td className="px-6 py-3 font-bold">{log.action}</td>
                  <td className="px-6 py-3 text-slate-500">{log.target_model}#{log.target_id}</td>
                  <td className="px-6 py-3 font-mono text-slate-400">{log.ip_address || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// USER MANAGEMENT
// ============================================================
const UserManagement = ({ api, toast }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/users/')
      .then(res => setUsers(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <SkeletonLoader />;

  return (
    <div className="animate-fade-in">
      <header className="mb-10">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">User Management</h2>
        <p className="text-slate-500 mt-2 font-medium">{users.length} total users</p>
      </header>

      <div className="bg-white rounded-3xl shadow-xl border overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Username</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Name</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Email</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Role</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Branch</th>
              <th className="px-8 py-4 text-xs font-bold text-slate-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {users.map(u => (
              <tr key={u.id} className="hover:bg-slate-50">
                <td className="px-8 py-5 font-bold text-slate-800">{u.username}</td>
                <td className="px-8 py-5 text-sm">{u.first_name} {u.last_name}</td>
                <td className="px-8 py-5 text-sm text-slate-500">{u.email || '—'}</td>
                <td className="px-8 py-5">
                  {u.role ? (
                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-lg text-xs font-bold">{u.role.role_display}</span>
                  ) : '—'}
                </td>
                <td className="px-8 py-5 text-sm text-slate-500">{u.role?.branch || '—'}</td>
                <td className="px-8 py-5">
                  {u.is_active ? (
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-lg text-xs font-bold">Active</span>
                  ) : (
                    <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-lg text-xs font-bold">Inactive</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default App;