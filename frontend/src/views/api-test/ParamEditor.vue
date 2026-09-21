<template>
  <div class="param-editor">
    <div class="param-head">
      <span class="col-check"></span>
      <span class="col-key">参数名</span>
      <span class="col-type">类型</span>
      <span class="col-value">参数值</span>
      <span class="col-desc">描述</span>
      <span class="col-op"></span>
    </div>
    <div v-for="(row, index) in rows" :key="index" class="param-row">
      <input
        class="col-check"
        type="checkbox"
        :checked="row.enabled !== false"
        @change="updateRow(index, 'enabled', $event.target.checked)"
      />
      <el-select
        v-if="keyOptions && keyOptions.length"
        :value="row.key"
        filterable
        allow-create
        default-first-option
        placeholder="选择或输入 Header"
        size="small"
        class="col-key"
        @change="val => updateRow(index, 'key', val)"
      >
        <el-option v-for="name in keyOptions" :key="name" :label="name" :value="name" />
      </el-select>
      <el-input
        v-else
        :value="row.key"
        placeholder="参数名"
        size="small"
        class="col-key"
        @input="val => updateRow(index, 'key', val)"
      />
      <el-select :value="row.type || 'string'" size="small" class="col-type" @change="val => updateRow(index, 'type', val)">
        <el-option label="String" value="string" />
        <el-option label="Integer" value="integer" />
        <el-option label="Number" value="number" />
        <el-option label="Boolean" value="boolean" />
      </el-select>
      <el-input :value="row.value" placeholder="参数值" size="small" class="col-value" @input="val => updateRow(index, 'value', val)" />
      <el-input :value="row.description" placeholder="描述" size="small" class="col-desc" @input="val => updateRow(index, 'description', val)" />
      <button type="button" class="link-btn is-danger col-op" @click="removeRow(index)">删除</button>
    </div>
    <button type="button" class="add-btn" @click="addRow">+ 添加参数</button>
  </div>
</template>

<script>
function emptyRow() {
  return { key: '', value: '', type: 'string', required: false, description: '', enabled: true }
}

export default {
  name: 'ParamEditor',
  props: {
    value: {
      type: Array,
      default: () => []
    },
    keyOptions: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    rows() {
      return this.value && this.value.length ? this.value : [emptyRow()]
    }
  },
  methods: {
    emit(next) {
      this.$emit('input', next)
    },
    updateRow(index, key, val) {
      const base = (this.value && this.value.length) ? this.value : [emptyRow()]
      const next = base.map((item, i) => (i === index ? { ...item, [key]: val } : { ...item }))
      this.emit(next)
    },
    addRow() {
      const base = (this.value && this.value.length) ? this.value : [emptyRow()]
      this.emit(base.concat([emptyRow()]))
    },
    removeRow(index) {
      const base = (this.value && this.value.length) ? this.value.slice() : [emptyRow()]
      base.splice(index, 1)
      this.emit(base.length ? base : [emptyRow()])
    }
  }
}
</script>

<style scoped>
.param-head,
.param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.param-head {
  color: #6b7280;
  font-size: 12px;
}

.col-check {
  width: 18px;
  flex: none;
}

.col-key {
  width: 220px;
  flex: none;
}

.col-type {
  width: 110px;
  flex: none;
}

.col-value,
.col-desc {
  flex: 1;
}

.col-op {
  width: 48px;
  flex: none;
}

.add-btn,
.link-btn {
  border: none;
  background: none;
  padding: 0 6px;
  color: #0f766e;
  cursor: pointer;
  font-size: 14px;
}

.link-btn.is-danger {
  color: #c45656;
}
</style>
