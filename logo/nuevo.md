<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inkora - Prototipo Maestro Definitivo</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/@phosphor-icons/web"></script>
    
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        brand: {
                            50: '#EEF2FF',
                            500: '#6366F1',
                            600: '#4F46E5',
                            800: '#3730A3', 
                            900: '#1A1846',
                            950: '#0F0E29',
                        }
                    },
                    fontFamily: {
                        sans: ['Inter', 'system-ui', 'sans-serif'],
                        mono: ['"JetBrains Mono"', '"Roboto Mono"', 'monospace'], 
                    },
                    animation: {
                        'gradient-x': 'gradient-x 3s ease infinite',
                    },
                    keyframes: {
                        'gradient-x': {
                            '0%, 100%': { 'background-size': '200% 200%', 'background-position': 'left center' },
                            '50%': { 'background-size': '200% 200%', 'background-position': 'right center' }
                        }
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
        
        body { font-family: 'Inter', sans-serif; background-color: #F4F5F8; }
        
        .print-grid {
            background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
            background-size: 40px 40px;
        }
        .tech-grid {
            background-image: linear-gradient(rgba(99, 102, 241, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(99, 102, 241, 0.04) 1px, transparent 1px);
            background-size: 32px 32px;
        }
        
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .glass-header { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
        
        input[type=number]::-webkit-inner-spin-button, 
        input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
        
        .spreadsheet-cell:focus-within {
            background-color: #ffffff;
            box-shadow: inset 0 0 0 2px #4F46E5;
            z-index: 10;
            position: relative;
        }
    </style>
</head>
<body class="h-screen w-full flex overflow-hidden selection:bg-brand-500 selection:text-white relative">

    <div class="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#3B82F6] via-[#6366F1] to-[#D946EF] z-[100] animate-gradient-x"></div>

    <!-- =========================================================================
         MÓDULO 1: VISTA DE LOGIN INDUSTRIAL
         ========================================================================= -->
    <div id="view-login" class="flex flex-col lg:flex-row w-full h-full absolute inset-0 z-50 bg-white transition-opacity duration-500">
        <section class="lg:w-[45%] bg-brand-950 text-white print-grid flex flex-col justify-between p-6 lg:p-12 relative border-b lg:border-b-0 lg:border-r border-brand-800/30 flex-none h-auto lg:h-full">
            <div class="hidden lg:block absolute top-6 left-6 w-4 h-4 border-t border-l border-white/20"></div>
            <div class="hidden lg:block absolute top-6 right-6 w-4 h-4 border-t border-r border-white/20"></div>
            <div class="hidden lg:block absolute bottom-6 left-6 w-4 h-4 border-b border-l border-white/20"></div>
            <div class="hidden lg:block absolute bottom-6 right-6 w-4 h-4 border-b border-r border-white/20"></div>

            <div class="flex items-center gap-3 relative z-10">
                <div class="w-10 h-10 lg:w-12 lg:h-12 flex items-center justify-center">
                    <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
                        <defs>
                            <linearGradient id="inkoraGradientLogin" x1="0%" y1="100%" x2="100%" y2="0%">
                                <stop offset="0%" stop-color="#3B82F6" /><stop offset="40%" stop-color="#6366F1" /><stop offset="100%" stop-color="#D946EF" />
                            </linearGradient>
                        </defs>
                        <path d="M50 0 C50 0 5 35 5 65 C5 89.8 25.2 100 50 100 C74.8 100 95 89.8 95 65 C95 35 50 0 50 0 Z M 35 25 L 50 25 L 50 52 L 72 25 L 88 25 L 62 58 L 88 90 L 72 90 L 50 63 L 50 90 L 35 90 Z" fill="url(#inkoraGradientLogin)"/>
                    </svg>
                </div>
                <h1 class="text-2xl lg:text-3xl font-bold tracking-tight text-white">Inkora</h1>
            </div>

            <div class="my-auto space-y-12 relative z-10 hidden lg:block">
                <div>
                    <h2 class="text-brand-500 font-mono text-sm tracking-widest uppercase mb-4">Core Operativo</h2>
                    <p class="text-4xl xl:text-5xl font-light text-slate-200 leading-tight">Facturación de <br><span class="font-semibold text-white">alto rendimiento.</span></p>
                </div>
                <div class="grid grid-cols-2 gap-8 border-t border-brand-800/50 pt-8">
                    <div><p class="font-mono text-sm text-slate-400 mb-1">LATENCIA_EMISIÓN</p><p class="text-3xl font-mono text-white">3.2<span class="text-brand-500 text-xl">s</span></p></div>
                    <div><p class="font-mono text-sm text-slate-400 mb-1">UPTIME_SUNAT</p><p class="text-3xl font-mono text-white">99.2<span class="text-brand-500 text-xl">%</span></p></div>
                </div>
            </div>

            <div class="relative z-10 flex items-center justify-between lg:border-t lg:border-brand-800/50 pt-0 lg:pt-6 mt-4 lg:mt-0">
                <div class="flex items-center gap-3">
                    <span class="relative flex h-2.5 w-2.5"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span></span>
                    <span class="font-mono text-[10px] lg:text-xs text-slate-300 uppercase tracking-wider">Gateway SUNAT Conectado</span>
                </div>
                <span class="font-mono text-[10px] lg:text-xs text-brand-500 hidden sm:block">v2.4.0</span>
            </div>
        </section>

        <section class="lg:w-[55%] flex-1 bg-white flex items-center justify-center p-6 sm:p-12 lg:p-24 relative">
            <div class="w-full max-w-[420px]">
                <div class="mb-10">
                    <h2 class="text-2xl lg:text-3xl font-bold text-slate-900 mb-2">Acceso de Operador</h2>
                    <p class="text-slate-500 text-sm lg:text-base">Ingrese sus credenciales para inicializar la sesión.</p>
                </div>
                <form class="space-y-6" onsubmit="event.preventDefault(); handleLogin();">
                    <div class="space-y-2 group">
                        <label class="block text-xs font-bold text-slate-900 uppercase tracking-wider transition-colors group-focus-within:text-brand-600">Correo Electrónico</label>
                        <div class="relative flex items-center border-b-2 border-slate-200 focus-within:border-brand-600 focus-within:bg-slate-50 transition-colors">
                            <i class="ph ph-terminal-window absolute left-2 text-slate-400 text-lg group-focus-within:text-brand-600 transition-colors"></i>
                            <input type="email" value="admin@demo.inkora.pe" class="w-full pl-10 pr-4 py-3.5 bg-transparent border-0 text-slate-900 text-lg focus:ring-0 placeholder:text-slate-300 outline-none" required>
                        </div>
                    </div>
                    <div class="space-y-2 group relative">
                        <div class="flex justify-between items-end">
                            <label class="block text-xs font-bold text-slate-900 uppercase tracking-wider transition-colors group-focus-within:text-brand-600">Contraseña</label>
                        </div>
                        <div class="relative flex items-center border-b-2 border-slate-200 focus-within:border-brand-600 focus-within:bg-slate-50 transition-colors">
                            <i class="ph ph-password absolute left-2 text-slate-400 text-lg group-focus-within:text-brand-600 transition-colors"></i>
                            <input type="password" value="password123" class="w-full pl-10 pr-12 py-3.5 bg-transparent border-0 text-slate-900 text-lg focus:ring-0 tracking-widest outline-none" required>
                        </div>
                    </div>
                    <button type="submit" class="w-full bg-slate-900 hover:bg-brand-600 text-white font-bold text-sm tracking-widest uppercase py-5 px-6 rounded-none mt-8 transition-all duration-300 flex items-center justify-between group shadow-[4px_4px_0px_0px_rgba(99,102,241,0)] hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] border border-transparent hover:border-brand-600 active:translate-y-1 active:translate-x-1 active:shadow-none outline-none">
                        <span>Iniciar Operación</span>
                        <i class="ph ph-arrow-right text-xl transform group-hover:translate-x-2 transition-transform"></i>
                    </button>
                </form>
            </div>
        </section>
    </div>


    <!-- =========================================================================
         MÓDULO 2: APLICACIÓN PRINCIPAL
         ========================================================================= -->
    <div id="view-app" class="w-full h-full relative z-30 hidden flex tech-grid">
        
        <!-- SIDEBAR -->
        <aside class="w-[280px] bg-brand-950 flex-none flex flex-col justify-between shadow-2xl relative z-40 hidden md:flex border-r border-white/5">
            <div class="flex-1 overflow-y-auto no-scrollbar pt-2">
                <div class="p-6">
                    <div class="flex items-center gap-3 mb-2">
                        <div class="w-9 h-9 flex items-center justify-center filter drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]">
                            <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
                                <defs>
                                    <linearGradient id="inkoraGradientApp" x1="0%" y1="100%" x2="100%" y2="0%">
                                        <stop offset="0%" stop-color="#3B82F6" /><stop offset="40%" stop-color="#6366F1" /><stop offset="100%" stop-color="#D946EF" />
                                    </linearGradient>
                                </defs>
                                <path d="M50 0 C50 0 5 35 5 65 C5 89.8 25.2 100 50 100 C74.8 100 95 89.8 95 65 C95 35 50 0 50 0 Z M 35 25 L 50 25 L 50 52 L 72 25 L 88 25 L 62 58 L 88 90 L 72 90 L 50 63 L 50 90 L 35 90 Z" fill="url(#inkoraGradientApp)"/>
                            </svg>
                        </div>
                        <h1 class="text-2xl font-bold tracking-tight text-white">Inkora</h1>
                    </div>
                    <p class="text-[10px] font-mono text-slate-400 uppercase tracking-widest pl-12">Imprentas Core</p>
                </div>

                <nav class="p-4 space-y-1 mt-4">
                    <a id="nav-dashboard" onclick="navigateTo('dashboard')" class="nav-item flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group cursor-pointer relative">
                        <div class="active-indicator absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF] hidden"></div>
                        <i class="ph ph-squares-four text-xl group-hover:text-brand-400 transition-colors"></i> Dashboard
                    </a>
                    <a id="nav-clientes" onclick="navigateTo('clientes')" class="nav-item flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group cursor-pointer relative">
                        <div class="active-indicator absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF] hidden"></div>
                        <i class="ph ph-users text-xl group-hover:text-brand-400 transition-colors"></i> Clientes
                    </a>
                    <a id="nav-productos" onclick="navigateTo('productos')" class="nav-item flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group cursor-pointer relative">
                        <div class="active-indicator absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF] hidden"></div>
                        <i class="ph ph-package text-xl group-hover:text-brand-400 transition-colors"></i> Productos
                    </a>
                    <a id="nav-cotizaciones" onclick="navigateTo('cotizaciones')" class="nav-item flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group cursor-pointer relative">
                        <div class="active-indicator absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF] hidden"></div>
                        <i class="ph ph-file-text text-xl group-hover:text-brand-400 transition-colors"></i> Cotizaciones
                    </a>
                    <a id="nav-cobranza" onclick="navigateTo('cobranza')" class="nav-item flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group cursor-pointer relative">
                        <div class="active-indicator absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF] hidden"></div>
                        <i class="ph ph-credit-card text-xl group-hover:text-brand-400 transition-colors"></i> Cobranza
                    </a>
                    <a id="nav-guias" onclick="navigateTo('guias')" class="nav-item flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group cursor-pointer relative">
                        <div class="active-indicator absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF] hidden"></div>
                        <i class="ph ph-truck text-xl group-hover:text-brand-400 transition-colors"></i> Guías
                    </a>
                    
                    <div class="pt-4 mt-4 border-t border-white/10"></div>
                    
                    <a id="nav-configuracion" onclick="navigateTo('configuracion')" class="nav-item flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group cursor-pointer relative">
                        <div class="active-indicator absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF] hidden"></div>
                        <i class="ph ph-gear text-xl group-hover:text-brand-400 transition-colors"></i> Configuración
                    </a>
                </nav>
            </div>

            <div class="p-4">
                <div class="flex items-center justify-between px-4 py-3 bg-brand-900/50 rounded-none border border-white/5 hover:border-brand-500/50 transition-colors cursor-pointer group">
                    <div class="flex items-center gap-3 overflow-hidden">
                        <div class="w-8 h-8 bg-brand-800 flex items-center justify-center text-white font-bold text-sm group-hover:bg-brand-600 transition-colors">A</div>
                        <div class="flex-1 overflow-hidden">
                            <p class="text-sm font-semibold text-white truncate">Admin Demo</p>
                            <p class="text-[10px] font-mono text-brand-400 uppercase">Pro Access</p>
                        </div>
                    </div>
                    <button onclick="handleLogout()" class="text-slate-500 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-all px-1 outline-none" title="Cerrar sesión">
                        <i class="ph-bold ph-power text-xl"></i>
                    </button>
                </div>
            </div>
        </aside>

        <!-- MAIN CONTENT AREA -->
        <main class="flex-1 flex flex-col h-screen overflow-hidden relative z-10 bg-[#F4F5F8]">
            
            <header class="glass-header border-b border-slate-200/50 px-8 py-4 flex items-center justify-between flex-none sticky top-0 z-20 pt-5">
                <div>
                    <h2 id="global-page-title" class="text-xl font-bold text-slate-900 flex items-center gap-3">
                        Panel General
                        <span id="global-page-subtitle" class="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-mono tracking-widest uppercase">Vista Global</span>
                    </h2>
                </div>
                <div class="flex items-center gap-6">
                    <div class="hidden lg:flex flex-col items-end">
                        <p class="sysClock font-mono text-sm font-bold text-slate-800">00:00:00</p>
                        <p class="sysDate text-[10px] font-mono text-slate-500 uppercase tracking-widest">LIMA (PET)</p>
                    </div>
                    <div class="h-8 w-px bg-slate-200 hidden sm:block"></div>
                    <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-emerald-50/80 border border-emerald-200 rounded-none">
                        <span class="relative flex h-2 w-2">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </span>
                        <span class="font-mono text-[10px] text-emerald-800 uppercase tracking-widest font-bold">SUNAT Sync</span>
                    </div>
                </div>
            </header>

            <div class="flex-1 overflow-y-auto p-0 no-scrollbar relative">
                
                <!-- ----------------------------------------------------
                     PÁGINA: DASHBOARD
                     ---------------------------------------------------- -->
                <div id="page-dashboard" class="page-section p-8 pb-12 block">
                    <div class="max-w-[1400px] mx-auto space-y-8">
                        <div class="flex justify-between items-end">
                            <div>
                                <h3 class="text-4xl font-bold text-slate-900 tracking-tight">Hola, Admin</h3>
                                <p class="text-slate-500 mt-2 text-sm">Resumen de liquidez y flujo fiscal del período actual.</p>
                            </div>
                            <button onclick="navigateTo('cotizaciones'); openModal('quoteModal');" class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-6 py-3 transition-all flex items-center gap-2 rounded-none hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 outline-none">
                                <div class="absolute inset-0 border border-white/20"></div>
                                <i class="ph ph-lightning text-brand-400 text-lg group-hover:animate-pulse"></i> Nueva Cotización
                            </button>
                        </div>

                        <!-- KPIs -->
                        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
                            <div class="bg-white p-6 border border-slate-200 border-t-2 border-t-brand-500 shadow-sm relative overflow-hidden group hover:border-brand-300 transition-colors">
                                <div class="relative z-10">
                                    <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Emisiones (Mes)</p>
                                    <p class="text-4xl font-mono font-bold text-slate-900 mb-1">1,248</p>
                                    <p class="text-xs text-emerald-600 font-mono font-bold flex items-center gap-1"><i class="ph-bold ph-arrow-up-right"></i> +12.5% <span class="text-slate-400 font-normal">vs anterior</span></p>
                                </div>
                                <svg class="absolute bottom-0 right-0 w-32 h-16 text-brand-50 opacity-50 group-hover:opacity-100 transition-opacity" viewBox="0 0 100 50" fill="none" preserveAspectRatio="none"><path d="M0 50 L20 40 L40 45 L60 20 L80 30 L100 10" stroke="currentColor" stroke-width="3" fill="none"/><path d="M0 50 L20 40 L40 45 L60 20 L80 30 L100 10 L100 50 L0 50 Z" fill="currentColor"/></svg>
                            </div>
                            <div class="bg-white p-6 border border-slate-200 border-t-2 border-t-emerald-500 shadow-sm relative overflow-hidden group hover:border-emerald-300 transition-colors">
                                <div class="relative z-10">
                                    <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Ingresos Registrados</p>
                                    <div class="flex items-baseline gap-1 mb-1"><span class="text-lg font-bold text-emerald-600">S/</span><p class="text-4xl font-mono font-bold text-emerald-600">42,350<span class="text-xl text-emerald-400">.00</span></p></div>
                                    <p class="text-xs text-emerald-600 font-mono font-bold flex items-center gap-1"><i class="ph-bold ph-arrow-up-right"></i> +4.2% <span class="text-slate-400 font-normal">vs anterior</span></p>
                                </div>
                                <svg class="absolute bottom-0 right-0 w-32 h-16 text-emerald-50 opacity-50 group-hover:opacity-100 transition-opacity" viewBox="0 0 100 50" fill="none" preserveAspectRatio="none"><path d="M0 50 L20 35 L40 40 L60 15 L80 20 L100 5" stroke="currentColor" stroke-width="3" fill="none"/><path d="M0 50 L20 35 L40 40 L60 15 L80 20 L100 5 L100 50 L0 50 Z" fill="currentColor"/></svg>
                            </div>
                            <div class="bg-white p-6 border border-slate-200 border-t-2 border-t-amber-500 shadow-sm relative overflow-hidden group hover:border-amber-300 transition-colors">
                                <div class="relative z-10">
                                    <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Capital Por Cobrar</p>
                                    <div class="flex items-baseline gap-1 mb-1"><span class="text-lg font-bold text-amber-600">S/</span><p class="text-4xl font-mono font-bold text-amber-600">33,826<span class="text-xl text-amber-400">.00</span></p></div>
                                    <p class="text-xs text-amber-600 font-mono font-bold flex items-center gap-1"><i class="ph-bold ph-minus"></i> 0.0% <span class="text-slate-400 font-normal">Estable</span></p>
                                </div>
                                <svg class="absolute bottom-0 right-0 w-32 h-16 text-amber-50 opacity-50 group-hover:opacity-100 transition-opacity" viewBox="0 0 100 50" fill="none" preserveAspectRatio="none"><path d="M0 50 L20 25 L40 25 L60 25 L80 25 L100 25" stroke="currentColor" stroke-width="3" stroke-dasharray="4 4" fill="none"/></svg>
                            </div>
                            <div class="bg-slate-900 p-6 border border-rose-500/50 border-t-2 border-t-rose-500 shadow-sm relative overflow-hidden group">
                                <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMSIgY3k9IjEiIHI9IjEiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')] opacity-50"></div>
                                <div class="absolute top-0 right-0 w-24 h-24 bg-rose-500 opacity-20 blur-2xl rounded-full animate-pulse"></div>
                                <div class="relative z-10">
                                    <div class="flex justify-between items-start mb-4">
                                        <p class="text-[10px] font-bold font-mono text-rose-400 uppercase tracking-widest">Docs. Vencidos</p>
                                        <span class="flex h-2 w-2"><span class="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-rose-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span></span>
                                    </div>
                                    <p class="text-4xl font-mono font-bold text-white mb-1">14</p>
                                    <p class="text-xs text-rose-400 font-mono flex items-center gap-1"><i class="ph-bold ph-warning-circle"></i> Acción inmediata requerida</p>
                                </div>
                            </div>
                        </div>

                        <!-- Lista Dashboard -->
                        <div class="bg-white border border-slate-200 rounded-none shadow-sm">
                            <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/80 backdrop-blur-sm">
                                <div class="flex items-center gap-3">
                                    <div class="w-8 h-8 bg-white border border-slate-200 flex items-center justify-center text-slate-800 shadow-sm"><i class="ph-bold ph-list-numbers"></i></div>
                                    <h4 class="font-bold text-slate-900 font-mono uppercase tracking-wider text-sm">Ledger: Cobranza Urgente</h4>
                                </div>
                                <button onclick="navigateTo('cobranza')" class="text-xs font-mono font-bold text-brand-600 hover:text-brand-800 flex items-center gap-1 transition-colors outline-none">
                                    Ver todo el reporte <i class="ph-bold ph-arrow-right"></i>
                                </button>
                            </div>
                            <div class="flex items-center justify-between p-4 border-b border-slate-100 hover:bg-brand-50/50 transition-all group relative">
                                <div class="flex items-center gap-4">
                                    <div class="w-10 h-10 bg-rose-50 flex items-center justify-center border border-rose-100 text-rose-600 font-mono text-xs font-bold">#01</div>
                                    <div>
                                        <p class="font-bold text-slate-900 group-hover:text-brand-700 transition-colors">Cliente Corporativo SAC</p>
                                        <div class="flex items-center gap-2 mt-1">
                                            <span class="px-1.5 py-0.5 bg-rose-100 text-rose-700 text-[9px] font-bold font-mono uppercase tracking-widest border border-rose-200">Vencido</span>
                                            <p class="text-xs text-slate-500 font-mono">FACT-001-492 · Venció: 01/01/2026</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="flex items-center gap-6">
                                    <div class="text-right transition-transform group-hover:-translate-x-4 duration-300"><p class="font-mono font-bold text-rose-600 text-lg">S/ 1,200.00</p></div>
                                    <div class="absolute right-6 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="bg-brand-600 hover:bg-brand-700 text-white font-mono text-[10px] uppercase tracking-widest px-4 py-2 border border-brand-700 shadow-sm">Notificar</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ----------------------------------------------------
                     PÁGINA: CLIENTES
                     ---------------------------------------------------- -->
                <div id="page-clientes" class="page-section p-8 pb-12 hidden">
                    <div class="max-w-[1400px] mx-auto space-y-6">
                        <div class="bg-white border border-slate-200 rounded-none p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                            <div class="relative w-full sm:w-[400px] group">
                                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><i class="ph-bold ph-magnifying-glass text-slate-400 group-focus-within:text-brand-600 transition-colors"></i></div>
                                <input type="text" class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-mono placeholder:font-sans placeholder:text-slate-400" placeholder="Buscar por nombre o RUC/DNI...">
                            </div>
                            <div class="flex items-center gap-3 w-full sm:w-auto">
                                <button class="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 px-4 py-2.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors"><i class="ph-bold ph-funnel"></i> Filtrar</button>
                                <button onclick="openModal('clientModal')" class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-6 py-2.5 transition-all flex items-center gap-2 rounded-none hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 border border-transparent hover:border-brand-500 outline-none">
                                    <i class="ph-bold ph-user-plus"></i> Nuevo Cliente
                                </button>
                            </div>
                        </div>

                        <div class="bg-white border border-slate-200 rounded-none shadow-sm overflow-x-auto">
                            <table class="w-full text-left border-collapse">
                                <thead class="bg-slate-100/80 border-b border-slate-200">
                                    <tr>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Razón Social</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">RUC / DNI</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Contacto</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Condición</th>
                                        <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-100">
                                    <tr class="hover:bg-brand-50/40 transition-colors group">
                                        <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px] group-hover:text-brand-700 transition-colors">ARCOR DE PERU S A</p></td>
                                        <td class="px-6 py-3"><span class="font-mono text-[13px] text-slate-700 font-semibold">20191308868</span></td>
                                        <td class="px-6 py-3"><span class="text-slate-400 font-mono text-[13px]">--</span></td>
                                        <td class="px-6 py-3"><span class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono font-bold uppercase tracking-widest">Contado</span></td>
                                        <td class="px-6 py-3 text-right">
                                            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                                <button class="p-1 text-slate-400 hover:text-brand-600"><i class="ph-bold ph-pencil-simple text-base"></i></button>
                                                <button class="p-1 text-slate-400 hover:text-rose-600"><i class="ph-bold ph-trash text-base"></i></button>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr class="hover:bg-brand-50/40 transition-colors group">
                                        <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px] group-hover:text-brand-700 transition-colors">Cliente Corporativo SAC</p></td>
                                        <td class="px-6 py-3"><span class="font-mono text-[13px] text-slate-700 font-semibold">20100100100</span></td>
                                        <td class="px-6 py-3"><span class="text-slate-600 text-[13px]">compras@corporativo.pe</span></td>
                                        <td class="px-6 py-3"><span class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-mono font-bold uppercase tracking-widest">Crédito 30</span></td>
                                        <td class="px-6 py-3 text-right">
                                            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                                <button class="p-1 text-slate-400 hover:text-brand-600"><i class="ph-bold ph-pencil-simple text-base"></i></button>
                                                <button class="p-1 text-slate-400 hover:text-rose-600"><i class="ph-bold ph-trash text-base"></i></button>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ----------------------------------------------------
                     PÁGINA: PRODUCTOS
                     ---------------------------------------------------- -->
                <div id="page-productos" class="page-section p-8 pb-12 hidden">
                    <div class="max-w-[1400px] mx-auto space-y-6">
                        <div class="bg-white border border-slate-200 rounded-none p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                            <div class="relative w-full sm:w-[450px] group">
                                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><i class="ph-bold ph-magnifying-glass text-slate-400 group-focus-within:text-brand-600 transition-colors"></i></div>
                                <input type="text" class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-mono placeholder:font-sans placeholder:text-slate-400" placeholder="Buscar por nombre o código SKU...">
                            </div>
                            <div class="flex items-center gap-3 w-full sm:w-auto">
                                <button onclick="openModal('productModal')" class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-6 py-2.5 transition-all flex items-center gap-2 rounded-none hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 border border-transparent hover:border-brand-500 outline-none">
                                    <i class="ph-bold ph-plus"></i> Nuevo Producto
                                </button>
                            </div>
                        </div>

                        <div class="bg-white border border-slate-200 rounded-none shadow-sm overflow-x-auto">
                            <table class="w-full text-left border-collapse">
                                <thead class="bg-slate-100/80 border-b border-slate-200">
                                    <tr>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest w-[40%]">Nombre y Descripción</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest w-[20%]">Código (SKU)</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest w-[15%]">U.M. SUNAT</th>
                                        <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest w-[15%]">Precio Unit.</th>
                                        <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest w-[10%]">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-100">
                                    <tr class="hover:bg-brand-50/40 transition-colors group">
                                        <td class="px-6 py-2.5">
                                            <div class="flex items-center gap-3"><div class="w-2 h-2 rounded-full bg-brand-500 shrink-0"></div><p class="font-bold text-slate-900 text-[13px] group-hover:text-brand-700 transition-colors">Diseño Gráfico</p></div>
                                        </td>
                                        <td class="px-6 py-2.5"><span class="inline-block px-2 py-0.5 bg-slate-50 border border-slate-200 text-slate-600 font-mono text-[11px] font-semibold tracking-wider">DIS-GFX</span></td>
                                        <td class="px-6 py-2.5"><span class="inline-block px-1.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-mono font-bold uppercase tracking-widest">ZZ</span></td>
                                        <td class="px-6 py-2.5 text-right"><div class="flex justify-end items-baseline gap-1"><span class="text-[10px] font-bold text-slate-400">S/</span><span class="font-mono text-[13px] font-bold text-slate-900">50.00</span></div></td>
                                        <td class="px-6 py-2.5 text-right">
                                            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                                <button class="p-1 text-slate-400 hover:text-brand-600 transition-colors"><i class="ph-bold ph-pencil-simple text-base"></i></button>
                                                <button class="p-1 text-slate-400 hover:text-rose-600 transition-colors"><i class="ph-bold ph-trash text-base"></i></button>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr class="hover:bg-brand-50/40 transition-colors group">
                                        <td class="px-6 py-2.5">
                                            <div class="flex items-center gap-3"><div class="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></div><p class="font-bold text-slate-900 text-[13px] group-hover:text-brand-700 transition-colors">Impresión A4 Full Color</p></div>
                                        </td>
                                        <td class="px-6 py-2.5"><span class="inline-block px-2 py-0.5 bg-slate-50 border border-slate-200 text-slate-600 font-mono text-[11px] font-semibold tracking-wider">IMP-A4-FC</span></td>
                                        <td class="px-6 py-2.5"><span class="inline-block px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono font-bold uppercase tracking-widest">NIU</span></td>
                                        <td class="px-6 py-2.5 text-right"><div class="flex justify-end items-baseline gap-1"><span class="text-[10px] font-bold text-slate-400">S/</span><span class="font-mono text-[13px] font-bold text-slate-900">5.90</span></div></td>
                                        <td class="px-6 py-2.5 text-right">
                                            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                                <button class="p-1 text-slate-400 hover:text-brand-600 transition-colors"><i class="ph-bold ph-pencil-simple text-base"></i></button>
                                                <button class="p-1 text-slate-400 hover:text-rose-600 transition-colors"><i class="ph-bold ph-trash text-base"></i></button>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ----------------------------------------------------
                     PÁGINA: COTIZACIONES
                     ---------------------------------------------------- -->
                <div id="page-cotizaciones" class="page-section p-8 pb-12 hidden">
                    <div class="max-w-[1400px] mx-auto space-y-6">
                        <div class="bg-white border border-slate-200 p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                            <div class="relative w-full sm:w-[450px] group">
                                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><i class="ph-bold ph-magnifying-glass text-slate-400 group-focus-within:text-brand-600 transition-colors"></i></div>
                                <input type="text" class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-mono placeholder:font-sans placeholder:text-slate-400" placeholder="Buscar por cliente o N° de orden...">
                            </div>
                            <div class="flex items-center gap-3 w-full sm:w-auto">
                                <button onclick="openModal('quoteModal')" class="relative group bg-brand-600 text-white font-mono text-xs uppercase tracking-widest px-6 py-2.5 flex items-center gap-2 hover:bg-brand-700 transition-all hover:shadow-[4px_4px_0px_0px_rgba(49,46,129,0.5)] hover:-translate-y-0.5 hover:-translate-x-0.5 outline-none">
                                    <i class="ph-bold ph-plus"></i> Nueva Cotización
                                </button>
                            </div>
                        </div>

                        <div class="bg-white border border-slate-200 shadow-sm overflow-x-auto">
                            <table class="w-full text-left border-collapse">
                                <thead class="bg-slate-100/80 border-b border-slate-200">
                                    <tr>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Documento</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Cliente</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Fecha</th>
                                        <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Total</th>
                                        <th class="px-6 py-3 text-center text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Estado</th>
                                        <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-100">
                                    <tr class="hover:bg-brand-50/40 transition-colors group">
                                        <td class="px-6 py-3"><div class="flex items-center gap-2"><i class="ph-fill ph-file-text text-slate-400"></i><span class="font-mono text-[13px] font-bold text-brand-600">COT-2026-0001</span></div></td>
                                        <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px]">Cliente Corporativo SAC</p></td>
                                        <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">14/04/2026</span></td>
                                        <td class="px-6 py-3 text-right"><span class="font-mono text-[13px] font-bold text-slate-900">S/ 1,250.00</span></td>
                                        <td class="px-6 py-3 text-center"><span class="inline-flex px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-mono font-bold uppercase tracking-widest">Pendiente</span></td>
                                        <td class="px-6 py-3 text-right">
                                            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                                <button class="p-1 text-slate-400 hover:text-brand-600 transition-colors"><i class="ph-bold ph-eye text-base"></i></button>
                                                <button class="p-1 text-slate-400 hover:text-emerald-600 transition-colors"><i class="ph-bold ph-check-circle text-base"></i></button>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ----------------------------------------------------
                     PÁGINA: COBRANZA
                     ---------------------------------------------------- -->
                <div id="page-cobranza" class="page-section p-8 pb-12 hidden">
                    <div class="max-w-[1400px] mx-auto space-y-8">
                        <div>
                            <h3 class="text-3xl font-bold text-slate-900 tracking-tight">Control de Liquidez</h3>
                            <p class="text-slate-500 mt-1 text-sm">Seguimiento de saldos pendientes y vencimientos comerciales.</p>
                        </div>
                        
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
                            <div class="bg-white p-6 border border-slate-200 border-t-4 border-t-amber-500 shadow-sm relative group">
                                <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Total Pendiente</p>
                                <div class="flex items-baseline gap-1 mb-1"><span class="text-lg font-bold text-amber-600">S/</span><p class="text-4xl font-mono font-bold text-amber-600">33,826<span class="text-xl text-amber-400">.00</span></p></div>
                            </div>
                            <div class="bg-slate-900 p-6 border border-rose-500/50 border-t-4 border-t-rose-500 shadow-sm relative overflow-hidden">
                                <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMSIgY3k9IjEiIHI9IjEiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')] opacity-50"></div>
                                <div class="absolute top-0 right-0 w-24 h-24 bg-rose-500 opacity-20 blur-2xl rounded-full animate-pulse"></div>
                                <div class="relative z-10">
                                    <div class="flex justify-between items-start mb-4"><p class="text-[10px] font-bold font-mono text-rose-400 uppercase tracking-widest">Docs. Vencidos</p><span class="flex h-2 w-2"><span class="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-rose-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span></span></div>
                                    <p class="text-4xl font-mono font-bold text-white mb-1">14</p>
                                    <p class="text-xs text-rose-400 font-mono flex items-center gap-1"><i class="ph-bold ph-warning-circle"></i> Acción requerida</p>
                                </div>
                            </div>
                            <div class="bg-white p-6 border border-slate-200 border-t-4 border-t-emerald-500 shadow-sm relative group hover:border-emerald-300 transition-colors">
                                <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Cobrado Este Mes</p>
                                <div class="flex items-baseline gap-1 mb-1"><span class="text-lg font-bold text-emerald-600">S/</span><p class="text-4xl font-mono font-bold text-emerald-600">42,350<span class="text-xl text-emerald-400">.00</span></p></div>
                            </div>
                        </div>

                        <div class="bg-white border border-slate-200 shadow-sm overflow-x-auto">
                            <div class="px-6 py-4 border-b border-slate-200 bg-rose-50/50 flex justify-between items-center">
                                <div class="flex items-center gap-3"><i class="ph-fill ph-warning-circle text-rose-500 text-xl"></i><div><h4 class="font-bold text-slate-900 font-mono text-sm uppercase tracking-widest">Aging Report</h4><p class="text-xs text-slate-500">Priorizar por días de mora.</p></div></div>
                            </div>
                            <table class="w-full text-left border-collapse">
                                <thead class="bg-slate-100/80 border-b border-slate-200">
                                    <tr>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Doc.</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Cliente</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Vence</th>
                                        <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Saldo</th>
                                        <th class="px-6 py-3 text-center text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Días</th>
                                        <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Acción</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-100">
                                    <tr class="hover:bg-brand-50/40 transition-colors group bg-rose-50/20">
                                        <td class="px-6 py-3"><div class="flex items-center gap-2"><span class="inline-block w-1.5 h-1.5 rounded-full bg-rose-500"></span><span class="font-mono text-[13px] font-bold text-slate-700">ORD-0006-0008</span></div></td>
                                        <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px]">Cliente Corporativo SAC</p></td>
                                        <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">01/01/2026</span></td>
                                        <td class="px-6 py-3 text-right"><span class="font-mono text-[14px] font-bold text-rose-600">S/ 200.00</span></td>
                                        <td class="px-6 py-3 text-center"><span class="inline-flex px-2 py-1 bg-rose-100 text-rose-700 border border-rose-200 text-[11px] font-mono font-bold uppercase tracking-widest shadow-sm">+103 Días</span></td>
                                        <td class="px-6 py-3 text-right">
                                            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                                <button class="px-3 py-1.5 bg-emerald-600 text-white font-mono text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 shadow-sm"><i class="ph-bold ph-currency-circle-dollar text-sm"></i> Pagar</button>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr class="hover:bg-brand-50/40 transition-colors group">
                                        <td class="px-6 py-3"><div class="flex items-center gap-2"><span class="inline-block w-1.5 h-1.5 rounded-full bg-amber-500"></span><span class="font-mono text-[13px] font-bold text-slate-700">FACT-001-4099</span></div></td>
                                        <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px]">Distribuidora Norte</p></td>
                                        <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">30/03/2026</span></td>
                                        <td class="px-6 py-3 text-right"><span class="font-mono text-[14px] font-bold text-amber-600">S/ 1,500.00</span></td>
                                        <td class="px-6 py-3 text-center"><span class="inline-flex px-2 py-1 bg-amber-100 text-amber-700 border border-amber-200 text-[11px] font-mono font-bold uppercase tracking-widest">+15 Días</span></td>
                                        <td class="px-6 py-3 text-right">
                                            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                                <button class="px-3 py-1.5 bg-emerald-600 text-white font-mono text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 shadow-sm"><i class="ph-bold ph-currency-circle-dollar text-sm"></i> Pagar</button>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr class="hover:bg-brand-50/40 transition-colors group">
                                        <td class="px-6 py-3"><div class="flex items-center gap-2"><span class="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span><span class="font-mono text-[13px] font-bold text-slate-700">FACT-001-4105</span></div></td>
                                        <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px]">García Pérez</p></td>
                                        <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">16/04/2026</span></td>
                                        <td class="px-6 py-3 text-right"><span class="font-mono text-[14px] font-bold text-slate-900">S/ 450.00</span></td>
                                        <td class="px-6 py-3 text-center"><span class="inline-flex px-2 py-1 bg-slate-100 text-slate-600 border border-slate-200 text-[11px] font-mono font-bold uppercase tracking-widest">Vence en 2d</span></td>
                                        <td class="px-6 py-3 text-right">
                                            <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                                <button class="px-3 py-1.5 bg-emerald-600 text-white font-mono text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 shadow-sm"><i class="ph-bold ph-currency-circle-dollar text-sm"></i> Pagar</button>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ----------------------------------------------------
                     PÁGINA: GUÍAS DE REMISIÓN
                     ---------------------------------------------------- -->
                <div id="page-guias" class="page-section p-8 pb-12 hidden">
                    <div class="max-w-[1400px] mx-auto space-y-6">
                        <div class="bg-white border border-slate-200 p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                            <div class="relative w-full sm:w-[450px] group">
                                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><i class="ph-bold ph-magnifying-glass text-slate-400"></i></div>
                                <input type="text" class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:border-brand-500 font-mono placeholder:font-sans placeholder:text-slate-400" placeholder="Buscar por N° de guía...">
                            </div>
                            <div class="flex items-center gap-3">
                                <button onclick="openModal('guideModal')" class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-6 py-2.5 flex items-center gap-2 hover:bg-brand-600 transition-all outline-none">
                                    <i class="ph-bold ph-plus"></i> Nueva Guía
                                </button>
                            </div>
                        </div>

                        <div class="bg-white border border-slate-200 shadow-sm overflow-x-auto">
                            <div class="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                                <div class="flex items-center gap-3"><i class="ph-fill ph-truck text-slate-500 text-xl"></i><div><h4 class="font-bold text-slate-900 font-mono text-sm uppercase tracking-widest">Bitácora de Despachos</h4></div></div>
                            </div>
                            <table class="w-full text-left border-collapse">
                                <thead class="bg-slate-100/80 border-b border-slate-200">
                                    <tr>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Número</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest w-[25%]">Origen</th>
                                        <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest w-[25%]">Destino</th>
                                        <th class="px-6 py-3 text-center text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Estado</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-100">
                                    <tr class="hover:bg-brand-50/40 transition-colors group">
                                        <td class="px-6 py-3"><div class="flex items-center gap-2"><i class="ph-fill ph-truck text-slate-400"></i><span class="font-mono text-[13px] font-bold text-slate-800">T001-000001</span></div></td>
                                        <td class="px-6 py-3"><p class="text-slate-900 text-[12px] truncate max-w-[200px]">Av. Demo 123, Lima</p></td>
                                        <td class="px-6 py-3"><p class="font-semibold text-slate-900 text-[12px] truncate max-w-[200px]">Jr. Cliente 456, Miraflores</p></td>
                                        <td class="px-6 py-3 text-center"><span class="inline-flex px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-mono font-bold uppercase tracking-widest">En ruta</span></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ----------------------------------------------------
                     PÁGINA: CONFIGURACIÓN
                     ---------------------------------------------------- -->
                <div id="page-configuracion" class="page-section p-8 pb-12 hidden">
                    <div class="bg-white border-b border-slate-200 px-8 pt-6 flex gap-8 -mx-8 -mt-8 mb-8 sticky top-0 z-10">
                        <button onclick="switchTab('empresa')" id="tab-empresa" class="pb-3 border-b-2 border-brand-600 text-brand-600 font-bold text-sm tracking-wide uppercase transition-colors outline-none">Perfil de Empresa</button>
                        <button onclick="switchTab('fiscal')" id="tab-fiscal" class="pb-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 font-semibold text-sm tracking-wide uppercase transition-colors outline-none">Configuración Fiscal</button>
                        <button onclick="switchTab('cuenta')" id="tab-cuenta" class="pb-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 font-semibold text-sm tracking-wide uppercase transition-colors outline-none">Mi Cuenta</button>
                    </div>

                    <div class="max-w-[1000px] mx-auto space-y-8">
                        <!-- TAB: EMPRESA -->
                        <div id="content-empresa" class="space-y-6 block">
                            <div><h3 class="text-2xl font-bold text-slate-900 tracking-tight">Perfil de Empresa</h3></div>
                            <div class="bg-white border border-slate-200 p-8 shadow-sm">
                                <div class="flex items-center gap-3 mb-8 border-b border-slate-100 pb-4"><i class="ph-bold ph-buildings text-brand-600 text-xl"></i><h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Identidad Tributaria</h4></div>
                                <div class="space-y-6">
                                    <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Razón Social</label><input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 text-slate-900 text-sm font-semibold focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500" value="Imprenta Demo PrintFlow SAC"></div>
                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">RUC</label><input type="text" maxlength="11" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 font-mono text-sm font-bold tracking-widest focus:bg-white focus:border-brand-500" value="20999999999"></div>
                                        <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Teléfono de Contacto</label><input type="tel" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 font-mono text-sm focus:bg-white focus:border-brand-500" value="999-777-888"></div>
                                    </div>
                                    <div class="pt-6 border-t border-slate-100 flex justify-end">
                                        <button class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-3 flex items-center gap-2 hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 outline-none"><i class="ph-bold ph-floppy-disk text-lg"></i> Guardar Cambios</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- TAB: FISCAL -->
                        <div id="content-fiscal" class="space-y-6 hidden">
                            <div><h3 class="text-2xl font-bold text-slate-900 tracking-tight">Integración Fiscal</h3></div>
                            <div class="bg-white border border-slate-200 p-8 shadow-sm">
                                <div class="flex items-center gap-3 mb-6 border-b border-slate-100 pb-4"><i class="ph-bold ph-shield-check text-brand-600 text-xl"></i><h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Credenciales y Certificados</h4></div>
                                <div class="divide-y divide-slate-100 mb-8">
                                    <div class="py-4 flex justify-between items-center"><div><p class="font-bold text-slate-900 text-sm">Token ApisPeru</p><p class="text-xs text-slate-500">Conexión API para consulta.</p></div><span class="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono font-bold uppercase tracking-widest">Configurado</span></div>
                                    <div class="py-4 flex justify-between items-center"><div><p class="font-bold text-slate-900 text-sm">Credenciales SOL</p><p class="text-xs text-slate-500">Transmisión a SUNAT.</p></div><span class="px-3 py-1 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-mono font-bold uppercase tracking-widest">Pendiente</span></div>
                                    <div class="py-4 flex justify-between items-center"><div><p class="font-bold text-slate-900 text-sm">Certificado Digital (PFX)</p><p class="text-xs text-slate-500">Firma electrónica de XML.</p></div><span class="px-3 py-1 bg-slate-100 text-slate-500 border border-slate-200 text-[10px] font-mono font-bold uppercase tracking-widest">No Cargado</span></div>
                                </div>
                                <div class="bg-brand-900 border border-brand-800 p-5 flex gap-4 items-start"><i class="ph-bold ph-info text-brand-400 text-xl mt-0.5"></i><div><h5 class="text-white font-bold text-sm">Actualización Restringida</h5><p class="text-brand-200 text-xs mt-1">Contacte al administrador para escalar permisos.</p></div></div>
                            </div>
                        </div>

                        <!-- TAB: CUENTA -->
                        <div id="content-cuenta" class="space-y-6 hidden">
                            <div><h3 class="text-2xl font-bold text-slate-900 tracking-tight">Tu Perfil</h3></div>
                            <div class="bg-white border border-slate-200 p-8 shadow-sm">
                                <div class="flex items-center gap-3 mb-6 border-b border-slate-100 pb-4"><i class="ph-bold ph-user-circle text-brand-600 text-xl"></i><h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Datos de Sesión</h4></div>
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                                    <div class="md:col-span-1 flex flex-col items-center border-r border-slate-100 pr-0 md:pr-8 py-4">
                                        <div class="w-24 h-24 bg-brand-50 border border-brand-200 rounded-full flex items-center justify-center text-brand-600 font-bold text-3xl mb-4">A</div>
                                        <button class="text-[10px] font-mono font-bold text-brand-600 uppercase tracking-widest outline-none">Cambiar Foto</button>
                                    </div>
                                    <div class="md:col-span-2 space-y-6">
                                        <div><label class="block text-[10px] font-bold font-mono text-slate-400 uppercase tracking-widest mb-1">Nombre Completo</label><p class="text-slate-900 font-bold text-sm">Admin Demo Inkora</p></div>
                                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                            <div><label class="block text-[10px] font-bold font-mono text-slate-400 uppercase tracking-widest mb-1">Email (Acceso)</label><p class="text-slate-900 font-mono text-sm">admin@demo.inkora.pe</p></div>
                                            <div><label class="block text-[10px] font-bold font-mono text-slate-400 uppercase tracking-widest mb-1">Rol Asignado</label><span class="inline-flex px-2 py-0.5 bg-brand-100 text-brand-700 font-mono font-bold text-[10px] uppercase tracking-widest">Admin</span></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

            </div>
        </main>
    </div>

    <!-- =========================================================================
         MODALES DE LA APLICACIÓN (Completos y Detallados)
         ========================================================================= -->

    <!-- MODAL CLIENTE (Full) -->
    <div id="clientModal" class="fixed inset-0 bg-brand-950/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4 transition-opacity hidden">
        <div class="bg-white border border-slate-200 rounded-none w-full max-w-3xl shadow-[8px_8px_0px_0px_rgba(15,14,41,0.15)] flex flex-col max-h-[90vh]">
            <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50 flex-none">
                <h3 class="font-bold text-slate-900 font-mono uppercase tracking-widest text-sm flex items-center gap-2"><i class="ph-bold ph-user-plus text-brand-600 text-lg"></i> Nuevo Cliente</h3>
                <button onclick="closeModal('clientModal')" class="text-slate-400 hover:text-rose-500 p-1 outline-none"><i class="ph-bold ph-x text-xl"></i></button>
            </div>
            <div class="p-6 space-y-6 overflow-y-auto no-scrollbar">
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
                    <div class="space-y-1.5 custom-select-container col-span-1">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Tipo doc.</label>
                        <div class="custom-select relative">
                            <input type="hidden" value="RUC">
                            <button type="button" class="select-trigger w-full px-4 py-3 bg-slate-50 border border-slate-300 text-slate-900 font-mono text-sm font-semibold flex justify-between items-center"><span class="select-text">RUC</span><i class="ph-bold ph-caret-down text-slate-400 pointer-events-none"></i></button>
                            <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col"><li class="px-4 py-3 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="RUC">RUC</li><li class="px-4 py-3 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="DNI">DNI</li></ul>
                        </div>
                    </div>
                    <div class="space-y-1.5 col-span-2 group">
                        <div class="flex justify-between items-end"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Número documento</label><button class="text-[9px] font-bold font-mono text-brand-600 uppercase flex items-center gap-1"><i class="ph-bold ph-magnifying-glass"></i> Consultar</button></div>
                        <input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 font-mono text-sm font-semibold focus:bg-white focus:border-brand-500 outline-none" placeholder="Ej. 20100200300">
                    </div>
                </div>
                <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Razón social / nombre</label><input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 text-sm font-medium focus:bg-white focus:border-brand-500 outline-none"></div>
                <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Dirección fiscal</label><input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 text-sm focus:bg-white focus:border-brand-500 outline-none"></div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Email</label><input type="email" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 font-mono text-sm focus:bg-white focus:border-brand-500 outline-none"></div>
                    <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Teléfono</label><input type="tel" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 font-mono text-sm focus:bg-white focus:border-brand-500 outline-none"></div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">WhatsApp</label><input type="tel" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 font-mono text-sm focus:bg-white focus:border-brand-500 outline-none"></div>
                    <div class="space-y-1.5 custom-select-container">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Condición de pago</label>
                        <div class="custom-select relative">
                            <input type="hidden" value="contado">
                            <button type="button" class="select-trigger w-full px-4 py-3 bg-slate-50 border border-slate-300 text-slate-900 font-mono text-sm font-semibold flex justify-between items-center outline-none"><span class="select-text">Contado</span><i class="ph-bold ph-caret-down text-slate-400 pointer-events-none"></i></button>
                            <ul class="select-menu absolute bottom-full mb-1 z-50 w-full bg-white border border-slate-200 shadow-[4px_-4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col"><li class="px-4 py-3 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="contado">Contado</li><li class="px-4 py-3 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="credito30">Crédito 30 días</li></ul>
                        </div>
                    </div>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-3 flex-none">
                <button onclick="closeModal('clientModal')" class="px-6 py-2.5 text-xs font-bold font-mono uppercase tracking-widest text-slate-600 hover:bg-slate-200 outline-none border border-transparent">Cancelar</button>
                <button onclick="closeModal('clientModal')" class="bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-2.5 flex items-center gap-2 hover:-translate-y-1 hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] transition-all outline-none border border-transparent"><i class="ph-bold ph-floppy-disk text-lg"></i> Guardar</button>
            </div>
        </div>
    </div>

    <!-- MODAL PRODUCTO (Full) -->
    <div id="productModal" class="fixed inset-0 bg-brand-950/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4 transition-opacity hidden">
        <div class="bg-white border border-slate-200 rounded-none w-full max-w-2xl shadow-[8px_8px_0px_0px_rgba(15,14,41,0.15)] flex flex-col">
            <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50 flex-none">
                <h3 class="font-bold text-slate-900 font-mono uppercase tracking-widest text-sm flex items-center gap-2"><i class="ph-bold ph-package text-brand-600 text-lg"></i> Registrar Producto</h3>
                <button onclick="closeModal('productModal')" class="text-slate-400 hover:text-rose-500 p-1 outline-none"><i class="ph-bold ph-x text-xl"></i></button>
            </div>
            <div class="p-6 space-y-6">
                <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Nombre</label><input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 text-sm focus:bg-white focus:border-brand-500 outline-none"></div>
                <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Descripción Interna</label><textarea rows="2" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 text-sm focus:bg-white focus:border-brand-500 outline-none resize-none"></textarea></div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
                    <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Precio Unitario</label><div class="relative"><span class="absolute left-4 top-1/2 -translate-y-1/2 font-bold text-slate-400">S/</span><input type="number" class="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-300 font-mono text-right text-base font-bold focus:bg-white focus:border-brand-500 outline-none"></div></div>
                    <div class="space-y-1.5 custom-select-container">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Unidad (U.M.)</label>
                        <div class="custom-select relative">
                            <button type="button" class="select-trigger w-full px-4 py-3 bg-slate-50 border border-slate-300 font-mono text-sm font-semibold flex justify-between items-center outline-none"><span class="select-text">NIU - Unidad</span><i class="ph-bold ph-caret-down text-slate-400 pointer-events-none"></i></button>
                            <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col"><li class="px-4 py-3 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="NIU">NIU - Unidad</li><li class="px-4 py-3 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="ZZ">ZZ - Servicio</li><li class="px-4 py-3 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="MIL">MIL - Millar</li></ul>
                        </div>
                    </div>
                    <div class="space-y-1.5 group"><div class="flex justify-between items-end"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Código SKU</label><button class="text-[9px] font-bold font-mono text-brand-600 uppercase flex items-center gap-1"><i class="ph-bold ph-arrows-clockwise"></i> Generar</button></div><input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 font-mono text-sm font-semibold focus:bg-white focus:border-brand-500 uppercase outline-none" placeholder="Ej. IMP-01"></div>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-3 flex-none">
                <button onclick="closeModal('productModal')" class="px-6 py-2.5 text-xs font-bold font-mono uppercase tracking-widest text-slate-600 hover:bg-slate-200 outline-none border border-transparent">Cancelar</button>
                <button onclick="closeModal('productModal')" class="bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-2.5 flex items-center gap-2 hover:-translate-y-1 hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] transition-all outline-none border border-transparent"><i class="ph-bold ph-floppy-disk text-lg"></i> Guardar</button>
            </div>
        </div>
    </div>

    <!-- MODAL COTIZACION (Wide Modal Spreadsheet Full) -->
    <div id="quoteModal" class="fixed inset-0 bg-brand-950/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4 transition-opacity hidden">
        <div class="bg-white border border-slate-200 rounded-none w-full max-w-5xl shadow-[8px_8px_0px_0px_rgba(15,14,41,0.15)] flex flex-col max-h-[95vh]">
            <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50 flex-none">
                <div class="flex items-center gap-4">
                    <h3 class="font-bold text-slate-900 font-mono uppercase tracking-widest text-sm flex items-center gap-2"><i class="ph-bold ph-file-plus text-brand-600 text-lg"></i> Nueva Cotización</h3>
                    <span class="px-2 py-0.5 bg-brand-100 text-brand-700 font-mono text-[10px] font-bold tracking-widest">Borrador</span>
                </div>
                <button onclick="closeModal('quoteModal')" class="text-slate-400 hover:text-rose-500 p-1 outline-none"><i class="ph-bold ph-x text-xl"></i></button>
            </div>
            <div class="flex-1 overflow-y-auto no-scrollbar flex flex-col">
                <div class="p-6 bg-white border-b border-slate-200 space-y-5">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div class="space-y-1.5 custom-select-container md:col-span-2">
                            <div class="flex justify-between items-end"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Cliente</label><button class="text-[9px] font-bold font-mono text-brand-600 uppercase flex items-center gap-1"><i class="ph-bold ph-plus"></i> Nuevo Cliente</button></div>
                            <div class="custom-select relative">
                                <button type="button" class="select-trigger w-full px-4 py-2.5 bg-slate-50 border border-slate-300 font-mono text-sm font-semibold flex justify-between items-center outline-none"><span class="select-text text-slate-400">Buscar o seleccionar cliente...</span><i class="ph-bold ph-caret-down text-slate-400 pointer-events-none"></i></button>
                                <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col"><li class="px-4 py-2.5 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="corp">Cliente Corporativo SAC</li></ul>
                            </div>
                        </div>
                        <div class="space-y-1.5 custom-select-container">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Moneda</label>
                            <div class="custom-select relative">
                                <button type="button" class="select-trigger w-full px-4 py-2.5 bg-slate-50 border border-slate-300 font-mono text-sm font-semibold flex justify-between items-center outline-none"><span class="select-text">PEN (S/) Soles</span><i class="ph-bold ph-caret-down text-slate-400 pointer-events-none"></i></button>
                                <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col"><li class="px-4 py-2.5 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="PEN">PEN (S/) Soles</li><li class="px-4 py-2.5 hover:bg-brand-50 cursor-pointer border-l-2 border-transparent hover:border-brand-500 text-sm" data-value="USD">USD ($) Dólares</li></ul>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="flex-1 bg-slate-50 p-6">
                    <div class="mb-4 flex justify-between items-center"><h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Líneas de Detalle</h4></div>
                    <div class="bg-white border border-slate-300 shadow-sm overflow-hidden">
                        <table class="w-full text-left border-collapse">
                            <thead class="bg-slate-100 border-b border-slate-300">
                                <tr>
                                    <th class="px-4 py-2 text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest w-[30%] border-r border-slate-200">Producto / Servicio</th>
                                    <th class="px-4 py-2 text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest w-[35%] border-r border-slate-200">Descripción detallada</th>
                                    <th class="px-4 py-2 text-right text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest w-[10%] border-r border-slate-200">Cant.</th>
                                    <th class="px-4 py-2 text-right text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest w-[12%] border-r border-slate-200">P. Unit</th>
                                    <th class="px-4 py-2 text-right text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest w-[10%] border-r border-slate-200">Total</th>
                                    <th class="w-[3%] bg-slate-100"></th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-200">
                                <tr class="group bg-white hover:bg-slate-50 transition-colors">
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0 relative"><select class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm font-semibold text-slate-900 focus:ring-0 cursor-pointer appearance-none outline-none"><option>Diseño Gráfico</option></select></td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0"><input type="text" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm text-slate-700 focus:ring-0 outline-none placeholder:text-slate-300" placeholder="Añadir descripción..."></td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0"><input type="number" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-900 text-right focus:ring-0 outline-none" value="1"></td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0 relative"><span class="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 font-mono">S/</span><input type="number" class="w-full h-full min-h-[40px] pl-6 pr-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-900 text-right focus:ring-0 outline-none" value="50.00"></td>
                                    <td class="border-r border-slate-200 p-0 bg-slate-50 relative"><span class="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 font-mono">S/</span><input type="text" readonly class="w-full h-full min-h-[40px] pl-6 pr-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-500 text-right outline-none" value="50.00"></td>
                                    <td class="p-0 text-center"><button class="w-full h-full flex items-center justify-center text-slate-300 hover:text-rose-500 transition-colors outline-none"><i class="ph-bold ph-trash"></i></button></td>
                                </tr>
                            </tbody>
                        </table>
                        <div class="p-2 bg-white border-t border-slate-200">
                            <button class="text-[11px] font-mono font-bold text-brand-600 uppercase tracking-widest hover:text-brand-800 hover:bg-brand-50 px-4 py-2 transition-colors flex items-center gap-1 outline-none"><i class="ph-bold ph-plus-circle text-base"></i> Agregar línea de detalle</button>
                        </div>
                    </div>
                    <div class="mt-6 flex justify-end">
                        <div class="w-full sm:w-80 bg-white border border-slate-300 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.05)] p-5">
                            <div class="space-y-3 font-mono text-sm">
                                <div class="flex justify-between text-slate-500"><span>Subtotal</span><span>S/ 50.00</span></div>
                                <div class="flex justify-between text-slate-500"><span>IGV (18%)</span><span>S/ 9.00</span></div>
                                <div class="pt-3 border-t border-slate-200 flex justify-between items-end"><span class="font-bold text-slate-900 uppercase tracking-widest text-[11px]">Total Cotización</span><span class="text-2xl font-black text-brand-600">S/ 59.00</span></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-slate-200 bg-slate-100 flex items-center justify-end gap-4 flex-none">
                <button onclick="closeModal('quoteModal')" class="px-6 py-2.5 text-xs font-bold font-mono uppercase tracking-widest text-slate-600 hover:bg-slate-200 outline-none border border-transparent">Cancelar</button>
                <button onclick="closeModal('quoteModal')" class="bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-3 flex items-center gap-2 hover:-translate-y-1 hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] transition-all outline-none border border-transparent"><i class="ph-bold ph-paper-plane-right text-lg"></i> Emitir Cotización</button>
            </div>
        </div>
    </div>

    <!-- MODAL GUÍA (Full Symmetry Grid Logístico) -->
    <div id="guideModal" class="fixed inset-0 bg-brand-950/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4 transition-opacity hidden">
        <div class="bg-white border border-slate-200 rounded-none w-full max-w-5xl shadow-[8px_8px_0px_0px_rgba(15,14,41,0.15)] flex flex-col max-h-[95vh]">
            <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50 flex-none">
                <div class="flex items-center gap-4">
                    <h3 class="font-bold text-slate-900 font-mono uppercase tracking-widest text-sm flex items-center gap-2"><i class="ph-bold ph-truck text-brand-600 text-lg"></i> Registrar Guía de Remisión</h3>
                    <span class="px-2 py-0.5 bg-brand-100 text-brand-700 font-mono text-[10px] font-bold tracking-widest">Emisión SUNAT</span>
                </div>
                <button onclick="closeModal('guideModal')" class="text-slate-400 hover:text-rose-500 p-1 outline-none"><i class="ph-bold ph-x text-xl"></i></button>
            </div>
            <div class="flex-1 overflow-y-auto no-scrollbar flex flex-col bg-white">
                <div class="p-6 border-b border-slate-200 space-y-6">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div class="space-y-1.5 custom-select-container">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Motivo traslado</label>
                            <div class="custom-select relative">
                                <button type="button" class="select-trigger w-full px-4 py-2.5 bg-slate-50 border border-slate-300 text-slate-900 font-mono text-sm font-semibold flex justify-between items-center outline-none"><span class="select-text flex items-center gap-2"><i class="ph-bold ph-shopping-cart text-slate-400"></i> Venta</span><i class="ph-bold ph-caret-down text-slate-400 pointer-events-none"></i></button>
                                <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col"><li class="px-4 py-2.5 hover:bg-brand-50 cursor-pointer text-sm flex items-center gap-2 border-l-2 border-transparent hover:border-brand-500"><i class="ph-bold ph-shopping-cart"></i> Venta</li><li class="px-4 py-2.5 hover:bg-brand-50 cursor-pointer text-sm flex items-center gap-2 border-l-2 border-transparent hover:border-brand-500"><i class="ph-bold ph-arrows-left-right"></i> Traslado entre establecimientos</li></ul>
                            </div>
                        </div>
                        <div class="space-y-1.5 custom-select-container">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Modalidad</label>
                            <div class="custom-select relative">
                                <button type="button" class="select-trigger w-full px-4 py-2.5 bg-slate-50 border border-slate-300 text-slate-900 font-mono text-sm font-semibold flex justify-between items-center outline-none"><span class="select-text flex items-center gap-2"><i class="ph-bold ph-bus text-slate-400"></i> Transporte público</span><i class="ph-bold ph-caret-down text-slate-400 pointer-events-none"></i></button>
                                <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col"><li class="px-4 py-2.5 hover:bg-brand-50 cursor-pointer text-sm flex items-center gap-2 border-l-2 border-transparent hover:border-brand-500"><i class="ph-bold ph-bus"></i> Transporte público</li><li class="px-4 py-2.5 hover:bg-brand-50 cursor-pointer text-sm flex items-center gap-2 border-l-2 border-transparent hover:border-brand-500"><i class="ph-bold ph-truck"></i> Transporte privado</li></ul>
                            </div>
                        </div>
                        <div class="space-y-1.5 group">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Peso Bruto Total</label>
                            <div class="relative flex items-center">
                                <input type="number" class="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm font-bold text-right focus:bg-white focus:border-brand-500 outline-none pr-12" placeholder="0.000">
                                <span class="absolute right-3 font-mono text-xs font-bold text-slate-400 pointer-events-none select-none">KGM</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-200 border-b border-slate-200">
                    <div class="p-6 bg-slate-50/50 space-y-5">
                        <h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest flex items-center gap-2 mb-4"><i class="ph-bold ph-map-pin text-slate-400 text-base"></i> Punto de Partida</h4>
                        <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Dirección Partida</label><input type="text" class="w-full px-4 py-2.5 bg-white border border-slate-300 text-sm focus:border-brand-500 outline-none" placeholder="Av. Los Pinos 123"></div>
                        <div class="space-y-1.5 group">
                            <div class="flex justify-between items-end"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Ubigeo Partida</label><button type="button" class="text-[9px] font-bold font-mono text-brand-600 uppercase flex items-center gap-1"><i class="ph-bold ph-magnifying-glass"></i> Buscar</button></div>
                            <input type="text" maxlength="6" class="w-full px-4 py-2.5 bg-white border border-slate-300 font-mono text-sm tracking-widest font-bold focus:border-brand-500 outline-none" placeholder="150101">
                        </div>
                    </div>
                    <div class="p-6 bg-white space-y-5 relative">
                        <div class="hidden md:flex absolute top-1/2 -left-4 w-8 h-8 bg-white border border-slate-200 rounded-full items-center justify-center text-slate-400 z-10"><i class="ph-bold ph-arrow-right"></i></div>
                        <h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest flex items-center gap-2 mb-4"><i class="ph-fill ph-map-pin text-brand-500 text-base"></i> Punto de Llegada</h4>
                        <div class="space-y-1.5 group"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Dirección Llegada</label><input type="text" class="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 text-sm focus:bg-white focus:border-brand-500 outline-none" placeholder="Jr. El Sol 456"></div>
                        <div class="space-y-1.5 group">
                            <div class="flex justify-between items-end"><label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Ubigeo Llegada</label><button type="button" class="text-[9px] font-bold font-mono text-brand-600 uppercase flex items-center gap-1"><i class="ph-bold ph-magnifying-glass"></i> Buscar</button></div>
                            <input type="text" maxlength="6" class="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 font-mono text-sm tracking-widest font-bold focus:bg-white focus:border-brand-500 outline-none" placeholder="150102">
                        </div>
                    </div>
                </div>
                <div class="flex-1 bg-slate-50/50 p-6">
                    <div class="mb-4 flex justify-between items-center"><h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Bienes a Trasladar</h4></div>
                    <div class="bg-white border border-slate-300 shadow-sm overflow-hidden">
                        <table class="w-full text-left border-collapse">
                            <thead class="bg-slate-100 border-b border-slate-300">
                                <tr>
                                    <th class="px-4 py-2 text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest w-[20%] border-r border-slate-200">Código</th>
                                    <th class="px-4 py-2 text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest w-[50%] border-r border-slate-200">Descripción del bien</th>
                                    <th class="px-4 py-2 text-right text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest w-[15%] border-r border-slate-200">Unidad</th>
                                    <th class="px-4 py-2 text-right text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest w-[12%] border-r border-slate-200">Cant.</th>
                                    <th class="w-[3%] bg-slate-100"></th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-200">
                                <tr class="group bg-white hover:bg-slate-50 transition-colors">
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0"><input type="text" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-900 focus:ring-0 outline-none uppercase" placeholder="SKU-001"></td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0"><input type="text" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm text-slate-700 focus:ring-0 outline-none placeholder:text-slate-300" placeholder="Descripción detallada..."></td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0"><select class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-xs font-mono font-bold text-slate-600 focus:ring-0 cursor-pointer appearance-none outline-none text-right-override" style="text-align-last: right;"><option>NIU (Und)</option><option>MIL (Millar)</option></select></td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0"><input type="number" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-900 text-right focus:ring-0 outline-none" value="1"></td>
                                    <td class="p-0 text-center"><button class="w-full h-full flex items-center justify-center text-slate-300 hover:text-rose-500 transition-colors outline-none"><i class="ph-bold ph-trash"></i></button></td>
                                </tr>
                            </tbody>
                        </table>
                        <div class="p-2 bg-white border-t border-slate-200"><button class="text-[11px] font-mono font-bold text-brand-600 uppercase tracking-widest hover:text-brand-800 hover:bg-brand-50 px-4 py-2 transition-colors flex items-center gap-1 outline-none"><i class="ph-bold ph-plus-circle text-base"></i> Agregar bien a trasladar</button></div>
                    </div>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-slate-200 bg-slate-100 flex items-center justify-end gap-4 flex-none">
                <button onclick="closeModal('guideModal')" class="px-6 py-2.5 text-xs font-bold font-mono uppercase tracking-widest text-slate-600 hover:bg-slate-200 outline-none border border-transparent">Cancelar</button>
                <button onclick="closeModal('guideModal')" class="bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-3 flex items-center gap-2 hover:-translate-y-1 hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] transition-all outline-none border border-transparent"><i class="ph-bold ph-truck text-lg"></i> Emitir Guía</button>
            </div>
        </div>
    </div>


    <!-- =========================================================================
         SCRIPTS: LÓGICA DE LA SINGLE PAGE APP (SPA)
         ========================================================================= -->
    <script>
        // --- 1. Lógica de Reloj Global ---
        function updateClock() {
            const now = new Date();
            const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
            document.querySelectorAll('.sysClock, #sysClock').forEach(el => el.textContent = time);
            
            const options = { day: 'numeric', month: 'short', year: 'numeric' };
            const dateStr = now.toLocaleDateString('es-PE', options).toUpperCase();
            document.querySelectorAll('.sysDate, #sysDate').forEach(el => el.textContent = `${dateStr} · LIMA (PET)`);
        }
        setInterval(updateClock, 1000); updateClock();

        // --- 2. Lógica de Login a App ---
        function handleLogin() {
            const loginView = document.getElementById('view-login');
            const appView = document.getElementById('view-app');
            loginView.style.opacity = '0';
            setTimeout(() => {
                loginView.style.display = 'none';
                appView.classList.remove('hidden');
                navigateTo('dashboard');
            }, 500);
        }

        function handleLogout() {
            const loginView = document.getElementById('view-login');
            const appView = document.getElementById('view-app');
            appView.classList.add('hidden');
            loginView.style.display = 'flex';
            setTimeout(() => { loginView.style.opacity = '1'; }, 50);
        }

        // --- 3. Lógica de Navegación del Sidebar (SPA Routing) ---
        const pageTitles = {
            'dashboard': { title: 'Panel General', subtitle: 'Vista Global' },
            'clientes': { title: 'Clientes', subtitle: 'Directorio' },
            'productos': { title: 'Productos y servicios', subtitle: 'Catálogo' },
            'cotizaciones': { title: 'Cotizaciones', subtitle: 'Motor Comercial' },
            'cobranza': { title: 'Cobranza', subtitle: 'Flujo de Caja' },
            'guias': { title: 'Guías de remisión', subtitle: 'Despacho Fiscal' },
            'configuracion': { title: 'Configuración del Sistema', subtitle: 'Admin' }
        };

        function navigateTo(pageId) {
            document.querySelectorAll('.page-section').forEach(el => {
                el.classList.add('hidden'); el.classList.remove('block');
            });
            
            const targetPage = document.getElementById('page-' + pageId);
            if(targetPage) {
                targetPage.classList.remove('hidden'); targetPage.classList.add('block');
            }

            document.getElementById('global-page-title').childNodes[0].textContent = pageTitles[pageId].title + " ";
            document.getElementById('global-page-subtitle').textContent = pageTitles[pageId].subtitle;

            document.querySelectorAll('.nav-item').forEach(el => {
                el.classList.remove('bg-gradient-to-r', 'from-brand-600/20', 'to-transparent', 'text-white', 'font-semibold');
                el.classList.add('text-slate-400', 'hover:text-white', 'hover:bg-white/5', 'font-medium');
                const indicator = el.querySelector('.active-indicator');
                if(indicator) indicator.classList.add('hidden');
                const icon = el.querySelector('i');
                if(icon) { icon.classList.replace('ph-fill', 'ph'); icon.classList.remove('text-brand-400'); }
            });

            const activeNav = document.getElementById('nav-' + pageId);
            if(activeNav) {
                activeNav.classList.remove('text-slate-400', 'hover:text-white', 'hover:bg-white/5', 'font-medium');
                activeNav.classList.add('bg-gradient-to-r', 'from-brand-600/20', 'to-transparent', 'text-white', 'font-semibold');
                const indicator = activeNav.querySelector('.active-indicator');
                if(indicator) indicator.classList.remove('hidden');
                const icon = activeNav.querySelector('i');
                if(icon) { icon.classList.replace('ph', 'ph-fill'); icon.classList.add('text-brand-400'); }
            }
        }

        // --- 4. Lógica de Pestañas (Configuración) ---
        function switchTab(tabId) {
            ['empresa', 'fiscal', 'cuenta'].forEach(id => {
                const btn = document.getElementById(`tab-${id}`);
                const content = document.getElementById(`content-${id}`);
                if(!btn || !content) return;
                
                if(id === tabId) {
                    btn.classList.add('border-brand-600', 'text-brand-600');
                    btn.classList.remove('border-transparent', 'text-slate-500');
                    content.classList.remove('hidden'); content.classList.add('block');
                } else {
                    btn.classList.remove('border-brand-600', 'text-brand-600');
                    btn.classList.add('border-transparent', 'text-slate-500');
                    content.classList.add('hidden'); content.classList.remove('block');
                }
            });
        }

        // --- 5. Lógica de Modales ---
        function openModal(modalId) {
            document.getElementById(modalId).classList.remove('hidden');
        }
        function closeModal(modalId) {
            document.getElementById(modalId).classList.add('hidden');
        }

        // --- 6. Lógica de Custom Selects Globales ---
        document.addEventListener('click', (e) => {
            const isClickInsideSelect = e.target.closest('.custom-select-container');
            document.querySelectorAll('.select-menu').forEach(menu => {
                if(!isClickInsideSelect || menu.parentElement !== isClickInsideSelect.querySelector('.custom-select')) {
                    menu.classList.add('hidden'); menu.classList.remove('flex');
                    const trigger = menu.parentElement.querySelector('.select-trigger');
                    const icon = menu.parentElement.querySelector('.ph-caret-down');
                    if(trigger) trigger.classList.remove('border-brand-500', 'ring-1', 'ring-brand-500', 'bg-white');
                    if(icon) icon.classList.remove('rotate-180');
                }
            });
        });

        document.querySelectorAll('.custom-select-container').forEach(container => {
            const select = container.querySelector('.custom-select');
            const trigger = container.querySelector('.select-trigger');
            const menu = container.querySelector('.select-menu');
            const text = container.querySelector('.select-text');
            const icon = container.querySelector('.ph-caret-down');
            const hiddenInput = container.querySelector('input[type="hidden"]');
            
            if(!trigger || !menu) return;

            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                const isHidden = menu.classList.contains('hidden');
                
                // Close others
                document.querySelectorAll('.select-menu').forEach(m => { 
                    m.classList.add('hidden'); m.classList.remove('flex'); 
                    const t = m.parentElement.querySelector('.select-trigger');
                    const i = m.parentElement.querySelector('.ph-caret-down');
                    if(t) t.classList.remove('border-brand-500', 'ring-1', 'ring-brand-500', 'bg-white');
                    if(i) i.classList.remove('rotate-180');
                });

                if(isHidden) { 
                    menu.classList.remove('hidden'); 
                    menu.classList.add('flex'); 
                    trigger.classList.add('border-brand-500', 'ring-1', 'ring-brand-500', 'bg-white');
                    if(icon) icon.classList.add('rotate-180');
                }
            });

            menu.querySelectorAll('li').forEach(opt => {
                opt.addEventListener('click', (e) => {
                    e.stopPropagation();
                    text.innerHTML = opt.innerHTML;
                    if(text.classList.contains('text-slate-400')) { 
                        text.classList.remove('text-slate-400'); 
                        text.classList.add('text-slate-900'); 
                    }
                    if(hiddenInput) hiddenInput.value = opt.getAttribute('data-value') || opt.textContent.trim();
                    menu.classList.add('hidden'); 
                    menu.classList.remove('flex');
                    trigger.classList.remove('border-brand-500', 'ring-1', 'ring-brand-500', 'bg-white');
                    if(icon) icon.classList.remove('rotate-180');
                });
            });
        });
    </script>
</body>
</html>