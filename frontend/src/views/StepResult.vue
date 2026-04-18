<template>
  <div class="step-result">
    <el-steps :active="2" finish-status="success" align-center class="steps">
      <el-step title="上传简历" />
      <el-step title="审核建议" />
      <el-step title="下载结果" />
    </el-steps>

    <el-card class="card">
      <template #header>
        <div class="card-header">
          <span>优化后简历预览</span>
          <div class="btn-group">
            <el-button type="success" size="small" @click="downloadMd">下载 Markdown</el-button>
            <el-button type="primary" size="small" :loading="pdfLoading" @click="downloadPdf">下载 PDF</el-button>
            <el-button size="small" @click="restart">重新开始</el-button>
          </div>
        </div>
      </template>

      <!-- markdown rendered preview -->
      <div class="md-preview" v-html="rendered" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { exportResume } from '../api/index.js'
import { useSessionStore } from '../store.js'

const router = useRouter()
const store = useSessionStore()
const pdfLoading = ref(false)

const rendered = computed(() => marked.parse(store.optimizedResume || ''))

function downloadMd() {
  const blob = new Blob([store.optimizedResume], { type: 'text/markdown' })
  triggerDownload(blob, 'resume_optimized.md')
}

async function downloadPdf() {
  pdfLoading.value = true
  try {
    const blob = await exportResume(store.sessionId, 'pdf')
    triggerDownload(blob, 'resume_optimized.pdf')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    pdfLoading.value = false
  }
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function restart() {
  store.$reset()
  router.push('/')
}
</script>

<style scoped>
.step-result { max-width: 860px; margin: 40px auto; padding: 0 16px; }
.steps { margin-bottom: 32px; }
.card { border-radius: 8px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.btn-group { display: flex; gap: 8px; }
.md-preview {
  line-height: 1.7;
  font-size: 14px;
  padding: 8px 0;
}
.md-preview :deep(h1),
.md-preview :deep(h2),
.md-preview :deep(h3) { margin: 16px 0 8px; }
.md-preview :deep(ul) { padding-left: 20px; }
.md-preview :deep(code) { background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }
</style>
