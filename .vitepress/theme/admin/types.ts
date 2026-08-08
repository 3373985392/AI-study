export interface AdminAuthState {
  authenticated: boolean
  expiresAt?: number
}

export interface AdminInvite {
  id: string
  label: string
  active: boolean
  minuteLimit: number
  dayLimit: number
  createdAt: number
  revokedAt?: number
  lastUsedAt?: number
  conversationCount: number
  lastChatAt?: number
  totalUsed: number
  inputTokens: number
  outputTokens: number
  estimatedCostUsd: number
}

export interface AdminConversation {
  id: string
  title: string
  persona: 'normal' | 'vue' | 'brat'
  createdAt: number
  updatedAt: number
  messageCount: number
}

export interface AdminMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources: Array<{ file: string; documentTitle: string; sectionTitle: string; url: string }>
  createdAt: number
  feedback?: -1 | 1
  feedbackComment?: string
}

export interface AdminMemory {
  summary: string
  facts: string[]
  decisions: string[]
  openItems: string[]
  summarizedThroughMessageId?: string
  updatedAt: number
}

export interface Page<T> {
  items: T[]
  page: number
  pageSize: number
  total: number
}
