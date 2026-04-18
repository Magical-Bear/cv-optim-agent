import { defineStore } from 'pinia'

export const useSessionStore = defineStore('session', {
  state: () => ({
    sessionId: '',
    matchReport: { score: 0, highlights: [], gaps: [] },
    suggestions: [],
    optimizedResume: '',
  }),
  actions: {
    $reset() {
      this.sessionId = ''
      this.matchReport = { score: 0, highlights: [], gaps: [] }
      this.suggestions = []
      this.optimizedResume = ''
    },
  },
})
