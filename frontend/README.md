# Frontend de SNIFF

La instalación completa está en [README principal](../README.md).

- Node.js 22.18+ (rama 22) o 24.11+ (rama 24), con npm.
- Instalar con npm ci.
- Desarrollo: npm run dev; usa la API local si no se configura otra.
- Ajustar VITE_API_BASE_URL según .env.example; para producción puede usarse
  /api/ detrás de un proxy del mismo origen.
- Compilar: npm run build. Cambiar la URL exige volver a compilar.
- Publicar dist con fallback SPA; separar /api/, /admin/ y /static/.
- Pruebas: npm test.
- No incluir secretos en variables VITE_* ni usar vite preview como servidor
  institucional.
