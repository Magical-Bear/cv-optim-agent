<template>
  <div class="step-upload">
    <el-steps :active="0" finish-status="success" align-center class="steps">
      <el-step title="上传简历" />
      <el-step title="审核建议" />
      <el-step title="下载结果" />
    </el-steps>

    <el-card class="card">
      <template #header>简历 + JD 输入</template>

      <el-form label-position="top" @submit.prevent>
        <!-- Resume input -->
        <el-form-item label="简历内容">
          <el-upload
            class="upload-btn"
            :before-upload="handleFile"
            :show-file-list="false"
            accept=".pdf,.docx"
          >
            <el-button :loading="uploading" size="small" type="primary" plain>
              上传 PDF / Word
            </el-button>
          </el-upload>
          <el-input
            v-model="resumeText"
            type="textarea"
            :rows="10"
            placeholder="或直接粘贴简历文本..."
            class="textarea"
          />
        </el-form-item>

        <!-- JD input -->
        <el-form-item label="职位描述 (JD)">
          <el-input
            v-model="jdText"
            type="textarea"
            :rows="8"
            placeholder="粘贴职位描述..."
            class="textarea"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="analyzing"
            :disabled="!resumeText.trim() || !jdText.trim()"
            @click="submit"
          >
            开始分析
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { uploadResume, analyze } from '../api/index.js'
import { useSessionStore } from '../store.js'

const router = useRouter()
const store = useSessionStore()

const resumeText = ref('')
const jdText = ref('')
const uploading = ref(false)
const analyzing = ref(false)

async function handleFile(file) {
  uploading.value = true
  try {
    const res = await uploadResume(file)
    store.sessionId = res.session_id
    resumeText.value = res.text
    ElMessage.success('文件解析成功')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    uploading.value = false
  }
  return false // prevent default upload
}

async function submit() {
  analyzing.value = true
  try {
    const payload = {
      session_id: store.sessionId || undefined,
      resume_text: resumeText.value,
      jd_text: jdText.value,
    }
    const res = await analyze(payload)
    store.sessionId = res.session_id || store.sessionId
    store.matchReport = res.match_report
    store.suggestions = res.suggestions
    router.push('/review')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    analyzing.value = false
  }
}
</script>

<style scoped>
.step-upload { max-width: 800px; margin: 40px auto; padding: 0 16px; }
.steps { margin-bottom: 32px; }
.card { border-radius: 8px; }
.upload-btn { margin-bottom: 8px; }
.textarea { margin-top: 4px; }
</style>
