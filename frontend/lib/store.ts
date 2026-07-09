import { create } from 'zustand'

interface LogEntry {
  id: number
  ts: string
  agent: string
  task_id: string
  tool: string
  ok: number
  detail: string
}

interface AppState {
  logs: LogEntry[]
  addLog: (log: LogEntry) => void
  connectWebSockets: () => void
}

export const useStore = create<AppState>((set, get) => ({
  logs: [],
  addLog: (log) => set((state) => ({ logs: [log, ...state.logs].slice(0, 50) })),
  connectWebSockets: () => {
    // Events WebSocket
    const wsEvents = new WebSocket('ws://localhost:27180/dashboard/events')
    wsEvents.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'audit') {
        get().addLog({
          id: Date.now(), // fallback id
          ts: new Date().toISOString(),
          agent: data.agent,
          task_id: data.task_id,
          tool: data.tool,
          ok: data.ok ? 1 : 0,
          detail: data.detail,
        })
      }
    }

    // Tokens WebSocket
    const wsTokens = new WebSocket('ws://localhost:27180/dashboard/tokens/ws')
    wsTokens.onmessage = (event) => {
      // Could parse and store tokens in another zustand store or array if needed
      console.log('Token event:', JSON.parse(event.data))
    }
  }
}))
