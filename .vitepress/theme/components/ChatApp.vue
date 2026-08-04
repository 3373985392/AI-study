<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { ApiError, getSession, logoutSession, redeemInvite, streamReply } from '../chat/api'
import { renderMarkdown } from '../chat/markdown'
import { clearHistory, loadHistory, prepareHistory, saveHistory } from '../chat/storage'
import type { AuthState, ChatMessage, ChatMode } from '../chat/types'


// 认证状态模块：页面加载前不展示邀请码表单，避免会话检查时闪烁。
const loadingSession = ref(true)
const auth = ref<AuthState>({ authenticated: false })
const inviteCode = ref('')
const showInvite = ref(false)
const authBusy = ref(false)
const authError = ref('')

// 聊天状态模块：历史按 viewerId 隔离，并始终限制为最近十轮。
const messages = ref<ChatMessage[]>([])
const input = ref('')
const mode = ref<ChatMode>('chat')
const generating = ref(false)
const chatError = ref('')
const messageList = ref<HTMLElement | null>(null)
let controller: AbortController | null = null

const viewerId = computed(() => auth.value.viewerId || '')
const canSend = computed(() => input.value.trim().length > 0 && !generating.value)

function hydrateSession(state: AuthState): void {
  auth.value = state
  messages.value = state.authenticated && state.viewerId
    ? loadHistory(state.viewerId)
    : []
}

function formatError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429 && error.retryAfter) {
      return `${error.message}（约 ${error.retryAfter} 秒后可重试）`
    }
    return error.message
  }
  return '网络连接失败，请稍后重试'
}

async function scrollToBottom(): Promise<void> {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

async function submitInvite(): Promise<void> {
  if (!inviteCode.value || authBusy.value) return
  authBusy.value = true
  authError.value = ''
  try {
    const state = await redeemInvite(inviteCode.value)
    inviteCode.value = ''
    hydrateSession(state)
  } catch (error) {
    authError.value = formatError(error)
  } finally {
    authBusy.value = false
  }
}

async function sendMessage(): Promise<void> {
  const question = input.value.trim()
  if (!question || generating.value || !viewerId.value) return

  const previousHistory = prepareHistory(messages.value)
  const userMessage: ChatMessage = { role: 'user', content: question }
  const assistantMessage: ChatMessage = { role: 'assistant', content: '' }
  messages.value.push(userMessage, assistantMessage)
  const assistantIndex = messages.value.length - 1
  input.value = ''
  chatError.value = ''
  generating.value = true
  controller = new AbortController()
  await scrollToBottom()

  try {
    await streamReply({
      message: question,
      history: previousHistory,
      mode: mode.value,
      signal: controller.signal,
      onToken(text) {
        // 通过 Vue 的响应式数组写入，确保流式 token 立即刷新到页面。
        messages.value[assistantIndex].content += text
        void scrollToBottom()
      },
    })
    messages.value = messages.value.slice(-20)
    saveHistory(viewerId.value, messages.value)
    if (auth.value.limits) {
      auth.value.limits.minuteRemaining = Math.max(0, auth.value.limits.minuteRemaining - 1)
      auth.value.limits.dayRemaining = Math.max(0, auth.value.limits.dayRemaining - 1)
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      if (messages.value[assistantIndex]?.content) {
        messages.value = messages.value.slice(-20)
        saveHistory(viewerId.value, messages.value)
      } else {
        messages.value.splice(-2, 2)
        input.value = question
      }
      chatError.value = '已停止生成'
    } else {
      messages.value.splice(-2, 2)
      input.value = question
      chatError.value = formatError(error)
      if (error instanceof ApiError && error.status === 401) {
        auth.value = { authenticated: false }
      }
    }
  } finally {
    generating.value = false
    controller = null
  }
}

function stopGeneration(): void {
  controller?.abort()
}

function clearMessages(): void {
  if (!viewerId.value) return
  messages.value = []
  clearHistory(viewerId.value)
  chatError.value = ''
}

async function logout(): Promise<void> {
  if (generating.value) stopGeneration()
  const currentViewer = viewerId.value
  try {
    await logoutSession()
  } finally {
    if (currentViewer) clearHistory(currentViewer)
    auth.value = { authenticated: false }
    messages.value = []
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void sendMessage()
  }
}

onMounted(async () => {
  try {
    hydrateSession(await getSession())
  } catch (error) {
    authError.value = formatError(error)
  } finally {
    loadingSession.value = false
  }
})
</script>

<template>
  <section class="chat-shell" aria-label="AI Chat">
    <div v-if="loadingSession" class="state-card" role="status">正在检查访问权限…</div>

    <form v-else-if="!auth.authenticated" class="invite-card" @submit.prevent="submitInvite">
      <div class="invite-mark" aria-hidden="true">✦</div>
      <h1>进入 AI Chat</h1>
      <p>此功能仅对受邀用户开放。邀请码只发送到服务器验证，不会保存在浏览器。</p>
      <label for="invite-code">邀请码</label>
      <div class="invite-input-row">
        <input
          id="invite-code"
          v-model="inviteCode"
          :type="showInvite ? 'text' : 'password'"
          autocomplete="off"
          minlength="16"
          maxlength="64"
          placeholder="请输入邀请码"
          required
        >
        <button type="button" class="quiet-button" @click="showInvite = !showInvite">
          {{ showInvite ? '隐藏' : '显示' }}
        </button>
      </div>
      <p v-if="authError" class="error-text" role="alert">{{ authError }}</p>
      <button class="primary-button" type="submit" :disabled="authBusy || !inviteCode">
        {{ authBusy ? '验证中…' : '验证并进入' }}
      </button>
    </form>

    <div v-else class="chat-card">
      <header class="chat-header">
        <div>
          <h1>AI Chat</h1>
          <p v-if="auth.limits">
            今日剩余 {{ auth.limits.dayRemaining }} 次 · 本分钟 {{ auth.limits.minuteRemaining }} 次
          </p>
        </div>
        <div class="header-actions">
          <button class="quiet-button" type="button" @click="clearMessages">清空</button>
          <button class="quiet-button" type="button" @click="logout">退出</button>
        </div>
      </header>

      <div class="mode-switch" aria-label="聊天模式">
        <button :class="{ active: mode === 'chat' }" type="button" @click="mode = 'chat'">普通聊天</button>
        <button :class="{ active: mode === 'rag' }" type="button" @click="mode = 'rag'">知识库 RAG</button>
      </div>

      <div ref="messageList" class="message-list" aria-live="polite">
        <div v-if="messages.length === 0" class="empty-state">
          <strong>{{ mode === 'rag' ? '向本地知识库提问' : '开始一段新对话' }}</strong>
          <span>{{ mode === 'rag' ? '回答会引用检索到的 Vue 学习资料。' : '支持 Markdown 与多轮上下文。' }}</span>
        </div>
        <article
          v-for="(message, index) in messages"
          :key="index"
          class="message"
          :class="message.role"
        >
          <span class="message-label">{{ message.role === 'user' ? '你' : 'AI' }}</span>
          <div
            v-if="message.role === 'assistant'"
            class="message-content markdown-body"
            v-html="renderMarkdown(message.content || '…')"
          />
          <div v-else class="message-content">{{ message.content }}</div>
        </article>
      </div>

      <p v-if="chatError" class="error-text chat-error" role="status">{{ chatError }}</p>
      <div class="composer">
        <textarea
          v-model="input"
          maxlength="4000"
          rows="3"
          :disabled="generating"
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          @keydown="handleKeydown"
        />
        <button v-if="generating" class="stop-button" type="button" @click="stopGeneration">停止</button>
        <button v-else class="primary-button send-button" type="button" :disabled="!canSend" @click="sendMessage">发送</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.chat-shell { max-width: 920px; min-height: 620px; margin: 0 auto; padding: 28px 0; }
.state-card, .invite-card, .chat-card { border: 1px solid var(--vp-c-divider); border-radius: 18px; background: var(--vp-c-bg-soft); box-shadow: 0 18px 50px rgba(0, 0, 0, .08); }
.state-card { padding: 80px 24px; text-align: center; color: var(--vp-c-text-2); }
.invite-card { max-width: 460px; margin: 70px auto; padding: 38px; }
.invite-mark { color: var(--vp-c-brand-1); font-size: 34px; }
.invite-card h1, .chat-header h1 { margin: 8px 0; border: 0; font-size: 26px; }
.invite-card p { color: var(--vp-c-text-2); line-height: 1.7; }
.invite-card label { display: block; margin: 24px 0 8px; font-weight: 600; }
.invite-input-row { display: flex; gap: 8px; }
input, textarea { width: 100%; border: 1px solid var(--vp-c-divider); border-radius: 10px; background: var(--vp-c-bg); color: var(--vp-c-text-1); font: inherit; }
input { min-width: 0; padding: 11px 13px; }
textarea { resize: vertical; min-height: 78px; padding: 12px 14px; line-height: 1.6; }
input:focus, textarea:focus { outline: 2px solid var(--vp-c-brand-soft); border-color: var(--vp-c-brand-1); }
button { border: 0; border-radius: 9px; padding: 9px 14px; font-weight: 600; cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: .55; }
.primary-button { width: 100%; margin-top: 16px; background: var(--vp-c-brand-1); color: white; }
.quiet-button { white-space: nowrap; background: var(--vp-c-bg-alt); color: var(--vp-c-text-2); }
.error-text { margin: 12px 0 0 !important; color: var(--vp-c-danger-1) !important; font-size: 14px; }
.chat-card { overflow: hidden; background: var(--vp-c-bg); }
.chat-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 22px; border-bottom: 1px solid var(--vp-c-divider); }
.chat-header p { margin: 0; color: var(--vp-c-text-3); font-size: 13px; }
.header-actions { display: flex; gap: 8px; }
.mode-switch { display: flex; gap: 6px; padding: 12px 22px; border-bottom: 1px solid var(--vp-c-divider); }
.mode-switch button { background: transparent; color: var(--vp-c-text-2); }
.mode-switch button.active { background: var(--vp-c-brand-soft); color: var(--vp-c-brand-1); }
.message-list { height: 470px; overflow-y: auto; padding: 24px; }
.empty-state { height: 100%; display: grid; place-content: center; gap: 8px; text-align: center; color: var(--vp-c-text-3); }
.empty-state strong { color: var(--vp-c-text-2); font-size: 18px; }
.message { max-width: 82%; margin-bottom: 20px; }
.message.user { margin-left: auto; }
.message-label { display: block; margin: 0 4px 6px; color: var(--vp-c-text-3); font-size: 12px; }
.message.user .message-label { text-align: right; }
.message-content { border-radius: 14px; padding: 12px 15px; line-height: 1.7; white-space: pre-wrap; overflow-wrap: anywhere; }
.message.user .message-content { background: var(--vp-c-brand-1); color: white; }
.message.assistant .message-content { background: var(--vp-c-bg-soft); }
.markdown-body { white-space: normal; }
.markdown-body :deep(p) { margin: 0 0 10px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(pre) { overflow-x: auto; border-radius: 8px; padding: 12px; background: var(--vp-code-block-bg); }
.chat-error { padding: 0 22px; }
.composer { display: flex; align-items: flex-end; gap: 10px; padding: 16px 20px 20px; border-top: 1px solid var(--vp-c-divider); }
.send-button, .stop-button { width: 82px; min-height: 44px; margin: 0; }
.stop-button { background: var(--vp-c-danger-soft); color: var(--vp-c-danger-1); }
@media (max-width: 640px) {
  .chat-shell { padding: 0; min-height: calc(100vh - 64px); }
  .invite-card { margin: 24px 0; padding: 26px 20px; }
  .chat-card { border-radius: 0; border-left: 0; border-right: 0; }
  .chat-header { align-items: flex-start; padding: 14px; }
  .mode-switch { padding: 10px 14px; }
  .message-list { height: calc(100vh - 330px); min-height: 330px; padding: 16px 12px; }
  .message { max-width: 92%; }
  .composer { padding: 12px; }
}
</style>
