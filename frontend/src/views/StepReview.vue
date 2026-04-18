<template>
  <div class="step-review">
    <el-steps :active="1" finish-status="success" align-center class="steps">
      <el-step title="上传简历" />
      <el-step title="审核建议" />
      <el-step title="下载结果" />
    </el-steps>

    <!-- Match Report -->
    <el-card class="card">
      <template #header>匹配报告</template>
      <div class="score-row">
        <el-progress
          type="circle"
          :percentage="store.matchReport.score"
          :color="scoreColor"
          :width="90"
        />
        <div class="score-meta">
          <p><strong>匹配度:</strong> {{ store.matchReport.score }} / 100</p>
        </div>
      </div>

      <el-row :gutter="16" class="report-lists">
        <el-col :span="12">
          <p class="list-title success-text">✔ 优势匹配</p>
          <ul>
            <li v-for="h in store.matchReport.highlights" :key="h">{{ h }}</li>
          </ul>
        </el-col>
        <el-col :span="12">
          <p class="list-title danger-text">✘ 缺失技能</p>
          <ul>
            <li v-for="g in store.matchReport.gaps" :key="g">{{ g }}</li>
          </ul>
        </el-col>
      </el-row>
    </el-card>

    <!-- Suggestions -->
    <el-card class="card">
      <template #header>优化建议 (勾选 + 可编辑)</template>

      <el-card
        v-for="s in store.suggestions"
        :key="s.id"
        class="suggestion-card"
        shadow="never"
      >
        <div class="sug-header">
          <el-checkbox v-model="selected[s.id]">
            <el-tag :type="priorityType(s.priority)" size="small">{{ s.priority }}</el-tag>
            &nbsp;{{ s.id }}
          </el-checkbox>
        </div>
        <div class="sug-body">
          <p class="label">原文:</p>
          <p class="original">{{ s.original_text }}</p>
          <p class="label">建议改为:</p>
          <el-input
            v-model="edited[s.id]"
            type="textarea"
            :rows="3"
            :disabled="!selected[s.id]"
          />
        </div>
      </el-card>

      <el-form-item label="额外说明 (可选)" class="extra-note">
        <el-input v-model="extraNote" type="textarea" :rows="2" placeholder="可补充给AI的改写要求..." />
      </el-form-item>

      <el-button
        type="primary"
        :loading="confirming"
        :disabled="!hasSelected"
        @click="submit"
      >
        确认并生成优化简历
      </el-button>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { confirm } from '../api/index.js'
import { useSessionStore } from '../store.js'

const router = useRouter()
const store = useSessionStore()

const selected = reactive({})
const edited = reactive({})
const extraNote = ref('')
const confirming = ref(false)

// init edited text from suggestions
store.suggestions.forEach((s) => {
  selected[s.id] = false
  edited[s.id] = s.suggested_text
})

const hasSelected = computed(() => Object.values(selected).some(Boolean))

const scoreColor = computed(() => {
  const s = store.matchReport.score
  if (s >= 75) return '#67c23a'
  if (s >= 50) return '#e6a23c'
  return '#f56c6c'
})

function priorityType(p) {
  return { high: 'danger', mid: 'warning', low: 'info' }[p] ?? 'info'
}

async function submit() {
  confirming.value = true
  try {
    const selectedIds = Object.keys(selected).filter((id) => selected[id])
    const editedList = selectedIds
      .filter((id) => {
        const orig = store.suggestions.find((s) => s.id === id)?.suggested_text
        return edited[id] !== orig
      })
      .map((id) => ({ id, suggested_text: edited[id] }))

    const res = await confirm({
      session_id: store.sessionId,
      selected_suggestions: selectedIds,
      edited_suggestions: editedList,
      extra_note: extraNote.value,
    })
    store.optimizedResume = res.optimized_resume
    router.push('/result')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    confirming.value = false
  }
}
</script>

<style scoped>
.step-review { max-width: 860px; margin: 40px auto; padding: 0 16px; }
.steps { margin-bottom: 32px; }
.card { margin-bottom: 20px; border-radius: 8px; }
.score-row { display: flex; align-items: center; gap: 24px; margin-bottom: 16px; }
.report-lists { margin-top: 12px; }
.list-title { font-weight: bold; margin-bottom: 6px; }
.success-text { color: #67c23a; }
.danger-text { color: #f56c6c; }
.suggestion-card { margin-bottom: 12px; }
.sug-header { margin-bottom: 8px; }
.sug-body .label { font-size: 12px; color: #909399; margin: 4px 0 2px; }
.sug-body .original { background: #f5f5f5; padding: 6px 8px; border-radius: 4px; font-size: 13px; }
.extra-note { margin-top: 20px; }
</style>
