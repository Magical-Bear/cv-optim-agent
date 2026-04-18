import { createRouter, createWebHistory } from 'vue-router'
import StepUpload from '../views/StepUpload.vue'
import StepReview from '../views/StepReview.vue'
import StepResult from '../views/StepResult.vue'

const routes = [
  { path: '/', component: StepUpload },
  { path: '/review', component: StepReview },
  { path: '/result', component: StepResult },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
