import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()], server: {proxy:{"/api":"http://127.0.0.1:8000"}}, preview: {proxy:{"/api":"http://127.0.0.1:8000"}}, build: { rollupOptions: { output: { manualChunks(id) { if(id.includes('src/data/products.json')) return 'product-data'; if(id.includes('node_modules/react')||id.includes('node_modules/scheduler')) return 'react-vendor'; } } } } });
