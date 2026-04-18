import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

http.interceptors.response.use(
  (r) => r.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    return Promise.reject(new Error(msg))
  }
)

export function uploadResume(file) {
  const form = new FormData()
  form.append('file', file)
  return http.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function analyze(payload) {
  // payload: { session_id, resume_text, jd_text }
  return http.post('/analyze', payload)
}

export function confirm(payload) {
  // payload: { session_id, selected_suggestions, edited_suggestions, extra_note }
  return http.post('/confirm', payload)
}

export function exportResume(sessionId, format = 'md') {
  return http.get(`/export/${sessionId}`, {
    params: { format },
    responseType: 'blob',
  })
}
