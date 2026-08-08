<script setup lang="ts">
import {
  Ban, CheckCircle2, ChevronLeft, ChevronRight, Copy, KeyRound, LogOut,
  MessageSquare, Plus, Save, Search, ShieldCheck,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import {
  AdminApiError, createAdminInvite, getAdminSession, listAdminConversations,
  listAdminInvites, listAdminMessages, loginAdmin, logoutAdmin, updateAdminInvite,
} from '../admin/api'
import type {
  AdminAuthState, AdminConversation, AdminInvite, AdminMemory, AdminMessage,
} from '../admin/types'
import { renderMarkdown } from '../chat/markdown'


// 认证模块：管理员 Cookie 与普通邀请码 Cookie 完全独立。
const loadingSession = ref(true)
const auth = ref<AdminAuthState>({ authenticated: false })
const password = ref('')
const busy = ref(false)
const errorMessage = ref('')

// 邀请码模块：列表支持查询、状态过滤、分页和受控编辑。
const invites = ref<AdminInvite[]>([])
const inviteQuery = ref('')
const inviteStatus = ref<'all' | 'active' | 'revoked'>('all')
const invitePage = ref(1)
const inviteTotal = ref(0)
const selectedInvite = ref<AdminInvite | null>(null)
const editLabel = ref('')
const editMinuteLimit = ref(5)
const editDayLimit = ref(50)

// 会话与消息模块：只读取同步会话，管理员界面不提供删除能力。
const conversations = ref<AdminConversation[]>([])
const conversationPage = ref(1)
const conversationTotal = ref(0)
const selectedConversation = ref<AdminConversation | null>(null)
const messages = ref<AdminMessage[]>([])
const memory = ref<AdminMemory | undefined>()
const messagePage = ref(1)
const messageTotal = ref(0)

// 创建模块：邀请码明文只在创建成功后保留在当前页面内存中。
const creating = ref(false)
const createMode = ref<'generated' | 'custom'>('generated')
const createLabel = ref('')
const createMinuteLimit = ref(5)
const createDayLimit = ref(50)
const customCode = ref('')
const customCodeConfirmation = ref('')
const oneTimeCode = ref('')

const invitePages = computed(() => Math.max(1, Math.ceil(inviteTotal.value / 30)))
const conversationPages = computed(() => Math.max(1, Math.ceil(conversationTotal.value / 30)))
const messagePages = computed(() => Math.max(1, Math.ceil(messageTotal.value / 100)))

function formatError(error: unknown): string {
  if (error instanceof AdminApiError) {
    return error.retryAfter ? `${error.message}（约 ${error.retryAfter} 秒后重试）` : error.message
  }
  return '请求失败，请检查网络后重试'
}

function formatTime(value?: number): string {
  return value ? new Date(value * 1000).toLocaleString('zh-CN') : '-'
}

function syncEditForm(invite: AdminInvite): void {
  editLabel.value = invite.label
  editMinuteLimit.value = invite.minuteLimit
  editDayLimit.value = invite.dayLimit
}

async function loadInvites(resetSelection = false): Promise<void> {
  const result = await listAdminInvites({
    query: inviteQuery.value.trim(), status: inviteStatus.value, page: invitePage.value,
  })
  invites.value = result.items
  inviteTotal.value = result.total
  if (resetSelection) {
    selectedInvite.value = null
    selectedConversation.value = null
    conversations.value = []
    messages.value = []
    memory.value = undefined
  }
}

async function selectInvite(invite: AdminInvite): Promise<void> {
  selectedInvite.value = invite
  syncEditForm(invite)
  conversationPage.value = 1
  selectedConversation.value = null
  messages.value = []
  memory.value = undefined
  const result = await listAdminConversations(invite.id, conversationPage.value)
  conversations.value = result.items
  conversationTotal.value = result.total
}

async function loadConversationPage(page: number): Promise<void> {
  if (!selectedInvite.value) return
  conversationPage.value = page
  const result = await listAdminConversations(selectedInvite.value.id, page)
  conversations.value = result.items
  conversationTotal.value = result.total
}

async function selectConversation(conversation: AdminConversation): Promise<void> {
  selectedConversation.value = conversation
  messagePage.value = 1
  const result = await listAdminMessages(conversation.id, messagePage.value)
  messages.value = result.items
  messageTotal.value = result.total
  memory.value = result.memory
}

async function loadMessagePage(page: number): Promise<void> {
  if (!selectedConversation.value) return
  messagePage.value = page
  const result = await listAdminMessages(selectedConversation.value.id, page)
  messages.value = result.items
  messageTotal.value = result.total
  memory.value = result.memory
}

async function submitLogin(): Promise<void> {
  if (!password.value || busy.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    auth.value = await loginAdmin(password.value)
    password.value = ''
    await loadInvites(true)
  } catch (error) {
    errorMessage.value = formatError(error)
  } finally {
    busy.value = false
  }
}

async function submitSearch(): Promise<void> {
  invitePage.value = 1
  errorMessage.value = ''
  try { await loadInvites(true) } catch (error) { errorMessage.value = formatError(error) }
}

async function changeInvitePage(page: number): Promise<void> {
  invitePage.value = page
  try { await loadInvites(true) } catch (error) { errorMessage.value = formatError(error) }
}

async function saveInvite(): Promise<void> {
  if (!selectedInvite.value || busy.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    const updated = await updateAdminInvite(selectedInvite.value.id, {
      label: editLabel.value.trim(),
      minuteLimit: editMinuteLimit.value,
      dayLimit: editDayLimit.value,
    })
    Object.assign(selectedInvite.value, updated)
    await loadInvites()
  } catch (error) {
    errorMessage.value = formatError(error)
  } finally {
    busy.value = false
  }
}

async function toggleInvite(): Promise<void> {
  const invite = selectedInvite.value
  if (!invite || busy.value) return
  const nextActive = !invite.active
  if (!nextActive && !window.confirm(`撤销“${invite.label}”？该邀请码的登录会话会立即失效。`)) return
  busy.value = true
  try {
    const updated = await updateAdminInvite(invite.id, { active: nextActive })
    Object.assign(invite, updated)
    await loadInvites()
  } catch (error) {
    errorMessage.value = formatError(error)
  } finally {
    busy.value = false
  }
}

async function submitCreateInvite(): Promise<void> {
  if (busy.value || !createLabel.value.trim()) return
  busy.value = true
  oneTimeCode.value = ''
  errorMessage.value = ''
  try {
    const result = await createAdminInvite({
      mode: createMode.value,
      label: createLabel.value.trim(),
      minuteLimit: createMinuteLimit.value,
      dayLimit: createDayLimit.value,
      code: createMode.value === 'custom' ? customCode.value : undefined,
      codeConfirmation: createMode.value === 'custom' ? customCodeConfirmation.value : undefined,
    })
    oneTimeCode.value = result.oneTimeCode
    createLabel.value = ''
    customCode.value = ''
    customCodeConfirmation.value = ''
    await loadInvites()
  } catch (error) {
    errorMessage.value = formatError(error)
  } finally {
    busy.value = false
  }
}

async function copyOneTimeCode(): Promise<void> {
  if (oneTimeCode.value) await navigator.clipboard.writeText(oneTimeCode.value)
}

async function signOut(): Promise<void> {
  try { await logoutAdmin() } finally {
    auth.value = { authenticated: false }
    invites.value = []
    conversations.value = []
    messages.value = []
    selectedInvite.value = null
    selectedConversation.value = null
  }
}

onMounted(async () => {
  try {
    auth.value = await getAdminSession()
    if (auth.value.authenticated) await loadInvites()
  } catch (error) {
    errorMessage.value = formatError(error)
  } finally {
    loadingSession.value = false
  }
})
</script>

<template>
  <section class="admin-shell" aria-label="AI Chat 管理员后台">
    <div v-if="loadingSession" class="admin-center">正在检查管理员会话…</div>

    <form v-else-if="!auth.authenticated" class="admin-login" @submit.prevent="submitLogin">
      <ShieldCheck :size="34" />
      <h1>管理员后台</h1>
      <p>此页面可以查看服务器同步聊天正文，请仅在可信设备上登录。</p>
      <label for="admin-password">管理员密码</label>
      <input id="admin-password" v-model="password" type="password" autocomplete="current-password" required>
      <button type="submit" :disabled="busy || !password"><KeyRound :size="16" />{{ busy ? '验证中…' : '登录' }}</button>
      <p v-if="errorMessage" class="admin-error">{{ errorMessage }}</p>
    </form>

    <div v-else class="admin-workspace">
      <header class="admin-header">
        <div><ShieldCheck :size="21" /><strong>AI Chat 管理后台</strong></div>
        <button type="button" class="ghost" @click="signOut"><LogOut :size="15" />退出</button>
      </header>

      <div class="admin-toolbar">
        <form class="admin-search" @submit.prevent="submitSearch">
          <Search :size="15" />
          <input v-model="inviteQuery" placeholder="搜索邀请码 ID 或备注">
          <select v-model="inviteStatus" @change="submitSearch">
            <option value="all">全部状态</option>
            <option value="active">已启用</option>
            <option value="revoked">已撤销</option>
          </select>
          <button type="submit">查询</button>
        </form>
        <button type="button" @click="creating = !creating"><Plus :size="15" />创建邀请码</button>
      </div>

      <p v-if="errorMessage" class="admin-error global-error">{{ errorMessage }}</p>

      <form v-if="creating" class="create-panel" @submit.prevent="submitCreateInvite">
        <div class="field"><label>创建方式</label><select v-model="createMode"><option value="generated">系统生成</option><option value="custom">自定义</option></select></div>
        <div class="field"><label>备注</label><input v-model="createLabel" maxlength="80" required></div>
        <div class="field"><label>每分钟额度</label><input v-model.number="createMinuteLimit" type="number" min="1" required></div>
        <div class="field"><label>每日额度</label><input v-model.number="createDayLimit" type="number" min="1" required></div>
        <template v-if="createMode === 'custom'">
          <div class="field"><label>自定义邀请码</label><input v-model="customCode" type="password" minlength="16" maxlength="64" required></div>
          <div class="field"><label>再次输入</label><input v-model="customCodeConfirmation" type="password" minlength="16" maxlength="64" required></div>
        </template>
        <button type="submit" :disabled="busy">创建</button>
        <div v-if="oneTimeCode" class="one-time-code">
          <strong>邀请码仅显示这一次，请立即保存</strong>
          <code>{{ oneTimeCode }}</code>
          <button type="button" @click="copyOneTimeCode"><Copy :size="14" />复制</button>
        </div>
      </form>

      <div class="admin-columns">
        <aside class="admin-panel invite-panel">
          <h2>邀请码 <small>{{ inviteTotal }}</small></h2>
          <button v-for="invite in invites" :key="invite.id" type="button" class="list-item" :class="{ selected: selectedInvite?.id === invite.id }" @click="selectInvite(invite)">
            <span><strong>{{ invite.label }}</strong><small>{{ invite.id }}</small></span>
            <em :class="invite.active ? 'active' : 'revoked'">{{ invite.active ? '启用' : '撤销' }}</em>
            <small>{{ invite.conversationCount }} 个会话 · {{ invite.totalUsed }} 次调用</small>
          </button>
          <div class="pager"><button :disabled="invitePage <= 1" @click="changeInvitePage(invitePage - 1)"><ChevronLeft :size="14" /></button><span>{{ invitePage }}/{{ invitePages }}</span><button :disabled="invitePage >= invitePages" @click="changeInvitePage(invitePage + 1)"><ChevronRight :size="14" /></button></div>
        </aside>

        <section class="admin-panel conversation-panel">
          <template v-if="selectedInvite">
            <h2>{{ selectedInvite.label }} <small>{{ selectedInvite.id }}</small></h2>
            <div class="invite-editor">
              <label>备注<input v-model="editLabel"></label>
              <label>分钟额度<input v-model.number="editMinuteLimit" type="number" min="1"></label>
              <label>每日额度<input v-model.number="editDayLimit" type="number" min="1"></label>
              <button type="button" :disabled="busy" @click="saveInvite"><Save :size="14" />保存</button>
              <button type="button" :class="selectedInvite.active ? 'danger' : 'success'" :disabled="busy" @click="toggleInvite">
                <Ban v-if="selectedInvite.active" :size="14" /><CheckCircle2 v-else :size="14" />{{ selectedInvite.active ? '撤销' : '启用' }}
              </button>
            </div>
            <button v-for="conversation in conversations" :key="conversation.id" type="button" class="list-item" :class="{ selected: selectedConversation?.id === conversation.id }" @click="selectConversation(conversation)">
              <MessageSquare :size="15" /><span><strong>{{ conversation.title }}</strong><small>{{ conversation.persona }} · {{ conversation.messageCount }} 条 · {{ formatTime(conversation.updatedAt) }}</small></span>
            </button>
            <div class="pager"><button :disabled="conversationPage <= 1" @click="loadConversationPage(conversationPage - 1)"><ChevronLeft :size="14" /></button><span>{{ conversationPage }}/{{ conversationPages }}</span><button :disabled="conversationPage >= conversationPages" @click="loadConversationPage(conversationPage + 1)"><ChevronRight :size="14" /></button></div>
          </template>
          <div v-else class="empty-state">选择邀请码以查看同步会话</div>
        </section>

        <main class="admin-panel message-panel">
          <template v-if="selectedConversation">
            <h2>{{ selectedConversation.title }} <small>{{ messageTotal }} 条消息</small></h2>
            <details v-if="memory" class="memory-card">
              <summary>滚动记忆摘要</summary>
              <p>{{ memory.summary }}</p>
              <div v-if="memory.facts.length"><strong>事实</strong><ul><li v-for="item in memory.facts" :key="item">{{ item }}</li></ul></div>
              <div v-if="memory.decisions.length"><strong>决定</strong><ul><li v-for="item in memory.decisions" :key="item">{{ item }}</li></ul></div>
              <div v-if="memory.openItems.length"><strong>未完成</strong><ul><li v-for="item in memory.openItems" :key="item">{{ item }}</li></ul></div>
            </details>
            <article v-for="message in messages" :key="message.id" class="admin-message" :class="message.role">
              <header><strong>{{ message.role === 'user' ? '用户' : '助手' }}</strong><time>{{ formatTime(message.createdAt) }}</time></header>
              <div class="message-body" v-html="renderMarkdown(message.content)"></div>
              <small v-if="message.feedback">反馈：{{ message.feedback > 0 ? '赞' : '踩' }} {{ message.feedbackComment || '' }}</small>
              <ul v-if="message.sources.length" class="source-list"><li v-for="source in message.sources" :key="source.url"><a :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.documentTitle }} / {{ source.sectionTitle }}</a></li></ul>
            </article>
            <div class="pager"><button :disabled="messagePage <= 1" @click="loadMessagePage(messagePage - 1)"><ChevronLeft :size="14" /></button><span>{{ messagePage }}/{{ messagePages }}</span><button :disabled="messagePage >= messagePages" @click="loadMessagePage(messagePage + 1)"><ChevronRight :size="14" /></button></div>
          </template>
          <div v-else class="empty-state">选择会话以查看完整聊天历史</div>
        </main>
      </div>
    </div>
  </section>
</template>

<style scoped>
:global(.VPPage:has(.admin-shell)),:global(.VPContent:has(.admin-shell)){padding:0!important;overflow:hidden}.admin-shell{height:calc(100dvh - var(--vp-nav-height));min-height:560px;padding:12px 18px;background:var(--vp-c-bg-soft)}.admin-center,.empty-state{display:grid;place-items:center;height:100%;color:var(--vp-c-text-3)}.admin-login{width:min(430px,calc(100% - 32px));margin:9vh auto;padding:30px;border:1px solid var(--vp-c-divider);border-radius:10px;background:var(--vp-c-bg);box-shadow:0 18px 44px rgba(0,0,0,.08)}.admin-login>svg{color:var(--vp-c-brand-1)}.admin-login h1{margin:12px 0 4px;border:0}.admin-login p{color:var(--vp-c-text-2)}.admin-login label,.field label{font-size:12px;font-weight:600}.admin-login input{width:100%;height:42px;margin:7px 0 12px}.admin-login button,.admin-toolbar button,.create-panel button,.invite-editor button{display:inline-flex;align-items:center;justify-content:center;gap:6px}.admin-login button{width:100%;height:42px;background:var(--vp-c-brand-1);color:white}.admin-workspace{height:100%;display:grid;grid-template-rows:auto auto auto minmax(0,1fr);overflow:hidden;border:1px solid var(--vp-c-divider);border-radius:9px;background:var(--vp-c-bg)}.admin-header,.admin-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px;border-bottom:1px solid var(--vp-c-divider)}.admin-header>div,.admin-header button,.admin-search{display:flex;align-items:center;gap:8px}.admin-toolbar{background:var(--vp-c-bg-soft)}.admin-search{flex:1}.admin-search input{width:min(360px,45vw)}input,select{min-height:36px;padding:7px 9px;border:1px solid var(--vp-c-divider);border-radius:6px;background:var(--vp-c-bg);color:var(--vp-c-text-1)}button{min-height:34px;padding:6px 10px;border-radius:6px;background:var(--vp-c-brand-1);color:#fff}button.ghost,.pager button{background:transparent;color:var(--vp-c-text-2);border:1px solid var(--vp-c-divider)}button:disabled{opacity:.45;cursor:not-allowed}.admin-error{color:var(--vp-c-danger-1)}.global-error{margin:0;padding:6px 14px;border-bottom:1px solid var(--vp-c-divider)}.create-panel{display:flex;flex-wrap:wrap;align-items:end;gap:10px;padding:10px 14px;border-bottom:1px solid var(--vp-c-divider);background:var(--vp-c-bg-soft)}.field{display:grid;gap:3px}.one-time-code{width:100%;display:flex;align-items:center;gap:10px;padding:9px;border:1px solid var(--vp-c-warning-1);border-radius:6px}.one-time-code code{user-select:all}.admin-columns{min-height:0;display:grid;grid-template-columns:minmax(220px,0.8fr) minmax(280px,1fr) minmax(360px,1.7fr)}.admin-panel{min-width:0;min-height:0;overflow-y:auto;padding:10px;border-right:1px solid var(--vp-c-divider)}.admin-panel:last-child{border-right:0}.admin-panel h2{display:flex;align-items:baseline;gap:7px;margin:2px 4px 10px;border:0;font-size:15px}.admin-panel h2 small{color:var(--vp-c-text-3);font-weight:400}.list-item{width:100%;display:flex;align-items:center;gap:8px;margin-bottom:5px;padding:9px;text-align:left;background:transparent;color:var(--vp-c-text-2);border:1px solid transparent}.list-item:hover,.list-item.selected{background:var(--vp-c-bg-soft);border-color:var(--vp-c-divider)}.list-item span{min-width:0;flex:1;display:grid}.list-item strong,.list-item small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.list-item em{font-size:11px;font-style:normal}.list-item em.active{color:var(--vp-c-success-1)}.list-item em.revoked{color:var(--vp-c-danger-1)}.invite-editor{display:grid;grid-template-columns:1fr 86px 96px auto auto;gap:6px;margin-bottom:10px;padding:8px;background:var(--vp-c-bg-soft);border-radius:7px}.invite-editor label{display:grid;gap:3px;font-size:10px}.invite-editor input{width:100%;min-width:0}.danger{background:var(--vp-c-danger-1)}.success{background:var(--vp-c-success-1)}.memory-card{margin:0 0 10px;padding:9px;border:1px solid var(--vp-c-divider);border-radius:7px;background:var(--vp-c-bg-soft);font-size:12px}.memory-card summary{cursor:pointer;font-weight:600}.admin-message{margin-bottom:10px;padding:10px 12px;border:1px solid var(--vp-c-divider);border-radius:8px}.admin-message.user{margin-left:8%;background:var(--vp-c-brand-soft)}.admin-message.assistant{margin-right:8%}.admin-message header{display:flex;justify-content:space-between;margin-bottom:6px;font-size:11px;color:var(--vp-c-text-3)}.message-body{font-size:13px}.message-body :deep(p){margin:5px 0}.source-list{font-size:11px}.pager{display:flex;align-items:center;justify-content:center;gap:8px;padding:8px}.pager button{min-height:28px;padding:3px 7px}@media(max-width:900px){.admin-shell{height:auto;min-height:calc(100dvh - var(--vp-nav-height));padding:0}.admin-workspace{overflow:visible;border-radius:0}.admin-columns{grid-template-columns:1fr}.admin-panel{max-height:60vh;border-right:0;border-bottom:1px solid var(--vp-c-divider)}.invite-editor{grid-template-columns:1fr 1fr}.admin-toolbar{align-items:stretch;flex-direction:column}.admin-search{flex-wrap:wrap}.admin-search input{width:100%}}
</style>
