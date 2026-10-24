<template>
  <div class="dialogue-root" :class="{ compact }">
    <div v-if="!turns.length" class="empty">-</div>
    <div v-for="(item, idx) in turns" :key="idx" class="turn-card">
      <div class="turn-badge">第 {{ item.turn }} 轮</div>
      <div class="pair">
        <div class="bubble user">
          <div class="role">用户输入</div>
          <div class="text">{{ item.user_input || '-' }}</div>
        </div>
        <div class="bubble agent">
          <div class="role">Agent 输出</div>
          <div v-if="item.answer" class="text">{{ item.answer }}</div>
          <div v-else class="text pending">{{ pendingLabel(item) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DialogueTurns',
  props: {
    turns: {
      type: Array,
      default: () => []
    },
    compact: {
      type: Boolean,
      default: false
    },
    pendingText: {
      type: String,
      default: '未执行'
    }
  },
  methods: {
    pendingLabel(item) {
      if (item && item.legacy_note) return item.legacy_note
      if (item && (item.executed || item.request_id)) return '本轮无文本回复'
      return this.pendingText
    }
  }
}
</script>

<style scoped>
.dialogue-root {
  text-align: left;
}

.empty {
  color: #94a3b8;
  font-size: 13px;
}

.turn-card + .turn-card {
  margin-top: 10px;
}

.turn-badge {
  display: inline-block;
  margin-bottom: 4px;
  padding: 1px 8px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
}

.pair {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bubble {
  border-radius: 8px;
  padding: 8px 10px;
  border: 1px solid #e2e8f0;
}

.bubble.user {
  background: #f8fafc;
}

.bubble.agent {
  background: #ecfdf5;
  border-color: #a7f3d0;
}

.role {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 2px;
}

.text {
  font-size: 13px;
  line-height: 1.45;
  color: #0f172a;
  white-space: pre-wrap;
  word-break: break-word;
}

.text.pending {
  color: #94a3b8;
}

.compact .turn-card + .turn-card {
  margin-top: 8px;
}

.compact .bubble {
  padding: 6px 8px;
}

.compact .text {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  max-height: 4.4em;
  font-size: 12px;
}
</style>
