const api = require('../../utils/api')

Page({
  data: {
    loading: true,
    results: [],
    switches: [],
    date: '',
    generatedAt: '',
    total: 0,
    filters: ['总计', '做多', '做空', '观望'],
    currentFilter: '总计',
    stats: { long: 0, short: 0, wait: 0 }
  },

  onLoad() {
    this.loadData()
  },

  onPullDownRefresh() {
    this.loadData().then(() => wx.stopPullDownRefresh())
  },

  async loadData() {
    this.setData({ loading: true })
    try {
      const res = await api.getResults(null, this.data.currentFilter)
      const stats = this.calcStats(res.results)
      // 提取时间部分（如 "2025-12-15 09:30" -> "09:30"）
      const generatedAt = res.generated_at && res.generated_at.includes(' ')
        ? res.generated_at.split(' ')[1] : ''
      this.setData({
        results: res.results,
        switches: res.switches || [],
        date: res.date,
        generatedAt,
        total: res.total,
        stats,
        loading: false
      })
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  calcStats(results) {
    return {
      long: results.filter(r => r.direction === '做多').length,
      short: results.filter(r => r.direction === '做空').length,
      wait: results.filter(r => r.direction === '观望').length
    }
  },

  onFilterTap(e) {
    const filter = e.currentTarget.dataset.filter
    if (filter === this.data.currentFilter) return
    this.setData({ currentFilter: filter })
    this.loadData()
  },

  onItemTap(e) {
    const contract = e.currentTarget.dataset.contract
    wx.navigateTo({ url: `/pages/detail/detail?contract=${contract}&date=${this.data.date}` })
  },

  getDirectionClass(direction) {
    if (direction === '做多') return 'tag-long'
    if (direction === '做空') return 'tag-short'
    return 'tag-wait'
  },

  getStatusIcon(status) {
    if (status === '主力') return '🔥'
    if (status === '移仓中') return '📦'
    return ''
  }
})

