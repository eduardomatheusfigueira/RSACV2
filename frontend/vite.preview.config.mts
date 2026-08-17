import { resolve } from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({ root: __dirname, plugins:[react()],
  resolve:{alias:{'@':resolve(__dirname,'src')}}, server:{port:5201,strictPort:true} })
