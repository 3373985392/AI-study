export type PersonaId = 'normal' | 'vue' | 'brat'
export type MessageRole = 'user' | 'assistant'

export interface ChatSource {
  file: string
  documentTitle: string
  sectionTitle: string
  subsectionTitle?: string
  score: number
  url: string
}

export interface ChatMessage {
  id?: string
  role: MessageRole
  content: string
  sources?: ChatSource[]
  createdAt?: number
  feedback?: -1 | 1
}

export interface Conversation {
  id: string
  title: string
  persona: PersonaId
  localOnly: boolean
  createdAt: number
  updatedAt: number
  messages?: ChatMessage[]
}

export interface AuthState {
  authenticated: boolean
  viewerId?: string
  expiresAt?: number
  limits?: {
    minute: number
    day: number
    minuteRemaining: number
    dayRemaining: number
  }
}
