export type ChatMode = 'chat' | 'rag'
export type PersonaId = 'brat' | 'normal'
export type MessageRole = 'user' | 'assistant'

export interface ChatMessage {
  role: MessageRole
  content: string
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
