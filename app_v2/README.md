# KLKCHAN — Frontend Integration Guide v2

> **Para:** — Frontend Developer
> **Stack frontend:** Next.js + TypeScript
> **Hosting frontend:** Vercel
> **Backend:** FastAPI — uvicorn
> **Versión API:** v2 (anónima — sin registro, sin login)

---

## 1. Base URL

| Entorno | URL |
|---|---|
| Local (desarrollo) | `http://localhost:8000/v2` |
| Producción | _Se define cuando el backend esté deployado_ |

```env
# .env.local (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000/v2
NEXT_PUBLIC_HCAPTCHA_SITE_KEY=10000000-ffff-ffff-ffff-000000000001
```

---

## 2. Cómo funciona v2 — El flujo completo

En v2 no hay registro ni login. El flujo es:

```
Usuario quiere postear o comentar
       ↓
Le aparece el widget hCaptcha
       ↓
Completa el captcha → frontend recibe un token
       ↓
Frontend llama a POST /captcha/verify con ese token
       ↓
Backend verifica → setea cookie guest_token (HTTP-only, 1 hora)
       ↓
Usuario puede postear y comentar libremente por 1 hora
       ↓
Cada post/comentario renueva la cookie 1 hora más (sliding window)
```

La cookie es HTTP-only — el browser la maneja automáticamente.
Solo asegúrate de incluir `credentials: "include"` en todos tus fetch de escritura.

---

## 3. Configuración de hCaptcha

**Instalar**
```bash
npm install @hcaptcha/react-hcaptcha
```

**Site key de prueba (no necesita cuenta)**
```
10000000-ffff-ffff-ffff-000000000001
```

Cuando vayan a producción, equipo backend  te pasa la site key real.

**Componente CaptchaGate**
```tsx
// components/CaptchaGate.tsx
import HCaptcha from "@hcaptcha/react-hcaptcha";
import { useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const SITE_KEY = process.env.NEXT_PUBLIC_HCAPTCHA_SITE_KEY || "10000000-ffff-ffff-ffff-000000000001";

interface CaptchaGateProps {
  onVerified: () => void;
}

export default function CaptchaGate({ onVerified }: CaptchaGateProps) {
  const captchaRef = useRef<HCaptcha>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async (token: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/captcha/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // ← CRÍTICO para que el backend setee la cookie
        body: JSON.stringify({ hcaptcha_token: token }),
      });
      if (!res.ok) throw new Error("Captcha inválido");
      onVerified();
    } catch (e) {
      setError("Error verificando captcha. Intenta nuevamente.");
      captchaRef.current?.resetCaptcha();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {loading ? <p>Verificando...</p> : (
        <HCaptcha sitekey={SITE_KEY} onVerify={handleVerify} ref={captchaRef} />
      )}
    </div>
  );
}
```

---

## 4. Helper: fetch para v2

```typescript
// lib/api-v2.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL;

// Requests públicos (GET boards, GET posts, GET comments)
export const publicFetch = (path: string) =>
  fetch(`${API_URL}${path}`);

// Requests que requieren captcha (POST posts, POST comments)
export const anonFetch = async (path: string, options: RequestInit = {}) => {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include", // ← incluye la cookie guest_token automáticamente
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (res.status === 401) throw new Error("CAPTCHA_REQUIRED");
  return res;
};
```

---

## 5. Endpoints disponibles

**Captcha**

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/captcha/verify` | — | Verificar hCaptcha → obtener guest token en cookie |

**Boards (público)**

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/boards` | — | Listar todos los boards |
| GET | `/boards/{id}` | — | Obtener un board |

**Posts**

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/posts` | — | Listar posts (filtrar con `?board_id=1`) |
| GET | `/posts/{id}` | — | Obtener un post |
| POST | `/posts` |  guest token | Crear un post |

**Comments**

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/comments/{post_id}` | — | Obtener comentarios de un post |
| POST | `/comments` | guest token | Crear un comentario o reply |

---

## 6. Ejemplos de uso

**Listar boards**
```typescript
const getBoards = async () => {
  const res = await publicFetch("/boards");
  return res.json();
  // { items: [{ id, name, description, post_count }], total }
};
```

**Listar posts de un board**
```typescript
const getPosts = async (boardId: number) => {
  const res = await publicFetch(`/posts?board_id=${boardId}`);
  return res.json();
  // { items: [{ id, title, body, board_id, created_at, votes, image, anon_id, comment_count }], total }
};
```

**Obtener comentarios**
```typescript
const getComments = async (postId: number) => {
  const res = await publicFetch(`/comments/${postId}`);
  return res.json();
  // [{ id, body, post_id, created_at, votes, anon_id, replies: [...] }]
};
```

**Crear un post (requiere captcha)**
```typescript
const createPost = async (data: {
  title: string;
  body: string;
  board_id: number;
  image?: string; // base64
}) => {
  const res = await anonFetch("/posts", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};
```

**Crear un comentario (requiere captcha)**
```typescript
const createComment = async (data: {
  body: string;
  post_id: number;
  parent_comment_id?: number; // para replies
}) => {
  const res = await anonFetch("/comments", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};
```

---

## 7. Componente NewPost — ejemplo completo

```tsx
// components/NewPost.tsx
import { useState } from "react";
import CaptchaGate from "./CaptchaGate";
import { anonFetch } from "@/lib/api-v2";

export default function NewPost({ boardId }: { boardId: number }) {
  const [captchaVerified, setCaptchaVerified] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await anonFetch("/posts", {
        method: "POST",
        body: JSON.stringify({ title, body, board_id: boardId }),
      });
      const post = await res.json();
      console.log("Post creado:", post);
    } catch (e: any) {
      if (e.message === "CAPTCHA_REQUIRED") {
        setCaptchaVerified(false); // mostrar captcha de nuevo
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (!captchaVerified) {
    return (
      <div>
        <p>Completa el captcha para poder postear</p>
        <CaptchaGate onVerified={() => setCaptchaVerified(true)} />
      </div>
    );
  }

  return (
    <div>
      <input placeholder="Título" value={title} onChange={(e) => setTitle(e.target.value)} />
      <textarea placeholder="Contenido" value={body} onChange={(e) => setBody(e.target.value)} />
      <button onClick={handleSubmit} disabled={submitting}>
        {submitting ? "Publicando..." : "Publicar"}
      </button>
    </div>
  );
}
```

---

## 8. El campo `anon_id`

Cada post y comentario tiene `anon_id` con formato `Anon-xxxx` (ej: `Anon-3f2a`).

- Consistente por sesión del usuario
- No rastreable entre sesiones
- Muéstralo en la UI como identificador del autor estilo 4chan

---

## 9. Códigos de error

| Código | Significado | Qué hacer |
|---|---|---|
| `400` | Captcha inválido | Mostrar error, resetear widget |
| `401` | Guest token expirado | Mostrar captcha de nuevo |
| `404` | Board o post no encontrado | Página de error |
| `422` | Campos inválidos | Mostrar errores de validación |
| `429` | Rate limit | Mostrar mensaje de espera |

---

## 10. CORS

El backend ya permite estos orígenes sin configuración adicional:

```
http://localhost:3000
http://localhost:5173
```

Cuando hagas deploy en Vercel, pásale tu dominio a Melvin.

 `credentials: "include"` es obligatorio en todos los requests POST.
Sin esto el browser no envía la cookie y el backend responde 401.

---


