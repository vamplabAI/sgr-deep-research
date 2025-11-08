import './assets/styles/normalize.css'
import './assets/styles/main.scss'
import './assets/styles/highlight.css'
import './assets/styles/default.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
