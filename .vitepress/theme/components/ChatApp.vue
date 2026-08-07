<script setup lang="ts">
import { Eye, EyeOff, LogOut, Send, Sparkles, Square, Trash2 } from '@lucide/vue'
import { computed, nextTick, onMounted, ref } from 'vue'
import { ApiError, getSession, logoutSession, redeemInvite, streamReply } from '../chat/api'
import { renderMarkdown } from '../chat/markdown'
import { clearHistory, loadHistory, prepareHistory, saveHistory } from '../chat/storage'
import type { AuthState, ChatMessage, PersonaId } from '../chat/types'


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
const persona = ref<PersonaId>('brat')
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
      mode: 'chat',
      persona: persona.value,
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

function selectPersona(nextPersona: PersonaId): void {
  if (persona.value === nextPersona) return
  clearMessages()
  persona.value = nextPersona
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
    <div v-if="loadingSession" class="state-panel" role="status">
      <Sparkles :size="20" aria-hidden="true" />
      <span>正在检查访问权限…</span>
    </div>

    <form v-else-if="!auth.authenticated" class="invite-card" @submit.prevent="submitInvite">
      <div class="invite-mark" aria-hidden="true"><Sparkles :size="24" /></div>
      <h1>AI Chat</h1>
      <p>请输入邀请码继续</p>
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
        <button
          type="button"
          class="icon-button"
          :aria-label="showInvite ? '隐藏邀请码' : '显示邀请码'"
          :title="showInvite ? '隐藏邀请码' : '显示邀请码'"
          @click="showInvite = !showInvite"
        >
          <EyeOff v-if="showInvite" :size="18" />
          <Eye v-else :size="18" />
        </button>
      </div>
      <p v-if="authError" class="error-text" role="alert">{{ authError }}</p>
      <button class="primary-button" type="submit" :disabled="authBusy || !inviteCode">
        {{ authBusy ? '验证中…' : '验证并进入' }}
      </button>
    </form>

    <div v-else class="chat-card">
      <header class="chat-toolbar">
        <div class="chat-identity">
          <span class="identity-icon" aria-hidden="true"><Sparkles :size="18" /></span>
          <div>
            <h1>AI Chat</h1>
            <p>在线</p>
          </div>
        </div>

        <div class="mode-switch" aria-label="角色设置">
          <span class="mode-label">角色</span>
          <button :class="{ active: persona === 'brat' }" type="button" @click="selectPersona('brat')">雌小鬼</button>
          <button :class="{ active: persona === 'normal' }" type="button" @click="selectPersona('normal')">普通</button>
          <button type="button" disabled title="暂未开放">RAG</button>
        </div>

        <div class="toolbar-meta">
          <div v-if="auth.limits" class="quota" title="邀请码剩余额度">
            <span>今日 {{ auth.limits.dayRemaining }}</span>
            <span>本分钟 {{ auth.limits.minuteRemaining }}</span>
          </div>
          <div class="header-actions">
            <button class="icon-button" type="button" aria-label="清空对话" title="清空对话" @click="clearMessages">
              <Trash2 :size="17" />
            </button>
            <button class="icon-button" type="button" aria-label="退出登录" title="退出登录" @click="logout">
              <LogOut :size="17" />
            </button>
          </div>
        </div>
      </header>

      <div ref="messageList" class="message-list" aria-live="polite">
        <div v-if="messages.length === 0" class="empty-state">
          <span class="empty-icon" aria-hidden="true"><Sparkles :size="22" /></span>
          <strong>{{ persona === 'brat' ? '大叔，想聊点什么？' : '有什么想问的？' }}</strong>
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

      <footer class="composer-panel">
        <p v-if="chatError" class="error-text chat-error" role="status">{{ chatError }}</p>
        <div class="composer">
          <textarea
            v-model="input"
            maxlength="4000"
            rows="2"
            :disabled="generating"
            placeholder="输入消息…"
            @keydown="handleKeydown"
          />
          <button
            v-if="generating"
            class="stop-button composer-button"
            type="button"
            aria-label="停止生成"
            title="停止生成"
            @click="stopGeneration"
          >
            <Square :size="17" fill="currentColor" />
          </button>
          <button
            v-else
            class="primary-button send-button composer-button"
            type="button"
            :disabled="!canSend"
            aria-label="发送消息"
            title="发送消息"
            @click="sendMessage"
          >
            <Send :size="18" />
          </button>
        </div>
      </footer>
    </div>
  </section>
</template>

<style scoped>
:global(.VPPage:has(.chat-shell)) { padding: 0 !important; }
:global(.VPContent:has(.chat-shell)) { overflow: hidden; }
* { box-sizing: border-box; }
.chat-shell { width: min(1180px, 100%); height: calc(100dvh - var(--vp-nav-height)); min-height: 520px; margin: 0 auto; padding: 12px 20px 16px; }
.state-panel { height: 100%; display: flex; align-items: center; justify-content: center; gap: 10px; color: var(--vp-c-text-2); }
.invite-card { width: min(420px, calc(100% - 32px)); margin: clamp(36px, 12vh, 110px) auto 0; padding: 30px; border: 1px solid var(--vp-c-divider); border-radius: 8px; background: var(--vp-c-bg); box-shadow: 0 18px 44px rgba(0, 0, 0, .08); }
.invite-mark, .identity-icon, .empty-icon { display: inline-grid; place-items: center; color: var(--vp-c-brand-1); }
.invite-mark { width: 42px; height: 42px; border-radius: 8px; background: var(--vp-c-brand-soft); }
.invite-card h1 { margin: 16px 0 4px; border: 0; font-size: 24px; }
.invite-card p { margin: 0; color: var(--vp-c-text-2); }
.invite-card label { display: block; margin: 22px 0 8px; font-size: 13px; font-weight: 600; }
.invite-input-row { display: flex; gap: 8px; }
input, textarea { width: 100%; border: 1px solid var(--vp-c-divider); border-radius: 7px; background: var(--vp-c-bg); color: var(--vp-c-text-1); font: inherit; letter-spacing: 0; }
input { min-width: 0; height: 42px; padding: 0 12px; }
textarea { height: 64px; min-height: 64px; max-height: 64px; resize: none; padding: 10px 12px; line-height: 1.45; overflow-y: auto; }
input:focus, textarea:focus { outline: 2px solid var(--vp-c-brand-soft); border-color: var(--vp-c-brand-1); }
button { border: 0; border-radius: 7px; font: inherit; font-weight: 600; letter-spacing: 0; cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: .5; }
.primary-button { height: 42px; margin-top: 14px; background: var(--vp-c-brand-1); color: white; }
.invite-card > .primary-button { width: 100%; }
.icon-button { width: 36px; height: 36px; display: inline-grid; flex: 0 0 auto; place-items: center; padding: 0; background: transparent; color: var(--vp-c-text-2); }
.icon-button:hover { background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); }
.invite-input-row .icon-button { width: 42px; height: 42px; border: 1px solid var(--vp-c-divider); }
.error-text { margin: 9px 0 0 !important; color: var(--vp-c-danger-1) !important; font-size: 13px; }
.chat-card { height: 100%; min-height: 0; display: flex; flex-direction: column; overflow: hidden; border: 1px solid var(--vp-c-divider); border-radius: 8px; background: var(--vp-c-bg); }
.chat-toolbar { min-height: 62px; display: grid; grid-template-columns: minmax(150px, 1fr) auto minmax(220px, 1fr); align-items: center; gap: 16px; padding: 9px 14px; border-bottom: 1px solid var(--vp-c-divider); }
.chat-identity { display: flex; align-items: center; gap: 10px; min-width: 0; }
.identity-icon { width: 34px; height: 34px; flex: 0 0 auto; border-radius: 7px; background: var(--vp-c-brand-soft); }
.chat-identity h1 { margin: 0; border: 0; font-size: 16px; line-height: 1.2; }
.chat-identity p { margin: 3px 0 0; color: var(--vp-c-green-1); font-size: 11px; }
.mode-switch { height: 36px; display: flex; align-items: center; gap: 2px; padding: 3px; border: 1px solid var(--vp-c-divider); border-radius: 7px; background: var(--vp-c-bg-soft); }
.mode-label { padding: 0 7px; color: var(--vp-c-text-3); font-size: 12px; }
.mode-switch button { height: 28px; padding: 0 10px; background: transparent; color: var(--vp-c-text-2); font-size: 12px; white-space: nowrap; }
.mode-switch button.active { background: var(--vp-c-bg); color: var(--vp-c-brand-1); box-shadow: 0 1px 3px rgba(0, 0, 0, .1); }
.mode-switch button:disabled { color: var(--vp-c-text-3); text-decoration: line-through; }
.toolbar-meta { display: flex; align-items: center; justify-content: flex-end; gap: 10px; min-width: 0; }
.quota { display: flex; gap: 9px; color: var(--vp-c-text-3); font-size: 11px; white-space: nowrap; }
.header-actions { display: flex; gap: 2px; }
.message-list { flex: 1 1 auto; min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 20px clamp(16px, 4vw, 54px); scroll-behavior: smooth; }
.empty-state { height: 100%; display: grid; place-content: center; justify-items: center; gap: 10px; color: var(--vp-c-text-3); text-align: center; }
.empty-icon { width: 42px; height: 42px; border-radius: 50%; background: var(--vp-c-bg-soft); }
.empty-state strong { color: var(--vp-c-text-2); font-size: 15px; }
.message { width: fit-content; max-width: min(78%, 740px); margin-bottom: 16px; }
.message.user { margin-left: auto; }
.message-label { display: block; margin: 0 3px 5px; color: var(--vp-c-text-3); font-size: 11px; }
.message.user .message-label { text-align: right; }
.message-content { border-radius: 8px; padding: 10px 13px; line-height: 1.65; white-space: pre-wrap; overflow-wrap: anywhere; }
.message.user .message-content { background: var(--vp-c-brand-1); color: white; }
.message.assistant .message-content { border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg-soft); }
.markdown-body { white-space: normal; }
.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(pre) { overflow-x: auto; border-radius: 6px; padding: 10px; background: var(--vp-code-block-bg); }
.composer-panel { flex: 0 0 auto; padding: 10px 14px 12px; border-top: 1px solid var(--vp-c-divider); background: var(--vp-c-bg-soft); }
.chat-error { margin: 0 0 7px !important; }
.composer { display: flex; align-items: center; gap: 8px; }
.composer-button { width: 42px; height: 42px; min-width: 42px; display: inline-grid; place-items: center; margin: 0; padding: 0; }
.stop-button { background: var(--vp-c-danger-soft); color: var(--vp-c-danger-1); }
@media (max-width: 760px) {
  .chat-shell { height: calc(100dvh - var(--vp-nav-height)); min-height: 440px; padding: 0; }
  .chat-card { border-right: 0; border-left: 0; border-radius: 0; }
  .chat-toolbar { grid-template-columns: 1fr auto; gap: 8px; padding: 8px 10px; }
  .chat-identity p, .mode-label, .quota { display: none; }
  .mode-switch { grid-column: 1 / -1; grid-row: 2; justify-self: stretch; justify-content: center; width: 100%; }
  .mode-switch button { flex: 1; }
  .toolbar-meta { grid-column: 2; grid-row: 1; }
  .message-list { padding: 14px 12px; }
  .message { max-width: 90%; }
  .composer-panel { padding: 8px 10px 10px; }
  textarea { height: 58px; min-height: 58px; max-height: 58px; }
}
@media (max-height: 620px) and (min-width: 761px) {
  .chat-shell { min-height: 420px; padding-top: 6px; padding-bottom: 8px; }
  .chat-toolbar { min-height: 54px; }
  textarea { height: 54px; min-height: 54px; max-height: 54px; }
  .composer-panel { padding-top: 8px; padding-bottom: 8px; }
}
</style>
