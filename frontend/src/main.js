import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElIcons from '@element-plus/icons-vue'
import { createPinia } from 'pinia'
import router from './router/index.js'
import App from './App.vue'

const app = createApp(App)

Object.entries(ElIcons).forEach(([name, comp]) => app.component(name, comp))

app.use(ElementPlus)
app.use(createPinia())
app.use(router)
app.mount('#app')
