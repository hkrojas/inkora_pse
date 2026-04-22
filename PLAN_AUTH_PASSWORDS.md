# Plan de Autenticación y Gestión de Contraseñas

Diseño del flujo de identidad para PrintFlow: creación de usuarios, login, cambio/recuperación de contraseña, sesiones, y gaps que debemos cerrar antes del launch.

Contexto:
- No tenemos infraestructura de correo (no SMTP, no Resend, no SendGrid).
- El canal de comunicación con el cliente es WhatsApp.
- Roles: `vendedor` → `operador` → `admin` → `superadmin`.
- Modelo actual: [backend/models/tenants.py](backend/models/tenants.py) `User` tiene `email`, `hashed_password`, `is_active`, `last_login_at`. **No tiene** `must_change_password`, `password_changed_at`, ni contador de intentos fallidos.

---

## 1. Principios no negociables

1. **El superadmin nunca ve contraseñas en texto plano.** Ni en UI, ni en logs, ni en DB, ni en respuestas repetidas.
2. **Contraseñas se muestran una sola vez** (en la respuesta HTTP de creación/reset). Si el superadmin la pierde, debe resetearla otra vez.
3. **Hash con bcrypt/argon2** en DB (`hashed_password`). Nunca almacenar el plano ni derivados reversibles.
4. **HTTPS obligatorio en producción** (ya configurado en Render/Railway, verificar).
5. **Nada de contraseñas en logs, audit_logs, ni mensajes de error.**

---

## 2. Estado actual (gap analysis)

Lo que ya funciona:
- Login con JWT (`/token` en [backend/routers/auth.py](backend/routers/auth.py)).
- Superadmin puede crear tenants y usuarios iniciales ([backend/routers/superadmin.py](backend/routers/superadmin.py)).
- Superadmin puede resetear password de cualquier usuario (`resetUserPassword` en [frontend/src/services/superadmin.js](frontend/src/services/superadmin.js#L17)).
- Hashing en [backend/security.py](backend/security.py) (verificar algoritmo).

Lo que falta:
- [ ] Flag `must_change_password` en `User`.
- [ ] Campo `password_changed_at` en `User` (para políticas futuras de expiración).
- [ ] Endpoint `POST /users/me/change-password` (usuario logueado cambia su propia password, conociendo la actual).
- [ ] Endpoint de "olvidé mi contraseña" vía admin del tenant (no superadmin).
- [ ] UI de "Cambiar contraseña" dentro del perfil del usuario.
- [ ] UI que fuerce cambio en primer login si `must_change_password=true`.
- [ ] Política de fortaleza de contraseña (mínimo 10 chars, al menos una letra y un número).
- [ ] Rate limiting en `/token` (mitigar brute force).
- [ ] Auditoría de eventos sensibles: creación de usuario, reset de password, cambio de password, login fallido 5x.
- [ ] Confirmar que la response de `resetUserPassword` devuelve la nueva password en plano **una sola vez** y no la guarda en ningún lado.

---

## 3. Modelo de roles y quién puede hacer qué

| Acción | vendedor/operador | admin (del tenant) | superadmin |
|---|---|---|---|
| Crear usuarios en su tenant | ❌ | ✅ (vendedor/operador/admin) | ✅ (cualquier rol) |
| Resetear password de otro usuario del mismo tenant | ❌ | ✅ (solo a los que creó o de rol ≤ al suyo) | ✅ (cualquiera) |
| Cambiar su propia password | ✅ | ✅ | ✅ |
| Ver hash o password plano de otro | ❌ | ❌ | ❌ |
| Desactivar usuarios del tenant | ❌ | ✅ | ✅ |
| Crear tenants | ❌ | ❌ | ✅ |

**Regla crítica**: un admin de tenant puede resetear solo usuarios **de su mismo tenant**. Enforcement en backend (no confiar en frontend).

---

## 4. Ciclo de vida del usuario

### 4.1 Bootstrap (primer superadmin)
- Se crea vía variable de entorno + script de bootstrap en primer deploy.
- **No** debe ser creable por API pública.
- Actualmente: `INTERNAL_PROVISIONING_TOKEN` protege `/register` — verificar que no permita crear superadmins desde ese endpoint.

### 4.2 Creación de tenant + admin inicial (lo hace el superadmin)
Flujo:
1. Superadmin registra tenant (RUC, razón social, etc).
2. Crea el admin del tenant: indica email + nombre. **No escribe la password**.
3. Backend genera una password temporal aleatoria (12 chars, letras+números, sin ambigüedades tipo `0/O`, `1/l`).
4. Backend guarda `hashed_password`, setea `must_change_password=true`.
5. Response HTTP devuelve `{ email, temporary_password }` **una sola vez**.
6. Frontend muestra un modal: "Copia estas credenciales, envíalas por WhatsApp. No se mostrarán de nuevo."
7. Superadmin envía al cliente por WhatsApp. Link de comunicación ya existe en [backend/services/comunicacion_service.py](backend/services/comunicacion_service.py).

### 4.3 Creación de usuarios adicionales (lo hace el admin del tenant)
Mismo flujo que 4.2, pero:
- El admin del tenant solo puede crear roles ≤ `admin` en **su propio** tenant.
- La password temporal la ve el admin del tenant (no el superadmin), y la pasa al usuario final por el canal que prefiera.

### 4.4 Primer login (forzado)
1. Usuario entra con email + password temporal.
2. Backend valida, ve `must_change_password=true`, devuelve token **con flag especial** (o claim `requires_password_change`).
3. Frontend detecta el claim, redirige a `/first-login-change-password`. **Bloquea navegación a cualquier otra pantalla** hasta que cambie.
4. Usuario ingresa password nueva (2x, con confirmación).
5. Backend valida política de fortaleza, actualiza hash, setea `must_change_password=false`, actualiza `password_changed_at=now()`.
6. Devuelve token nuevo sin el flag. Usuario entra normal.

### 4.5 Cambio voluntario (usuario logueado)
- Formulario en perfil: "contraseña actual", "nueva", "confirmar nueva".
- Backend valida actual (esto confirma identidad — no se necesita correo).
- Aplica política, actualiza hash.
- Audita evento: `user.password_changed`.
- Se aconseja (no obliga) invalidar otras sesiones — ver §6.

### 4.6 Recuperación (olvidó la contraseña)

**Sin correo, tres caminos según quién olvida:**

| Caso | Quién resetea | Cómo se entrega la nueva |
|---|---|---|
| Vendedor/operador olvida | Admin de su tenant | Admin le dice la temporal en persona/WhatsApp |
| Admin del tenant olvida | Superadmin (tú) | Tú le mandas la temporal por WhatsApp |
| Superadmin olvida | Acceso directo a DB (script) | N/A — riesgo aceptado mientras seas 1 persona |

Cada reset:
- Genera password temporal (mismo algoritmo que 4.2).
- Setea `must_change_password=true`.
- Invalida sesiones activas del usuario (ver §6).
- Audita evento.

**A futuro (post-launch, cuando tengamos volumen):**
- Agregar SMTP (Resend tiene free tier 3k emails/mes) → self-service "olvidé contraseña" clásico con token firmado de 15 min.
- O canal WhatsApp Business API (pagado, pero el cliente ya lo usa para todo).

### 4.7 Desactivación / offboarding
- Admin/superadmin puede setear `is_active=false`. Ya existe (`toggleUserActive`).
- Además: invalidar sesiones activas del usuario desactivado inmediatamente.
- El usuario queda en DB (no se borra, para preservar referencias en cotizaciones, audit_logs).

---

## 5. Política de contraseña

**Mínimo aceptable para launch:**
- Longitud ≥ 10 caracteres.
- Al menos 1 letra y 1 número.
- No igual al email.
- No permitir passwords en top-100 comunes (lista embedded, ~1KB).

**No hacer al inicio** (over-engineering):
- Obligar mayúsculas/minúsculas/símbolos (genera frustración, no aporta mucho vs. longitud).
- Rotación forzada cada X días (discontinuada por NIST 800-63B).
- Historial de últimas 5 passwords.

---

## 6. Sesiones y JWT

Estado actual:
- JWT firmado con `SECRET_KEY`. Expiración — revisar valor.

Mejoras necesarias:
- [ ] Confirmar expiración razonable (propuesta: 12 horas para web).
- [ ] Endpoint `POST /logout` que invalide el token del lado servidor (lista de tokens revocados en Redis/DB, o rotar `password_changed_at` y validar ese campo en cada request).
- [ ] Al cambiar password o resetear: invalidar todos los tokens previos del usuario (comparar `iat` del JWT contra `password_changed_at`).
- [ ] No usar "remember me" infinito.

**Decisión pendiente**: ¿implementar refresh tokens? Para launch probablemente no — un JWT de 12h y re-login diario es suficiente.

---

## 7. Rate limiting y brute force

- [ ] Limitar `/token` a 5 intentos por email por 15 min.
- [ ] Limitar `/token` a 20 intentos por IP por 15 min.
- [ ] Al fallar 5x en 15 min: bloquear login del email por 15 min más (soft lock).
- [ ] Auditar intentos fallidos.
- No bloquear cuentas permanentemente por intentos fallidos (genera DoS al usuario real).

Librería sugerida: `slowapi` (wrapper de `limits` para FastAPI).

---

## 8. Auditoría

Eventos que deben aparecer en `audit_logs`:
- `user.created` (quién creó a quién)
- `user.password_reset` (por quién) — **sin guardar la password**
- `user.password_changed` (self-service)
- `user.login.success`
- `user.login.failed` (con email intentado + IP, sin password)
- `user.deactivated` / `user.reactivated`
- `user.role_changed`
- `superadmin.*` — cualquier acción con privilegios elevados

Ya existe modelo `AuditLog` — solo falta poblarlo desde los handlers relevantes.

---

## 9. Otras cosas que estábamos olvidando

Revisando el modelo actual encontré estos gaps adicionales:

- **Registro público de tenants**: hoy no existe (solo el superadmin crea tenants). Confirmar si queremos que sea así para launch, o si abriremos signup con tarjeta. → **Decisión**: quedarse con onboarding manual por ahora. Menor fricción para el superadmin, filtra a clientes serios.
- **Invitaciones por link**: alternativa a enviar password temporal por WhatsApp — generar un link con token firmado (TTL 7 días) donde el usuario mismo crea su password. Elimina el problema de "el admin vio la password temporal del vendedor". Ver §11.
- **Cambio de email del usuario**: hoy no hay endpoint. Si un usuario cambia de correo, debe pedirlo al admin. Aceptable para launch.
- **Dos usuarios con el mismo email**: la unique constraint está por email globalmente (no por tenant). Esto significa que el mismo email no puede estar en dos tenants. Confirmar si es la intención — probablemente sí, porque el login es por email.
- **Superadmin se impersona a un tenant**: útil para soporte. No existe hoy. Si se agrega, debe auditarse cada entrada y no debería permitir ejecutar operaciones fiscales (emitir facturas) como otro usuario.
- **Eliminación de usuarios**: `deleteUser` existe. Verificar que no borra físicamente (debería soft-delete para no romper FKs de `cotizaciones.usuario_id`, `audit_logs.user_id`).
- **Tokens ApísPeru en logs**: revisar que `apisperu_token` no se loguee al hacer debug de SUNAT. Es una credencial de terceros igual de sensible.
- **Almacenamiento de `sunat_clave_sol` y `sunat_cert_password`** en `Tenant`: actualmente son `String` planos. Si se usan en el flujo GRE, cifrar en DB con clave derivada de `SECRET_KEY` o mover a Supabase Vault.

---

## 10. Plan de implementación por fases

### Fase 0 — Auditoría de lo existente (1 día)
- Leer [backend/security.py](backend/security.py) y confirmar algoritmo de hash.
- Confirmar qué devuelve `resetUserPassword` hoy — si devuelve la password o no.
- Confirmar expiración del JWT en [backend/security.py](backend/security.py) o donde esté configurado.
- Documentar findings acá mismo.

### Fase 1 — Higiene básica (imprescindible para launch)
1. Migration: agregar `must_change_password: bool`, `password_changed_at: datetime` al `User`.
2. Endpoint `POST /users/me/change-password` (user logueado).
3. Endpoint superadmin `POST /superadmin/users/{id}/reset-password` — devolver temporary password en response **una vez**. Confirmar que ya existe así; si no, cambiarlo.
4. Backend: al crear usuario, generar password temporal random y setear `must_change_password=true`.
5. Frontend: modal de creación muestra la temporal 1 vez, con botón "copiar". Al cerrar, desaparece.
6. Frontend: detectar `must_change_password` en perfil al cargar la app, forzar redirect a change-password.
7. Política de fortaleza mínima (longitud + letra + número).
8. Sacar cualquier UI que muestre passwords existentes (audit del frontend).

### Fase 2 — Seguridad operativa (primer mes post-launch)
9. Rate limiting en `/token`.
10. Audit logs completos de eventos de auth.
11. Invalidación de sesiones al cambiar password (comparar `iat` vs `password_changed_at`).
12. Admin de tenant puede resetear passwords de su propio tenant (endpoint nuevo + UI).

### Fase 3 — Cuando tengamos volumen (3-6 meses)
13. SMTP para "olvidé mi contraseña" con token firmado.
14. Invitaciones por link (evita que nadie vea la password del otro).
15. 2FA opcional para superadmin y admins de tenant.

### Fase 4 — Escala (cuando lleguemos a ~200 tenants)
16. Cifrado en reposo de credenciales SUNAT (Supabase Vault o KMS).
17. Impersonación auditada para soporte.
18. Opcional: SSO con Google Workspace para tenants empresariales.

---

## 11. Decisiones abiertas (necesito input)

1. **Longitud password temporal**: ¿12 chars alfanuméricos es ok? (Lo suficientemente fácil de leer por WhatsApp, suficientemente fuerte si solo dura hasta el primer login.)
2. **Expiración del JWT**: ¿12h, 24h, 8h? → Recomiendo **12h**.
3. **Invitaciones por link vs. password temporal**: el link es más seguro (nadie ve la password intermedia), pero requiere UI pública sin auth. ¿Lo hacemos en Fase 1 o Fase 3?
4. **Rate limiting**: ¿bloqueamos por email+IP o solo por email? → Recomiendo **ambos** (IP ataca varias cuentas, email ataca una cuenta desde varias IPs).
5. **Primer superadmin (tú)**: ¿cómo recuperas tu propia password si la olvidas? → Aceptemos que es manual vía DB mientras seas la única persona. Documentar el procedimiento.

---

## 12. Checklist de seguridad pre-launch

- [ ] Ningún endpoint devuelve `hashed_password`.
- [ ] Ningún log contiene passwords, tokens JWT completos, ni tokens ApísPeru.
- [ ] `SECRET_KEY` en producción es ≥ 64 chars aleatorios y no está en git.
- [ ] `INTERNAL_PROVISIONING_TOKEN` está solo en servidor, nunca en frontend.
- [ ] CORS restringido al dominio del frontend en producción.
- [ ] HTTPS obligatorio (redirect 301 de http→https en Render/Railway).
- [ ] `is_superadmin=true` nunca se puede setear vía API pública.
- [ ] Response de creación/reset de usuario devuelve temporary password **solo una vez**.
- [ ] Hay al menos un test de integración que verifique: crear usuario → primer login → forzar cambio → login con nueva.

---

**Fecha de creación**: 2026-04-21
**Responsable**: superadmin (Kennedy)
**Estado**: borrador para revisión
