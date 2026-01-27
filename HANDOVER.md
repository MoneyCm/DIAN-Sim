# 🚀 HANDOVER: DIAN Sim - De Casa a Oficina

Este documento contiene todo el contexto necesario para continuar el trabajo en el equipo de la oficina sin perder el progreso técnico.

## 📌 Estado Actual del Proyecto
- **Versión Actual:** v47.3.1 (Escudo Supernova + Manual Import).
- **Último Cambio Crítico:** Se corrigió un `NameError` en la pestaña de Importación JSON.
- **Base de Datos:** Sincronizada con Supabase (Postgres Cloud).

---

## 🛠️ Instrucciones de Sincronización

### 1. En Casa (Antes de salir)
Ejecuta esto en la terminal para asegurar que todo esté en la nube:
```powershell
git add .
git commit -m "Handover: v47.3.1 - Importación JSON y modo GOA refinado"
git push origin main
```

### 2. En la Oficina (Al llegar)
Ejecuta esto para bajar los cambios:
```powershell
git pull origin main
```

---

## 🧩 Herramientas de Continuidad

### Mega-Prompt Maestro para Gemini Web
Si la cuota de la API se agota, usa este prompt en [Gemini Web](https://gemini.google.com/):

> **Actúa como un Experto en Normativa de la DIAN y constructor de ítems para la CNSC.**
> Genera 10 preguntas siguiendo el **Protocolo GOA 2667** (Juicio Situacional).
> - **Caso:** 80-120 palabras con ruido técnico.
> - **Opciones:** EXACTAMENTE 3 (A, B, C).
> - **Formato:** JSON compatible con el simulador.
> (Pega el resto del prompt que guardamos en la conversación).

---

## 📝 Qué decirle a Antigravity en la Oficina
Copia y pega este mensaje al iniciar el chat allá:
> "Antigravity, soy el usuario. Acabo de sincronizar desde casa. Estamos en **v47.3.1**. Ya está lista la pestaña de **Importación JSON**. Por favor, revisa el archivo `task.md` en el 'brain' local para ver los objetivos de la Fase 7 y ayúdame a verificar que la conexión a Supabase esté activa."

---

## 📅 Próximos Pasos
1. **Prueba de Fuego:** Generar preguntas en la oficina vía Gemini Web e importarlas usando el nuevo botón.
2. **Revisión de Banco:** Confirmar que las preguntas guardadas en casa se ven correctamente en la oficina.
3. **Optimización RAG:** Continuar con la integración del Estatuto Tributario completo para el motor de búsqueda.

---
*Generado por Antigravity v47.3.1 - 2026-01-27*
