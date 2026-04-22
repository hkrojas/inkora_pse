Sistema de Diseño - Inkora (Facturación para Imprentas)

Estilo Global Aprobado: Industrial / Editorial Edge-to-Edge (Versión Élite).
Concepto: Alta precisión, contraste severo, interacciones dinámicas de revelación y estética de centro de mando (Command Center) para finanzas y logística.

1. Módulo: Login y Acceso

Contraste Severo (Claroscuro): Panel oscuro inmovilizado a la izquierda (Blueprint) y lienzo de acción blanco a la derecha.

Brutalismo Funcional: Botones sin bordes redondeados (rounded-none), con sombra sólida desplazada al hacer hover (shadow-[4px_4px_0px_0px_rgba(99,102,241,1)]).

Tipografía de Precisión: Uso de JetBrains Mono para metadatos, latencias y etiquetas de seguridad.

2. Módulo: Dashboard Principal

Sidebar Industrial: Barra lateral siempre en Dark Mode (bg-brand-950) para anclar la vista y evitar la "ceguera de nieve".

Semántica de Liquidez:

Verde (emerald-600): Ingresos / Éxito.

Ámbar (amber-600): Capital Pendiente / Precaución.

Rojo (rose-600): Capital en Riesgo / Vencido (Uso de glow animado para alertas críticas).

Sparklines: Micro-gráficos vectoriales de tendencia en el fondo de los KPIs positivos.

3. Módulo: Formularios y Modales (Data Entry)

Sombra Brutalista: Los modales usan sombra sólida desplazada sobre un fondo de cristal esmerilado oscuro (bg-brand-950/60 backdrop-blur-sm).

Inputs de Caja Técnica: Fondo gris sutil (bg-slate-50) que cambia a blanco puro con borde índigo al hacer focus.

Custom Selects: Prohibido el uso de <select> nativo. Se utilizan menús flotantes personalizados con tipografía monoespaciada e indicador lateral de hover.

4. Módulo: Documentos Transaccionales (Cotizaciones)

Wide Modals: Modales ultra-anchos (max-w-5xl) divididos en Cabecera (Metadatos) y Detalle (Ledger).

Spreadsheet UI: Las tablas de ítems simulan una hoja de Excel. Celdas transparentes que adquieren borde interactivo al hacer focus, optimizando la tabulación.

Panel de Liquidación: Los totales se anclan en la esquina inferior derecha con jerarquía tipográfica dominante (text-2xl font-black).

5. Módulo: Finanzas y Cobranza (Accounts Receivable)

Aging Badges (Antigüedad de Deuda): Los días de mora se encapsulan en etiquetas monoespaciadas escalonadas por color (Gris -> Ámbar -> Rojo Crítico).

Hover Reveal (Micro-acciones): Botones de "Registrar Pago" y "Notificar" se mantienen ocultos y solo se revelan al pasar el cursor sobre la fila del cliente.

6. Módulo: Logística y Despacho (Guías de Remisión)

Agrupación Simétrica de Rutas: El layout divide visualmente el "Origen" (fondo grisáceo) del "Destino" (fondo blanco) para reducir la carga cognitiva espacial.

Sufijos Físicos: Los inputs de magnitudes (peso, volumen) incluyen su unidad técnica inamovible (ej. KGM) y texto alineado a la derecha.

7. Módulo: Configuración y Paneles de Control (Settings)

Arquitectura de Pestañas (Tabs): Prohibido el scroll infinito para configuraciones complejas. Se exige una sub-navegación superior con estilo editorial (texto con border-b-2 activo).

Estados Read-Only: Los datos no editables (ej. Email de acceso, Rol) se muestran como texto plano o cajas bloqueadas, nunca como inputs activos.

Alertas de Terminal: Los avisos de sistema crítico (ej. permisos insuficientes) utilizan cajas oscuras (bg-brand-900) con texto blanco, alejándose de los banners color pastel genéricos.

Badges de Integración: Uso de etiquetas para denotar la salud del entorno (Configurado, Pendiente, No Cargado).

Estilo del dashboard

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inkora - Centro de Mando Operativo</title>
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
                        'slide-in': 'slide-in 0.2s ease-out forwards',
                    },
                    keyframes: {
                        'gradient-x': {
                            '0%, 100%': {
                                'background-size': '200% 200%',
                                'background-position': 'left center'
                            },
                            '50%': {
                                'background-size': '200% 200%',
                                'background-position': 'right center'
                            }
                        },
                        'slide-in': {
                            '0%': { transform: 'translateX(10px)', opacity: '0' },
                            '100%': { transform: 'translateX(0)', opacity: '1' }
                        }
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap');
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: #F4F5F8; 
        }

        .tech-grid {
            background-image: 
                linear-gradient(rgba(99, 102, 241, 0.04) 1px, transparent 1px),
                linear-gradient(90deg, rgba(99, 102, 241, 0.04) 1px, transparent 1px);
            background-size: 32px 32px;
        }
        
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

        /* Efecto de cristal esmerilado avanzado */
        .glass-header {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }
    </style>
</head>
<body class="h-screen w-full flex overflow-hidden selection:bg-brand-500 selection:text-white tech-grid relative">

    <!-- Micro-detalle Élite: Línea de tensión superior con tu degradado -->
    <div class="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#3B82F6] via-[#6366F1] to-[#D946EF] z-50 animate-gradient-x"></div>

    <!-- ==========================================
         SIDEBAR (Navegación Industrial)
         ========================================== -->
    <aside class="w-[280px] bg-brand-950 flex-none flex flex-col justify-between shadow-2xl relative z-40 hidden md:flex border-r border-white/5">
        
        <div class="flex-1 overflow-y-auto no-scrollbar pt-2">
            <!-- Logo -->
            <div class="p-6">
                <div class="flex items-center gap-3 mb-2">
                    <div class="w-9 h-9 flex items-center justify-center filter drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]">
                        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
                            <defs>
                                <linearGradient id="inkoraGradient" x1="0%" y1="100%" x2="100%" y2="0%">
                                    <stop offset="0%" stop-color="#3B82F6" />
                                    <stop offset="40%" stop-color="#6366F1" />
                                    <stop offset="100%" stop-color="#D946EF" />
                                </linearGradient>
                            </defs>
                            <path d="M50 0 C50 0 5 35 5 65 C5 89.8 25.2 100 50 100 C74.8 100 95 89.8 95 65 C95 35 50 0 50 0 Z M 35 25 L 50 25 L 50 52 L 72 25 L 88 25 L 62 58 L 88 90 L 72 90 L 50 63 L 50 90 L 35 90 Z" fill="url(#inkoraGradient)"/>
                        </svg>
                    </div>
                    <h1 class="text-2xl font-bold tracking-tight text-white">Inkora</h1>
                </div>
                <p class="text-[10px] font-mono text-slate-400 uppercase tracking-widest pl-12">Imprentas Core</p>
            </div>

            <!-- Menú -->
            <nav class="p-4 space-y-1 mt-4">
                <!-- Ítem Activo (Con detalle de degradado) -->
                <a href="#" class="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-brand-600/20 to-transparent text-white font-semibold text-sm transition-colors relative group">
                    <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF]"></div>
                    <i class="ph-fill ph-squares-four text-xl text-brand-400"></i>
                    Centro de Mando
                </a>
                <!-- Ítems Inactivos -->
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-users text-xl group-hover:text-brand-400 transition-colors"></i>
                    Clientes
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-package text-xl group-hover:text-brand-400 transition-colors"></i>
                    Productos
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-file-text text-xl group-hover:text-brand-400 transition-colors"></i>
                    Cotizaciones
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-credit-card text-xl group-hover:text-brand-400 transition-colors"></i>
                    Cobranza
                </a>
            </nav>
        </div>

        <!-- Footer Sidebar (Usuario y Cierre de Sesión Élite) -->
        <div class="p-4">
            <div class="flex items-center justify-between px-4 py-3 bg-brand-900/50 rounded-none border border-white/5 hover:border-brand-500/50 transition-colors cursor-pointer group">
                <div class="flex items-center gap-3 overflow-hidden">
                    <div class="w-8 h-8 bg-brand-800 rounded-none flex items-center justify-center text-white font-bold text-sm group-hover:bg-brand-600 transition-colors shrink-0">
                        A
                    </div>
                    <div class="flex-1 overflow-hidden">
                        <p class="text-sm font-semibold text-white truncate">Admin Demo</p>
                        <p class="text-[10px] font-mono text-brand-400 uppercase">Pro Access</p>
                    </div>
                </div>
                
                <!-- Acción de Cerrar Sesión (Aparece en Hover) -->
                <button 
                    onclick="alert('Cerrando sesión del sistema Inkora...')"
                    class="text-slate-500 hover:text-rose-400 opacity-0 group-hover:opacity-100 transform translate-x-2 group-hover:translate-x-0 transition-all duration-300 px-1" 
                    title="Cerrar sesión segura">
                    <i class="ph-bold ph-power text-xl"></i>
                </button>
            </div>
        </div>
    </aside>

    <!-- ==========================================
         ÁREA PRINCIPAL (Workspace)
         ========================================== -->
    <main class="flex-1 flex flex-col h-screen overflow-hidden relative z-10">
        
        <!-- Topbar Glassmorphism -->
        <header class="glass-header border-b border-slate-200/50 px-8 py-4 flex items-center justify-between flex-none sticky top-0 z-30 pt-5">
            <div>
                <h2 class="text-xl font-bold text-slate-900 flex items-center gap-3">
                    Panel General
                    <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-mono tracking-widest uppercase">Vista Global</span>
                </h2>
            </div>

            <div class="flex items-center gap-6">
                <!-- Reloj de Sistema en Tiempo Real -->
                <div class="hidden lg:flex flex-col items-end">
                    <p id="sysClock" class="font-mono text-sm font-bold text-slate-800">00:00:00</p>
                    <p id="sysDate" class="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Cargando fecha...</p>
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

        <!-- Contenido -->
        <div class="flex-1 overflow-y-auto p-8 no-scrollbar">
            <div class="max-w-[1400px] mx-auto space-y-8 pb-12">

                <!-- Header de Sección -->
                <div class="flex justify-between items-end">
                    <div>
                        <h3 class="text-4xl font-bold text-slate-900 tracking-tight">Hola, Admin</h3>
                        <p class="text-slate-500 mt-2 text-sm">Resumen de liquidez y flujo fiscal del período actual.</p>
                    </div>
                    
                    <!-- Botón Élite (Doble borde y animación) -->
                    <button class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-6 py-3 transition-all flex items-center gap-2 rounded-none hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1">
                        <div class="absolute inset-0 border border-white/20"></div>
                        <i class="ph ph-lightning text-brand-400 text-lg group-hover:animate-pulse"></i> 
                        Nueva Emisión
                    </button>
                </div>

                <!-- KPIs (Con Sparklines SVG) -->
                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
                    
                    <!-- KPI 1 -->
                    <div class="bg-white p-6 border border-slate-200 border-t-2 border-t-brand-500 shadow-sm relative overflow-hidden group hover:border-brand-300 transition-colors">
                        <div class="relative z-10">
                            <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Emisiones (Mes)</p>
                            <p class="text-4xl font-mono font-bold text-slate-900 mb-1">1,248</p>
                            <p class="text-xs text-emerald-600 font-mono font-bold flex items-center gap-1">
                                <i class="ph-bold ph-arrow-up-right"></i> +12.5% <span class="text-slate-400 font-normal">vs anterior</span>
                            </p>
                        </div>
                        <!-- Sparkline Decorativo -->
                        <svg class="absolute bottom-0 right-0 w-32 h-16 text-brand-50 opacity-50 group-hover:opacity-100 transition-opacity" viewBox="0 0 100 50" fill="none" preserveAspectRatio="none">
                            <path d="M0 50 L20 40 L40 45 L60 20 L80 30 L100 10" stroke="currentColor" stroke-width="3" fill="none"/>
                            <path d="M0 50 L20 40 L40 45 L60 20 L80 30 L100 10 L100 50 L0 50 Z" fill="currentColor"/>
                        </svg>
                    </div>

                    <!-- KPI 2 -->
                    <div class="bg-white p-6 border border-slate-200 border-t-2 border-t-emerald-500 shadow-sm relative overflow-hidden group hover:border-emerald-300 transition-colors">
                        <div class="relative z-10">
                            <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Ingresos Registrados</p>
                            <div class="flex items-baseline gap-1 mb-1">
                                <span class="text-lg font-bold text-emerald-600">S/</span>
                                <p class="text-4xl font-mono font-bold text-emerald-600">42,350<span class="text-xl text-emerald-400">.00</span></p>
                            </div>
                            <p class="text-xs text-emerald-600 font-mono font-bold flex items-center gap-1">
                                <i class="ph-bold ph-arrow-up-right"></i> +4.2% <span class="text-slate-400 font-normal">vs anterior</span>
                            </p>
                        </div>
                        <svg class="absolute bottom-0 right-0 w-32 h-16 text-emerald-50 opacity-50 group-hover:opacity-100 transition-opacity" viewBox="0 0 100 50" fill="none" preserveAspectRatio="none">
                            <path d="M0 50 L20 35 L40 40 L60 15 L80 20 L100 5" stroke="currentColor" stroke-width="3" fill="none"/>
                            <path d="M0 50 L20 35 L40 40 L60 15 L80 20 L100 5 L100 50 L0 50 Z" fill="currentColor"/>
                        </svg>
                    </div>

                    <!-- KPI 3 -->
                    <div class="bg-white p-6 border border-slate-200 border-t-2 border-t-amber-500 shadow-sm relative overflow-hidden group hover:border-amber-300 transition-colors">
                        <div class="relative z-10">
                            <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Capital Por Cobrar</p>
                            <div class="flex items-baseline gap-1 mb-1">
                                <span class="text-lg font-bold text-amber-600">S/</span>
                                <p class="text-4xl font-mono font-bold text-amber-600">33,826<span class="text-xl text-amber-400">.00</span></p>
                            </div>
                            <p class="text-xs text-amber-600 font-mono font-bold flex items-center gap-1">
                                <i class="ph-bold ph-minus"></i> 0.0% <span class="text-slate-400 font-normal">Estable</span>
                            </p>
                        </div>
                        <svg class="absolute bottom-0 right-0 w-32 h-16 text-amber-50 opacity-50 group-hover:opacity-100 transition-opacity" viewBox="0 0 100 50" fill="none" preserveAspectRatio="none">
                            <path d="M0 50 L20 25 L40 25 L60 25 L80 25 L100 25" stroke="currentColor" stroke-width="3" stroke-dasharray="4 4" fill="none"/>
                        </svg>
                    </div>

                    <!-- KPI 4: Alerta Crítica (Look Terminal) -->
                    <div class="bg-slate-900 p-6 border border-rose-500/50 border-t-2 border-t-rose-500 shadow-sm relative overflow-hidden group">
                        <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMSIgY3k9IjEiIHI9IjEiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')] opacity-50"></div>
                        <div class="absolute top-0 right-0 w-24 h-24 bg-rose-500 opacity-20 blur-2xl rounded-full animate-pulse"></div>
                        
                        <div class="relative z-10">
                            <div class="flex justify-between items-start mb-4">
                                <p class="text-[10px] font-bold font-mono text-rose-400 uppercase tracking-widest">Docs. Vencidos</p>
                                <span class="flex h-2 w-2">
                                  <span class="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-rose-400 opacity-75"></span>
                                  <span class="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
                                </span>
                            </div>
                            <p class="text-4xl font-mono font-bold text-white mb-1">14</p>
                            <p class="text-xs text-rose-400 font-mono flex items-center gap-1">
                                <i class="ph-bold ph-warning-circle"></i> Acción inmediata requerida
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Lista de Cobranza (Revelación Progresiva) -->
                <div class="bg-white border border-slate-200 rounded-none shadow-sm">
                    <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/80 backdrop-blur-sm">
                        <div class="flex items-center gap-3">
                            <div class="w-8 h-8 bg-white border border-slate-200 flex items-center justify-center text-slate-800 shadow-sm">
                                <i class="ph-bold ph-list-numbers"></i>
                            </div>
                            <h4 class="font-bold text-slate-900 font-mono uppercase tracking-wider text-sm">Ledger: Cobranza Urgente</h4>
                        </div>
                        <a href="#" class="text-xs font-mono font-bold text-brand-600 hover:text-brand-800 flex items-center gap-1 transition-colors">
                            Ver todo el reporte <i class="ph-bold ph-arrow-right"></i>
                        </a>
                    </div>
                    
                    <!-- Item 1 (Hover Reveal Action) -->
                    <div class="flex items-center justify-between p-4 border-b border-slate-100 hover:bg-brand-50/50 transition-all group relative">
                        <div class="flex items-center gap-4">
                            <div class="w-10 h-10 bg-rose-50 flex items-center justify-center border border-rose-100 text-rose-600 font-mono text-xs font-bold">
                                #01
                            </div>
                            <div>
                                <p class="font-bold text-slate-900 group-hover:text-brand-700 transition-colors">Cliente Corporativo SAC</p>
                                <div class="flex items-center gap-2 mt-1">
                                    <span class="px-1.5 py-0.5 bg-rose-100 text-rose-700 text-[9px] font-bold font-mono uppercase tracking-widest border border-rose-200">
                                        Vencido
                                    </span>
                                    <p class="text-xs text-slate-500 font-mono">FACT-001-492 · Venció: 01/01/2026</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="flex items-center gap-6">
                            <div class="text-right transition-transform group-hover:-translate-x-4 duration-300">
                                <p class="font-mono font-bold text-rose-600 text-lg">S/ 1,200.00</p>
                            </div>
                            <!-- Botón oculto que aparece en hover -->
                            <div class="absolute right-6 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                <button class="bg-brand-600 hover:bg-brand-700 text-white font-mono text-[10px] uppercase tracking-widest px-4 py-2 border border-brand-700 shadow-sm">
                                    Notificar
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Item 2 -->
                    <div class="flex items-center justify-between p-4 hover:bg-brand-50/50 transition-all group relative border-b border-slate-100">
                        <div class="flex items-center gap-4">
                            <div class="w-10 h-10 bg-slate-50 flex items-center justify-center border border-slate-200 text-slate-600 font-mono text-xs font-bold">
                                #02
                            </div>
                            <div>
                                <p class="font-bold text-slate-900 group-hover:text-brand-700 transition-colors">Imprenta Universal EIRL</p>
                                <div class="flex items-center gap-2 mt-1">
                                    <span class="px-1.5 py-0.5 bg-amber-50 text-amber-700 text-[9px] font-bold font-mono uppercase tracking-widest border border-amber-200">
                                        Vence Mañana
                                    </span>
                                    <p class="text-xs text-slate-500 font-mono">FACT-001-495 · Vence: 15/04/2026</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="flex items-center gap-6">
                            <div class="text-right transition-transform group-hover:-translate-x-4 duration-300">
                                <p class="font-mono font-bold text-slate-900 text-lg">S/ 450.50</p>
                            </div>
                            <div class="absolute right-6 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                <button class="bg-brand-600 hover:bg-brand-700 text-white font-mono text-[10px] uppercase tracking-widest px-4 py-2 border border-brand-700 shadow-sm">
                                    Revisar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </main>

    <!-- Script del Reloj -->
    <script>
        function updateClock() {
            const now = new Date();
            
            // Hora
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            document.getElementById('sysClock').textContent = `${hours}:${minutes}:${seconds}`;
            
            // Fecha
            const options = { day: 'numeric', month: 'short', year: 'numeric' };
            const dateStr = now.toLocaleDateString('es-PE', options).toUpperCase();
            document.getElementById('sysDate').textContent = `${dateStr} · LIMA (PET)`;
        }
        
        setInterval(updateClock, 1000);
        updateClock(); // Llamada inicial
    </script>
</body>
</html>

Estilo de Clientes

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inkora - Clientes</title>
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
        .tech-grid {
            background-image: linear-gradient(rgba(99, 102, 241, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(99, 102, 241, 0.04) 1px, transparent 1px);
            background-size: 32px 32px;
        }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .glass-header { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
        
        /* Ocultar flechas numéricas */
        input[type=number]::-webkit-inner-spin-button, 
        input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
</head>
<body class="h-screen w-full flex overflow-hidden selection:bg-brand-500 selection:text-white tech-grid relative">

    <!-- Línea de tensión superior -->
    <div class="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#3B82F6] via-[#6366F1] to-[#D946EF] z-50 animate-gradient-x"></div>

    <!-- ==========================================
         SIDEBAR (Navegación Industrial)
         ========================================== -->
    <aside class="w-[280px] bg-brand-950 flex-none flex flex-col justify-between shadow-2xl relative z-30 hidden md:flex border-r border-white/5">
        
        <div class="flex-1 overflow-y-auto no-scrollbar pt-2">
            <!-- Logo -->
            <div class="p-6">
                <div class="flex items-center gap-3 mb-2">
                    <div class="w-9 h-9 flex items-center justify-center filter drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]">
                        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
                            <defs>
                                <linearGradient id="inkoraGradient" x1="0%" y1="100%" x2="100%" y2="0%">
                                    <stop offset="0%" stop-color="#3B82F6" />
                                    <stop offset="40%" stop-color="#6366F1" />
                                    <stop offset="100%" stop-color="#D946EF" />
                                </linearGradient>
                            </defs>
                            <path d="M50 0 C50 0 5 35 5 65 C5 89.8 25.2 100 50 100 C74.8 100 95 89.8 95 65 C95 35 50 0 50 0 Z M 35 25 L 50 25 L 50 52 L 72 25 L 88 25 L 62 58 L 88 90 L 72 90 L 50 63 L 50 90 L 35 90 Z" fill="url(#inkoraGradient)"/>
                        </svg>
                    </div>
                    <h1 class="text-2xl font-bold tracking-tight text-white">Inkora</h1>
                </div>
                <p class="text-[10px] font-mono text-slate-400 uppercase tracking-widest pl-12">Imprentas Core</p>
            </div>

            <!-- Menú de Navegación -->
            <nav class="p-4 space-y-1 mt-4">
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-squares-four text-xl group-hover:text-brand-400 transition-colors"></i> Dashboard
                </a>
                <!-- Ítem Activo (Clientes) -->
                <a href="#" class="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-brand-600/20 to-transparent text-white font-semibold text-sm transition-colors relative group">
                    <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF]"></div>
                    <i class="ph-fill ph-users text-xl text-brand-400"></i> Clientes
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-package text-xl group-hover:text-brand-400 transition-colors"></i> Productos
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-file-text text-xl group-hover:text-brand-400 transition-colors"></i> Cotizaciones
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-credit-card text-xl group-hover:text-brand-400 transition-colors"></i> Cobranza
                </a>
            </nav>
        </div>

        <!-- Footer del Sidebar -->
        <div class="p-4">
            <div class="flex items-center justify-between px-4 py-3 bg-brand-900/50 rounded-none border border-white/5 hover:border-brand-500/50 transition-colors cursor-pointer group">
                <div class="flex items-center gap-3 overflow-hidden">
                    <div class="w-8 h-8 bg-brand-800 rounded-none flex items-center justify-center text-white font-bold text-sm group-hover:bg-brand-600 transition-colors shrink-0">A</div>
                    <div class="flex-1 overflow-hidden">
                        <p class="text-sm font-semibold text-white truncate">Admin Demo</p>
                        <p class="text-[10px] font-mono text-brand-400 uppercase">Pro Access</p>
                    </div>
                </div>
                <button class="text-slate-500 hover:text-rose-400 opacity-0 group-hover:opacity-100 transform translate-x-2 group-hover:translate-x-0 transition-all duration-300 px-1" title="Cerrar sesión">
                    <i class="ph-bold ph-power text-xl"></i>
                </button>
            </div>
        </div>
    </aside>

    <!-- ==========================================
         ÁREA PRINCIPAL (Workspace)
         ========================================== -->
    <main class="flex-1 flex flex-col h-screen overflow-hidden relative z-10">
        
        <!-- Header Superior -->
        <header class="glass-header border-b border-slate-200/50 px-8 py-4 flex items-center justify-between flex-none sticky top-0 z-20 pt-5">
            <div>
                <h2 class="text-xl font-bold text-slate-900 flex items-center gap-3">
                    Clientes
                    <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-mono tracking-widest uppercase">Directorio</span>
                </h2>
            </div>
            <div class="flex items-center gap-6">
                <div class="hidden lg:flex flex-col items-end">
                    <p id="sysClock" class="font-mono text-sm font-bold text-slate-800">00:00:00</p>
                    <p id="sysDate" class="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Cargando fecha...</p>
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

        <!-- Contenido principal -->
        <div class="flex-1 overflow-y-auto p-8 no-scrollbar">
            <div class="max-w-[1400px] mx-auto space-y-6 pb-12">

                <!-- Barra de Herramientas -->
                <div class="bg-white border border-slate-200 rounded-none p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div class="relative w-full sm:w-[450px] group">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="ph-bold ph-magnifying-glass text-slate-400 group-focus-within:text-brand-600 transition-colors"></i>
                        </div>
                        <input type="text" class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-mono placeholder:font-sans placeholder:text-slate-400" placeholder="Buscar por nombre o RUC/DNI...">
                        <div class="absolute inset-y-0 right-0 pr-2 flex items-center pointer-events-none">
                            <span class="text-[10px] font-mono text-slate-400 border border-slate-200 px-1.5 bg-white">CTRL+K</span>
                        </div>
                    </div>

                    <div class="flex items-center gap-3 w-full sm:w-auto">
                        <button class="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 px-4 py-2.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors">
                            <i class="ph-bold ph-funnel"></i> Filtrar
                        </button>
                        
                        <!-- CTA Nuevo Cliente (Activa el Modal) -->
                        <button id="btnOpenModal" class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-6 py-2.5 transition-all flex items-center gap-2 rounded-none hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 border border-transparent hover:border-brand-500">
                            <i class="ph-bold ph-user-plus"></i> Nuevo Cliente
                        </button>
                    </div>
                </div>

                <!-- Tabla de Clientes (Ledger Table) -->
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
                            
                            <!-- Cliente 1 -->
                            <tr class="hover:bg-brand-50/40 transition-colors group">
                                <td class="px-6 py-3">
                                    <p class="font-bold text-slate-900 text-[13px] group-hover:text-brand-700 transition-colors">ARCOR DE PERU S A</p>
                                </td>
                                <td class="px-6 py-3">
                                    <div class="flex items-center gap-2">
                                        <span class="font-mono text-[13px] text-slate-700 font-semibold">20191308868</span>
                                    </div>
                                </td>
                                <td class="px-6 py-3">
                                    <span class="text-slate-400 font-mono text-[13px]">--</span>
                                </td>
                                <td class="px-6 py-3">
                                    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono font-bold uppercase tracking-widest">
                                        Contado
                                    </span>
                                </td>
                                <td class="px-6 py-3 text-right">
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="p-1 text-slate-400 hover:text-brand-600 transition-colors" title="Editar"><i class="ph-bold ph-pencil-simple text-base"></i></button>
                                        <button class="p-1 text-slate-400 hover:text-rose-600 transition-colors" title="Eliminar"><i class="ph-bold ph-trash text-base"></i></button>
                                    </div>
                                </td>
                            </tr>

                            <!-- Cliente 2 -->
                            <tr class="hover:bg-brand-50/40 transition-colors group">
                                <td class="px-6 py-3">
                                    <p class="font-bold text-slate-900 text-[13px] group-hover:text-brand-700 transition-colors">Cliente Corporativo SAC</p>
                                </td>
                                <td class="px-6 py-3">
                                    <div class="flex items-center gap-2">
                                        <span class="font-mono text-[13px] text-slate-700 font-semibold">20100100100</span>
                                    </div>
                                </td>
                                <td class="px-6 py-3">
                                    <span class="text-slate-600 text-[13px]">compras@corporativo.pe</span>
                                </td>
                                <td class="px-6 py-3">
                                    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-mono font-bold uppercase tracking-widest">
                                        Crédito 30
                                    </span>
                                </td>
                                <td class="px-6 py-3 text-right">
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="p-1 text-slate-400 hover:text-brand-600 transition-colors" title="Editar"><i class="ph-bold ph-pencil-simple text-base"></i></button>
                                        <button class="p-1 text-slate-400 hover:text-rose-600 transition-colors" title="Eliminar"><i class="ph-bold ph-trash text-base"></i></button>
                                    </div>
                                </td>
                            </tr>
                            
                        </tbody>
                    </table>
                    
                    <!-- Paginación con Alta Densidad -->
                    <div class="p-4 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <p class="text-xs font-mono text-slate-500">Mostrando <span class="font-bold text-slate-900">1-2</span> de <span class="font-bold text-slate-900">7</span> clientes</p>
                        </div>
                        <div class="flex items-center gap-1">
                            <button class="px-3 py-1.5 bg-white border border-slate-200 text-slate-400 hover:text-slate-900 transition-colors" disabled><i class="ph-bold ph-caret-left"></i></button>
                            <button class="px-3 py-1.5 bg-brand-600 border border-brand-600 text-white font-mono text-xs font-bold">1</button>
                            <button class="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 font-mono text-xs font-bold transition-colors">2</button>
                            <button class="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"><i class="ph-bold ph-caret-right"></i></button>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </main>

    <!-- ==========================================
         MODAL DE NUEVO CLIENTE (Estilo Industrial Elite)
         ========================================== -->
    <div id="clientModal" class="fixed inset-0 bg-brand-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 transition-opacity hidden">
        
        <!-- Contenedor del Modal (Brutalismo Funcional) -->
        <div class="bg-white border border-slate-200 rounded-none w-full max-w-3xl shadow-[8px_8px_0px_0px_rgba(15,14,41,0.15)] flex flex-col transform transition-all max-h-[90vh]">
            
            <!-- Header del Modal -->
            <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50 flex-none">
                <h3 class="font-bold text-slate-900 font-mono uppercase tracking-widest text-sm flex items-center gap-2">
                    <i class="ph-bold ph-user-plus text-brand-600 text-lg"></i>
                    Nuevo Cliente
                </h3>
                <button id="btnCloseModalX" class="text-slate-400 hover:text-rose-500 transition-colors p-1 outline-none">
                    <i class="ph-bold ph-x text-xl"></i>
                </button>
            </div>
            
            <!-- Cuerpo del Modal (Formulario Scrollable) -->
            <div class="p-6 space-y-6 overflow-y-auto no-scrollbar">
                
                <!-- Fila 1: Documento (Grid Asimétrico) -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
                    
                    <!-- Tipo Documento (Custom Select) -->
                    <div class="space-y-1.5 col-span-1">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Tipo doc.</label>
                        <div class="custom-select relative" data-name="tipo_doc">
                            <input type="hidden" name="tipo_doc" value="RUC">
                            <button type="button" class="select-trigger w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm font-semibold flex justify-between items-center focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all">
                                <span class="select-text">RUC</span>
                                <i class="ph-bold ph-caret-down text-slate-400 pointer-events-none transition-transform duration-200"></i>
                            </button>
                            <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] rounded-none hidden flex-col max-h-48 overflow-y-auto">
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors" data-value="RUC">RUC</li>
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors" data-value="DNI">DNI</li>
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors" data-value="CE">CE</li>
                            </ul>
                        </div>
                    </div>

                    <!-- Número de Documento + Botón de Consulta SUNAT/RENIEC -->
                    <div class="space-y-1.5 col-span-2 group">
                        <div class="flex justify-between items-end">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Número documento</label>
                            <!-- Detalle Élite: Consulta rápida a API -->
                            <button type="button" class="text-[9px] font-bold font-mono text-brand-600 hover:text-brand-800 uppercase tracking-wider outline-none flex items-center gap-1">
                                <i class="ph-bold ph-magnifying-glass"></i> Consultar
                            </button>
                        </div>
                        <input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm font-semibold focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors placeholder:font-sans placeholder:font-normal placeholder:text-slate-400" placeholder="Ej. 20100200300">
                    </div>
                </div>

                <!-- Fila 2: Nombre o Razón Social -->
                <div class="space-y-1.5 group">
                    <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Razón social / nombre</label>
                    <input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 text-sm font-medium focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors placeholder:text-slate-400">
                </div>

                <!-- Fila 3: Dirección -->
                <div class="space-y-1.5 group">
                    <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Dirección fiscal / Entrega</label>
                    <input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 text-sm focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors placeholder:text-slate-400">
                </div>

                <!-- Fila 4: Contacto (Email y Teléfono) -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div class="space-y-1.5 group">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Email</label>
                        <input type="email" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors placeholder:font-sans placeholder:text-slate-400" placeholder="correo@empresa.com">
                    </div>
                    <div class="space-y-1.5 group">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Teléfono</label>
                        <input type="tel" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors">
                    </div>
                </div>

                <!-- Fila 5: WhatsApp y Condición de Pago -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div class="space-y-1.5 group">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">WhatsApp</label>
                        <input type="tel" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors">
                    </div>
                    
                    <!-- Condición de Pago (Custom Select 2) -->
                    <div class="space-y-1.5">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Condición de pago</label>
                        <div class="custom-select relative" data-name="condicion_pago">
                            <input type="hidden" name="condicion_pago" value="contado">
                            <button type="button" class="select-trigger w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm font-semibold flex justify-between items-center focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all">
                                <span class="select-text">Contado</span>
                                <i class="ph-bold ph-caret-down text-slate-400 pointer-events-none transition-transform duration-200"></i>
                            </button>
                            <ul class="select-menu absolute bottom-full mb-1 z-50 w-full bg-white border border-slate-200 shadow-[4px_-4px_0px_0px_rgba(15,14,41,0.1)] rounded-none hidden flex-col max-h-48 overflow-y-auto">
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors" data-value="contado">Contado</li>
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors" data-value="credito_15">Crédito 15 días</li>
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors" data-value="credito_30">Crédito 30 días</li>
                            </ul>
                        </div>
                    </div>
                </div>

            </div>

            <!-- Footer del Modal -->
            <div class="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-3 flex-none">
                <button id="btnCancelModal" class="px-6 py-2.5 text-xs font-bold font-mono uppercase tracking-widest text-slate-600 hover:text-slate-900 hover:bg-slate-200 transition-colors border border-transparent outline-none">
                    Cancelar
                </button>
                <button class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-2.5 transition-all flex items-center gap-2 rounded-none hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 border border-transparent hover:border-brand-500 outline-none">
                    <i class="ph-bold ph-floppy-disk text-lg"></i> Guardar
                </button>
            </div>
            
        </div>
    </div>

    <!-- Scripts (Reloj, Modal y Custom Selects) -->
    <script>
        // --- 1. LÓGICA DEL RELOJ ---
        function updateClock() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            document.getElementById('sysClock').textContent = `${hours}:${minutes}:${seconds}`;
            
            const options = { day: 'numeric', month: 'short', year: 'numeric' };
            const dateStr = now.toLocaleDateString('es-PE', options).toUpperCase();
            document.getElementById('sysDate').textContent = `${dateStr} · LIMA (PET)`;
        }
        setInterval(updateClock, 1000);
        updateClock();

        // --- 2. LÓGICA DEL MODAL ---
        const modal = document.getElementById('clientModal');
        const btnOpenModal = document.getElementById('btnOpenModal');
        const btnCloseModalX = document.getElementById('btnCloseModalX');
        const btnCancelModal = document.getElementById('btnCancelModal');

        btnOpenModal.addEventListener('click', () => modal.classList.remove('hidden'));
        
        const closeModal = () => modal.classList.add('hidden');
        btnCloseModalX.addEventListener('click', closeModal);
        btnCancelModal.addEventListener('click', closeModal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        // --- 3. LÓGICA GENÉRICA PARA MÚLTIPLES CUSTOM SELECTS ---
        const customSelects = document.querySelectorAll('.custom-select');

        function closeAllSelects(except = null) {
            customSelects.forEach(select => {
                if (select !== except) {
                    const menu = select.querySelector('.select-menu');
                    const icon = select.querySelector('.ph-caret-down');
                    const trigger = select.querySelector('.select-trigger');
                    const label = select.parentElement.querySelector('label');
                    
                    menu.classList.add('hidden');
                    menu.classList.remove('flex');
                    if(icon) icon.classList.remove('rotate-180');
                    trigger.classList.remove('border-brand-500', 'ring-1', 'ring-brand-500', 'bg-white');
                    if(label) label.classList.remove('text-brand-600');
                }
            });
        }

        customSelects.forEach(select => {
            const trigger = select.querySelector('.select-trigger');
            const menu = select.querySelector('.select-menu');
            const icon = select.querySelector('.ph-caret-down');
            const text = select.querySelector('.select-text');
            const hiddenInput = select.querySelector('input[type="hidden"]');
            const options = select.querySelectorAll('li');
            const label = select.parentElement.querySelector('label');

            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                const isExpanded = !menu.classList.contains('hidden');
                
                closeAllSelects(select); // Cierra otros selects antes de abrir este

                if (isExpanded) {
                    closeAllSelects();
                } else {
                    menu.classList.remove('hidden');
                    menu.classList.add('flex');
                    icon.classList.add('rotate-180');
                    trigger.classList.add('border-brand-500', 'ring-1', 'ring-brand-500', 'bg-white');
                    if(label) label.classList.add('text-brand-600');
                }
            });

            options.forEach(option => {
                option.addEventListener('click', (e) => {
                    e.stopPropagation();
                    text.textContent = option.textContent.trim();
                    hiddenInput.value = option.getAttribute('data-value');
                    closeAllSelects();
                });
            });
        });

        // Cerrar selects al hacer click fuera
        document.addEventListener('click', () => closeAllSelects());
    </script>
</body>
</html>

Estilo de Productos
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inkora - Catálogo de Productos</title>
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
        .tech-grid {
            background-image: linear-gradient(rgba(99, 102, 241, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(99, 102, 241, 0.04) 1px, transparent 1px);
            background-size: 32px 32px;
        }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .glass-header { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
        
        /* Ocultar las flechas de los inputs numéricos para un look más limpio */
        input[type=number]::-webkit-inner-spin-button, 
        input[type=number]::-webkit-outer-spin-button { 
            -webkit-appearance: none; 
            margin: 0; 
        }
    </style>
</head>
<body class="h-screen w-full flex overflow-hidden selection:bg-brand-500 selection:text-white tech-grid relative">

    <!-- Línea de tensión superior -->
    <div class="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#3B82F6] via-[#6366F1] to-[#D946EF] z-50 animate-gradient-x"></div>

    <!-- ==========================================
         SIDEBAR (Navegación Industrial)
         ========================================== -->
    <aside class="w-[280px] bg-brand-950 flex-none flex flex-col justify-between shadow-2xl relative z-30 hidden md:flex border-r border-white/5">
        
        <div class="flex-1 overflow-y-auto no-scrollbar pt-2">
            <!-- Logo -->
            <div class="p-6">
                <div class="flex items-center gap-3 mb-2">
                    <div class="w-9 h-9 flex items-center justify-center filter drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]">
                        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
                            <defs>
                                <linearGradient id="inkoraGradient" x1="0%" y1="100%" x2="100%" y2="0%">
                                    <stop offset="0%" stop-color="#3B82F6" />
                                    <stop offset="40%" stop-color="#6366F1" />
                                    <stop offset="100%" stop-color="#D946EF" />
                                </linearGradient>
                            </defs>
                            <path d="M50 0 C50 0 5 35 5 65 C5 89.8 25.2 100 50 100 C74.8 100 95 89.8 95 65 C95 35 50 0 50 0 Z M 35 25 L 50 25 L 50 52 L 72 25 L 88 25 L 62 58 L 88 90 L 72 90 L 50 63 L 50 90 L 35 90 Z" fill="url(#inkoraGradient)"/>
                        </svg>
                    </div>
                    <h1 class="text-2xl font-bold tracking-tight text-white">Inkora</h1>
                </div>
                <p class="text-[10px] font-mono text-slate-400 uppercase tracking-widest pl-12">Imprentas Core</p>
            </div>

            <!-- Menú de Navegación -->
            <nav class="p-4 space-y-1 mt-4">
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-squares-four text-xl group-hover:text-brand-400 transition-colors"></i> Dashboard
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-users text-xl group-hover:text-brand-400 transition-colors"></i> Clientes
                </a>
                <!-- Ítem Activo (Productos) -->
                <a href="#" class="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-brand-600/20 to-transparent text-white font-semibold text-sm transition-colors relative group">
                    <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF]"></div>
                    <i class="ph-fill ph-package text-xl text-brand-400"></i> Productos
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-file-text text-xl group-hover:text-brand-400 transition-colors"></i> Cotizaciones
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-credit-card text-xl group-hover:text-brand-400 transition-colors"></i> Cobranza
                </a>
            </nav>
        </div>

        <!-- Footer del Sidebar -->
        <div class="p-4">
            <div class="flex items-center justify-between px-4 py-3 bg-brand-900/50 rounded-none border border-white/5 hover:border-brand-500/50 transition-colors cursor-pointer group">
                <div class="flex items-center gap-3 overflow-hidden">
                    <div class="w-8 h-8 bg-brand-800 rounded-none flex items-center justify-center text-white font-bold text-sm group-hover:bg-brand-600 transition-colors shrink-0">A</div>
                    <div class="flex-1 overflow-hidden">
                        <p class="text-sm font-semibold text-white truncate">Admin Demo</p>
                        <p class="text-[10px] font-mono text-brand-400 uppercase">Pro Access</p>
                    </div>
                </div>
                <button class="text-slate-500 hover:text-rose-400 opacity-0 group-hover:opacity-100 transform translate-x-2 group-hover:translate-x-0 transition-all duration-300 px-1" title="Cerrar sesión">
                    <i class="ph-bold ph-power text-xl"></i>
                </button>
            </div>
        </div>
    </aside>

    <!-- ==========================================
         ÁREA PRINCIPAL (Workspace)
         ========================================== -->
    <main class="flex-1 flex flex-col h-screen overflow-hidden relative z-10">
        
        <!-- Header Superior -->
        <header class="glass-header border-b border-slate-200/50 px-8 py-4 flex items-center justify-between flex-none sticky top-0 z-20 pt-5">
            <div>
                <h2 class="text-xl font-bold text-slate-900 flex items-center gap-3">
                    Productos y servicios
                    <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-mono tracking-widest uppercase">Catálogo</span>
                </h2>
            </div>
            <div class="flex items-center gap-6">
                <div class="hidden lg:flex flex-col items-end">
                    <p id="sysClock" class="font-mono text-sm font-bold text-slate-800">00:00:00</p>
                    <p id="sysDate" class="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Cargando fecha...</p>
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

        <!-- Contenido principal -->
        <div class="flex-1 overflow-y-auto p-8 no-scrollbar">
            <div class="max-w-[1400px] mx-auto space-y-6 pb-12">

                <!-- Barra de Herramientas -->
                <div class="bg-white border border-slate-200 rounded-none p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div class="relative w-full sm:w-[450px] group">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="ph-bold ph-magnifying-glass text-slate-400 group-focus-within:text-brand-600 transition-colors"></i>
                        </div>
                        <input type="text" class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-mono placeholder:font-sans placeholder:text-slate-400" placeholder="Buscar por nombre o código SKU...">
                        <div class="absolute inset-y-0 right-0 pr-2 flex items-center pointer-events-none">
                            <span class="text-[10px] font-mono text-slate-400 border border-slate-200 px-1.5 bg-white">CTRL+K</span>
                        </div>
                    </div>

                    <div class="flex items-center gap-3 w-full sm:w-auto">
                        <button class="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 px-4 py-2.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors">
                            <i class="ph-bold ph-funnel"></i> Categorías
                        </button>
                        
                        <!-- CTA Nuevo Producto (Activa el Modal) -->
                        <button id="btnOpenModal" class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-6 py-2.5 transition-all flex items-center gap-2 rounded-none hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 border border-transparent hover:border-brand-500">
                            <i class="ph-bold ph-plus"></i> Nuevo Producto
                        </button>
                    </div>
                </div>

                <!-- Tabla de Productos (Resumida para este ejemplo) -->
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
                                    <div class="flex items-center gap-3">
                                        <div class="w-2 h-2 rounded-full bg-brand-500 shrink-0"></div>
                                        <p class="font-bold text-slate-900 text-[13px] group-hover:text-brand-700 transition-colors">Diseño Gráfico</p>
                                    </div>
                                </td>
                                <td class="px-6 py-2.5">
                                    <span class="inline-block px-2 py-0.5 bg-slate-50 border border-slate-200 text-slate-600 font-mono text-[11px] font-semibold tracking-wider">DIS-GFX</span>
                                </td>
                                <td class="px-6 py-2.5">
                                    <span class="inline-block px-1.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-mono font-bold uppercase tracking-widest">ZZ</span>
                                </td>
                                <td class="px-6 py-2.5 text-right">
                                    <div class="flex justify-end items-baseline gap-1">
                                        <span class="text-[10px] font-bold text-slate-400">S/</span>
                                        <span class="font-mono text-[13px] font-bold text-slate-900">50.00</span>
                                    </div>
                                </td>
                                <td class="px-6 py-2.5 text-right">
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="p-1 text-slate-400 hover:text-brand-600 transition-colors"><i class="ph-bold ph-pencil-simple text-base"></i></button>
                                        <button class="p-1 text-slate-400 hover:text-rose-600 transition-colors"><i class="ph-bold ph-trash text-base"></i></button>
                                    </div>
                                </td>
                            </tr>
                            <tr class="hover:bg-brand-50/40 transition-colors group">
                                <td class="px-6 py-2.5">
                                    <div class="flex items-center gap-3">
                                        <div class="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></div>
                                        <p class="font-bold text-slate-900 text-[13px] group-hover:text-brand-700 transition-colors">Impresión A3 Full Color</p>
                                    </div>
                                </td>
                                <td class="px-6 py-2.5">
                                    <span class="inline-block px-2 py-0.5 bg-slate-50 border border-slate-200 text-slate-600 font-mono text-[11px] font-semibold tracking-wider">IMP-A3-FC</span>
                                </td>
                                <td class="px-6 py-2.5">
                                    <span class="inline-block px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono font-bold uppercase tracking-widest">NIU</span>
                                </td>
                                <td class="px-6 py-2.5 text-right">
                                    <div class="flex justify-end items-baseline gap-1">
                                        <span class="text-[10px] font-bold text-slate-400">S/</span>
                                        <span class="font-mono text-[13px] font-bold text-slate-900">9.50</span>
                                    </div>
                                </td>
                                <td class="px-6 py-2.5 text-right">
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="p-1 text-slate-400 hover:text-brand-600 transition-colors"><i class="ph-bold ph-pencil-simple text-base"></i></button>
                                        <button class="p-1 text-slate-400 hover:text-rose-600 transition-colors"><i class="ph-bold ph-trash text-base"></i></button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <!-- Paginación -->
                    <div class="p-4 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between">
                        <p class="text-xs font-mono text-slate-500">Mostrando <span class="font-bold text-slate-900">1-2</span> de <span class="font-bold text-slate-900">124</span> productos</p>
                        <div class="flex items-center gap-1">
                            <button class="px-3 py-1.5 bg-white border border-slate-200 text-slate-400 hover:text-slate-900 transition-colors" disabled><i class="ph-bold ph-caret-left"></i></button>
                            <button class="px-3 py-1.5 bg-brand-600 border border-brand-600 text-white font-mono text-xs font-bold">1</button>
                            <button class="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 font-mono text-xs font-bold transition-colors">2</button>
                            <button class="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"><i class="ph-bold ph-caret-right"></i></button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- ==========================================
         MODAL DE NUEVO PRODUCTO (Estilo Industrial Elite)
         ========================================== -->
    <div id="productModal" class="fixed inset-0 bg-brand-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 transition-opacity hidden">
        
        <!-- Contenedor del Modal (Brutalismo Funcional) -->
        <div class="bg-white border border-slate-200 rounded-none w-full max-w-2xl shadow-[8px_8px_0px_0px_rgba(15,14,41,0.15)] flex flex-col transform transition-all">
            
            <!-- Header del Modal -->
            <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50">
                <h3 class="font-bold text-slate-900 font-mono uppercase tracking-widest text-sm flex items-center gap-2">
                    <i class="ph-bold ph-package text-brand-600 text-lg"></i>
                    Registrar Nuevo Producto
                </h3>
                <button id="btnCloseModalX" class="text-slate-400 hover:text-rose-500 transition-colors p-1 outline-none">
                    <i class="ph-bold ph-x text-xl"></i>
                </button>
            </div>
            
            <!-- Cuerpo del Modal (Formulario) -->
            <div class="p-6 space-y-6">
                
                <!-- Fila 1: Nombre -->
                <div class="space-y-1.5 group">
                    <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Nombre del Producto / Servicio</label>
                    <input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 text-sm font-medium focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors placeholder:font-normal placeholder:text-slate-400" placeholder="Ej. Impresión A4 Full Color">
                </div>

                <!-- Fila 2: Descripción -->
                <div class="space-y-1.5 group">
                    <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Descripción Interna (Opcional)</label>
                    <textarea rows="3" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 text-sm focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors placeholder:text-slate-400 resize-none" placeholder="Detalles de papel, gramaje, acabado..."></textarea>
                </div>

                <!-- Fila 3: Grid de Datos Críticos -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
                    
                    <!-- Precio Unitario -->
                    <div class="space-y-1.5 group">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Precio Unitario</label>
                        <div class="relative">
                            <span class="absolute left-4 top-1/2 -translate-y-1/2 font-bold text-slate-400 select-none">S/</span>
                            <input type="number" step="0.01" class="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-right text-base font-bold focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors" placeholder="0.00">
                        </div>
                    </div>

                    <!-- Unidad SUNAT (CUSTOM SELECT ELITE) -->
                    <div class="space-y-1.5">
                        <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest" id="unidadLabel">Unidad (U.M.)</label>
                        
                        <!-- Contenedor del Dropdown Custom -->
                        <div class="relative" id="customUnidadSelect">
                            <!-- Input oculto para guardar el valor real para el backend -->
                            <input type="hidden" name="unidad_sunat" id="unidadValue" value="NIU">
                            
                            <!-- Botón disparador (El que ve el usuario) -->
                            <button type="button" id="unidadTrigger" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm font-semibold flex justify-between items-center hover:bg-white focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all">
                                <span id="unidadText">NIU - Unidad</span>
                                <i class="ph-bold ph-caret-down text-slate-400 pointer-events-none transition-transform duration-200" id="unidadIcon"></i>
                            </button>

                            <!-- Lista Flotante de Opciones -->
                            <ul id="unidadMenu" class="absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] rounded-none hidden flex-col max-h-48 overflow-y-auto">
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors flex items-center gap-2" data-value="NIU">
                                    <span class="font-bold w-8 text-slate-400">NIU</span> Unidad
                                </li>
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors flex items-center gap-2" data-value="ZZ">
                                    <span class="font-bold w-8 text-slate-400">ZZ</span> Servicio
                                </li>
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors flex items-center gap-2" data-value="MIL">
                                    <span class="font-bold w-8 text-slate-400">MIL</span> Millar
                                </li>
                                <li class="px-4 py-3 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 transition-colors flex items-center gap-2" data-value="MTR">
                                    <span class="font-bold w-8 text-slate-400">MTR</span> Metro
                                </li>
                            </ul>
                        </div>
                    </div>

                    <!-- Código Interno / SKU -->
                    <div class="space-y-1.5 group">
                        <div class="flex justify-between items-end">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Código SKU</label>
                            <button type="button" class="text-[9px] font-bold font-mono text-brand-600 hover:text-brand-800 uppercase tracking-wider outline-none"><i class="ph-bold ph-arrows-clockwise"></i> Generar</button>
                        </div>
                        <input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm font-semibold focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors uppercase placeholder:normal-case placeholder:font-sans placeholder:font-normal placeholder:text-slate-400" placeholder="Ej. IMP-A4-01">
                    </div>

                </div>
            </div>

            <!-- Footer del Modal -->
            <div class="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-3">
                <button id="btnCancelModal" class="px-6 py-2.5 text-xs font-bold font-mono uppercase tracking-widest text-slate-600 hover:text-slate-900 hover:bg-slate-200 transition-colors border border-transparent outline-none">
                    Cancelar
                </button>
                <button class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-2.5 transition-all flex items-center gap-2 rounded-none hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 border border-transparent hover:border-brand-500 outline-none">
                    <i class="ph-bold ph-floppy-disk text-lg"></i> Guardar
                </button>
            </div>
            
        </div>
    </div>

    <!-- Scripts (Reloj, Modal y Custom Select) -->
    <script>
        // --- 1. LÓGICA DEL RELOJ ---
        function updateClock() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            document.getElementById('sysClock').textContent = `${hours}:${minutes}:${seconds}`;
            
            const options = { day: 'numeric', month: 'short', year: 'numeric' };
            const dateStr = now.toLocaleDateString('es-PE', options).toUpperCase();
            document.getElementById('sysDate').textContent = `${dateStr} · LIMA (PET)`;
        }
        setInterval(updateClock, 1000);
        updateClock();

        // --- 2. LÓGICA DEL MODAL ---
        const modal = document.getElementById('productModal');
        const btnOpenModal = document.getElementById('btnOpenModal');
        const btnCloseModalX = document.getElementById('btnCloseModalX');
        const btnCancelModal = document.getElementById('btnCancelModal');

        btnOpenModal.addEventListener('click', () => modal.classList.remove('hidden'));
        
        const closeModal = () => modal.classList.add('hidden');
        btnCloseModalX.addEventListener('click', closeModal);
        btnCancelModal.addEventListener('click', closeModal);

        // --- 3. LÓGICA DEL CUSTOM SELECT (UNIDAD SUNAT) ---
        const selectContainer = document.getElementById('customUnidadSelect');
        const selectTrigger = document.getElementById('unidadTrigger');
        const selectMenu = document.getElementById('unidadMenu');
        const selectIcon = document.getElementById('unidadIcon');
        const selectText = document.getElementById('unidadText');
        const hiddenValue = document.getElementById('unidadValue');
        const selectOptions = selectMenu.querySelectorAll('li');
        const label = document.getElementById('unidadLabel');

        // Abrir/Cerrar el menú al hacer clic en el botón
        selectTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isExpanded = !selectMenu.classList.contains('hidden');
            
            if (isExpanded) {
                closeSelect();
            } else {
                selectMenu.classList.remove('hidden');
                selectMenu.classList.add('flex');
                selectIcon.classList.add('rotate-180');
                selectTrigger.classList.add('border-brand-500', 'ring-1', 'ring-brand-500', 'bg-white');
                label.classList.add('text-brand-600');
            }
        });

        // Función para cerrar el menú
        const closeSelect = () => {
            selectMenu.classList.add('hidden');
            selectMenu.classList.remove('flex');
            selectIcon.classList.remove('rotate-180');
            selectTrigger.classList.remove('border-brand-500', 'ring-1', 'ring-brand-500', 'bg-white');
            label.classList.remove('text-brand-600');
        };

        // Seleccionar una opción
        selectOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                // Extraer el texto visible completo para mostrar en el botón
                selectText.textContent = option.textContent.trim().replace(/\s+/g, ' ');
                // Guardar el valor real en el input oculto (para el formulario)
                hiddenValue.value = option.getAttribute('data-value');
                closeSelect();
            });
        });

        // Cerrar al hacer clic fuera del select o del modal
        document.addEventListener('click', (e) => {
            // Cierra el select si se hace click fuera
            if (!selectContainer.contains(e.target)) {
                closeSelect();
            }
            // Cierra el modal si se hace clic en el fondo oscurecido
            if (e.target === modal) {
                closeModal();
            }
        });
    </script>
</body>
</html>

Estilo de Cotizaciones

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inkora - Cotizaciones</title>
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
        .tech-grid {
            background-image: linear-gradient(rgba(99, 102, 241, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(99, 102, 241, 0.04) 1px, transparent 1px);
            background-size: 32px 32px;
        }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .glass-header { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
        
        input[type=number]::-webkit-inner-spin-button, 
        input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
        
        /* Efecto de Celda Activa para la tabla de items */
        .spreadsheet-cell:focus-within {
            background-color: #ffffff;
            box-shadow: inset 0 0 0 2px #4F46E5;
            z-index: 10;
            position: relative;
        }
    </style>
</head>
<body class="h-screen w-full flex overflow-hidden selection:bg-brand-500 selection:text-white tech-grid relative">

    <div class="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#3B82F6] via-[#6366F1] to-[#D946EF] z-50 animate-gradient-x"></div>

    <!-- ==========================================
         SIDEBAR
         ========================================== -->
    <aside class="w-[280px] bg-brand-950 flex-none flex flex-col justify-between shadow-2xl relative z-30 hidden md:flex border-r border-white/5">
        <div class="flex-1 overflow-y-auto no-scrollbar pt-2">
            <div class="p-6">
                <div class="flex items-center gap-3 mb-2">
                    <div class="w-9 h-9 flex items-center justify-center filter drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]">
                        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
                            <defs>
                                <linearGradient id="inkoraGradient" x1="0%" y1="100%" x2="100%" y2="0%">
                                    <stop offset="0%" stop-color="#3B82F6" />
                                    <stop offset="40%" stop-color="#6366F1" />
                                    <stop offset="100%" stop-color="#D946EF" />
                                </linearGradient>
                            </defs>
                            <path d="M50 0 C50 0 5 35 5 65 C5 89.8 25.2 100 50 100 C74.8 100 95 89.8 95 65 C95 35 50 0 50 0 Z M 35 25 L 50 25 L 50 52 L 72 25 L 88 25 L 62 58 L 88 90 L 72 90 L 50 63 L 50 90 L 35 90 Z" fill="url(#inkoraGradient)"/>
                        </svg>
                    </div>
                    <h1 class="text-2xl font-bold tracking-tight text-white">Inkora</h1>
                </div>
                <p class="text-[10px] font-mono text-slate-400 uppercase tracking-widest pl-12">Imprentas Core</p>
            </div>

            <nav class="p-4 space-y-1 mt-4">
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-squares-four text-xl group-hover:text-brand-400 transition-colors"></i> Dashboard
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-users text-xl group-hover:text-brand-400 transition-colors"></i> Clientes
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-package text-xl group-hover:text-brand-400 transition-colors"></i> Productos
                </a>
                <!-- Ítem Activo -->
                <a href="#" class="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-brand-600/20 to-transparent text-white font-semibold text-sm transition-colors relative group">
                    <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF]"></div>
                    <i class="ph-fill ph-file-text text-xl text-brand-400"></i> Cotizaciones
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-credit-card text-xl group-hover:text-brand-400 transition-colors"></i> Cobranza
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
                <button class="text-slate-500 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-all px-1"><i class="ph-bold ph-power text-xl"></i></button>
            </div>
        </div>
    </aside>

    <!-- ==========================================
         WORKSPACE
         ========================================== -->
    <main class="flex-1 flex flex-col h-screen overflow-hidden relative z-10">
        
        <header class="glass-header border-b border-slate-200/50 px-8 py-4 flex items-center justify-between flex-none sticky top-0 z-20 pt-5">
            <div>
                <h2 class="text-xl font-bold text-slate-900 flex items-center gap-3">
                    Cotizaciones
                    <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-mono tracking-widest uppercase">Motor Comercial</span>
                </h2>
            </div>
            <div class="flex items-center gap-6">
                <div class="hidden lg:flex flex-col items-end">
                    <p id="sysClock" class="font-mono text-sm font-bold text-slate-800">00:00:00</p>
                    <p id="sysDate" class="text-[10px] font-mono text-slate-500 uppercase tracking-widest">LIMA (PET)</p>
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

        <div class="flex-1 overflow-y-auto p-8 no-scrollbar">
            <div class="max-w-[1400px] mx-auto space-y-6 pb-12">

                <!-- Toolbar -->
                <div class="bg-white border border-slate-200 p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div class="relative w-full sm:w-[450px] group">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="ph-bold ph-magnifying-glass text-slate-400 group-focus-within:text-brand-600 transition-colors"></i>
                        </div>
                        <input type="text" class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-mono placeholder:font-sans placeholder:text-slate-400" placeholder="Buscar por cliente o N° de orden...">
                    </div>

                    <div class="flex items-center gap-3 w-full sm:w-auto">
                        <button class="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 px-4 py-2.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors">
                            <i class="ph-bold ph-funnel"></i> Filtrar
                        </button>
                        <button id="btnOpenModal" class="relative group bg-brand-600 text-white font-mono text-xs uppercase tracking-widest px-6 py-2.5 flex items-center gap-2 hover:bg-brand-700 transition-all hover:shadow-[4px_4px_0px_0px_rgba(49,46,129,0.5)] hover:-translate-y-0.5 hover:-translate-x-0.5">
                            <i class="ph-bold ph-plus"></i> Nueva Cotización
                        </button>
                    </div>
                </div>

                <!-- Listado de Cotizaciones -->
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
                                <td class="px-6 py-3">
                                    <div class="flex items-center gap-2">
                                        <i class="ph-fill ph-file-text text-slate-400"></i>
                                        <span class="font-mono text-[13px] font-bold text-brand-600">COT-2026-0001</span>
                                    </div>
                                </td>
                                <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px]">Cliente Corporativo SAC</p></td>
                                <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">14/04/2026</span></td>
                                <td class="px-6 py-3 text-right"><span class="font-mono text-[13px] font-bold text-slate-900">S/ 1,250.00</span></td>
                                <td class="px-6 py-3 text-center">
                                    <span class="inline-flex px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-mono font-bold uppercase tracking-widest">Pendiente</span>
                                </td>
                                <td class="px-6 py-3 text-right">
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="p-1 text-slate-400 hover:text-brand-600 transition-colors" title="Ver/Editar"><i class="ph-bold ph-eye text-base"></i></button>
                                        <button class="p-1 text-slate-400 hover:text-emerald-600 transition-colors" title="Aprobar (Convertir a Factura)"><i class="ph-bold ph-check-circle text-base"></i></button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

            </div>
        </div>
    </main>

    <!-- ==========================================
         MODAL: NUEVA COTIZACIÓN (Wide Modal / Spreadsheet UI)
         ========================================== -->
    <div id="quoteModal" class="fixed inset-0 bg-brand-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 transition-opacity hidden">
        
        <div class="bg-white border border-slate-200 rounded-none w-full max-w-5xl shadow-[8px_8px_0px_0px_rgba(15,14,41,0.15)] flex flex-col transform transition-all max-h-[95vh]">
            
            <!-- Header Modal -->
            <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50 flex-none">
                <div class="flex items-center gap-4">
                    <h3 class="font-bold text-slate-900 font-mono uppercase tracking-widest text-sm flex items-center gap-2">
                        <i class="ph-bold ph-file-plus text-brand-600 text-lg"></i> Nueva Cotización
                    </h3>
                    <span class="px-2 py-0.5 bg-brand-100 text-brand-700 font-mono text-[10px] font-bold tracking-widest">Borrador</span>
                </div>
                <button id="btnCloseModalX" class="text-slate-400 hover:text-rose-500 transition-colors p-1 outline-none">
                    <i class="ph-bold ph-x text-xl"></i>
                </button>
            </div>
            
            <!-- Body Modal (Scrollable) -->
            <div class="flex-1 overflow-y-auto no-scrollbar flex flex-col">
                
                <!-- ZONA 1: METADATOS (Cabecera del documento) -->
                <div class="p-6 bg-white border-b border-slate-200 space-y-5">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        
                        <!-- Cliente -->
                        <div class="space-y-1.5 md:col-span-2">
                            <div class="flex justify-between items-end">
                                <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Cliente</label>
                                <button class="text-[9px] font-bold font-mono text-brand-600 hover:text-brand-800 uppercase tracking-wider"><i class="ph-bold ph-plus"></i> Nuevo Cliente</button>
                            </div>
                            <div class="custom-select relative">
                                <input type="hidden" value="">
                                <button type="button" class="select-trigger w-full px-4 py-2.5 bg-slate-50 border border-slate-300 text-slate-900 font-mono text-sm font-semibold flex justify-between items-center focus:border-brand-500 focus:bg-white transition-all">
                                    <span class="select-text text-slate-400">Buscar o seleccionar cliente...</span>
                                    <i class="ph-bold ph-caret-down text-slate-400"></i>
                                </button>
                            </div>
                        </div>

                        <!-- Moneda -->
                        <div class="space-y-1.5">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Moneda</label>
                            <div class="custom-select relative">
                                <input type="hidden" value="PEN">
                                <button type="button" class="select-trigger w-full px-4 py-2.5 bg-slate-50 border border-slate-300 text-slate-900 font-mono text-sm font-semibold flex justify-between items-center focus:border-brand-500 focus:bg-white transition-all">
                                    <span class="select-text">PEN (S/) Soles</span>
                                    <i class="ph-bold ph-caret-down text-slate-400"></i>
                                </button>
                                <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col">
                                    <li class="px-4 py-2.5 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500">PEN (S/) Soles</li>
                                    <li class="px-4 py-2.5 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500">USD ($) Dólares</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ZONA 2: SPREADSHEET UI (Detalle de Items) -->
                <div class="flex-1 bg-slate-50 p-6">
                    <div class="mb-4 flex justify-between items-center">
                        <h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Líneas de Detalle</h4>
                    </div>

                    <!-- Tabla estilo Excel -->
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
                            <tbody id="itemsContainer" class="divide-y divide-slate-200">
                                
                                <!-- Fila 1 (Celdas editables) -->
                                <tr class="group bg-white hover:bg-slate-50 transition-colors">
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0 relative">
                                        <select class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm font-semibold text-slate-900 focus:ring-0 cursor-pointer appearance-none outline-none">
                                            <option>Desde catálogo...</option>
                                            <option>Diseño Gráfico</option>
                                            <option>Impresión A3 Full Color</option>
                                        </select>
                                    </td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0">
                                        <input type="text" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm text-slate-700 focus:ring-0 outline-none placeholder:text-slate-300" placeholder="Añadir descripción...">
                                    </td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0">
                                        <input type="number" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-900 text-right focus:ring-0 outline-none" value="1">
                                    </td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0 relative">
                                        <span class="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 font-mono">S/</span>
                                        <input type="number" class="w-full h-full min-h-[40px] pl-6 pr-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-900 text-right focus:ring-0 outline-none" placeholder="0.00">
                                    </td>
                                    <td class="border-r border-slate-200 p-0 bg-slate-50 relative">
                                        <span class="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 font-mono">S/</span>
                                        <input type="text" readonly class="w-full h-full min-h-[40px] pl-6 pr-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-500 text-right outline-none" value="0.00">
                                    </td>
                                    <td class="p-0 text-center">
                                        <button class="w-full h-full flex items-center justify-center text-slate-300 hover:text-rose-500 transition-colors"><i class="ph-bold ph-trash"></i></button>
                                    </td>
                                </tr>

                            </tbody>
                        </table>
                        <!-- Agregar Línea -->
                        <div class="p-2 bg-white border-t border-slate-200">
                            <button class="text-[11px] font-mono font-bold text-brand-600 uppercase tracking-widest hover:text-brand-800 hover:bg-brand-50 px-4 py-2 transition-colors flex items-center gap-1">
                                <i class="ph-bold ph-plus-circle text-base"></i> Agregar línea de detalle
                            </button>
                        </div>
                    </div>

                    <!-- ZONA 3: PANEL DE LIQUIDACIÓN (Totales) -->
                    <div class="mt-6 flex justify-end">
                        <div class="w-full sm:w-80 bg-white border border-slate-300 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.05)] p-5">
                            <div class="space-y-3 font-mono text-sm">
                                <div class="flex justify-between text-slate-500">
                                    <span>Subtotal</span>
                                    <span>S/ 0.00</span>
                                </div>
                                <div class="flex justify-between text-slate-500">
                                    <span>IGV (18%)</span>
                                    <span>S/ 0.00</span>
                                </div>
                                <div class="pt-3 border-t border-slate-200 flex justify-between items-end">
                                    <span class="font-bold text-slate-900 uppercase tracking-widest text-[11px]">Total Cotización</span>
                                    <span class="text-2xl font-black text-brand-600">S/ 0.00</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer Modal -->
            <div class="px-6 py-4 border-t border-slate-200 bg-slate-100 flex items-center justify-end gap-4 flex-none">
                <button id="btnCancelModal" class="px-6 py-2.5 text-xs font-bold font-mono uppercase tracking-widest text-slate-600 hover:text-slate-900 transition-colors outline-none">
                    Cancelar
                </button>
                <button class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-3 transition-all flex items-center gap-2 hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 border border-transparent outline-none">
                    <i class="ph-bold ph-paper-plane-right text-lg"></i> Emitir Cotización
                </button>
            </div>
            
        </div>
    </div>

    <script>
        // Reloj
        function updateClock() {
            const now = new Date();
            document.getElementById('sysClock').textContent = 
                `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        }
        setInterval(updateClock, 1000); updateClock();

        // Modal
        const modal = document.getElementById('quoteModal');
        const btnOpenModal = document.getElementById('btnOpenModal');
        const btnCloseModalX = document.getElementById('btnCloseModalX');
        const btnCancelModal = document.getElementById('btnCancelModal');

        btnOpenModal.addEventListener('click', () => modal.classList.remove('hidden'));
        const closeModal = () => modal.classList.add('hidden');
        btnCloseModalX.addEventListener('click', closeModal);
        btnCancelModal.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

        // Select Custom (Básico para moneda)
        document.querySelectorAll('.custom-select').forEach(select => {
            const trigger = select.querySelector('.select-trigger');
            const menu = select.querySelector('.select-menu');
            const text = select.querySelector('.select-text');
            if(!menu) return;

            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                menu.classList.toggle('hidden');
                menu.classList.toggle('flex');
            });

            menu.querySelectorAll('li').forEach(opt => {
                opt.addEventListener('click', (e) => {
                    e.stopPropagation();
                    text.textContent = opt.textContent;
                    text.classList.remove('text-slate-400');
                    text.classList.add('text-slate-900');
                    menu.classList.add('hidden');
                    menu.classList.remove('flex');
                });
            });
        });
        document.addEventListener('click', () => {
            document.querySelectorAll('.select-menu').forEach(m => { m.classList.add('hidden'); m.classList.remove('flex'); });
        });
    </script>
</body>
</html>

Estilo de Cobranza

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inkora - Control de Cobranza</title>
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
        .tech-grid {
            background-image: linear-gradient(rgba(99, 102, 241, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(99, 102, 241, 0.04) 1px, transparent 1px);
            background-size: 32px 32px;
        }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .glass-header { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
    </style>
</head>
<body class="h-screen w-full flex overflow-hidden selection:bg-brand-500 selection:text-white tech-grid relative">

    <div class="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#3B82F6] via-[#6366F1] to-[#D946EF] z-50 animate-gradient-x"></div>

    <!-- ==========================================
         SIDEBAR (Navegación Industrial)
         ========================================== -->
    <aside class="w-[280px] bg-brand-950 flex-none flex flex-col justify-between shadow-2xl relative z-30 hidden md:flex border-r border-white/5">
        <div class="flex-1 overflow-y-auto no-scrollbar pt-2">
            <div class="p-6">
                <div class="flex items-center gap-3 mb-2">
                    <div class="w-9 h-9 flex items-center justify-center filter drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]">
                        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
                            <defs>
                                <linearGradient id="inkoraGradient" x1="0%" y1="100%" x2="100%" y2="0%">
                                    <stop offset="0%" stop-color="#3B82F6" />
                                    <stop offset="40%" stop-color="#6366F1" />
                                    <stop offset="100%" stop-color="#D946EF" />
                                </linearGradient>
                            </defs>
                            <path d="M50 0 C50 0 5 35 5 65 C5 89.8 25.2 100 50 100 C74.8 100 95 89.8 95 65 C95 35 50 0 50 0 Z M 35 25 L 50 25 L 50 52 L 72 25 L 88 25 L 62 58 L 88 90 L 72 90 L 50 63 L 50 90 L 35 90 Z" fill="url(#inkoraGradient)"/>
                        </svg>
                    </div>
                    <h1 class="text-2xl font-bold tracking-tight text-white">Inkora</h1>
                </div>
                <p class="text-[10px] font-mono text-slate-400 uppercase tracking-widest pl-12">Imprentas Core</p>
            </div>

            <nav class="p-4 space-y-1 mt-4">
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-squares-four text-xl group-hover:text-brand-400 transition-colors"></i> Dashboard
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-users text-xl group-hover:text-brand-400 transition-colors"></i> Clientes
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-package text-xl group-hover:text-brand-400 transition-colors"></i> Productos
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-file-text text-xl group-hover:text-brand-400 transition-colors"></i> Cotizaciones
                </a>
                <!-- Ítem Activo (Cobranza) -->
                <a href="#" class="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-brand-600/20 to-transparent text-white font-semibold text-sm transition-colors relative group">
                    <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF]"></div>
                    <i class="ph-fill ph-credit-card text-xl text-brand-400"></i> Cobranza
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
                <button class="text-slate-500 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-all px-1"><i class="ph-bold ph-power text-xl"></i></button>
            </div>
        </div>
    </aside>

    <!-- ==========================================
         WORKSPACE
         ========================================== -->
    <main class="flex-1 flex flex-col h-screen overflow-hidden relative z-10">
        
        <header class="glass-header border-b border-slate-200/50 px-8 py-4 flex items-center justify-between flex-none sticky top-0 z-20 pt-5">
            <div>
                <h2 class="text-xl font-bold text-slate-900 flex items-center gap-3">
                    Cobranza
                    <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-mono tracking-widest uppercase">Flujo de Caja</span>
                </h2>
            </div>
            <div class="flex items-center gap-6">
                <div class="hidden lg:flex flex-col items-end">
                    <p id="sysClock" class="font-mono text-sm font-bold text-slate-800">00:00:00</p>
                    <p id="sysDate" class="text-[10px] font-mono text-slate-500 uppercase tracking-widest">LIMA (PET)</p>
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

        <div class="flex-1 overflow-y-auto p-8 no-scrollbar">
            <div class="max-w-[1400px] mx-auto space-y-8 pb-12">

                <div>
                    <h3 class="text-3xl font-bold text-slate-900 tracking-tight">Control de Liquidez</h3>
                    <p class="text-slate-500 mt-1 text-sm">Seguimiento de saldos pendientes y vencimientos comerciales.</p>
                </div>

                <!-- KPIs de Liquidez (Semántica Financiera) -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
                    
                    <!-- KPI 1: Capital Pendiente (Ámbar) -->
                    <div class="bg-white p-6 border border-slate-200 border-t-4 border-t-amber-500 shadow-sm relative overflow-hidden group hover:border-amber-300 transition-colors">
                        <div class="relative z-10">
                            <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Total Pendiente (Por Cobrar)</p>
                            <div class="flex items-baseline gap-1 mb-1">
                                <span class="text-lg font-bold text-amber-600">S/</span>
                                <p class="text-4xl font-mono font-bold text-amber-600">33,826<span class="text-xl text-amber-400">.00</span></p>
                            </div>
                            <p class="text-xs text-slate-500">Saldo global por regularizar</p>
                        </div>
                    </div>

                    <!-- KPI 2: Riesgo Crítico (Rojo + Terminal Look) -->
                    <div class="bg-slate-900 p-6 border border-rose-500/50 border-t-4 border-t-rose-500 shadow-sm relative overflow-hidden group">
                        <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMSIgY3k9IjEiIHI9IjEiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')] opacity-50"></div>
                        <div class="absolute top-0 right-0 w-24 h-24 bg-rose-500 opacity-20 blur-2xl rounded-full animate-pulse"></div>
                        
                        <div class="relative z-10">
                            <div class="flex justify-between items-start mb-4">
                                <p class="text-[10px] font-bold font-mono text-rose-400 uppercase tracking-widest">Docs. Vencidos</p>
                                <span class="flex h-2 w-2">
                                  <span class="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-rose-400 opacity-75"></span>
                                  <span class="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
                                </span>
                            </div>
                            <p class="text-4xl font-mono font-bold text-white mb-1">14</p>
                            <p class="text-xs text-rose-400 font-mono flex items-center gap-1">
                                <i class="ph-bold ph-warning-circle"></i> Casos que requieren acción
                            </p>
                        </div>
                    </div>

                    <!-- KPI 3: Éxito/Recaudación (Verde) -->
                    <div class="bg-white p-6 border border-slate-200 border-t-4 border-t-emerald-500 shadow-sm relative overflow-hidden group hover:border-emerald-300 transition-colors">
                        <div class="relative z-10">
                            <p class="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest mb-4">Cobrado Este Mes</p>
                            <div class="flex items-baseline gap-1 mb-1">
                                <span class="text-lg font-bold text-emerald-600">S/</span>
                                <p class="text-4xl font-mono font-bold text-emerald-600">42,350<span class="text-xl text-emerald-400">.00</span></p>
                            </div>
                            <p class="text-xs text-slate-500">Monto efectivamente recuperado</p>
                        </div>
                    </div>

                </div>

                <!-- Toolbar de la Tabla -->
                <div class="bg-white border border-slate-200 rounded-none p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div class="relative w-full sm:w-[450px] group">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="ph-bold ph-magnifying-glass text-slate-400 group-focus-within:text-brand-600 transition-colors"></i>
                        </div>
                        <input type="text" class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-mono placeholder:font-sans placeholder:text-slate-400" placeholder="Buscar por cliente o documento...">
                    </div>

                    <div class="flex items-center gap-3 w-full sm:w-auto">
                        <button class="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 px-4 py-2.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors">
                            <i class="ph-bold ph-calendar-blank"></i> Vencimiento
                        </button>
                        <button class="bg-slate-50 hover:bg-emerald-50 border border-slate-200 hover:border-emerald-200 hover:text-emerald-700 text-slate-600 px-4 py-2.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors">
                            <i class="ph-bold ph-microsoft-excel-logo"></i> Exportar
                        </button>
                    </div>
                </div>

                <!-- Aging Report Table (Tabla de Antigüedad) -->
                <div class="bg-white border border-slate-200 rounded-none shadow-sm overflow-x-auto">
                    <!-- Cabecera de Alerta -->
                    <div class="px-6 py-4 border-b border-slate-200 bg-rose-50/50 flex justify-between items-center">
                        <div class="flex items-center gap-3">
                            <i class="ph-fill ph-warning-circle text-rose-500 text-xl"></i>
                            <div>
                                <h4 class="font-bold text-slate-900 font-mono text-sm uppercase tracking-widest">Documentos en Seguimiento</h4>
                                <p class="text-xs text-slate-500">Ordene por días de mora para priorizar la gestión.</p>
                            </div>
                        </div>
                    </div>

                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-100/80 border-b border-slate-200">
                            <tr>
                                <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Documento</th>
                                <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Cliente</th>
                                <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Vencimiento</th>
                                <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Total Doc.</th>
                                <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Saldo Deudor</th>
                                <th class="px-6 py-3 text-center text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Días (Mora)</th>
                                <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Acción Rápida</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100">
                            
                            <!-- Fila Crítica (103 días) -->
                            <tr class="hover:bg-brand-50/40 transition-colors group bg-rose-50/20">
                                <td class="px-6 py-3">
                                    <div class="flex items-center gap-2">
                                        <span class="inline-block w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                                        <span class="font-mono text-[13px] font-bold text-slate-700">ORD-0006-000008</span>
                                    </div>
                                </td>
                                <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px]">Cliente Corporativo SAC</p></td>
                                <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">01/01/2026</span></td>
                                <td class="px-6 py-3 text-right"><span class="font-mono text-[13px] text-slate-500">S/ 200.00</span></td>
                                <td class="px-6 py-3 text-right"><span class="font-mono text-[14px] font-bold text-rose-600">S/ 200.00</span></td>
                                <td class="px-6 py-3 text-center">
                                    <!-- Aging Badge (Crítico) -->
                                    <span class="inline-flex px-2 py-1 bg-rose-100 text-rose-700 border border-rose-200 text-[11px] font-mono font-bold uppercase tracking-widest shadow-sm">
                                        +103 Días
                                    </span>
                                </td>
                                <td class="px-6 py-3 text-right">
                                    <!-- CTAs de Resolución Rápida (Hover) -->
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="px-3 py-1.5 bg-white border border-brand-200 text-brand-600 hover:bg-brand-50 font-mono text-[10px] font-bold uppercase tracking-widest transition-colors flex items-center gap-1 shadow-sm" title="Notificar Cliente">
                                            <i class="ph-bold ph-bell-ringing text-sm"></i> Aviso
                                        </button>
                                        <button class="px-3 py-1.5 bg-emerald-600 border border-emerald-600 text-white hover:bg-emerald-700 font-mono text-[10px] font-bold uppercase tracking-widest transition-colors flex items-center gap-1 shadow-sm" title="Registrar Pago">
                                            <i class="ph-bold ph-currency-circle-dollar text-sm"></i> Pagar
                                        </button>
                                    </div>
                                </td>
                            </tr>

                            <!-- Fila Temprana (15 días) -->
                            <tr class="hover:bg-brand-50/40 transition-colors group">
                                <td class="px-6 py-3">
                                    <div class="flex items-center gap-2">
                                        <span class="inline-block w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                                        <span class="font-mono text-[13px] font-bold text-slate-700">FACT-001-4099</span>
                                    </div>
                                </td>
                                <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px]">Distribuidora Norte EIRL</p></td>
                                <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">30/03/2026</span></td>
                                <td class="px-6 py-3 text-right"><span class="font-mono text-[13px] text-slate-500">S/ 1,500.00</span></td>
                                <td class="px-6 py-3 text-right"><span class="font-mono text-[14px] font-bold text-amber-600">S/ 1,500.00</span></td>
                                <td class="px-6 py-3 text-center">
                                    <!-- Aging Badge (Ámbar) -->
                                    <span class="inline-flex px-2 py-1 bg-amber-100 text-amber-700 border border-amber-200 text-[11px] font-mono font-bold uppercase tracking-widest">
                                        +15 Días
                                    </span>
                                </td>
                                <td class="px-6 py-3 text-right">
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="px-3 py-1.5 bg-white border border-brand-200 text-brand-600 hover:bg-brand-50 font-mono text-[10px] font-bold uppercase tracking-widest transition-colors flex items-center gap-1 shadow-sm">
                                            <i class="ph-bold ph-bell-ringing text-sm"></i> Aviso
                                        </button>
                                        <button class="px-3 py-1.5 bg-emerald-600 border border-emerald-600 text-white hover:bg-emerald-700 font-mono text-[10px] font-bold uppercase tracking-widest transition-colors flex items-center gap-1 shadow-sm">
                                            <i class="ph-bold ph-currency-circle-dollar text-sm"></i> Pagar
                                        </button>
                                    </div>
                                </td>
                            </tr>

                            <!-- Fila Por Vencer (-2 días) -->
                            <tr class="hover:bg-brand-50/40 transition-colors group">
                                <td class="px-6 py-3">
                                    <div class="flex items-center gap-2">
                                        <span class="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
                                        <span class="font-mono text-[13px] font-bold text-slate-700">FACT-001-4105</span>
                                    </div>
                                </td>
                                <td class="px-6 py-3"><p class="font-bold text-slate-900 text-[13px]">García Pérez Juan Carlos</p></td>
                                <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">16/04/2026</span></td>
                                <td class="px-6 py-3 text-right"><span class="font-mono text-[13px] text-slate-500">S/ 450.00</span></td>
                                <td class="px-6 py-3 text-right"><span class="font-mono text-[14px] font-bold text-slate-900">S/ 450.00</span></td>
                                <td class="px-6 py-3 text-center">
                                    <!-- Aging Badge (Neutro) -->
                                    <span class="inline-flex px-2 py-1 bg-slate-100 text-slate-600 border border-slate-200 text-[11px] font-mono font-bold uppercase tracking-widest">
                                        Vence en 2d
                                    </span>
                                </td>
                                <td class="px-6 py-3 text-right">
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="px-3 py-1.5 bg-emerald-600 border border-emerald-600 text-white hover:bg-emerald-700 font-mono text-[10px] font-bold uppercase tracking-widest transition-colors flex items-center gap-1 shadow-sm">
                                            <i class="ph-bold ph-currency-circle-dollar text-sm"></i> Pagar
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

            </div>
        </div>
    </main>

    <!-- Scripts -->
    <script>
        function updateClock() {
            const now = new Date();
            document.getElementById('sysClock').textContent = 
                `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        }
        setInterval(updateClock, 1000); updateClock();
    </script>
</body>
</html>

Estilo de guias

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inkora - Guías de Remisión</title>
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
<body class="h-screen w-full flex overflow-hidden selection:bg-brand-500 selection:text-white tech-grid relative">

    <div class="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#3B82F6] via-[#6366F1] to-[#D946EF] z-50 animate-gradient-x"></div>

    <!-- ==========================================
         SIDEBAR (Navegación Industrial)
         ========================================== -->
    <aside class="w-[280px] bg-brand-950 flex-none flex flex-col justify-between shadow-2xl relative z-30 hidden md:flex border-r border-white/5">
        <div class="flex-1 overflow-y-auto no-scrollbar pt-2">
            <div class="p-6">
                <div class="flex items-center gap-3 mb-2">
                    <div class="w-9 h-9 flex items-center justify-center filter drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]">
                        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
                            <defs>
                                <linearGradient id="inkoraGradient" x1="0%" y1="100%" x2="100%" y2="0%">
                                    <stop offset="0%" stop-color="#3B82F6" />
                                    <stop offset="40%" stop-color="#6366F1" />
                                    <stop offset="100%" stop-color="#D946EF" />
                                </linearGradient>
                            </defs>
                            <path d="M50 0 C50 0 5 35 5 65 C5 89.8 25.2 100 50 100 C74.8 100 95 89.8 95 65 C95 35 50 0 50 0 Z M 35 25 L 50 25 L 50 52 L 72 25 L 88 25 L 62 58 L 88 90 L 72 90 L 50 63 L 50 90 L 35 90 Z" fill="url(#inkoraGradient)"/>
                        </svg>
                    </div>
                    <h1 class="text-2xl font-bold tracking-tight text-white">Inkora</h1>
                </div>
                <p class="text-[10px] font-mono text-slate-400 uppercase tracking-widest pl-12">Imprentas Core</p>
            </div>

            <nav class="p-4 space-y-1 mt-4">
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-squares-four text-xl group-hover:text-brand-400 transition-colors"></i> Dashboard
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-users text-xl group-hover:text-brand-400 transition-colors"></i> Clientes
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-package text-xl group-hover:text-brand-400 transition-colors"></i> Productos
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-file-text text-xl group-hover:text-brand-400 transition-colors"></i> Cotizaciones
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-credit-card text-xl group-hover:text-brand-400 transition-colors"></i> Cobranza
                </a>
                <!-- Ítem Activo (Guías) -->
                <a href="#" class="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-brand-600/20 to-transparent text-white font-semibold text-sm transition-colors relative group">
                    <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF]"></div>
                    <i class="ph-fill ph-truck text-xl text-brand-400"></i> Guías
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
                <button class="text-slate-500 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-all px-1"><i class="ph-bold ph-power text-xl"></i></button>
            </div>
        </div>
    </aside>

    <!-- ==========================================
         WORKSPACE
         ========================================== -->
    <main class="flex-1 flex flex-col h-screen overflow-hidden relative z-10">
        
        <header class="glass-header border-b border-slate-200/50 px-8 py-4 flex items-center justify-between flex-none sticky top-0 z-20 pt-5">
            <div>
                <h2 class="text-xl font-bold text-slate-900 flex items-center gap-3">
                    Guías de remisión
                    <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-mono tracking-widest uppercase">Despacho Fiscal</span>
                </h2>
            </div>
            <div class="flex items-center gap-6">
                <div class="hidden lg:flex flex-col items-end">
                    <p id="sysClock" class="font-mono text-sm font-bold text-slate-800">00:00:00</p>
                    <p id="sysDate" class="text-[10px] font-mono text-slate-500 uppercase tracking-widest">LIMA (PET)</p>
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

        <div class="flex-1 overflow-y-auto p-8 no-scrollbar">
            <div class="max-w-[1400px] mx-auto space-y-6 pb-12">

                <!-- Toolbar de Despacho -->
                <div class="bg-white border border-slate-200 p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div class="relative w-full sm:w-[450px] group">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="ph-bold ph-magnifying-glass text-slate-400 group-focus-within:text-brand-600 transition-colors"></i>
                        </div>
                        <input type="text" class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-mono placeholder:font-sans placeholder:text-slate-400" placeholder="Buscar por cliente o N° de guía (ej. T001)...">
                    </div>

                    <div class="flex items-center gap-3 w-full sm:w-auto">
                        <button class="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 px-4 py-2.5 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors">
                            <i class="ph-bold ph-funnel"></i> Estado
                        </button>
                        <button id="btnOpenModal" class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-6 py-2.5 flex items-center gap-2 hover:bg-brand-600 transition-all hover:shadow-[4px_4px_0px_0px_rgba(49,46,129,0.5)] hover:-translate-y-0.5 hover:-translate-x-0.5 border border-transparent">
                            <i class="ph-bold ph-plus"></i> Nueva Guía
                        </button>
                    </div>
                </div>

                <!-- Tabla de Guías (Logística) -->
                <div class="bg-white border border-slate-200 shadow-sm overflow-x-auto">
                    <div class="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                        <div class="flex items-center gap-3">
                            <i class="ph-fill ph-truck text-slate-500 text-xl"></i>
                            <div>
                                <h4 class="font-bold text-slate-900 font-mono text-sm uppercase tracking-widest">Bitácora de Despachos</h4>
                                <p class="text-xs text-slate-500">Documentos logísticos sincronizados con SUNAT.</p>
                            </div>
                        </div>
                    </div>

                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-100/80 border-b border-slate-200">
                            <tr>
                                <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Número</th>
                                <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Fecha Traslado</th>
                                <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest w-[25%]">Origen</th>
                                <th class="px-6 py-3 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest w-[25%]">Destino</th>
                                <th class="px-6 py-3 text-center text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Estado</th>
                                <th class="px-6 py-3 text-right text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">Acciones</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100">
                            <tr class="hover:bg-brand-50/40 transition-colors group">
                                <td class="px-6 py-3">
                                    <div class="flex items-center gap-2">
                                        <i class="ph-fill ph-truck text-slate-400"></i>
                                        <span class="font-mono text-[13px] font-bold text-slate-800">T001-000001</span>
                                    </div>
                                </td>
                                <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">09/04/2026</span></td>
                                <td class="px-6 py-3"><p class="text-slate-900 text-[12px] truncate max-w-[200px]" title="Av. Demo 123, Lima">Av. Demo 123, Lima</p></td>
                                <td class="px-6 py-3"><p class="font-semibold text-slate-900 text-[12px] truncate max-w-[200px]" title="Jr. Cliente 456, Miraflores">Jr. Cliente 456, Miraflores</p></td>
                                <td class="px-6 py-3 text-center">
                                    <span class="inline-flex px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-mono font-bold uppercase tracking-widest">En ruta</span>
                                </td>
                                <td class="px-6 py-3 text-right">
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="p-1.5 text-slate-400 hover:text-brand-600 transition-colors" title="Ver Documento"><i class="ph-bold ph-eye text-base"></i></button>
                                        <button class="p-1.5 text-slate-400 hover:text-brand-600 transition-colors" title="Imprimir PDF"><i class="ph-bold ph-printer text-base"></i></button>
                                    </div>
                                </td>
                            </tr>
                            
                            <tr class="hover:bg-brand-50/40 transition-colors group">
                                <td class="px-6 py-3">
                                    <div class="flex items-center gap-2">
                                        <i class="ph-fill ph-truck text-slate-400"></i>
                                        <span class="font-mono text-[13px] font-bold text-slate-800">T001-000002</span>
                                    </div>
                                </td>
                                <td class="px-6 py-3"><span class="font-mono text-[12px] text-slate-500">10/04/2026</span></td>
                                <td class="px-6 py-3"><p class="text-slate-900 text-[12px] truncate max-w-[200px]">Av. Principal 456, Comas</p></td>
                                <td class="px-6 py-3"><p class="font-semibold text-slate-900 text-[12px] truncate max-w-[200px]">Almacén Central SUR, Lurin</p></td>
                                <td class="px-6 py-3 text-center">
                                    <span class="inline-flex px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono font-bold uppercase tracking-widest">Entregado</span>
                                </td>
                                <td class="px-6 py-3 text-right">
                                    <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <button class="p-1.5 text-slate-400 hover:text-brand-600 transition-colors" title="Ver Documento"><i class="ph-bold ph-eye text-base"></i></button>
                                        <button class="p-1.5 text-slate-400 hover:text-brand-600 transition-colors" title="Imprimir PDF"><i class="ph-bold ph-printer text-base"></i></button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

            </div>
        </div>
    </main>

    <!-- ==========================================
         MODAL: NUEVA GUÍA DE REMISIÓN (Industrial Logístico)
         ========================================== -->
    <div id="guideModal" class="fixed inset-0 bg-brand-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 transition-opacity hidden">
        
        <div class="bg-white border border-slate-200 rounded-none w-full max-w-5xl shadow-[8px_8px_0px_0px_rgba(15,14,41,0.15)] flex flex-col transform transition-all max-h-[95vh]">
            
            <!-- Header Modal -->
            <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50 flex-none">
                <div class="flex items-center gap-4">
                    <h3 class="font-bold text-slate-900 font-mono uppercase tracking-widest text-sm flex items-center gap-2">
                        <i class="ph-bold ph-truck text-brand-600 text-lg"></i> Registrar Guía de Remisión
                    </h3>
                    <span class="px-2 py-0.5 bg-brand-100 text-brand-700 font-mono text-[10px] font-bold tracking-widest">Emisión SUNAT</span>
                </div>
                <button id="btnCloseModalX" class="text-slate-400 hover:text-rose-500 transition-colors p-1 outline-none">
                    <i class="ph-bold ph-x text-xl"></i>
                </button>
            </div>
            
            <!-- Body Modal (Scrollable) -->
            <div class="flex-1 overflow-y-auto no-scrollbar flex flex-col bg-white">
                
                <!-- ZONA 1: CONFIGURACIÓN GENERAL -->
                <div class="p-6 border-b border-slate-200 space-y-6">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        
                        <!-- Motivo (Custom Select) -->
                        <div class="space-y-1.5 custom-select-container">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Motivo traslado</label>
                            <div class="custom-select relative">
                                <input type="hidden" value="venta">
                                <button type="button" class="select-trigger w-full px-4 py-2.5 bg-slate-50 border border-slate-300 text-slate-900 font-mono text-sm font-semibold flex justify-between items-center focus:border-brand-500 focus:bg-white transition-all">
                                    <span class="select-text flex items-center gap-2"><i class="ph-bold ph-shopping-cart text-slate-400"></i> Venta</span>
                                    <i class="ph-bold ph-caret-down text-slate-400"></i>
                                </button>
                                <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col">
                                    <li class="px-4 py-2.5 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 flex items-center gap-2"><i class="ph-bold ph-shopping-cart"></i> Venta</li>
                                    <li class="px-4 py-2.5 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 flex items-center gap-2"><i class="ph-bold ph-arrows-left-right"></i> Traslado entre establecimientos</li>
                                </ul>
                            </div>
                        </div>

                        <!-- Modalidad (Custom Select) -->
                        <div class="space-y-1.5 custom-select-container">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest">Modalidad</label>
                            <div class="custom-select relative">
                                <input type="hidden" value="publico">
                                <button type="button" class="select-trigger w-full px-4 py-2.5 bg-slate-50 border border-slate-300 text-slate-900 font-mono text-sm font-semibold flex justify-between items-center focus:border-brand-500 focus:bg-white transition-all">
                                    <span class="select-text flex items-center gap-2"><i class="ph-bold ph-bus text-slate-400"></i> Transporte público</span>
                                    <i class="ph-bold ph-caret-down text-slate-400"></i>
                                </button>
                                <ul class="select-menu absolute z-50 w-full mt-1 bg-white border border-slate-200 shadow-[4px_4px_0px_0px_rgba(15,14,41,0.1)] hidden flex-col">
                                    <li class="px-4 py-2.5 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 flex items-center gap-2"><i class="ph-bold ph-bus"></i> Transporte público</li>
                                    <li class="px-4 py-2.5 hover:bg-brand-50 font-mono text-sm cursor-pointer text-slate-700 hover:text-brand-700 border-l-2 border-transparent hover:border-brand-500 flex items-center gap-2"><i class="ph-bold ph-truck"></i> Transporte privado</li>
                                </ul>
                            </div>
                        </div>
                        
                        <!-- Peso Bruto (Magnitud Técnica) -->
                        <div class="space-y-1.5 group">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Peso Bruto Total</label>
                            <div class="relative flex items-center">
                                <input type="number" class="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm font-bold text-right focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors pr-12" placeholder="0.000">
                                <span class="absolute right-3 font-mono text-xs font-bold text-slate-400 pointer-events-none select-none">KGM</span>
                            </div>
                        </div>

                    </div>
                </div>

                <!-- ZONA 2: RUTA (Symmetry Grid: Origen vs Destino) -->
                <div class="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-200 border-b border-slate-200">
                    
                    <!-- Panel Origen -->
                    <div class="p-6 bg-slate-50/50 space-y-5">
                        <h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest flex items-center gap-2 mb-4">
                            <i class="ph-bold ph-map-pin text-slate-400 text-base"></i> Punto de Partida
                        </h4>
                        <div class="space-y-1.5 group">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Dirección Partida</label>
                            <input type="text" class="w-full px-4 py-2.5 bg-white border border-slate-300 text-slate-900 text-sm focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors" placeholder="Av. Los Pinos 123">
                        </div>
                        <div class="space-y-1.5 group">
                            <div class="flex justify-between items-end">
                                <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Ubigeo Partida</label>
                                <button type="button" class="text-[9px] font-bold font-mono text-brand-600 hover:text-brand-800 uppercase tracking-wider outline-none"><i class="ph-bold ph-magnifying-glass"></i> Buscar</button>
                            </div>
                            <input type="text" maxlength="6" class="w-full px-4 py-2.5 bg-white border border-slate-300 text-slate-900 font-mono text-sm tracking-widest font-bold focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors" placeholder="150101">
                        </div>
                    </div>

                    <!-- Panel Destino -->
                    <div class="p-6 bg-white space-y-5 relative">
                        <div class="hidden md:flex absolute top-1/2 -left-4 w-8 h-8 bg-white border border-slate-200 rounded-full items-center justify-center text-slate-400 z-10">
                            <i class="ph-bold ph-arrow-right"></i>
                        </div>
                        <h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest flex items-center gap-2 mb-4">
                            <i class="ph-fill ph-map-pin text-brand-500 text-base"></i> Punto de Llegada
                        </h4>
                        <div class="space-y-1.5 group">
                            <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Dirección Llegada</label>
                            <input type="text" class="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 text-slate-900 text-sm focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors" placeholder="Jr. El Sol 456">
                        </div>
                        <div class="space-y-1.5 group">
                            <div class="flex justify-between items-end">
                                <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Ubigeo Llegada</label>
                                <button type="button" class="text-[9px] font-bold font-mono text-brand-600 hover:text-brand-800 uppercase tracking-wider outline-none"><i class="ph-bold ph-magnifying-glass"></i> Buscar</button>
                            </div>
                            <input type="text" maxlength="6" class="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 text-slate-900 font-mono text-sm tracking-widest font-bold focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors" placeholder="150102">
                        </div>
                    </div>

                </div>

                <!-- ZONA 3: SPREADSHEET UI (Bienes a trasladar) -->
                <div class="flex-1 bg-slate-50/50 p-6">
                    <div class="mb-4 flex justify-between items-center">
                        <h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Bienes a Trasladar</h4>
                    </div>

                    <!-- Tabla estilo Excel Logístico -->
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
                                
                                <!-- Fila 1 (Celdas editables) -->
                                <tr class="group bg-white hover:bg-slate-50 transition-colors">
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0 relative">
                                        <input type="text" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-900 focus:ring-0 outline-none uppercase" placeholder="SKU-001">
                                    </td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0">
                                        <input type="text" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm text-slate-700 focus:ring-0 outline-none placeholder:text-slate-300" placeholder="Descripción detallada de la mercadería...">
                                    </td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0 relative">
                                        <select class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-xs font-mono font-bold text-slate-600 text-right focus:ring-0 cursor-pointer appearance-none outline-none text-right-override" style="text-align-last: right;">
                                            <option>NIU (Und)</option>
                                            <option>MIL (Millar)</option>
                                            <option>BX (Caja)</option>
                                        </select>
                                    </td>
                                    <td class="spreadsheet-cell border-r border-slate-200 p-0">
                                        <input type="number" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent border-0 text-sm font-mono font-bold text-slate-900 text-right focus:ring-0 outline-none" value="1">
                                    </td>
                                    <td class="p-0 text-center">
                                        <button class="w-full h-full flex items-center justify-center text-slate-300 hover:text-rose-500 transition-colors"><i class="ph-bold ph-trash"></i></button>
                                    </td>
                                </tr>

                            </tbody>
                        </table>
                        <!-- Agregar Línea -->
                        <div class="p-2 bg-white border-t border-slate-200">
                            <button class="text-[11px] font-mono font-bold text-brand-600 uppercase tracking-widest hover:text-brand-800 hover:bg-brand-50 px-4 py-2 transition-colors flex items-center gap-1">
                                <i class="ph-bold ph-plus-circle text-base"></i> Agregar bien a trasladar
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer Modal -->
            <div class="px-6 py-4 border-t border-slate-200 bg-slate-100 flex items-center justify-end gap-4 flex-none">
                <button id="btnCancelModal" class="px-6 py-2.5 text-xs font-bold font-mono uppercase tracking-widest text-slate-600 hover:text-slate-900 transition-colors outline-none">
                    Cancelar
                </button>
                <button class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-3 transition-all flex items-center gap-2 hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 border border-transparent hover:border-brand-500 outline-none">
                    <i class="ph-bold ph-truck text-lg"></i> Emitir Guía
                </button>
            </div>
            
        </div>
    </div>

    <script>
        // Reloj
        function updateClock() {
            const now = new Date();
            document.getElementById('sysClock').textContent = 
                `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        }
        setInterval(updateClock, 1000); updateClock();

        // Modal
        const modal = document.getElementById('guideModal');
        const btnOpenModal = document.getElementById('btnOpenModal');
        const btnCloseModalX = document.getElementById('btnCloseModalX');
        const btnCancelModal = document.getElementById('btnCancelModal');

        btnOpenModal.addEventListener('click', () => modal.classList.remove('hidden'));
        const closeModal = () => modal.classList.add('hidden');
        btnCloseModalX.addEventListener('click', closeModal);
        btnCancelModal.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

        // Select Custom Logic (Cerrar otros al abrir)
        document.querySelectorAll('.custom-select-container').forEach(container => {
            const trigger = container.querySelector('.select-trigger');
            const menu = container.querySelector('.select-menu');
            const text = container.querySelector('.select-text');
            
            if(!menu) return;

            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                // Cerrar todos primero
                document.querySelectorAll('.select-menu').forEach(m => {
                    if(m !== menu) { m.classList.add('hidden'); m.classList.remove('flex'); }
                });
                // Toggle actual
                menu.classList.toggle('hidden');
                menu.classList.toggle('flex');
            });

            menu.querySelectorAll('li').forEach(opt => {
                opt.addEventListener('click', (e) => {
                    e.stopPropagation();
                    text.innerHTML = opt.innerHTML; // Preserva iconos
                    menu.classList.add('hidden');
                    menu.classList.remove('flex');
                });
            });
        });
        document.addEventListener('click', () => {
            document.querySelectorAll('.select-menu').forEach(m => { m.classList.add('hidden'); m.classList.remove('flex'); });
        });
    </script>
</body>
</html>

Estilo de configuracion

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inkora - Configuración</title>
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
        .tech-grid {
            background-image: linear-gradient(rgba(99, 102, 241, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(99, 102, 241, 0.04) 1px, transparent 1px);
            background-size: 32px 32px;
        }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .glass-header { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
        
        input[type=number]::-webkit-inner-spin-button, 
        input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
</head>
<body class="h-screen w-full flex overflow-hidden selection:bg-brand-500 selection:text-white tech-grid relative">

    <div class="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#3B82F6] via-[#6366F1] to-[#D946EF] z-50 animate-gradient-x"></div>

    <!-- ==========================================
         SIDEBAR (Navegación Industrial)
         ========================================== -->
    <aside class="w-[280px] bg-brand-950 flex-none flex flex-col justify-between shadow-2xl relative z-30 hidden md:flex border-r border-white/5">
        <div class="flex-1 overflow-y-auto no-scrollbar pt-2">
            <div class="p-6">
                <div class="flex items-center gap-3 mb-2">
                    <div class="w-9 h-9 flex items-center justify-center filter drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]">
                        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
                            <defs>
                                <linearGradient id="inkoraGradient" x1="0%" y1="100%" x2="100%" y2="0%">
                                    <stop offset="0%" stop-color="#3B82F6" />
                                    <stop offset="40%" stop-color="#6366F1" />
                                    <stop offset="100%" stop-color="#D946EF" />
                                </linearGradient>
                            </defs>
                            <path d="M50 0 C50 0 5 35 5 65 C5 89.8 25.2 100 50 100 C74.8 100 95 89.8 95 65 C95 35 50 0 50 0 Z M 35 25 L 50 25 L 50 52 L 72 25 L 88 25 L 62 58 L 88 90 L 72 90 L 50 63 L 50 90 L 35 90 Z" fill="url(#inkoraGradient)"/>
                        </svg>
                    </div>
                    <h1 class="text-2xl font-bold tracking-tight text-white">Inkora</h1>
                </div>
                <p class="text-[10px] font-mono text-slate-400 uppercase tracking-widest pl-12">Imprentas Core</p>
            </div>

            <nav class="p-4 space-y-1 mt-4">
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-squares-four text-xl group-hover:text-brand-400 transition-colors"></i> Dashboard
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-users text-xl group-hover:text-brand-400 transition-colors"></i> Clientes
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-package text-xl group-hover:text-brand-400 transition-colors"></i> Productos
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-file-text text-xl group-hover:text-brand-400 transition-colors"></i> Cotizaciones
                </a>
                <a href="#" class="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 font-medium text-sm transition-colors group">
                    <i class="ph ph-truck text-xl group-hover:text-brand-400 transition-colors"></i> Guías
                </a>
                
                <div class="pt-4 mt-4 border-t border-white/10"></div>
                <!-- Ítem Activo (Configuración) -->
                <a href="#" class="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-brand-600/20 to-transparent text-white font-semibold text-sm transition-colors relative group">
                    <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#3B82F6] to-[#D946EF]"></div>
                    <i class="ph-fill ph-gear text-xl text-brand-400"></i> Configuración
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
                <button class="text-slate-500 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-all px-1"><i class="ph-bold ph-power text-xl"></i></button>
            </div>
        </div>
    </aside>

    <!-- ==========================================
         WORKSPACE
         ========================================== -->
    <main class="flex-1 flex flex-col h-screen overflow-hidden relative z-10">
        
        <header class="glass-header border-b border-slate-200/50 px-8 py-4 flex items-center justify-between flex-none sticky top-0 z-20 pt-5">
            <div>
                <h2 class="text-xl font-bold text-slate-900 flex items-center gap-3">
                    Configuración del Sistema
                    <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-mono tracking-widest uppercase">Admin</span>
                </h2>
            </div>
            <div class="flex items-center gap-6">
                <div class="hidden lg:flex flex-col items-end">
                    <p id="sysClock" class="font-mono text-sm font-bold text-slate-800">00:00:00</p>
                    <p id="sysDate" class="text-[10px] font-mono text-slate-500 uppercase tracking-widest">LIMA (PET)</p>
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

        <div class="flex-1 overflow-y-auto no-scrollbar">
            
            <!-- TABS (Sub-Navegación Industrial) -->
            <div class="bg-white border-b border-slate-200 px-8 pt-6 flex gap-8 sticky top-0 z-10">
                <button onclick="switchTab('empresa')" id="tab-empresa" class="pb-3 border-b-2 border-brand-600 text-brand-600 font-bold text-sm tracking-wide uppercase transition-colors outline-none">
                    Perfil de Empresa
                </button>
                <button onclick="switchTab('fiscal')" id="tab-fiscal" class="pb-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 font-semibold text-sm tracking-wide uppercase transition-colors outline-none">
                    Configuración Fiscal
                </button>
                <button onclick="switchTab('cuenta')" id="tab-cuenta" class="pb-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 font-semibold text-sm tracking-wide uppercase transition-colors outline-none">
                    Mi Cuenta
                </button>
            </div>

            <!-- CONTENEDOR DE PESTAÑAS -->
            <div class="max-w-[1000px] mx-auto p-8 space-y-8 pb-16">

                <!-- ==========================================
                     PESTAÑA 1: PERFIL DE EMPRESA
                     ========================================== -->
                <div id="content-empresa" class="space-y-6 block">
                    <div>
                        <h3 class="text-2xl font-bold text-slate-900 tracking-tight">Perfil de Empresa</h3>
                        <p class="text-slate-500 mt-1 text-sm">Datos visibles para la operación del tenant y emisión de comprobantes.</p>
                    </div>

                    <div class="bg-white border border-slate-200 rounded-none p-8 shadow-sm">
                        <div class="flex items-center gap-3 mb-8 border-b border-slate-100 pb-4">
                            <i class="ph-bold ph-buildings text-brand-600 text-xl"></i>
                            <h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Identidad Tributaria</h4>
                        </div>

                        <form class="space-y-6" onsubmit="event.preventDefault(); alert('Datos de empresa guardados');">
                            <!-- Razón Social -->
                            <div class="space-y-1.5 group">
                                <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Razón Social</label>
                                <input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 text-sm font-semibold focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors" value="Imprenta Demo PrintFlow SAC">
                            </div>

                            <!-- RUC y Teléfono (Grid) -->
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div class="space-y-1.5 group">
                                    <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">RUC</label>
                                    <input type="text" maxlength="11" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm font-bold tracking-widest focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors" value="20999999999">
                                </div>
                                <div class="space-y-1.5 group">
                                    <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Teléfono de Contacto</label>
                                    <input type="tel" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 font-mono text-sm focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors" value="999-777-888">
                                </div>
                            </div>

                            <!-- Dirección -->
                            <div class="space-y-1.5 group">
                                <label class="block text-[10px] font-bold font-mono text-slate-500 uppercase tracking-widest transition-colors group-focus-within:text-brand-600">Dirección Fiscal</label>
                                <input type="text" class="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-none text-slate-900 text-sm focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors" value="Av. Demo 456, Lima">
                            </div>

                            <!-- Footer Formulario -->
                            <div class="pt-6 border-t border-slate-100 flex justify-end">
                                <button type="submit" class="relative group bg-slate-900 text-white font-mono text-xs uppercase tracking-widest px-8 py-3 transition-all flex items-center gap-2 rounded-none hover:shadow-[4px_4px_0px_0px_rgba(99,102,241,1)] hover:-translate-y-1 hover:-translate-x-1 border border-transparent outline-none">
                                    <i class="ph-bold ph-floppy-disk text-lg"></i> Guardar Cambios
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- ==========================================
                     PESTAÑA 2: CONFIGURACIÓN FISCAL
                     ========================================== -->
                <div id="content-fiscal" class="space-y-6 hidden">
                    <div>
                        <h3 class="text-2xl font-bold text-slate-900 tracking-tight">Integración Fiscal</h3>
                        <p class="text-slate-500 mt-1 text-sm">Estado de conexión con SUNAT y ApisPeru. Los valores sensibles son gestionados por el administrador.</p>
                    </div>

                    <div class="bg-white border border-slate-200 rounded-none p-8 shadow-sm">
                        <div class="flex items-center gap-3 mb-6 border-b border-slate-100 pb-4">
                            <i class="ph-bold ph-shield-check text-brand-600 text-xl"></i>
                            <h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Credenciales y Certificados</h4>
                        </div>

                        <!-- Lista de Estados (Lectura) -->
                        <div class="divide-y divide-slate-100 mb-8">
                            
                            <!-- Item 1: Token ApisPeru -->
                            <div class="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div>
                                    <p class="font-bold text-slate-900 text-sm">Token ApisPeru</p>
                                    <p class="text-xs text-slate-500">Conexión API para consulta de RUC/DNI y tipo de cambio.</p>
                                </div>
                                <span class="inline-flex items-center justify-center px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono font-bold uppercase tracking-widest w-fit">
                                    Configurado
                                </span>
                            </div>

                            <!-- Item 2: Credenciales SOL -->
                            <div class="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div>
                                    <p class="font-bold text-slate-900 text-sm">Credenciales SOL</p>
                                    <p class="text-xs text-slate-500">Usuario y Clave SOL para transmisión directa a SUNAT.</p>
                                </div>
                                <span class="inline-flex items-center justify-center px-3 py-1 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-mono font-bold uppercase tracking-widest w-fit">
                                    Pendiente
                                </span>
                            </div>

                            <!-- Item 3: Certificado Digital -->
                            <div class="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div>
                                    <p class="font-bold text-slate-900 text-sm">Certificado Digital (PFX)</p>
                                    <p class="text-xs text-slate-500">Firma electrónica de documentos XML (Facturas, Boletas).</p>
                                </div>
                                <span class="inline-flex items-center justify-center px-3 py-1 bg-slate-100 text-slate-500 border border-slate-200 text-[10px] font-mono font-bold uppercase tracking-widest w-fit">
                                    No Cargado
                                </span>
                            </div>
                        </div>

                        <!-- Alerta Estilo Terminal (Industrial) -->
                        <div class="bg-brand-900 border border-brand-800 p-5 flex gap-4 items-start">
                            <i class="ph-bold ph-info text-brand-400 text-xl mt-0.5"></i>
                            <div>
                                <h5 class="text-white font-bold text-sm">Actualización Restringida</h5>
                                <p class="text-brand-200 text-xs mt-1 leading-relaxed">
                                    Para modificar o actualizar los certificados digitales y credenciales fiscales, por favor contacte al administrador global de la plataforma para escalar los permisos.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ==========================================
                     PESTAÑA 3: MI CUENTA (PERFIL)
                     ========================================== -->
                <div id="content-cuenta" class="space-y-6 hidden">
                    <div>
                        <h3 class="text-2xl font-bold text-slate-900 tracking-tight">Tu Perfil</h3>
                        <p class="text-slate-500 mt-1 text-sm">Información de tu cuenta de acceso y roles asignados.</p>
                    </div>

                    <div class="bg-white border border-slate-200 rounded-none p-8 shadow-sm">
                        <div class="flex items-center gap-3 mb-6 border-b border-slate-100 pb-4">
                            <i class="ph-bold ph-user-circle text-brand-600 text-xl"></i>
                            <h4 class="font-bold text-slate-800 font-mono text-xs uppercase tracking-widest">Datos de Sesión</h4>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                            
                            <!-- Avatar Placeholder -->
                            <div class="md:col-span-1 flex flex-col items-center justify-center border-r border-slate-100 pr-0 md:pr-8 py-4">
                                <div class="w-24 h-24 bg-brand-50 border border-brand-200 rounded-full flex items-center justify-center text-brand-600 font-bold text-3xl mb-4">
                                    A
                                </div>
                                <button class="text-[10px] font-mono font-bold text-brand-600 uppercase tracking-widest hover:text-brand-800 transition-colors">
                                    Cambiar Foto
                                </button>
                            </div>

                            <!-- Campos de Lectura (Read-Only) -->
                            <div class="md:col-span-2 space-y-6">
                                <div>
                                    <label class="block text-[10px] font-bold font-mono text-slate-400 uppercase tracking-widest mb-1">Nombre Completo</label>
                                    <p class="text-slate-900 font-bold text-sm">Admin Demo Inkora</p>
                                </div>
                                
                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                    <div>
                                        <label class="block text-[10px] font-bold font-mono text-slate-400 uppercase tracking-widest mb-1">Email (Acceso)</label>
                                        <p class="text-slate-900 font-mono text-sm">admin@demo.inkora.pe</p>
                                    </div>
                                    <div>
                                        <label class="block text-[10px] font-bold font-mono text-slate-400 uppercase tracking-widest mb-1">Rol Asignado</label>
                                        <span class="inline-flex px-2 py-0.5 bg-brand-100 text-brand-700 font-mono font-bold text-[10px] uppercase tracking-widest">
                                            Admin
                                        </span>
                                    </div>
                                </div>

                                <div class="pt-4 border-t border-slate-100">
                                    <button class="text-xs font-bold font-mono text-slate-500 hover:text-rose-600 uppercase tracking-widest transition-colors flex items-center gap-2">
                                        <i class="ph-bold ph-key"></i> Solicitar cambio de contraseña
                                    </button>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>

            </div>
        </div>
    </main>

    <script>
        // Reloj del sistema
        function updateClock() {
            const now = new Date();
            document.getElementById('sysClock').textContent = 
                `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        }
        setInterval(updateClock, 1000); updateClock();

        // Lógica de Pestañas (Tabs)
        function switchTab(tabId) {
            // Arrays de tabs y contenidos
            const tabs = ['empresa', 'fiscal', 'cuenta'];
            
            tabs.forEach(id => {
                const btn = document.getElementById(`tab-${id}`);
                const content = document.getElementById(`content-${id}`);
                
                if(id === tabId) {
                    // Activar
                    btn.classList.remove('border-transparent', 'text-slate-500', 'hover:text-slate-800');
                    btn.classList.add('border-brand-600', 'text-brand-600');
                    content.classList.remove('hidden');
                    content.classList.add('block');
                } else {
                    // Desactivar
                    btn.classList.add('border-transparent', 'text-slate-500', 'hover:text-slate-800');
                    btn.classList.remove('border-brand-600', 'text-brand-600');
                    content.classList.add('hidden');
                    content.classList.remove('block');
                }
            });
        }
    </script>
</body>
</html>