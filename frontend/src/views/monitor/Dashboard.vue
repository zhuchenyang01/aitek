<template>
  <div class="page">
    <div class="toolbar">
      <el-select
        v-model="serverId"
        placeholder="选择服务器"
        filterable
        clearable
        style="width: 240px"
        @change="onServerChange"
      >
        <el-option
          v-for="s in servers"
          :key="s.id"
          :label="`${s.name} (${s.host})`"
          :value="s.id"
        />
      </el-select>
      <el-radio-group v-model="range" size="small" @change="refreshHistory">
        <el-radio-button label="15m">15分钟</el-radio-button>
        <el-radio-button label="1h">1小时</el-radio-button>
        <el-radio-button label="6h">6小时</el-radio-button>
        <el-radio-button label="24h">24小时</el-radio-button>
      </el-radio-group>
      <el-switch
        v-model="autoCollect"
        active-text="自动采集"
        inactive-text=""
        :disabled="!serverId"
      />
      <el-button
        type="primary"
        plain
        icon="el-icon-refresh"
        :loading="collecting"
        :disabled="!serverId"
        @click="doCollect"
      >立即采集</el-button>
    </div>

    <el-empty v-if="!serverId" description="请先选择一台服务器" />

    <template v-else>
      <div class="cards" v-loading="collecting && !latest">
        <div class="card">
          <div class="card-label">CPU</div>
          <div class="card-value">{{ fmtPct(latest && latest.cpu_percent) }}</div>
        </div>
        <div class="card">
          <div class="card-label">内存</div>
          <div class="card-value">{{ fmtPct(latest && latest.mem_percent) }}</div>
        </div>
        <div class="card">
          <div class="card-label">根盘</div>
          <div class="card-value">{{ fmtPct(latest && latest.disk_percent) }}</div>
        </div>
        <div class="card">
          <div class="card-label">Load1</div>
          <div class="card-value">{{ fmtNum(latest && latest.load1) }}</div>
        </div>
        <div class="card">
          <div class="card-label">网络收</div>
          <div class="card-value">{{ fmtRate(latest && latest.net_rx_bps) }}</div>
        </div>
        <div class="card">
          <div class="card-label">网络发</div>
          <div class="card-value">{{ fmtRate(latest && latest.net_tx_bps) }}</div>
        </div>
      </div>
      <p v-if="latest" class="meta">最近采样：{{ latest.collected_at || '-' }}</p>
      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <div class="charts">
        <div class="chart-box">
          <div class="chart-title">CPU / 内存 / 磁盘 (%)</div>
          <div ref="chartPct" class="chart" />
        </div>
        <div class="chart-box">
          <div class="chart-title">系统负载</div>
          <div ref="chartLoad" class="chart" />
        </div>
        <div class="chart-box">
          <div class="chart-title">网络吞吐 (B/s)</div>
          <div ref="chartNet" class="chart" />
        </div>
        <div class="chart-box">
          <div class="chart-title">磁盘 IO (B/s)</div>
          <div ref="chartDisk" class="chart" />
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import {
  listMonitorServers,
  collectMonitorServer,
  getMonitorMetrics
} from '@/api/monitor'

const POLL_MS = 5000

export default {
  name: 'MonitorDashboard',
  data() {
    return {
      servers: [],
      serverId: null,
      range: '1h',
      autoCollect: true,
      collecting: false,
      latest: null,
      items: [],
      errorMsg: '',
      timer: null,
      charts: {
        pct: null,
        load: null,
        net: null,
        disk: null
      }
    }
  },
  watch: {
    autoCollect(val) {
      if (val) this.startPoll()
      else this.stopPoll()
    }
  },
  async created() {
    await this.fetchServers()
    if (this.servers.length) {
      this.serverId = this.servers[0].id
      await this.onServerChange()
    }
  },
  mounted() {
    window.addEventListener('resize', this.resizeCharts)
  },
  beforeDestroy() {
    this.stopPoll()
    window.removeEventListener('resize', this.resizeCharts)
    Object.values(this.charts).forEach((c) => c && c.dispose())
  },
  methods: {
    fmtPct(v) {
      if (v == null || v === '') return '-'
      return `${Number(v).toFixed(1)}%`
    },
    fmtNum(v) {
      if (v == null || v === '') return '-'
      return Number(v).toFixed(2)
    },
    fmtRate(v) {
      if (v == null || v === '') return '-'
      const n = Number(v)
      if (n >= 1048576) return `${(n / 1048576).toFixed(2)} MB/s`
      if (n >= 1024) return `${(n / 1024).toFixed(1)} KB/s`
      return `${n.toFixed(0)} B/s`
    },
    async fetchServers() {
      try {
        const res = await listMonitorServers()
        this.servers = (res && res.data) || []
      } catch (e) {
        this.servers = []
      }
    },
    async onServerChange() {
      this.stopPoll()
      this.latest = null
      this.items = []
      this.errorMsg = ''
      if (!this.serverId) return
      this.$nextTick(() => {
        this.initCharts()
        this.refreshHistory()
        if (this.autoCollect) this.startPoll()
      })
    },
    startPoll() {
      this.stopPoll()
      if (!this.serverId || !this.autoCollect) return
      this.doCollect()
      this.timer = setInterval(() => {
        this.doCollect()
      }, POLL_MS)
    },
    stopPoll() {
      if (this.timer) {
        clearInterval(this.timer)
        this.timer = null
      }
    },
    async doCollect() {
      if (!this.serverId || this.collecting) return
      this.collecting = true
      try {
        const res = await collectMonitorServer(this.serverId)
        this.latest = (res && res.data) || null
        this.errorMsg = ''
        await this.refreshHistory(false)
      } catch (e) {
        this.errorMsg = (e && (e.msg || e.message)) || '采集失败'
      } finally {
        this.collecting = false
      }
    },
    async refreshHistory(showLoading = true) {
      if (!this.serverId) return
      try {
        const res = await getMonitorMetrics(this.serverId, { range: this.range })
        const data = (res && res.data) || {}
        this.items = data.items || []
        if (this.items.length && !this.latest) {
          this.latest = this.items[this.items.length - 1]
        }
        this.renderCharts()
      } catch (e) {
        if (showLoading) this.errorMsg = '历史数据加载失败'
      }
    },
    initCharts() {
      const map = [
        ['pct', 'chartPct'],
        ['load', 'chartLoad'],
        ['net', 'chartNet'],
        ['disk', 'chartDisk']
      ]
      map.forEach(([key, ref]) => {
        const el = this.$refs[ref]
        if (!el) return
        if (this.charts[key]) this.charts[key].dispose()
        this.charts[key] = echarts.init(el)
      })
    },
    resizeCharts() {
      Object.values(this.charts).forEach((c) => c && c.resize())
    },
    baseOption(legend, series) {
      const times = this.items.map((i) => i.collected_at)
      return {
        tooltip: { trigger: 'axis' },
        legend: { data: legend, bottom: 0 },
        grid: { left: 48, right: 24, top: 24, bottom: 48 },
        xAxis: { type: 'category', data: times, boundaryGap: false },
        yAxis: { type: 'value', scale: true },
        series
      }
    },
    renderCharts() {
      if (!this.charts.pct) this.initCharts()
      const line = (name, key, color) => ({
        name,
        type: 'line',
        showSymbol: false,
        smooth: true,
        data: this.items.map((i) => (i[key] == null ? null : Number(i[key]))),
        itemStyle: color ? { color } : undefined
      })
      if (this.charts.pct) {
        this.charts.pct.setOption(
          this.baseOption(
            ['CPU', '内存', '磁盘'],
            [
              line('CPU', 'cpu_percent', '#5470c6'),
              line('内存', 'mem_percent', '#91cc75'),
              line('磁盘', 'disk_percent', '#fac858')
            ]
          ),
          true
        )
      }
      if (this.charts.load) {
        this.charts.load.setOption(
          this.baseOption(
            ['Load1', 'Load5', 'Load15'],
            [
              line('Load1', 'load1'),
              line('Load5', 'load5'),
              line('Load15', 'load15')
            ]
          ),
          true
        )
      }
      if (this.charts.net) {
        this.charts.net.setOption(
          this.baseOption(
            ['收', '发'],
            [line('收', 'net_rx_bps', '#73c0de'), line('发', 'net_tx_bps', '#ee6666')]
          ),
          true
        )
      }
      if (this.charts.disk) {
        this.charts.disk.setOption(
          this.baseOption(
            ['读', '写'],
            [
              line('读', 'disk_read_bps', '#3ba272'),
              line('写', 'disk_write_bps', '#fc8452')
            ]
          ),
          true
        )
      }
    }
  }
}
</script>

<style scoped>
.page {
  padding: 4px 0;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.cards {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 8px;
}
.card {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px 14px;
}
.card-label {
  color: #909399;
  font-size: 12px;
  margin-bottom: 6px;
}
.card-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}
.meta {
  color: #909399;
  font-size: 12px;
  margin: 0 0 8px;
}
.error {
  color: #f56c6c;
  font-size: 13px;
  margin: 0 0 8px;
}
.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.chart-box {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px 12px 4px;
}
.chart-title {
  font-size: 13px;
  color: #606266;
  margin-bottom: 4px;
}
.chart {
  height: 260px;
  width: 100%;
}
@media (max-width: 1100px) {
  .cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .charts {
    grid-template-columns: 1fr;
  }
}
</style>
