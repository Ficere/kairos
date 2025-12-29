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
    stats: { long: 0, short: 0, wait: 0 },
    availableDates: [],
    selectedDateIndex: 0
  },

  onLoad() {
    this.loadDates()
  },

  onPullDownRefresh() {
    this.loadData().then(() => wx.stopPullDownRefresh())
  },

  async loadDates() {
    try {
      const res = await api.getDates()
      const dates = res.dates || []
      this.setData({ availableDates: dates })
      if (dates.length > 0) {
        this.setData({ date: dates[0] })
      }
      this.loadData()
    } catch (e) {
      this.loadData()
    }
  },

  async loadData() {
    this.setData({ loading: true })
    try {
      const res = await api.getResults(this.data.date, this.data.currentFilter)
      const stats = this.calcStats(res.results)
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

  onDateChange(e) {
    const index = e.detail.value
    const date = this.data.availableDates[index]
    this.setData({ date: date, selectedDateIndex: index })
    this.loadData()
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

